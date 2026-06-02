"""
Asynchronous Checkpoint Manager
Implements non-blocking checkpoint operations with background processing
"""

import asyncio
import threading
import time
import copy
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue, PriorityQueue, Empty
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import logging

from .storage import IncrementalCheckpoint

logger = logging.getLogger(__name__)


class CheckpointPriority(Enum):
    """Priority levels for checkpoint operations"""
    CRITICAL = 0  # Immediate checkpoint (e.g., before shutdown)
    HIGH = 1      # User-initiated or scheduled
    NORMAL = 2    # Regular automatic checkpoints
    LOW = 3       # Background optimization checkpoints


@dataclass(order=True)
class CheckpointTask:
    """Represents a checkpoint task in the queue"""
    priority: int
    timestamp: float = field(compare=False)
    function_id: str = field(compare=False)
    state: Dict[str, Any] = field(compare=False)
    checkpoint_type: str = field(compare=False, default="auto")
    callback: Optional[Callable] = field(compare=False, default=None)
    task_id: str = field(compare=False, default="")
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"{self.function_id}_{self.timestamp}"


@dataclass
class AsyncCheckpointResult:
    """Result of an async checkpoint operation"""
    task_id: str
    checkpoint_id: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0
    checkpoint_size_bytes: int = 0
    is_complete: bool = False
    state_snapshot_time_ms: float = 0.0
    processing_time_ms: float = 0.0


