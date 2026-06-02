"""
Production Readiness Module
Provides error handling, logging, monitoring, and backward compatibility
"""

import logging
import pickle
import time
import traceback
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class CheckpointErrorType(Enum):
    """Types of checkpoint errors."""
    CREATION_FAILED = "creation_failed"
    RESTORATION_FAILED = "restoration_failed"
    CORRUPTION_DETECTED = "corruption_detected"
    STORAGE_ERROR = "storage_error"
    COMPRESSION_ERROR = "compression_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class CheckpointError:
    """Represents a checkpoint error with context."""
    error_type: CheckpointErrorType
    message: str
    checkpoint_id: Optional[int] = None
    timestamp: float = 0.0
    stack_trace: Optional[str] = None
    recoverable: bool = True
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ErrorHandler:
    """
    Centralized error handling for checkpoint operations.
    
    Provides retry logic, fallback strategies, and error reporting.
    """
    
    def __init__(self, max_retries: int = 3, retry_delay_ms: float = 100):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            retry_delay_ms: Delay between retries in milliseconds
        """
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self.errors: list[CheckpointError] = []
        self.logger = logging.getLogger(__name__)
    
    def handle_checkpoint_creation_error(
        self,
        error: Exception,
        checkpoint_id: int,
        fallback_fn: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Handle checkpoint creation errors.
        
        Args:
            error: The exception that occurred
            checkpoint_id: ID of checkpoint being created
            fallback_fn: Optional fallback function to call
            
        Returns:
            Result from fallback function if provided, None otherwise
        """
        checkpoint_error = CheckpointError(
            error_type=CheckpointErrorType.CREATION_FAILED,
            message=str(error),
            checkpoint_id=checkpoint_id,
            stack_trace=traceback.format_exc(),
            recoverable=True
        )
        
        self.errors.append(checkpoint_error)
        self.logger.error(
            f"Checkpoint creation failed (ID: {checkpoint_id}): {error}",
            exc_info=True
        )
        
        if fallback_fn:
            try:
                return fallback_fn()
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {fallback_error}")
        
        return None
    
    def handle_restoration_error(
        self,
        error: Exception,
        checkpoint_id: int,
        fallback_checkpoint_id: Optional[int] = None
    ) -> Optional[int]:
        """
        Handle restoration errors.
        
        Args:
            error: The exception that occurred
            checkpoint_id: ID of checkpoint that failed to restore
            fallback_checkpoint_id: Optional fallback checkpoint ID
            
        Returns:
            Fallback checkpoint ID if provided, None otherwise
        """
        checkpoint_error = CheckpointError(
            error_type=CheckpointErrorType.RESTORATION_FAILED,
            message=str(error),
            checkpoint_id=checkpoint_id,
            stack_trace=traceback.format_exc(),
            recoverable=fallback_checkpoint_id is not None
        )
        
        self.errors.append(checkpoint_error)
        self.logger.error(
            f"Restoration failed (ID: {checkpoint_id}): {error}",
            exc_info=True
        )
        
        if fallback_checkpoint_id:
            self.logger.info(f"Attempting fallback to checkpoint {fallback_checkpoint_id}")
            return fallback_checkpoint_id
        
        return None
    
    def retry_operation(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry an operation with exponential backoff.
        
        Args:
            operation: Function to execute
            operation_name: Name for logging
            *args, **kwargs: Arguments for operation
            
        Returns:
            Result from operation
            
        Raises:
            Exception: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay_ms * (2 ** attempt) / 1000
                    time.sleep(delay)
        
        # All retries failed
        self.logger.error(f"{operation_name} failed after {self.max_retries} attempts")
        raise last_error
    
    def get_recent_errors(self, count: int = 10) -> list[CheckpointError]:
        """Get recent errors."""
        return self.errors[-count:]
    
    def clear_errors(self):
        """Clear error history."""
        self.errors.clear()


class BackwardCompatibility:
    """
    Handles backward compatibility with legacy checkpoint formats.
    
    Provides migration and conversion utilities.
    """
    
    @staticmethod
    def is_legacy_checkpoint(checkpoint_data: Any) -> bool:
        """
        Check if checkpoint is in legacy format.
        
        Args:
            checkpoint_data: Checkpoint data to check
            
        Returns:
            True if legacy format
        """
        if isinstance(checkpoint_data, dict):
            # Legacy format typically has 'checkpoint_id', 'timestamp', 'state'
            legacy_keys = {'checkpoint_id', 'timestamp', 'state'}
            return legacy_keys.issubset(checkpoint_data.keys())
        return False
    
    @staticmethod
    def convert_from_legacy(legacy_checkpoint: dict) -> dict:
        """
        Convert legacy checkpoint to new incremental format.
        
        Args:
            legacy_checkpoint: Legacy checkpoint data
            
        Returns:
            Converted checkpoint in new format
        """
        from incremental_checkpoint.storage import IncrementalCheckpoint
        import zlib
        
        # Extract legacy data
        checkpoint_id = legacy_checkpoint.get('checkpoint_id', 1)
        timestamp = legacy_checkpoint.get('timestamp', time.time())
        state = legacy_checkpoint.get('state', {})
        
        # Convert to full checkpoint in new format
        serialized = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(serialized, level=6)
        
        new_checkpoint = IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=True,
            timestamp=timestamp,
            base_checkpoint_id=None,
            data=compressed,
            metadata={
                'type': 'full',
                'converted_from_legacy': True,
                'original_format': 'legacy_full',
                'state_size_bytes': len(serialized),
                'compressed_size_bytes': len(compressed)
            }
        )
        
        return new_checkpoint
    
    @staticmethod
    def convert_to_legacy(incremental_checkpoint) -> dict:
        """
        Convert incremental checkpoint to legacy format.
        
        Args:
            incremental_checkpoint: New format checkpoint
            
        Returns:
            Legacy format checkpoint
        """
        import zlib
        
        # Decompress and deserialize
        decompressed = zlib.decompress(incremental_checkpoint.data)
        state = pickle.loads(decompressed)
        
        # Convert to legacy format
        legacy_checkpoint = {
            'checkpoint_id': incremental_checkpoint.checkpoint_id,
            'timestamp': incremental_checkpoint.timestamp,
            'state': state,
            'metadata': {
                'converted_from_incremental': True,
                'was_full_checkpoint': incremental_checkpoint.is_full
            }
        }
        
        return legacy_checkpoint


