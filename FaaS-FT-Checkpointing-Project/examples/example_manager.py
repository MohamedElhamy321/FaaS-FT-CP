"""
Example usage of Incremental Checkpoint Manager
Demonstrates complete end-to-end incremental checkpointing
"""

import sys
import os
import time
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.manager import IncrementalCheckpointManager, ConditionalCheckpointManager


def example_basic_usage():
    """Basic end-to-end checkpoint management"""
    print("="*70)
    print("Example 1: Basic Checkpoint Management")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        # Initialize manager
        manager = IncrementalCheckpointManager(
            storage_path=storage_path,
            full_checkpoint_interval=5
        )
        
        print("\nCreating checkpoints...")
        
        # Simulate application state over time
        state = {
            'request_count': 0,
            'active_users': 0,
            'cache': {},
            'config': {'timeout': 30}
        }
        
        # Create 10 checkpoints with evolving state
        for i in range(1, 11):
            state['request_count'] += 100
            state['active_users'] = i * 5
            state['cache'][f'key_{i}'] = f'data_{i}'
            
            checkpoint = manager.create_checkpoint(state)
            
            cp_type = "FULL" if checkpoint.is_full else "INCR"
            print(f"  Checkpoint {checkpoint.checkpoint_id:2d} [{cp_type}]: {checkpoint.get_size():5d} bytes")
        
        # Get statistics
        print("\n" + "-"*70)
        print("Statistics:")
        stats = manager.get_statistics()
        print(f"  Total checkpoints: {stats['total_checkpoints']}")
        print(f"  Full: {stats['full_checkpoints']}, Incremental: {stats['incremental_checkpoints']}")
        print(f"  Total storage: {stats['total_storage_mb']:.2f} MB")
        print(f"  Compression ratio: {stats['compression_ratio']:.2f}x")
        print(f"  Size reduction: {stats['size_reduction_vs_full']:.2f}x")
        
        # Restore from checkpoint
        print("\n" + "-"*70)
        print("Restoring from checkpoint 10...")
        restored_state = manager.restore_from_checkpoint(10)
        
        print(f"  Request count: {restored_state['request_count']}")
        print(f"  Active users: {restored_state['active_users']}")
        print(f"  Cache entries: {len(restored_state['cache'])}")
        print(f"  State matches: {restored_state == state}")
        
    finally:
        shutil.rmtree(storage_path)


def example_serverless_function():
    """Serverless function execution with checkpointing"""
    print("\n" + "="*70)
    print("Example 2: Serverless Function with Incremental Checkpointing")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=10)
        
        # Simulate function execution state
        function_state = {
            'execution_id': 'exec_001',
            'invocation_count': 0,
            'memory_mb': 128,
            'variables': {},
            'results': []
        }
        
        print("\nSimulating 20 function invocations...")
        
        for i in range(1, 21):
            # Simulate function execution
            function_state['invocation_count'] = i
            function_state['memory_mb'] = 128 + (i * 5)
            function_state['variables'][f'var_{i}'] = i * 100
            function_state['results'].append({'invocation': i, 'result': i ** 2})
            
            # Create checkpoint after each invocation
            checkpoint = manager.create_checkpoint(function_state)
            
            if i % 5 == 0:
                print(f"  Invocation {i:2d}: Checkpoint {checkpoint.checkpoint_id} ({checkpoint.get_type()})")
        
        # Simulate failure at invocation 15 - restore from checkpoint
        print("\n" + "-"*70)
        print("Simulating failure at invocation 15...")
        print("Restoring from checkpoint 15...")
        
        restored = manager.restore_from_checkpoint(15)
        
        print(f"  Restored invocation count: {restored['invocation_count']}")
        print(f"  Restored memory: {restored['memory_mb']} MB")
        print(f"  Restored variables: {len(restored['variables'])}")
        print(f"  Restored results: {len(restored['results'])}")
        
        # Get statistics
        stats = manager.get_statistics()
        print("\n" + "-"*70)
        print("Checkpoint Statistics:")
        print(f"  Total storage: {stats['total_storage_bytes']:,} bytes")
        print(f"  Avg full checkpoint: {stats['avg_full_size_bytes']:,} bytes")
        print(f"  Avg incremental: {stats['avg_incremental_size_bytes']:,} bytes")
        print(f"  Space saved: {stats['compression_savings_percent']:.1f}%")
        
    finally:
        shutil.rmtree(storage_path)