class AsyncCheckpointManager:
    """
    Manages asynchronous checkpoint operations with non-blocking interface.
    
    Key Features:
    - Non-blocking checkpoint creation (returns immediately)
    - Background processing with thread pool
    - Copy-on-write state snapshots
    - Priority-based queue management
    - Backpressure handling
    - Comprehensive error handling and retries
    """
    
    def __init__(
        self,
        base_manager: IncrementalCheckpoint,
        max_workers: int = 4,
        max_queue_size: int = 100,
        enable_copy_on_write: bool = True,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 1.0
    ):
        """
        Initialize async checkpoint manager.
        
        Args:
            base_manager: Underlying checkpoint manager (incremental or base)
            max_workers: Number of worker threads for processing
            max_queue_size: Maximum checkpoint queue size (backpressure limit)
            enable_copy_on_write: Enable copy-on-write for state snapshots
            retry_attempts: Number of retry attempts for failed checkpoints
            retry_delay_seconds: Delay between retry attempts
        """
        self.base_manager = base_manager
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.enable_copy_on_write = enable_copy_on_write
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds
        
        # Processing infrastructure
        self.checkpoint_queue = PriorityQueue(maxsize=max_queue_size)
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="checkpoint_worker"
        )
        
        # Result tracking
        self.pending_tasks: Dict[str, Future] = {}
        self.completed_tasks: Dict[str, AsyncCheckpointResult] = {}
        self.task_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retries': 0,
            'queue_full_rejections': 0,
            'avg_snapshot_time_ms': 0.0,
            'avg_processing_time_ms': 0.0
        }
        self.stats_lock = threading.Lock()
        
        # Control flags
        self._running = False
        self._shutdown = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Start background worker
        self.start()
    
    def start(self):
        """Start the async processing worker thread"""
        if self._running:
            logger.warning("Async checkpoint manager already running")
            return
        
        self._running = True
        self._shutdown = False
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            name="checkpoint_queue_processor",
            daemon=True
        )
        self._worker_thread.start()
        logger.info(f"Async checkpoint manager started with {self.max_workers} workers")
    
    def stop(self, timeout: float = 30.0):
        """
        Stop the async processing and wait for pending tasks.
        
        Args:
            timeout: Maximum time to wait for pending tasks (seconds)
        """
        logger.info("Stopping async checkpoint manager...")
        self._shutdown = True
        
        # Wait for worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
        
        # Shutdown executor
        self.executor.shutdown(wait=True, cancel_futures=False)
        self._running = False
        logger.info("Async checkpoint manager stopped")
    
    def create_checkpoint_async(
        self,
        function_id: str,
        state: Dict[str, Any],
        priority: CheckpointPriority = CheckpointPriority.NORMAL,
        callback: Optional[Callable[[AsyncCheckpointResult], None]] = None
    ) -> str:
        """
        Create a checkpoint asynchronously (non-blocking).
        
        Args:
            function_id: Function identifier
            state: Application state to checkpoint
            priority: Priority level for this checkpoint
            callback: Optional callback when checkpoint completes
        
        Returns:
            task_id: Unique task identifier for tracking
        
        Raises:
            RuntimeError: If queue is full (backpressure)
        """
        if self._shutdown:
            raise RuntimeError("Async checkpoint manager is shutting down")
        
        # Create snapshot immediately (minimal blocking)
        snapshot_start = time.time()
        state_snapshot = self._create_state_snapshot(state)
        snapshot_duration_ms = (time.time() - snapshot_start) * 1000
        
        # Create task
        task = CheckpointTask(
            priority=priority.value,
            timestamp=time.time(),
            function_id=function_id,
            state=state_snapshot,
            callback=callback
        )
        
        # Try to enqueue (non-blocking)
        try:
            self.checkpoint_queue.put_nowait(task)
            
            with self.stats_lock:
                self.stats['total_submitted'] += 1
                # Update running average
                n = self.stats['total_submitted']
                avg = self.stats['avg_snapshot_time_ms']
                self.stats['avg_snapshot_time_ms'] = (avg * (n - 1) + snapshot_duration_ms) / n
            
            logger.debug(
                f"Checkpoint task queued: {task.task_id} "
                f"(priority={priority.name}, snapshot={snapshot_duration_ms:.1f}ms)"
            )
            return task.task_id
            
        except Exception as e:
            with self.stats_lock:
                self.stats['queue_full_rejections'] += 1
            
            logger.error(f"Queue full, rejecting checkpoint task: {e}")
            raise RuntimeError(
                f"Checkpoint queue full ({self.max_queue_size}). "
                "System is under heavy load. Try again later."
            )
    
    def _create_state_snapshot(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a snapshot of the state using copy-on-write if enabled.
        
        Args:
            state: Original state dictionary
        
        Returns:
            State snapshot (deep copy or reference)
        """
        if self.enable_copy_on_write:
            # Deep copy to prevent modifications during async processing
            # In production, could use more efficient COW mechanisms
            return copy.deepcopy(state)
        else:
            # Shallow copy (faster but risky if state is modified)
            return dict(state)
    
    def _process_queue(self):
        """Background thread that processes checkpoint queue"""
        logger.info("Checkpoint queue processor started")
        
        while not self._shutdown or not self.checkpoint_queue.empty():
            try:
                # Get task with timeout to check shutdown flag
                task = self.checkpoint_queue.get(timeout=1.0)
                
                # Submit to thread pool for processing
                future = self.executor.submit(self._process_checkpoint_task, task)
                
                with self.task_lock:
                    self.pending_tasks[task.task_id] = future
                
                # Cleanup completed tasks
                self._cleanup_completed_tasks()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error in queue processor: {e}", exc_info=True)
        
        logger.info("Checkpoint queue processor stopped")
    
    def _process_checkpoint_task(self, task: CheckpointTask) -> AsyncCheckpointResult:
        """
        Process a checkpoint task in a worker thread.
        
        Args:
            task: Checkpoint task to process
        
        Returns:
            Result of checkpoint operation
        """
        processing_start = time.time()
        result = AsyncCheckpointResult(task_id=task.task_id)
        
        # Retry logic
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                # Create checkpoint using base manager
                # Adapt to the actual API: create_checkpoint(application_state)
                checkpoint_start = time.time()
                checkpoint = self.base_manager.create_checkpoint(task.state)
                checkpoint_duration = time.time() - checkpoint_start
                
                # Get checkpoint ID - adapting to different possible return types
                if hasattr(checkpoint, 'checkpoint_id'):
                    checkpoint_id = checkpoint.checkpoint_id
                else:
                    checkpoint_id = str(checkpoint)
                
                # Get checkpoint info - handle different manager types
                try:
                    checkpoint_info = self.base_manager.get_checkpoint_info(checkpoint_id)
                except (AttributeError, TypeError):
                    checkpoint_info = {'size_bytes': 0}
                
                # Success
                result.checkpoint_id = checkpoint_id
                result.success = True
                result.processing_time_ms = checkpoint_duration * 1000
                result.checkpoint_size_bytes = checkpoint_info.get('size_bytes', 0)
                result.is_complete = True
                
                logger.debug(
                    f"Checkpoint created: {checkpoint_id} "
                    f"(task={task.task_id}, duration={checkpoint_duration*1000:.1f}ms)"
                )
                
                break  # Success, exit retry loop
                
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Checkpoint creation failed (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                
                with self.stats_lock:
                    self.stats['total_retries'] += 1
                
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
        
        # Handle final result
        if not result.success:
            result.error = last_error
            logger.error(f"Checkpoint failed after {self.retry_attempts} attempts: {last_error}")
            
            with self.stats_lock:
                self.stats['total_failed'] += 1
        else:
            with self.stats_lock:
                self.stats['total_completed'] += 1
                # Update processing time average
                n = self.stats['total_completed']
                avg = self.stats['avg_processing_time_ms']
                self.stats['avg_processing_time_ms'] = (
                    avg * (n - 1) + result.processing_time_ms
                ) / n
        
        # Total duration
        result.duration_ms = (time.time() - processing_start) * 1000
        
        # Store result
        with self.task_lock:
            self.completed_tasks[task.task_id] = result
            if task.task_id in self.pending_tasks:
                del self.pending_tasks[task.task_id]
        
        # Execute callback if provided
        if task.callback:
            try:
                task.callback(result)
            except Exception as e:
                logger.error(f"Callback error for task {task.task_id}: {e}", exc_info=True)
        
        return result
    
    def _cleanup_completed_tasks(self, max_age_seconds: float = 300.0):
        """
        Clean up old completed tasks to prevent memory growth.
        
        Args:
            max_age_seconds: Maximum age of completed tasks to keep
        """
        current_time = time.time()
        
        with self.task_lock:
            tasks_to_remove = []
            for task_id, result in self.completed_tasks.items():
                task_age = current_time - (result.duration_ms / 1000)
                if task_age > max_age_seconds:
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.completed_tasks[task_id]
            
            if tasks_to_remove:
                logger.debug(f"Cleaned up {len(tasks_to_remove)} old completed tasks")
    
    def get_task_status(self, task_id: str) -> Optional[AsyncCheckpointResult]:
        """
        Get the status of a checkpoint task.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Result if available, None if task not found or still pending
        """
        with self.task_lock:
            # Check completed tasks
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            
            # Check if still pending
            if task_id in self.pending_tasks:
                future = self.pending_tasks[task_id]
                if future.done():
                    try:
                        result = future.result()
                        self.completed_tasks[task_id] = result
                        del self.pending_tasks[task_id]
                        return result
                    except Exception as e:
                        logger.error(f"Error getting future result: {e}")
                        return None
                else:
                    # Still processing
                    return AsyncCheckpointResult(
                        task_id=task_id,
                        is_complete=False
                    )
            
            return None
    
    def wait_for_task(self, task_id: str, timeout: float = 30.0) -> Optional[AsyncCheckpointResult]:
        """
        Wait for a task to complete (blocking).
        
        Args:
            task_id: Task identifier
            timeout: Maximum time to wait (seconds)
        
        Returns:
            Result when complete, None if timeout
        """
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            result = self.get_task_status(task_id)
            if result and result.is_complete:
                return result
            time.sleep(0.1)
        
        logger.warning(f"Timeout waiting for task {task_id}")
        return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue and processing statistics"""
        with self.task_lock:
            pending_count = len(self.pending_tasks)
            completed_count = len(self.completed_tasks)
        
        with self.stats_lock:
            stats = dict(self.stats)
        
        stats.update({
            'queue_size': self.checkpoint_queue.qsize(),
            'queue_max_size': self.max_queue_size,
            'pending_tasks': pending_count,
            'completed_tasks_cached': completed_count,
            'worker_threads': self.max_workers,
            'is_running': self._running
        })
        
        return stats
    
    def create_checkpoint_sync(
        self,
        function_id: str,
        state: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[str]:
        """
        Create checkpoint and wait for completion (blocking).
        Convenience method for synchronous behavior.
        
        Args:
            function_id: Function identifier
            state: Application state
            timeout: Maximum time to wait
        
        Returns:
            Checkpoint ID if successful, None otherwise
        """
        task_id = self.create_checkpoint_async(
            function_id=function_id,
            state=state,
            priority=CheckpointPriority.HIGH
        )
        
        result = self.wait_for_task(task_id, timeout=timeout)
        
        if result and result.success:
            return result.checkpoint_id
        
        return None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.stop()
        return False
