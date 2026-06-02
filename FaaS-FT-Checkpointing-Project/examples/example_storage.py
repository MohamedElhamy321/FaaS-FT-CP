"""
Example usage of Checkpoint Storage
Demonstrates storing and retrieving checkpoints
"""

import sys
import os
import time
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.storage import IncrementalCheckpoint, CheckpointStorageManager
from incremental_checkpoint.compressor import DeltaCompressor
from incremental_checkpoint.state_tracker import StateChangeTracker


def example_basic_storage():
    """Basic checkpoint storage example"""
    print("="*70)
    print("Example 1: Basic Checkpoint Storage")
    print("="*70)
    
    # Create temporary storage directory
    storage_path = tempfile.mkdtemp()
    print(f"\nStorage path: {storage_path}")
    
    try:
        storage = CheckpointStorageManager(storage_path)
        compressor = DeltaCompressor()
        
        # Create a full checkpoint
        state = {'counter': 100, 'data': 'initial_state', 'active': True}
        compressed_data = compressor.compress_delta(state)
        
        full_checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=compressed_data,
            metadata={'num_keys': len(state), 'type': 'full'}
        )
        
        print("\nStoring full checkpoint...")
        filepath = storage.store_checkpoint(full_checkpoint)
        print(f"Stored at: {filepath}")
        print(f"Size: {full_checkpoint.get_size()} bytes")
        
        # Create incremental checkpoint
        changes = {'counter': 150}
        compressed_changes = compressor.compress_delta(changes)
        
        incr_checkpoint = IncrementalCheckpoint(
            checkpoint_id=2,
            is_full=False,
            timestamp=time.time(),
            base_checkpoint_id=1,
            data=compressed_changes,
            metadata={'num_changes': len(changes), 'type': 'incremental'}
        )
        
        print("\nStoring incremental checkpoint...")
        filepath = storage.store_checkpoint(incr_checkpoint)
        print(f"Stored at: {filepath}")
        print(f"Size: {incr_checkpoint.get_size()} bytes")
        
        # Load checkpoint
        print("\nLoading checkpoint 2...")
        loaded = storage.load_checkpoint(2)
        print(f"Loaded: ID={loaded.checkpoint_id}, Type={loaded.get_type()}")
        
    finally:
        shutil.rmtree(storage_path)


def example_checkpoint_chain():
    """Demonstrate checkpoint chain management"""
    print("\n" + "="*70)
    print("Example 2: Checkpoint Chain Management")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        storage = CheckpointStorageManager(storage_path)
        compressor = DeltaCompressor()
        tracker = StateChangeTracker()
        
        # Initial state
        state = {f'var_{i}': f'value_{i}' for i in range(100)}
        
        print("\nCreating checkpoint chain...")
        print("Full checkpoint at ID 1, incrementals at IDs 2-5")
        
        # Full checkpoint
        full_data = compressor.compress_delta(state)
        full_cp = IncrementalCheckpoint(1, True, time.time(), None, full_data, {})
        storage.store_checkpoint(full_cp)
        tracker.update_baseline(state)
        
        print(f"\nCheckpoint 1 (full): {full_cp.get_size()} bytes")
        
        # Create 4 incremental checkpoints
        for i in range(2, 6):
            # Simulate state changes
            state[f'var_{i}'] = f'modified_value_{i}'
            state[f'new_var_{i}'] = f'new_value_{i}'
            
            # Track changes
            changes = tracker.track_changes(state)
            incr_data = compressor.compress_delta(changes)
            
            incr_cp = IncrementalCheckpoint(i, False, time.time(), 1, incr_data, {})
            storage.store_checkpoint(incr_cp)
            tracker.update_baseline(state)
            
            print(f"Checkpoint {i} (incremental): {incr_cp.get_size()} bytes, {len(changes)} changes")
        
        # Get checkpoint chain
        print("\nRetrieving checkpoint chain for ID 5...")
        chain = storage.get_checkpoint_chain(5)
        
        print(f"\nChain length: {len(chain)}")
        for i, cp in enumerate(chain):
            print(f"  {i+1}. Checkpoint {cp.checkpoint_id} ({cp.get_type()})")
        
        # Verify chain
        is_valid = storage.verify_checkpoint_chain(5)
        print(f"\nChain valid: {is_valid}")
        
    finally:
        shutil.rmtree(storage_path)


