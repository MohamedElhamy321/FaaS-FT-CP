"""
Example: Using Production-Ready Enhanced Manager
Demonstrates all optimizations and production features
"""

import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint import ProductionCheckpointManager


def example_production_manager():
    """Demonstrate production checkpoint manager with all features."""
    print("="*70)
    print("EXAMPLE: Production-Ready Checkpoint Manager")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    # Initialize production manager with all features enabled
    manager = ProductionCheckpointManager(
        storage_path=storage_path,
        full_checkpoint_interval=10,
        enable_optimizations=True,
        enable_monitoring=True,
        max_retries=3
    )
    
    print("\n1. Creating Checkpoints with Monitoring")
    print("-" * 70)
    
    # Simulate FaaS function state
    state = {
        'function_name': 'data-processor',
        'invocation_count': 0,
        'processed_records': 0,
        'cache': {},
        'config': {'timeout': 30, 'max_retries': 3}
    }
    
    # Create 20 checkpoints
    for i in range(1, 21):
        state['invocation_count'] = i
        state['processed_records'] += 100
        state['cache'][f'key_{i}'] = f'value_{i}' * 10
        
        checkpoint = manager.create_checkpoint(state)
        
        if i % 5 == 0:
            print(f"  Checkpoint {checkpoint.checkpoint_id}: "
                  f"{'FULL' if checkpoint.is_full else 'INCR'} "
                  f"({checkpoint.get_size()} bytes)")
    
    print("\n2. Performance Report")
    print("-" * 70)
    
    perf_report = manager.get_performance_report()
    
    if perf_report['monitoring_enabled']:
        stats = perf_report['statistics']['checkpoint_times']
        print(f"  Checkpoint Statistics:")
        print(f"    Total created: {stats['count']}")
        print(f"    Avg time: {stats['avg_ms']:.2f}ms")
        print(f"    Min time: {stats['min_ms']:.2f}ms")
        print(f"    Max time: {stats['max_ms']:.2f}ms")
        
        if 'optimizations' in perf_report:
            opt = perf_report['optimizations']
            print(f"\n  Optimization Status:")
            print(f"    xxhash available: {opt['xxhash_available']}")
            if 'hash_calculator' in opt:
                cache = opt['hash_calculator']
                print(f"    Cache hit rate: {cache['hit_rate_percent']:.1f}%")
    
    print("\n3. Health Check")
    print("-" * 70)
    
    health = manager.run_health_check()
    print(f"  System Status: {health['status'].upper()}")
    print(f"  Storage: {'✓' if health['checks'].get('storage') else '✗'}")
    print(f"  Compression: {'✓' if health['checks'].get('compression') else '✗'}")
    
    print("\n4. Error Handling & Recovery")
    print("-" * 70)
    
    # Simulate restoration with automatic fallback
    restored = manager.restore_from_checkpoint(
        checkpoint_id=15,
        fallback_to_previous=True
    )
    
    if restored:
        print(f"  ✓ Successfully restored checkpoint 15")
        print(f"    Invocation count: {restored['invocation_count']}")
        print(f"    Cache entries: {len(restored['cache'])}")
    
    print("\n5. Diagnostic Information")
    print("-" * 70)
    
    diagnostics = manager.get_diagnostic_info()
    print(f"  Version: {diagnostics['version']}")
    print(f"  Total checkpoints: {diagnostics['checkpoint_statistics']['total_checkpoints']}")
    print(f"  Compression ratio: {diagnostics['checkpoint_statistics']['compression_ratio']:.2f}x")
    print(f"  Recent errors: {len(diagnostics['recent_errors'])}")
    
    print("\n6. Bottleneck Analysis")
    print("-" * 70)
    
    bottlenecks = perf_report.get('bottlenecks', {})
    if bottlenecks.get('status'):
        print(f"  {bottlenecks['status']}")
    else:
        for operation, message in bottlenecks.items():
            print(f"  ⚠ {operation}: {message}")
    
    print("\n7. Cleanup with Logging")
    print("-" * 70)
    
    manager.cleanup_old_checkpoints(keep_last_n=10, keep_all_full=True)
    
    remaining = len(manager.list_checkpoints())
    print(f"  Checkpoints remaining: {remaining}")
    
    print("\n" + "="*70)
    print("✓ Production manager demonstration complete")
    print("="*70)