def example_performance_comparison():
    """Compare full vs incremental checkpoint sizes"""
    print("\n" + "="*70)
    print("Example 3: Full vs Incremental Size Comparison")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=100)
        
        # Large initial state
        state = {
            'users': {f'user_{i}': {'name': f'User{i}', 'balance': 1000} for i in range(200)},
            'transactions': [{'id': i, 'amount': 10} for i in range(1000)],
            'config': {'version': '1.0', 'features': list(range(50))}
        }
        
        print("\nInitial state:")
        print(f"  Users: {len(state['users'])}")
        print(f"  Transactions: {len(state['transactions'])}")
        
        # Full checkpoint
        full_cp = manager.create_checkpoint(state)
        print(f"\nFull checkpoint size: {full_cp.get_size():,} bytes")
        
        # Make small changes and create incremental checkpoints
        print("\nCreating incremental checkpoints with small changes...")
        
        incremental_sizes = []
        for i in range(1, 6):
            # Small change
            state['users'][f'user_{i}']['balance'] += 100
            state['transactions'].append({'id': 1000 + i, 'amount': 20})
            
            incr_cp = manager.create_checkpoint(state)
            incremental_sizes.append(incr_cp.get_size())
            
            print(f"  Checkpoint {incr_cp.checkpoint_id}: {incr_cp.get_size():,} bytes")
        
        # Calculate savings
        avg_incr = sum(incremental_sizes) / len(incremental_sizes)
        savings = ((full_cp.get_size() - avg_incr) / full_cp.get_size()) * 100
        
        print("\n" + "-"*70)
        print(f"Average incremental size: {avg_incr:,.0f} bytes")
        print(f"Size reduction: {savings:.1f}%")
        print(f"Compression factor: {full_cp.get_size() / avg_incr:.1f}x")
        
    finally:
        shutil.rmtree(storage_path)


def example_conditional_checkpointing():
    """Demonstrate conditional checkpointing"""
    print("\n" + "="*70)
    print("Example 4: Conditional Checkpointing (Skip Unchanged)")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = ConditionalCheckpointManager(
            storage_path,
            full_checkpoint_interval=10,
            min_change_threshold=1
        )
        
        state = {'counter': 0, 'status': 'running'}
        
        print("\nAttempting checkpoints (some will be skipped)...")
        
        scenarios = [
            (0, 'running', "Initial state"),
            (0, 'running', "No change - should skip"),
            (5, 'running', "Counter changed"),
            (5, 'running', "No change - should skip"),
            (5, 'paused', "Status changed"),
            (10, 'paused', "Counter changed"),
            (10, 'paused', "No change - should skip"),
        ]
        
        for counter, status, description in scenarios:
            state['counter'] = counter
            state['status'] = status
            
            checkpoint = manager.create_checkpoint_if_changed(state)
            
            if checkpoint:
                print(f"  ✓ Created checkpoint {checkpoint.checkpoint_id}: {description}")
            else:
                print(f"  ✗ Skipped: {description}")
        
        # Statistics
        stats = manager.get_statistics()
        print("\n" + "-"*70)
        print("Statistics:")
        print(f"  Checkpoints created: {stats['total_checkpoints']}")
        print(f"  Checkpoints skipped: {stats['skipped_checkpoints']}")
        print(f"  Checkpoint efficiency: {stats['checkpoint_efficiency']:.1%}")
        
    finally:
        shutil.rmtree(storage_path)


def example_checkpoint_chain():
    """Demonstrate checkpoint chain visualization"""
    print("\n" + "="*70)
    print("Example 5: Checkpoint Chain Visualization")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=5)
        
        state = {'value': 0}
        
        # Create 12 checkpoints
        print("\nCreating checkpoint chain...")
        for i in range(1, 13):
            state['value'] = i * 10
            checkpoint = manager.create_checkpoint(state)
            
            cp_type = "FULL" if checkpoint.is_full else "INCR"
            base = f" (base: {checkpoint.base_checkpoint_id})" if not checkpoint.is_full else ""
            print(f"  Checkpoint {checkpoint.checkpoint_id:2d} [{cp_type}]{base}")
        
        # Show chain for different checkpoints
        test_checkpoints = [3, 7, 12]
        
        print("\n" + "-"*70)
        print("Checkpoint Chains:")
        
        for cp_id in test_checkpoints:
            chain = manager.storage_manager.get_checkpoint_chain(cp_id)
            chain_ids = [cp.checkpoint_id for cp in chain]
            chain_types = ['F' if cp.is_full else 'I' for cp in chain]
            
            print(f"\n  Chain for checkpoint {cp_id}:")
            print(f"    IDs: {' -> '.join(map(str, chain_ids))}")
            print(f"    Types: {' -> '.join(chain_types)}")
            print(f"    Length: {len(chain)} checkpoints")
        
    finally:
        shutil.rmtree(storage_path)


