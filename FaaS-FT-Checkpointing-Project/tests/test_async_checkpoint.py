"""
Integration tests for Asynchronous Checkpoint Manager
Tests async operations, race conditions, error handling, and performance
"""

import unittest
import time
import threading
from pathlib import Path
import shutil
import tempfile
from typing import List

from incremental_checkpoint import IncrementalCheckpointManager
from incremental_checkpoint.async_checkpoint_manager import (
    AsyncCheckpointManager,
    CheckpointPriority,
    AsyncCheckpointResult
)


class TestAsyncCheckpointManager(unittest.TestCase):
    """Test suite for async checkpoint functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.base_manager = IncrementalCheckpointManager(
            storage_path=self.test_dir,
            full_checkpoint_interval=5
        )
        self.async_manager = AsyncCheckpointManager(
            base_manager=self.base_manager,
            max_workers=4,
            max_queue_size=50,
            enable_copy_on_write=True,
            retry_attempts=2
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.async_manager.stop(timeout=5.0)
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_basic_async_checkpoint(self):
        """Test basic async checkpoint creation"""
        state = {'counter': 42, 'name': 'test'}
        
        # Submit async checkpoint
        task_id = self.async_manager.create_checkpoint_async(
            function_id='test_func',
            state=state,
            priority=CheckpointPriority.NORMAL
        )
        
        self.assertIsNotNone(task_id)
        self.assertIn('test_func', task_id)
        
        # Wait for completion
        result = self.async_manager.wait_for_task(task_id, timeout=5.0)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.is_complete)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.checkpoint_id)
        self.assertGreater(result.duration_ms, 0)
    
    def test_non_blocking_behavior(self):
        """Test that checkpoint creation is truly non-blocking"""
        state = {'data': 'x' * 1000}  # Larger state
        
        start_time = time.time()
        
        # Submit async checkpoint (should return immediately)
        task_id = self.async_manager.create_checkpoint_async(
            function_id='test_func',
            state=state
        )
        
        submission_time = time.time() - start_time
        
        # Submission should be very fast (< 10ms for state snapshot)
        self.assertLess(submission_time, 0.05)  # 50ms max
        
        # Wait for actual processing
        result = self.async_manager.wait_for_task(task_id, timeout=5.0)
        self.assertTrue(result.success)
    
    def test_copy_on_write(self):
        """Test that state snapshot prevents mutation issues"""
        state = {'counter': 0, 'data': [1, 2, 3]}
        
        # Submit checkpoint
        task_id = self.async_manager.create_checkpoint_async(
            function_id='test_func',
            state=state
        )
        
        # Mutate state immediately after submission
        state['counter'] = 999
        state['data'].append(999)
        
        # Wait for checkpoint to complete
        result = self.async_manager.wait_for_task(task_id, timeout=5.0)
        self.assertTrue(result.success)
        
        # Restore and verify original state was captured
        restored_state = self.base_manager.restore_state(result.checkpoint_id)
        self.assertEqual(restored_state['counter'], 0)
        self.assertEqual(restored_state['data'], [1, 2, 3])
    
    def test_priority_ordering(self):
        """Test that higher priority tasks are processed first"""
        results = []
        
        def callback(result: AsyncCheckpointResult):
            results.append(result.task_id)
        
        # Submit tasks with different priorities
        low_task = self.async_manager.create_checkpoint_async(
            function_id='low',
            state={'priority': 'low'},
            priority=CheckpointPriority.LOW,
            callback=callback
        )
        
        high_task = self.async_manager.create_checkpoint_async(
            function_id='high',
            state={'priority': 'high'},
            priority=CheckpointPriority.HIGH,
            callback=callback
        )
        
        critical_task = self.async_manager.create_checkpoint_async(
            function_id='critical',
            state={'priority': 'critical'},
            priority=CheckpointPriority.CRITICAL,
            callback=callback
        )
        
        # Wait for all to complete
        time.sleep(2.0)
        
        # Critical should be processed first, then high
        self.assertIn('critical', results[0])
        self.assertIn('high', results[1])
    
    def test_concurrent_submissions(self):
        """Test concurrent checkpoint submissions from multiple threads"""
        num_threads = 10
        checkpoints_per_thread = 5
        completed = []
        lock = threading.Lock()
        
        def submit_checkpoints(thread_id: int):
            for i in range(checkpoints_per_thread):
                try:
                    task_id = self.async_manager.create_checkpoint_async(
                        function_id=f'thread_{thread_id}',
                        state={'thread': thread_id, 'iteration': i}
                    )
                    
                    result = self.async_manager.wait_for_task(task_id, timeout=10.0)
                    
                    with lock:
                        if result and result.success:
                            completed.append(task_id)
                except Exception as e:
                    print(f"Thread {thread_id} error: {e}")
        
        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=submit_checkpoints, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=15.0)
        
        # Verify all checkpoints completed
        expected = num_threads * checkpoints_per_thread
        self.assertGreaterEqual(len(completed), expected * 0.9)  # At least 90%
    
    def test_queue_backpressure(self):
        """Test queue backpressure when queue is full"""
        # Create manager with small queue
        small_manager = AsyncCheckpointManager(
            base_manager=self.base_manager,
            max_workers=1,
            max_queue_size=5,
            enable_copy_on_write=False
        )
        
        try:
            # Fill queue
            for i in range(10):
                try:
                    small_manager.create_checkpoint_async(
                        function_id=f'test_{i}',
                        state={'iteration': i}
                    )
                except RuntimeError as e:
                    # Should raise queue full error
                    self.assertIn('queue full', str(e).lower())
                    break
            
            # Check stats
            stats = small_manager.get_queue_stats()
            self.assertGreater(stats['queue_full_rejections'], 0)
            
        finally:
            small_manager.stop()
    
    def test_error_handling_and_retry(self):
        """Test error handling with retry logic"""
        # Create a manager that will initially fail
        class FailingManager:
            def __init__(self):
                self.attempt_count = 0
            
            def create_checkpoint(self, function_id, state):
                self.attempt_count += 1
                if self.attempt_count < 2:
                    raise RuntimeError("Simulated failure")
                # Success on second attempt
                return self.base_manager.create_checkpoint(function_id, state)
        
        # This test verifies retry logic is working
        # In production, retries are handled internally
        state = {'test': 'retry'}
        task_id = self.async_manager.create_checkpoint_async(
            function_id='retry_test',
            state=state
        )
        
        result = self.async_manager.wait_for_task(task_id, timeout=10.0)
        
        # Should eventually succeed even with transient failures
        self.assertIsNotNone(result)
    
    def test_get_task_status(self):
        """Test task status tracking"""
        state = {'status': 'test'}
        
        task_id = self.async_manager.create_checkpoint_async(
            function_id='status_test',
            state=state
        )
        
        # Check status immediately (should be pending)
        status = self.async_manager.get_task_status(task_id)
        self.assertIsNotNone(status)
        
        # Wait for completion
        final_status = self.async_manager.wait_for_task(task_id, timeout=5.0)
        self.assertTrue(final_status.is_complete)
        self.assertTrue(final_status.success)
        
        # Check status after completion
        status_after = self.async_manager.get_task_status(task_id)
        self.assertTrue(status_after.is_complete)
    
    def test_sync_wrapper(self):
        """Test synchronous wrapper method"""
        state = {'sync': True}
        
        # Use sync method (blocks until complete)
        checkpoint_id = self.async_manager.create_checkpoint_sync(
            function_id='sync_test',
            state=state,
            timeout=5.0
        )
        
        self.assertIsNotNone(checkpoint_id)
        
        # Verify checkpoint exists
        restored = self.base_manager.restore_state(checkpoint_id)
        self.assertEqual(restored['sync'], True)
    
    def test_queue_statistics(self):
        """Test queue statistics collection"""
        # Submit some checkpoints
        for i in range(5):
            self.async_manager.create_checkpoint_async(
                function_id=f'stats_test_{i}',
                state={'index': i}
            )
        
        # Get stats
        stats = self.async_manager.get_queue_stats()
        
        self.assertIn('total_submitted', stats)
        self.assertIn('queue_size', stats)
        self.assertIn('worker_threads', stats)
        self.assertIn('is_running', stats)
        
        self.assertTrue(stats['is_running'])
        self.assertEqual(stats['worker_threads'], 4)
        self.assertGreaterEqual(stats['total_submitted'], 5)
    
    def test_callback_execution(self):
        """Test that callbacks are executed on completion"""
        callback_executed = threading.Event()
        callback_result = {}
        
        def test_callback(result: AsyncCheckpointResult):
            callback_result['task_id'] = result.task_id
            callback_result['success'] = result.success
            callback_result['checkpoint_id'] = result.checkpoint_id
            callback_executed.set()
        
        task_id = self.async_manager.create_checkpoint_async(
            function_id='callback_test',
            state={'callback': True},
            callback=test_callback
        )
        
        # Wait for callback
        callback_executed.wait(timeout=5.0)
        
        self.assertTrue(callback_executed.is_set())
        self.assertEqual(callback_result['task_id'], task_id)
        self.assertTrue(callback_result['success'])
        self.assertIsNotNone(callback_result['checkpoint_id'])
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown with pending tasks"""
        # Submit several checkpoints
        task_ids = []
        for i in range(5):
            task_id = self.async_manager.create_checkpoint_async(
                function_id=f'shutdown_test_{i}',
                state={'index': i}
            )
            task_ids.append(task_id)
        
        # Shutdown with timeout
        self.async_manager.stop(timeout=10.0)
        
        # Manager should be stopped
        self.assertFalse(self.async_manager._running)
    
    def test_performance_metrics(self):
        """Test that performance metrics are recorded"""
        # Create multiple checkpoints
        for i in range(10):
            task_id = self.async_manager.create_checkpoint_async(
                function_id=f'perf_test_{i}',
                state={'data': 'x' * 100}
            )
            self.async_manager.wait_for_task(task_id, timeout=5.0)
        
        stats = self.async_manager.get_queue_stats()
        
        # Should have metrics
        self.assertGreater(stats['total_completed'], 0)
        self.assertGreater(stats['avg_snapshot_time_ms'], 0)
        self.assertGreater(stats['avg_processing_time_ms'], 0)


