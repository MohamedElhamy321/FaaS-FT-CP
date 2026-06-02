"""
Integration Test Suite
Tests integration with existing FaaS-FT checkpointing system
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint import IncrementalCheckpointManager


def test_faas_function_state():
    """Test with FaaS function state structure"""
    print("="*70)
    print("Integration Test: FaaS Function State Checkpointing")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=10)
        
        # Simulate FaaS function state
        function_state = {
            'function_name': 'fibonacci-calculator',
            'execution_context': {
                'request_id': 'req_12345',
                'user_id': 'user_001',
                'timestamp': 1234567890
            },
            'variables': {
                'n': 10,
                'cache': {}
            },
            'memory': {
                'allocated_mb': 128,
                'used_mb': 45
            },
            'execution_stats': {
                'invocations': 0,
                'total_time_ms': 0,
                'errors': 0
            }
        }
        
        print("\nSimulating 20 function invocations with checkpoints...")
        
        for i in range(1, 21):
            # Update function state
            function_state['execution_context']['request_id'] = f'req_{12345 + i}'
            function_state['variables']['n'] = 10 + i
            function_state['variables']['cache'][f'fib_{i}'] = i * 89  # Simulated fibonacci value
            function_state['memory']['used_mb'] = 45 + (i * 2)
            function_state['execution_stats']['invocations'] = i
            function_state['execution_stats']['total_time_ms'] += 50 + (i * 5)
            
            checkpoint = manager.create_checkpoint(function_state)
            
            if i % 5 == 0:
                cp_type = "FULL" if checkpoint.is_full else "INCR"
                print(f"  Invocation {i:2d}: Checkpoint {checkpoint.checkpoint_id:2d} [{cp_type}] - {checkpoint.get_size():5d} bytes")
        
        # Test recovery scenario
        print("\n" + "-"*70)
        print("Simulating failure at invocation 15...")
        print("Recovering from checkpoint 15...")
        
        recovered_state = manager.restore_from_checkpoint(15)
        
        print(f"\nRecovered state:")
        print(f"  Invocations: {recovered_state['execution_stats']['invocations']}")
        print(f"  Cache entries: {len(recovered_state['variables']['cache'])}")
        print(f"  Memory used: {recovered_state['memory']['used_mb']} MB")
        print(f"  Total time: {recovered_state['execution_stats']['total_time_ms']} ms")
        
        # Verify accuracy
        assert recovered_state['execution_stats']['invocations'] == 15
        assert len(recovered_state['variables']['cache']) == 15
        assert recovered_state['memory']['used_mb'] == 45 + (15 * 2)
        
        print("\n✅ Recovery successful and accurate")
        
        # Statistics
        stats = manager.get_statistics()
        print("\n" + "-"*70)
        print("Checkpoint Statistics:")
        print(f"  Total checkpoints: {stats['total_checkpoints']}")
        print(f"  Storage used: {stats['total_storage_mb']:.3f} MB")
        print(f"  Compression ratio: {stats['compression_ratio']:.2f}x")
        print(f"  Space saved: {stats['compression_savings_percent']:.1f}%")
        
        print("\n✅ Integration test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(storage_path)


def test_backward_compatibility():
    """Test that new system can work alongside existing checkpoints"""
    print("\n" + "="*70)
    print("Integration Test: Backward Compatibility")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        # Simulate existing checkpoint format
        import pickle
        
        legacy_checkpoint = {
            'checkpoint_id': 1,
            'timestamp': 1234567890,
            'state': {'legacy': 'data', 'value': 100}
        }
        
        legacy_path = os.path.join(storage_path, 'legacy_checkpoint_1.pkl')
        with open(legacy_path, 'wb') as f:
            pickle.dump(legacy_checkpoint, f)
        
        print("\nLegacy checkpoint created")
        
        # Create new incremental checkpoint manager
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=5)
        
        # Create new checkpoints
        state = {'new': 'format', 'value': 200}
        checkpoint = manager.create_checkpoint(state)
        
        print(f"New checkpoint created: ID {checkpoint.checkpoint_id}")
        
        # Verify both can coexist
        assert os.path.exists(legacy_path)
        
        new_checkpoints = manager.list_checkpoints()
        assert len(new_checkpoints) > 0
        
        print("\n✅ Backward compatibility test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Backward compatibility test FAILED: {e}")
        return False
        
    finally:
        shutil.rmtree(storage_path)


def test_production_workload():
    """Test with production-like workload"""
    print("\n" + "="*70)
    print("Integration Test: Production Workload Simulation")
    print("="*70)
    
    storage_path = tempfile.mkdtemp()
    
    try:
        manager = IncrementalCheckpointManager(storage_path, full_checkpoint_interval=10)
        
        # Simulate production application state
        app_state = {
            'server_id': 'server_001',
            'uptime_seconds': 0,
            'request_stats': {
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'avg_response_time_ms': 0
            },
            'active_connections': {},
            'cache': {},
            'config': {
                'max_connections': 1000,
                'timeout_seconds': 30,
                'retry_count': 3
            }
        }
        
        print("\nSimulating 100 time intervals with checkpoints...")
        
        import time
        start_time = time.time()
        
        checkpoint_times = []
        
        for i in range(1, 101):
            # Simulate application changes
            app_state['uptime_seconds'] = i * 60  # 1 minute intervals
            app_state['request_stats']['total_requests'] += 100
            app_state['request_stats']['successful'] += 95
            app_state['request_stats']['failed'] += 5
            
            # Simulate connections (churn)
            if i % 5 == 0:
                app_state['active_connections'][f'conn_{i}'] = {
                    'user': f'user_{i}',
                    'connected_at': time.time()
                }
            
            # Simulate cache updates
            if i % 3 == 0:
                app_state['cache'][f'cache_key_{i}'] = f'cache_value_{i}' * 10
            
            # Create checkpoint
            cp_start = time.time()
            checkpoint = manager.create_checkpoint(app_state)
            cp_time = (time.time() - cp_start) * 1000
            checkpoint_times.append(cp_time)
            
            if i % 20 == 0:
                print(f"  Interval {i:3d}: Checkpoint {checkpoint.checkpoint_id:3d} - {cp_time:.2f}ms")
        
        total_time = time.time() - start_time
        
        print("\n" + "-"*70)
        print("Performance Metrics:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Avg checkpoint time: {sum(checkpoint_times)/len(checkpoint_times):.2f}ms")
        print(f"  Max checkpoint time: {max(checkpoint_times):.2f}ms")
        print(f"  Min checkpoint time: {min(checkpoint_times):.2f}ms")
        
        # Storage statistics
        stats = manager.get_statistics()
        print("\nStorage Statistics:")
        print(f"  Total storage: {stats['total_storage_mb']:.2f} MB")
        print(f"  Avg full checkpoint: {stats['avg_full_size_bytes']/1024:.2f} KB")
        print(f"  Avg incremental: {stats['avg_incremental_size_bytes']/1024:.2f} KB")
        
        # Verify performance requirements
        avg_cp_time = sum(checkpoint_times) / len(checkpoint_times)
        assert avg_cp_time < 100, "Average checkpoint time should be <100ms"
        
        print("\n✅ Production workload test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Production workload test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        shutil.rmtree(storage_path)


def run_integration_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("RUNNING INTEGRATION TESTS")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("FaaS Function State", test_faas_function_state()))
    results.append(("Backward Compatibility", test_backward_compatibility()))
    results.append(("Production Workload", test_production_workload()))
    
    # Summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
    else:
        print("\n⚠️  SOME INTEGRATION TESTS FAILED")
    
    print("="*70)
    
    return all_passed


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
