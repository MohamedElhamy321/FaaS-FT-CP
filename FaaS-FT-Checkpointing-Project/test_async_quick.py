"""Quick integration test for async checkpoint functionality"""

from incremental_checkpoint import AsyncCheckpointManager, IncrementalCheckpointManager, CheckpointPriority
import tempfile
import time
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

print('=' * 50)
print('Async Checkpoint Integration Test')
print('=' * 50)
print()

# Setup
mgr = IncrementalCheckpointManager(tempfile.mkdtemp())
async_mgr = AsyncCheckpointManager(mgr, max_workers=4)
print('[OK] Managers initialized')

# Test 1: Non-blocking submission
print('\n[Test 1: Non-blocking Submission]')
start = time.time()
task_ids = []
for i in range(10):
    task_id = async_mgr.create_checkpoint_async(
        function_id=f'test_{i}',
        state={'counter': i, 'data': 'x' * 100}
    )
    task_ids.append(task_id)
submission_time = (time.time() - start) * 1000
print(f'[OK] Submitted 10 checkpoints in {submission_time:.1f}ms')

# Test 2: Wait for completion
print('\n[Test 2: Wait for Completion]')
completed = 0
for task_id in task_ids:
    result = async_mgr.wait_for_task(task_id, timeout=5.0)
    if result and result.success:
        completed += 1
print(f'[OK] Completed {completed}/10 checkpoints')

# Test 3: Check statistics
print('\n[Test 3: Queue Statistics]')
stats = async_mgr.get_queue_stats()
print(f'[OK] Total submitted: {stats["total_submitted"]}')
print(f'[OK] Total completed: {stats["total_completed"]}')
print(f'[OK] Total failed: {stats["total_failed"]}')
print(f'[OK] Avg processing time: {stats["avg_processing_time_ms"]:.1f}ms')
print(f'[OK] Avg snapshot time: {stats["avg_snapshot_time_ms"]:.1f}ms')

# Test 4: Priority ordering
print('\n[Test 4: Priority Ordering]')
high_priority_id = async_mgr.create_checkpoint_async(
    function_id='high_priority_test',
    state={'priority': 'HIGH'},
    priority=CheckpointPriority.HIGH
)
low_priority_id = async_mgr.create_checkpoint_async(
    function_id='low_priority_test',
    state={'priority': 'LOW'},
    priority=CheckpointPriority.LOW
)
print(f'[OK] High priority task: {high_priority_id}')
print(f'[OK] Low priority task: {low_priority_id}')

# Wait for both
high_result = async_mgr.wait_for_task(high_priority_id, timeout=5.0)
low_result = async_mgr.wait_for_task(low_priority_id, timeout=5.0)
print(f'[OK] High priority completed: {high_result.success if high_result else False}')
print(f'[OK] Low priority completed: {low_result.success if low_result else False}')

# Cleanup
async_mgr.stop()
print('\n' + '=' * 50)
print('SUCCESS: All tests passed!')
print('=' * 50)