def example_backward_compatibility():
    """Demonstrate backward compatibility with legacy checkpoints."""
    print("\n" + "="*70)
    print("EXAMPLE: Backward Compatibility")
    print("="*70)
    
    from incremental_checkpoint import BackwardCompatibility
    import pickle
    
    storage_path = tempfile.mkdtemp()
    
    # Create a legacy checkpoint
    legacy_checkpoint = {
        'checkpoint_id': 1,
        'timestamp': time.time(),
        'state': {
            'function_id': 'legacy-func',
            'counter': 42,
            'data': ['item1', 'item2']
        }
    }
    
    # Save legacy checkpoint
    legacy_path = os.path.join(storage_path, 'legacy_checkpoint.pkl')
    with open(legacy_path, 'wb') as f:
        pickle.dump(legacy_checkpoint, f)
    
    print("\n1. Legacy Checkpoint Created")
    print(f"   State: {legacy_checkpoint['state']}")
    
    # Initialize production manager
    manager = ProductionCheckpointManager(storage_path)
    
    # Restore from legacy checkpoint
    print("\n2. Restoring Legacy Checkpoint")
    state = manager.restore_from_legacy_checkpoint(legacy_checkpoint)
    
    print(f"   ✓ Restored: {state}")
    
    # Continue with new format
    state['counter'] = 43
    new_checkpoint = manager.create_checkpoint(state)
    
    print(f"\n3. New Incremental Checkpoint Created")
    print(f"   ID: {new_checkpoint.checkpoint_id}")
    print(f"   Type: {'FULL' if new_checkpoint.is_full else 'INCR'}")
    
    print("\n✓ Backward compatibility demonstration complete")


def example_optimizations():
    """Demonstrate performance optimizations."""
    print("\n" + "="*70)
    print("EXAMPLE: Performance Optimizations")
    print("="*70)
    
    from incremental_checkpoint import (
        OptimizedHashCalculator,
        MemoryOptimizer,
        is_xxhash_available
    )
    
    print(f"\n1. xxhash Status")
    print("-" * 70)
    print(f"   xxhash available: {is_xxhash_available()}")
    
    if not is_xxhash_available():
        from incremental_checkpoint.optimizations import get_xxhash_install_command
        print(f"   Install with: {get_xxhash_install_command()}")
    
    print(f"\n2. Optimized Hash Calculator")
    print("-" * 70)
    
    calculator = OptimizedHashCalculator(use_xxhash=True, cache_size_limit=1000)
    
    # Hash some data
    test_data = {'key': 'value' * 100}
    
    start = time.time()
    for _ in range(100):
        calculator.calculate_hash(test_data, use_cache=True)
    elapsed = (time.time() - start) * 1000
    
    stats = calculator.get_cache_statistics()
    print(f"   100 hash calculations: {elapsed:.2f}ms")
    print(f"   Cache hit rate: {stats['hit_rate_percent']:.1f}%")
    print(f"   Cache size: {stats['cache_size']}")
    
    print(f"\n3. Memory Optimizer")
    print("-" * 70)
    
    large_state = {f'key_{i}': 'x' * 500 for i in range(100)}
    
    original_size = MemoryOptimizer.estimate_memory_usage(large_state)
    compressed_state = MemoryOptimizer.compress_state(large_state, threshold_bytes=1024)
    compressed_size = MemoryOptimizer.estimate_memory_usage(compressed_state)
    
    reduction = ((original_size - compressed_size) / original_size) * 100
    
    print(f"   Original size: {original_size:,} bytes")
    print(f"   Compressed size: {compressed_size:,} bytes")
    print(f"   Reduction: {reduction:.1f}%")
    
    # Decompress
    decompressed = MemoryOptimizer.decompress_state(compressed_state)
    print(f"   ✓ Decompression successful: {large_state == decompressed}")
    
    print("\n✓ Optimization demonstration complete")


if __name__ == '__main__':
    example_production_manager()
    example_backward_compatibility()
    example_optimizations()
    
    print("\n" + "="*70)
    print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
    print("="*70)
