"""
Example usage of StateChangeTracker
Demonstrates how to track state changes between checkpoints
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.state_tracker import StateChangeTracker


def example_basic_usage():
    """Basic usage example"""
    print("="*70)
    print("Example 1: Basic State Change Tracking")
    print("="*70)
    
    tracker = StateChangeTracker()
    
    # Initial state (checkpoint 1)
    state1 = {
        'request_count': 0,
        'active_connections': 0,
        'cache': {'user_123': 'data_abc'}
    }
    
    print("\nCheckpoint 1 - Initial State:")
    print(state1)
    tracker.update_baseline(state1)
    
    # State after some requests (checkpoint 2)
    state2 = {
        'request_count': 150,
        'active_connections': 5,
        'cache': {'user_123': 'data_abc', 'user_456': 'data_def'}
    }
    
    print("\nCheckpoint 2 - After 150 Requests:")
    print(state2)
    
    changes = tracker.track_changes(state2)
    print("\nDetected Changes:")
    for key, value in changes.items():
        print(f"  {key}: {value}")
    
    # Update baseline for next comparison
    tracker.update_baseline(state2)
    
    # State after more activity (checkpoint 3)
    state3 = {
        'request_count': 300,
        'active_connections': 3,
        'cache': {'user_456': 'data_def'}  # user_123 removed
    }
    
    print("\nCheckpoint 3 - After 300 Requests:")
    print(state3)
    
    changes = tracker.track_changes(state3)
    print("\nDetected Changes:")
    for key, value in changes.items():
        print(f"  {key}: {value}")
    
    # Get statistics
    stats = tracker.get_change_statistics()
    print("\nChange Statistics:")
    print(f"  Total changes: {stats['total_changes']}")
    print(f"  Unique keys changed: {stats['unique_keys_changed']}")
    print(f"  Changes by type: {stats['changes_by_type']}")


def example_serverless_function():
    """Example simulating serverless function state"""
    print("\n" + "="*70)
    print("Example 2: Serverless Function State Tracking")
    print("="*70)
    
    tracker = StateChangeTracker()
    
    # Function state at different execution points
    function_states = [
        {
            'execution_id': 'exec_001',
            'memory_used_mb': 128,
            'cpu_time_ms': 50,
            'variables': {'x': 10, 'y': 20, 'result': None}
        },
        {
            'execution_id': 'exec_001',
            'memory_used_mb': 256,
            'cpu_time_ms': 150,
            'variables': {'x': 10, 'y': 20, 'result': 30}
        },
        {
            'execution_id': 'exec_001',
            'memory_used_mb': 256,
            'cpu_time_ms': 200,
            'variables': {'x': 10, 'y': 20, 'result': 30, 'output': 'saved'}
        }
    ]
    
    for i, state in enumerate(function_states, 1):
        print(f"\n--- Checkpoint {i} ---")
        
        if i == 1:
            tracker.update_baseline(state)
            print("Baseline established")
        else:
            changes = tracker.track_changes(state)
            print(f"Changes detected: {len(changes)}")
            for key, value in changes.items():
                print(f"  {key}: {value}")
            tracker.update_baseline(state)


def example_performance_test():
    """Performance test with large state"""
    print("\n" + "="*70)
    print("Example 3: Performance Test with 10,000 Keys")
    print("="*70)
    
    import time
    
    tracker = StateChangeTracker()
    
    # Create large state
    large_state = {f'key_{i}': f'value_{i}' for i in range(10000)}
    
    print("\nCreating baseline with 10,000 keys...")
    start = time.time()
    tracker.update_baseline(large_state)
    elapsed = time.time() - start
    print(f"Baseline creation: {elapsed*1000:.2f}ms")
    
    # Modify 100 keys
    modified_state = large_state.copy()
    for i in range(0, 1000, 10):  # Modify every 10th key
        modified_state[f'key_{i}'] = f'modified_value_{i}'
    
    print("\nTracking changes (100 out of 10,000 keys modified)...")
    start = time.time()
    changes = tracker.track_changes(modified_state)
    elapsed = time.time() - start
    
    print(f"Change detection: {elapsed*1000:.2f}ms")
    print(f"Changes detected: {len(changes)}")
    print(f"Performance: {10000/elapsed:.0f} keys/second")
    
    # Get statistics
    stats = tracker.get_change_statistics()
    print(f"\nChange rate: {stats['change_rate']:.2f} changes/second")


def example_checkpoint_size_comparison():
    """Compare full vs incremental checkpoint sizes"""
    print("\n" + "="*70)
    print("Example 4: Full vs Incremental Checkpoint Size Comparison")
    print("="*70)
    
    import pickle
    
    tracker = StateChangeTracker()
    
    # Simulate application state
    state = {
        'users': {f'user_{i}': {'name': f'User {i}', 'balance': 1000} for i in range(100)},
        'transactions': [{'id': i, 'amount': 10} for i in range(500)],
        'config': {'timeout': 30, 'max_retries': 3, 'debug': False}
    }
    
    tracker.update_baseline(state)
    
    # Full checkpoint size
    full_checkpoint = pickle.dumps(state)
    full_size = len(full_checkpoint)
    print(f"\nFull checkpoint size: {full_size:,} bytes ({full_size/1024:.2f} KB)")
    
    # Make small changes
    modified_state = state.copy()
    modified_state['users']['user_5']['balance'] = 950  # Changed 1 user
    modified_state['config']['timeout'] = 60  # Changed 1 config value
    
    # Incremental checkpoint size
    changes = tracker.track_changes(modified_state)
    incremental_checkpoint = pickle.dumps(changes)
    incremental_size = len(incremental_checkpoint)
    print(f"Incremental checkpoint size: {incremental_size:,} bytes ({incremental_size/1024:.2f} KB)")
    
    # Calculate savings
    savings_percent = ((full_size - incremental_size) / full_size) * 100
    print(f"\nSize reduction: {savings_percent:.1f}%")
    print(f"Savings: {(full_size - incremental_size):,} bytes ({(full_size - incremental_size)/1024:.2f} KB)")
    
    print(f"\nChanges tracked:")
    for key in changes.keys():
        print(f"  - {key}")


def example_has_changes():
    """Demonstrate checking for changes without tracking"""
    print("\n" + "="*70)
    print("Example 5: Checking for Changes Without Tracking")
    print("="*70)
    
    tracker = StateChangeTracker()
    
    state1 = {'counter': 0, 'name': 'test'}
    tracker.update_baseline(state1)
    
    # Check without tracking
    state2 = {'counter': 0, 'name': 'test'}
    print(f"\nState unchanged: has_changes = {tracker.has_changes(state2)}")
    
    state3 = {'counter': 5, 'name': 'test'}
    print(f"State changed: has_changes = {tracker.has_changes(state3)}")
    
    # Demonstrate use case: only checkpoint when necessary
    print("\n--- Conditional Checkpointing ---")
    states = [
        {'counter': 0, 'name': 'test'},
        {'counter': 0, 'name': 'test'},  # No change
        {'counter': 5, 'name': 'test'},  # Changed
        {'counter': 5, 'name': 'test'},  # No change
    ]
    
    checkpoint_count = 0
    for i, state in enumerate(states, 1):
        if tracker.has_changes(state):
            checkpoint_count += 1
            print(f"State {i}: Creating checkpoint #{checkpoint_count}")
            tracker.track_changes(state)
            tracker.update_baseline(state)
        else:
            print(f"State {i}: Skipping checkpoint (no changes)")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("StateChangeTracker Examples")
    print("="*70)
    
    example_basic_usage()
    example_serverless_function()
    example_performance_test()
    example_checkpoint_size_comparison()
    example_has_changes()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