def example_list_and_statistics():
    """Demonstrate listing and statistics"""
    print("\n" + "="*70)
    print("Example 3: Checkpoint Listing and Statistics")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        storage = CheckpointStorageManager(storage_path)
        compressor = DeltaCompressor()
        
        # Create multiple checkpoints
        print("\nCreating 10 checkpoints (full every 5)...")
        
        for i in range(1, 11):
            is_full = (i % 5 == 0) or (i == 1)
            data_size = 1000 if is_full else 100
            data = b'x' * data_size
            
            checkpoint = IncrementalCheckpoint(
                checkpoint_id=i,
                is_full=is_full,
                timestamp=time.time() + i,
                base_checkpoint_id=None if is_full else ((i-1) // 5) * 5,
                data=data,
                metadata={}
            )
            
            storage.store_checkpoint(checkpoint)
        
        # List all checkpoints
        print("\nAll checkpoints:")
        checkpoints = storage.list_checkpoints()
        
        for cp in checkpoints:
            print(f"  ID {cp['checkpoint_id']:2d}: {cp['type']:11s} - {cp['size']:4d} bytes")
        
        # Get statistics
        print("\nStorage Statistics:")
        stats = storage.get_storage_statistics()
        
        print(f"  Total checkpoints: {stats['total_checkpoints']}")
        print(f"  Full checkpoints: {stats['full_checkpoints']}")
        print(f"  Incremental checkpoints: {stats['incremental_checkpoints']}")
        print(f"  Total size: {stats['total_size_bytes']:,} bytes ({stats['total_size_mb']:.2f} MB)")
        print(f"  Avg full checkpoint size: {stats['avg_full_size_bytes']:,} bytes")
        print(f"  Avg incremental size: {stats['avg_incremental_size_bytes']:,} bytes")
        print(f"  Size reduction ratio: {stats['size_reduction_ratio']:.2f}x")
        
    finally:
        shutil.rmtree(storage_path)


def example_cleanup():
    """Demonstrate checkpoint cleanup"""
    print("\n" + "="*70)
    print("Example 4: Checkpoint Cleanup")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        storage = CheckpointStorageManager(storage_path)
        
        # Create 20 checkpoints
        print("\nCreating 20 checkpoints...")
        for i in range(1, 21):
            is_full = (i % 10 == 0) or (i == 1)
            checkpoint = IncrementalCheckpoint(
                checkpoint_id=i,
                is_full=is_full,
                timestamp=time.time() + i,
                base_checkpoint_id=None if is_full else ((i-1) // 10) * 10,
                data=b'data',
                metadata={}
            )
            storage.store_checkpoint(checkpoint)
        
        print(f"Total checkpoints: {len(storage.list_checkpoints())}")
        
        # Cleanup - keep last 10, keep all full
        print("\nCleaning up (keep last 10, keep all full)...")
        storage.cleanup_old_checkpoints(keep_last_n=10, keep_all_full=True)
        
        remaining = storage.list_checkpoints()
        print(f"Remaining checkpoints: {len(remaining)}")
        
        print("\nRemaining checkpoint IDs:")
        ids = [cp['checkpoint_id'] for cp in remaining]
        print(f"  {ids}")
        
        # Note: Full checkpoints are kept even if old
        full_ids = [cp['checkpoint_id'] for cp in remaining if cp['is_full']]
        print(f"\nFull checkpoint IDs: {full_ids}")
        
    finally:
        shutil.rmtree(storage_path)


def example_restoration_from_chain():
    """Demonstrate full state restoration from checkpoint chain"""
    print("\n" + "="*70)
    print("Example 5: State Restoration from Checkpoint Chain")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        storage = CheckpointStorageManager(storage_path)
        compressor = DeltaCompressor()
        tracker = StateChangeTracker()
        
        # Initial state
        print("\nInitial state:")
        state = {'counter': 0, 'name': 'app', 'data': [1, 2, 3]}
        print(f"  {state}")
        
        # Create full checkpoint
        full_data = compressor.compress_delta(state)
        full_cp = IncrementalCheckpoint(1, True, time.time(), None, full_data, {})
        storage.store_checkpoint(full_cp)
        tracker.update_baseline(state)
        
        # Apply changes and create incremental checkpoints
        changes_log = []
        
        for i in range(2, 6):
            # Modify state
            state['counter'] += 10
            state['data'].append(i + 2)
            state[f'new_key_{i}'] = f'value_{i}'
            
            changes = tracker.track_changes(state)
            changes_log.append((i, changes.copy()))
            
            incr_data = compressor.compress_delta(changes)
            incr_cp = IncrementalCheckpoint(i, False, time.time(), 1, incr_data, {})
            storage.store_checkpoint(incr_cp)
            tracker.update_baseline(state)
        
        print("\nFinal state after 4 incremental changes:")
        print(f"  {state}")
        
        # Now restore from checkpoint chain
        print("\n" + "-"*70)
        print("Restoring state from checkpoint chain...")
        print("-"*70)
        
        chain = storage.get_checkpoint_chain(5)
        print(f"\nChain: {[cp.checkpoint_id for cp in chain]}")
        
        # Restore base state from full checkpoint
        restored_state = compressor.decompress_delta(chain[0].data)
        print(f"\nAfter full checkpoint (ID {chain[0].checkpoint_id}):")
        print(f"  {restored_state}")
        
        # Apply incremental changes
        for cp in chain[1:]:
            changes = compressor.decompress_delta(cp.data)
            
            # Apply changes
            for key, value in changes.items():
                if key.startswith("__deleted_"):
                    original_key = key.replace("__deleted_", "")
                    restored_state.pop(original_key, None)
                else:
                    restored_state[key] = value
            
            print(f"\nAfter incremental checkpoint (ID {cp.checkpoint_id}):")
            print(f"  Changes: {changes}")
            print(f"  State: {restored_state}")
        
        # Verify restoration
        print("\n" + "-"*70)
        print("Verification:")
        print(f"  Original state: {state}")
        print(f"  Restored state: {restored_state}")
        print(f"  Match: {state == restored_state}")
        
    finally:
        shutil.rmtree(storage_path)


def example_multiple_chains():
    """Demonstrate managing multiple independent checkpoint chains"""
    print("\n" + "="*70)
    print("Example 6: Multiple Independent Checkpoint Chains")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        storage = CheckpointStorageManager(storage_path)
        
        print("\nCreating two independent checkpoint chains:")
        print("  Chain A: IDs 1-5 (full at 1)")
        print("  Chain B: IDs 10-15 (full at 10)")
        
        # Chain A
        for i in range(1, 6):
            checkpoint = IncrementalCheckpoint(
                checkpoint_id=i,
                is_full=(i == 1),
                timestamp=time.time(),
                base_checkpoint_id=None if i == 1 else 1,
                data=f'chain_a_data_{i}'.encode(),
                metadata={'chain': 'A'}
            )
            storage.store_checkpoint(checkpoint)
        
        # Chain B
        for i in range(10, 16):
            checkpoint = IncrementalCheckpoint(
                checkpoint_id=i,
                is_full=(i == 10),
                timestamp=time.time(),
                base_checkpoint_id=None if i == 10 else 10,
                data=f'chain_b_data_{i}'.encode(),
                metadata={'chain': 'B'}
            )
            storage.store_checkpoint(checkpoint)
        
        print("\nAll stored checkpoints:")
        for cp in storage.list_checkpoints():
            chain = cp['metadata'].get('chain', '?')
            print(f"  ID {cp['checkpoint_id']:2d}: Chain {chain}, {cp['type']}")
        
        # Get both chains
        print("\nChain A (from ID 5):")
        chain_a = storage.get_checkpoint_chain(5)
        print(f"  {[cp.checkpoint_id for cp in chain_a]}")
        
        print("\nChain B (from ID 15):")
        chain_b = storage.get_checkpoint_chain(15)
        print(f"  {[cp.checkpoint_id for cp in chain_b]}")
        
    finally:
        shutil.rmtree(storage_path)


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("Checkpoint Storage Examples")
    print("="*70)
    
    example_basic_storage()
    example_checkpoint_chain()
    example_list_and_statistics()
    example_cleanup()
    example_restoration_from_chain()
    example_multiple_chains()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