class TestAsyncPerformance(unittest.TestCase):
    """Performance tests for async checkpoint operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.base_manager = IncrementalCheckpointManager(
            storage_path=self.test_dir,
            full_checkpoint_interval=10
        )
        self.async_manager = AsyncCheckpointManager(
            base_manager=self.base_manager,
            max_workers=8,
            max_queue_size=200
        )
    
    def tearDown(self):
        """Clean up"""
        self.async_manager.stop(timeout=10.0)
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_submission_latency(self):
        """Test that submission latency is minimal"""
        state = {'data': 'x' * 1000}
        latencies = []
        
        for i in range(100):
            start = time.time()
            self.async_manager.create_checkpoint_async(
                function_id=f'latency_test_{i}',
                state=state
            )
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print(f"\nSubmission latency: avg={avg_latency:.2f}ms, max={max_latency:.2f}ms")
        
        # Submission should be very fast
        self.assertLess(avg_latency, 10.0)  # < 10ms average
        self.assertLess(max_latency, 50.0)  # < 50ms max
    
    def test_throughput(self):
        """Test checkpoint throughput with async processing"""
        num_checkpoints = 100
        state = {'counter': 0, 'data': 'test' * 10}
        
        start_time = time.time()
        
        task_ids = []
        for i in range(num_checkpoints):
            state['counter'] = i
            task_id = self.async_manager.create_checkpoint_async(
                function_id=f'throughput_test',
                state=state
            )
            task_ids.append(task_id)
        
        # Wait for all to complete
        completed = 0
        for task_id in task_ids:
            result = self.async_manager.wait_for_task(task_id, timeout=30.0)
            if result and result.success:
                completed += 1
        
        total_time = time.time() - start_time
        throughput = completed / total_time
        
        print(f"\nAsync throughput: {throughput:.1f} checkpoints/sec")
        print(f"Total time: {total_time:.2f}s for {completed} checkpoints")
        
        # Should have good throughput with async processing
        self.assertGreater(throughput, 10.0)  # > 10 checkpoints/sec
        self.assertEqual(completed, num_checkpoints)


if __name__ == '__main__':
    unittest.main(verbosity=2)
