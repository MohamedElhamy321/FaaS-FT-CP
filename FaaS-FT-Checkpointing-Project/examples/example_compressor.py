"""
Example usage of DeltaCompressor
Demonstrates compression of state changes
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.compressor import DeltaCompressor, OptimizedDeltaCompressor


def example_basic_compression():
    """Basic compression example"""
    print("="*70)
    print("Example 1: Basic Delta Compression")
    print("="*70)
    
    compressor = DeltaCompressor()
    
    # State changes to compress
    changes = {
        'counter': 150,
        'active_connections': 5,
        'cache': {'user_123': 'data_abc', 'user_456': 'data_def'}
    }
    
    print("\nOriginal changes:")
    print(changes)
    
    # Compress
    compressed = compressor.compress_delta(changes)
    print(f"\nCompressed size: {len(compressed)} bytes")
    
    # Decompress
    decompressed = compressor.decompress_delta(compressed)
    print("\nDecompressed changes:")
    print(decompressed)
    
    # Verify integrity
    print(f"\nData integrity: {'✓ PASS' if changes == decompressed else '✗ FAIL'}")


def example_compression_ratio():
    """Demonstrate compression ratio"""
    print("\n" + "="*70)
    print("Example 2: Compression Ratio Analysis")
    print("="*70)
    
    compressor = DeltaCompressor()
    
    # Different types of data
    test_cases = [
        ("Small changes", {'key1': 'value1', 'key2': 'value2'}),
        ("Repeated data", {f'key_{i}': 'repeated_value' * 5 for i in range(20)}),
        ("Random data", {f'key_{i}': f'unique_value_{i}' * 3 for i in range(20)}),
        ("Large text", {'document': 'Lorem ipsum dolor sit amet. ' * 100})
    ]
    
    import pickle
    
    for name, changes in test_cases:
        # Original size
        original_size = len(pickle.dumps(changes))
        
        # Compressed size
        compressed = compressor.compress_delta(changes)
        compressed_size = len(compressed)
        
        # Calculate ratio
        ratio = original_size / compressed_size
        savings = ((original_size - compressed_size) / original_size) * 100
        
        print(f"\n{name}:")
        print(f"  Original size: {original_size:,} bytes")
        print(f"  Compressed size: {compressed_size:,} bytes")
        print(f"  Compression ratio: {ratio:.2f}x")
        print(f"  Space saved: {savings:.1f}%")


def example_compression_levels():
    """Compare different compression levels"""
    print("\n" + "="*70)
    print("Example 3: Compression Level Comparison")
    print("="*70)
    
    # Test data
    changes = {f'key_{i}': 'repeated_data' * 10 for i in range(100)}
    
    import time
    import pickle
    
    original_size = len(pickle.dumps(changes))
    print(f"\nOriginal size: {original_size:,} bytes\n")
    
    levels = [1, 3, 6, 9]
    
    for level in levels:
        compressor = DeltaCompressor(compression_level=level)
        
        # Measure compression time
        start = time.time()
        compressed = compressor.compress_delta(changes)
        compress_time = (time.time() - start) * 1000
        
        # Measure decompression time
        start = time.time()
        decompressed = compressor.decompress_delta(compressed)
        decompress_time = (time.time() - start) * 1000
        
        size = len(compressed)
        ratio = original_size / size
        
        print(f"Level {level}:")
        print(f"  Size: {size:,} bytes ({ratio:.2f}x compression)")
        print(f"  Compress time: {compress_time:.2f}ms")
        print(f"  Decompress time: {decompress_time:.2f}ms")
        print()


def example_statistics():
    """Demonstrate compression statistics"""
    print("="*70)
    print("Example 4: Compression Statistics")
    print("="*70)
    
    compressor = DeltaCompressor()
    
    # Simulate multiple compressions
    checkpoints = [
        {'request_count': 100, 'memory': 128},
        {'request_count': 200, 'memory': 256},
        {'request_count': 300, 'memory': 512, 'new_field': 'data'},
        {'request_count': 400, 'memory': 512},
        {'request_count': 500, 'memory': 1024, 'another_field': [1, 2, 3]}
    ]
    
    print("\nCompressing 5 checkpoint deltas...")
    for i, changes in enumerate(checkpoints, 1):
        compressor.compress_delta(changes)
        print(f"  Checkpoint {i}: {len(changes)} keys")
    
    # Get statistics
    stats = compressor.get_statistics()
    
    print("\n" + "-"*70)
    print("Compression Statistics:")
    print("-"*70)
    print(f"Total compressions: {stats['total_compressions']}")
    print(f"Average compression ratio: {stats['average_compression_ratio']:.2f}x")
    print(f"Total original size: {stats['total_original_size']:,} bytes")
    print(f"Total compressed size: {stats['total_compressed_size']:,} bytes")
    print(f"Total savings: {stats['total_savings_bytes']:,} bytes ({stats['total_savings_percent']:.1f}%)")
    print(f"Average compression time: {stats['average_compression_time_ms']:.2f}ms")


def example_parallel_compression():
    """Demonstrate parallel compression"""
    print("\n" + "="*70)
    print("Example 5: Parallel Compression (Large Dataset)")
    print("="*70)
    
    import time
    
    # Create large dataset
    large_changes = {f'key_{i}': f'value_{i}' * 10 for i in range(5000)}
    
    print(f"\nDataset: 5,000 keys")
    
    # Regular compression
    compressor = DeltaCompressor()
    start = time.time()
    regular_compressed = compressor.compress_delta(large_changes)
    regular_time = (time.time() - start) * 1000
    
    print(f"\nRegular compression:")
    print(f"  Time: {regular_time:.2f}ms")
    print(f"  Size: {len(regular_compressed):,} bytes")
    
    # Parallel compression
    parallel_compressor = OptimizedDeltaCompressor(num_workers=4, parallel_threshold=1000)
    start = time.time()
    parallel_compressed = parallel_compressor.compress_delta_parallel(large_changes)
    parallel_time = (time.time() - start) * 1000
    
    print(f"\nParallel compression (4 workers):")
    print(f"  Time: {parallel_time:.2f}ms")
    print(f"  Size: {len(parallel_compressed):,} bytes")
    
    if regular_time > 0:
        speedup = regular_time / parallel_time
        print(f"\nSpeedup: {speedup:.2f}x")
    
    # Verify decompression
    decompressed = parallel_compressor.decompress_delta_parallel(parallel_compressed)
    print(f"Data integrity: {'✓ PASS' if large_changes == decompressed else '✗ FAIL'}")
    
    parallel_compressor.shutdown()


def example_real_world_scenario():
    """Real-world serverless function checkpoint scenario"""
    print("\n" + "="*70)
    print("Example 6: Real-World Serverless Checkpoint Scenario")
    print("="*70)
    
    from incremental_checkpoint.state_tracker import StateChangeTracker
    
    compressor = DeltaCompressor()
    tracker = StateChangeTracker()
    
    # Initial function state
    state = {
        'function_id': 'fib-calculator-001',
        'invocation_count': 0,
        'memory_mb': 128,
        'cache': {},
        'result_history': []
    }
    
    print("\nSimulating 10 function invocations with checkpointing...")
    print("-"*70)
    
    tracker.update_baseline(state)
    total_full_size = 0
    total_incremental_size = 0
    
    import pickle
    
    for i in range(1, 11):
        # Simulate function execution
        state['invocation_count'] = i
        state['memory_mb'] = 128 + (i * 10)
        state['cache'][f'input_{i}'] = f'result_{i}'
        state['result_history'].append(i)
        
        # Full checkpoint size
        full_checkpoint = pickle.dumps(state)
        full_size = len(full_checkpoint)
        total_full_size += full_size
        
        # Incremental checkpoint
        changes = tracker.track_changes(state)
        incremental_checkpoint = compressor.compress_delta(changes)
        incremental_size = len(incremental_checkpoint)
        total_incremental_size += incremental_size
        
        savings = ((full_size - incremental_size) / full_size) * 100
        
        print(f"Checkpoint {i:2d}: Full={full_size:4d}B | Incremental={incremental_size:3d}B | Saved {savings:5.1f}%")
        
        tracker.update_baseline(state)
    
    print("-"*70)
    print(f"Total full checkpoints: {total_full_size:,} bytes")
    print(f"Total incremental: {total_incremental_size:,} bytes")
    total_savings = ((total_full_size - total_incremental_size) / total_full_size) * 100
    print(f"Overall savings: {total_savings:.1f}%")
    
    # Get compression statistics
    stats = compressor.get_statistics()
    print(f"\nAverage compression ratio: {stats['average_compression_ratio']:.2f}x")
    print(f"Average compression time: {stats['average_compression_time_ms']:.2f}ms")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("DeltaCompressor Examples")
    print("="*70)
    
    example_basic_compression()
    example_compression_ratio()
    example_compression_levels()
    example_statistics()
    example_parallel_compression()
    example_real_world_scenario()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