class ProductionLogger:
    """
    Production-grade logging for checkpoint operations.
    
    Provides structured logging with different levels and formats.
    """
    
    def __init__(self, name: str = "incremental_checkpoint", level: int = logging.INFO):
        """
        Initialize production logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            
            self.logger.addHandler(handler)
    
    def log_checkpoint_created(self, checkpoint_id: int, is_full: bool, size_bytes: int):
        """Log successful checkpoint creation."""
        checkpoint_type = "FULL" if is_full else "INCR"
        self.logger.info(
            f"Checkpoint created: ID={checkpoint_id}, Type={checkpoint_type}, Size={size_bytes}B"
        )
    
    def log_checkpoint_restored(self, checkpoint_id: int, restoration_time_ms: float):
        """Log successful checkpoint restoration."""
        self.logger.info(
            f"Checkpoint restored: ID={checkpoint_id}, Time={restoration_time_ms:.2f}ms"
        )
    
    def log_performance_warning(self, operation: str, time_ms: float, threshold_ms: float):
        """Log performance warning."""
        self.logger.warning(
            f"Performance warning: {operation} took {time_ms:.2f}ms (threshold: {threshold_ms}ms)"
        )
    
    def log_cleanup(self, deleted_count: int, kept_count: int):
        """Log cleanup operation."""
        self.logger.info(
            f"Cleanup completed: Deleted {deleted_count} checkpoints, Kept {kept_count}"
        )
    
    def log_error(self, error_type: str, message: str, checkpoint_id: Optional[int] = None):
        """Log error."""
        if checkpoint_id:
            self.logger.error(f"Error ({error_type}) for checkpoint {checkpoint_id}: {message}")
        else:
            self.logger.error(f"Error ({error_type}): {message}")


class HealthChecker:
    """
    Health checking for checkpoint system.
    
    Monitors system health and detects issues.
    """
    
    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, bool] = {}
        self.last_check_time = 0.0
    
    def check_storage_health(self, storage_manager) -> bool:
        """
        Check storage system health.
        
        Args:
            storage_manager: Storage manager to check
            
        Returns:
            True if healthy
        """
        try:
            # Try to list checkpoints
            checkpoints = storage_manager.list_checkpoints()
            
            # Verify index integrity
            for cp_info in checkpoints[:5]:  # Check first 5
                checkpoint_id = cp_info['checkpoint_id']
                storage_manager.load_checkpoint(checkpoint_id)
            
            self.checks['storage'] = True
            return True
        except Exception as e:
            self.checks['storage'] = False
            logging.error(f"Storage health check failed: {e}")
            return False
    
    def check_compression_health(self, compressor) -> bool:
        """
        Check compressor health.
        
        Args:
            compressor: Compressor to check
            
        Returns:
            True if healthy
        """
        try:
            # Test compression/decompression round-trip
            test_data = {'test_key': 'test_value' * 100}
            compressed = compressor.compress_delta(test_data)
            decompressed = compressor.decompress_delta(compressed)
            
            if test_data == decompressed:
                self.checks['compression'] = True
                return True
            else:
                self.checks['compression'] = False
                return False
        except Exception as e:
            self.checks['compression'] = False
            logging.error(f"Compression health check failed: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status.
        
        Returns:
            Health status dictionary
        """
        all_healthy = all(self.checks.values()) if self.checks else False
        
        return {
            'healthy': all_healthy,
            'checks': self.checks.copy(),
            'last_check_time': self.last_check_time,
            'status': 'healthy' if all_healthy else 'degraded'
        }
    
    def run_all_checks(self, manager) -> Dict[str, Any]:
        """
        Run all health checks.
        
        Args:
            manager: Checkpoint manager to check
            
        Returns:
            Health status
        """
        self.last_check_time = time.time()
        
        self.check_storage_health(manager.storage_manager)
        self.check_compression_health(manager.delta_compressor)
        
        return self.get_health_status()