def example_cleanup_policy():
    """Demonstrate checkpoint cleanup policies"""
    print("\n" + "="*70)
    print("Example 6: Checkpoint Cleanup Policies")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=10)
        
        state = {'counter': 0}
        
        # Create 30 checkpoints
        print("\nCreating 30 checkpoints...")
        for i in range(30):
            state['counter'] = i
            manager.create_checkpoint(state)
        
        print(f"Total checkpoints: {len(manager.list_checkpoints())}")
        
        # Show all checkpoints
        checkpoints = manager.list_checkpoints()
        full_ids = [cp['checkpoint_id'] for cp in checkpoints if cp['is_full']]
        incr_ids = [cp['checkpoint_id'] for cp in checkpoints if not cp['is_full']]
        
        print(f"Full checkpoint IDs: {full_ids}")
        print(f"Incremental IDs: {len(incr_ids)} checkpoints")
        
        # Apply cleanup policy
        print("\n" + "-"*70)
        print("Applying cleanup (keep last 15, keep all full)...")
        manager.cleanup_old_checkpoints(keep_last_n=15, keep_all_full=True)
        
        remaining = manager.list_checkpoints()
        print(f"Remaining checkpoints: {len(remaining)}")
        
        remaining_full = [cp['checkpoint_id'] for cp in remaining if cp['is_full']]
        remaining_incr = [cp['checkpoint_id'] for cp in remaining if not cp['is_full']]
        
        print(f"Full checkpoint IDs: {remaining_full}")
        print(f"Incremental count: {len(remaining_incr)}")
        
        # Storage statistics
        stats = manager.get_statistics()
        print("\n" + "-"*70)
        print("Storage after cleanup:")
        print(f"  Total size: {stats['total_storage_mb']:.2f} MB")
        
    finally:
        shutil.rmtree(storage_path)


def example_real_world_scenario():
    """Complete real-world scenario"""
    print("\n" + "="*70)
    print("Example 7: Real-World Fault-Tolerant Application")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=10)
        
        # Application state
        app_state = {
            'session_id': 'session_12345',
            'start_time': time.time(),
            'processed_requests': 0,
            'cache': {},
            'user_sessions': {},
            'error_count': 0
        }
        
        print("\nSimulating application with periodic checkpoints...")
        print("Checkpoint every 100 requests")
        
        checkpoint_interval = 100
        total_requests = 1000
        
        for request_num in range(1, total_requests + 1):
            # Process request (simulate)
            app_state['processed_requests'] = request_num
            
            if request_num % 50 == 0:
                app_state['cache'][f'item_{request_num}'] = f'cached_data_{request_num}'
            
            if request_num % 200 == 0:
                app_state['user_sessions'][f'user_{request_num}'] = {'login_time': time.time()}
            
            # Checkpoint every N requests
            if request_num % checkpoint_interval == 0:
                checkpoint = manager.create_checkpoint(app_state)
                cp_type = "FULL" if checkpoint.is_full else "INCR"
                print(f"  Request {request_num:4d}: Checkpoint {checkpoint.checkpoint_id:2d} [{cp_type}] - {checkpoint.get_size():5d} bytes")
        
        # Simulate failure and recovery
        print("\n" + "-"*70)
        print("Simulating application crash at request 750...")
        print("Recovering from checkpoint 7...")
        
        recovered_state = manager.restore_from_checkpoint(7)
        
        print(f"\nRecovered state:")
        print(f"  Processed requests: {recovered_state['processed_requests']}")
        print(f"  Cache entries: {len(recovered_state['cache'])}")
        print(f"  User sessions: {len(recovered_state['user_sessions'])}")
        print(f"  Lost requests: {total_requests - recovered_state['processed_requests']}")
        
        # Final statistics
        stats = manager.get_statistics()
        print("\n" + "-"*70)
        print("Final Statistics:")
        print(f"  Total checkpoints: {stats['total_checkpoints']}")
        print(f"  Storage used: {stats['total_storage_mb']:.3f} MB")
        print(f"  Avg compression: {stats['compression_ratio']:.2f}x")
        print(f"  Space saved: {stats['compression_savings_percent']:.1f}%")
        
        # Calculate checkpoint overhead
        checkpoint_size_per_request = stats['total_storage_bytes'] / total_requests
        print(f"  Overhead per request: {checkpoint_size_per_request:.1f} bytes")
        
    finally:
        shutil.rmtree(storage_path)


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("Incremental Checkpoint Manager Examples")
    print("="*70)
    
    example_basic_usage()
    example_serverless_function()
    example_performance_comparison()
    example_conditional_checkpointing()
    example_checkpoint_chain()
    example_cleanup_policy()
    example_real_world_scenario()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
