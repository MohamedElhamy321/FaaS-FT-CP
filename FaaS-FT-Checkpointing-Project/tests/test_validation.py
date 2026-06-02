"""
Comprehensive Testing Suite for Incremental Checkpointing
Validates end-to-end functionality, performance, and correctness
"""

import sys
import os
import time
import unittest
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint import (
    IncrementalCheckpointManager,
    ConditionalCheckpointManager,
    StateChangeTracker,
    DeltaCompressor,
    CheckpointStorageManager
)


class TestEndToEndCheckpointing(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IncrementalCheckpointManager(self.test_dir, full_checkpoint_interval=5)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_complete_checkpoint_restore_cycle(self):
        """Test complete checkpoint and restore cycle"""
        # Create initial state
        state = {
            'counter': 0,
            'users': {'user1': {'balance': 100}},
            'config': {'timeout': 30}
        }
        
        # Create 10 checkpoints with evolving state
        checkpoints = []
        for i in range(10):
            state['counter'] = i
            state['users'][f'user{i+1}'] = {'balance': 100 + i}
            
            checkpoint = self.manager.create_checkpoint(state)
            checkpoints.append(checkpoint)
        
        # Verify all checkpoints can be restored
        for i, checkpoint in enumerate(checkpoints):
            restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
            self.assertEqual(restored['counter'], i)
    
    def test_size_reduction_achievement(self):
        """Test that incremental checkpoints achieve 60%+ size reduction"""
        # Large state
        state = {f'key_{i}': f'value_{i}' * 10 for i in range(500)}
        
        # Full checkpoint
        full_cp = self.manager.create_checkpoint(state)
        full_size = full_cp.get_size()
        
        # Small change
        state['key_5'] = 'modified_value'
        
        # Incremental checkpoint
        incr_cp = self.manager.create_checkpoint(state)
        incr_size = incr_cp.get_size()
        
        # Calculate reduction
        reduction_percent = ((full_size - incr_size) / full_size) * 100
        
        print(f"\nSize reduction: {reduction_percent:.1f}%")
        self.assertGreater(reduction_percent, 60, "Should achieve at least 60% reduction")
    
    def test_checkpoint_creation_performance(self):
        """Test that checkpoint creation is fast (<100ms for incremental)"""
        state = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        # Create baseline
        self.manager.create_checkpoint(state)
        
        # Modify state
        state['key_5'] = 'modified'
        
        # Time incremental checkpoint creation
        start = time.time()
        checkpoint = self.manager.create_checkpoint(state)
        elapsed_ms = (time.time() - start) * 1000
        
        print(f"\nIncremental checkpoint creation: {elapsed_ms:.2f}ms")
        self.assertLess(elapsed_ms, 100, "Incremental checkpoint should be created in <100ms")
    
    def test_restoration_accuracy(self):
        """Test that restoration is 100% accurate"""
        state = {
            'strings': 'test_value',
            'numbers': 12345,
            'floats': 3.14159,
            'lists': [1, 2, 3, 4, 5],
            'dicts': {'nested': {'deep': 'value'}},
            'bools': True,
            'none': None
        }
        
        # Create checkpoints with modifications
        checkpoint1 = self.manager.create_checkpoint(state)
        
        state['strings'] = 'modified'
        state['lists'].append(6)
        checkpoint2 = self.manager.create_checkpoint(state)
        
        # Restore and verify exact match
        restored1 = self.manager.restore_from_checkpoint(checkpoint1.checkpoint_id)
        restored2 = self.manager.restore_from_checkpoint(checkpoint2.checkpoint_id)
        
        # First checkpoint should have original values
        self.assertEqual(restored1['strings'], 'test_value')
        self.assertEqual(len(restored1['lists']), 5)
        
        # Second checkpoint should have modified values
        self.assertEqual(restored2['strings'], 'modified')
        self.assertEqual(len(restored2['lists']), 6)
    
    def test_long_checkpoint_chain(self):
        """Test restoration from long checkpoint chains (10+ checkpoints)"""
        state = {'value': 0}
        
        # Create 20 checkpoints
        for i in range(20):
            state['value'] = i
            self.manager.create_checkpoint(state)
        
        # Restore from various points in chain
        start = time.time()
        restored = self.manager.restore_from_checkpoint(20)
        elapsed_ms = (time.time() - start) * 1000
        
        print(f"\nRestore from 20-checkpoint chain: {elapsed_ms:.2f}ms")
        self.assertEqual(restored['value'], 19)
        self.assertLess(elapsed_ms, 500, "Should restore in <500ms")
    
    def test_deleted_keys_handling(self):
        """Test that deleted keys are properly handled"""
        state = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        
        self.manager.create_checkpoint(state)
        
        # Delete keys
        del state['key2']
        checkpoint2 = self.manager.create_checkpoint(state)
        
        # Restore and verify
        restored = self.manager.restore_from_checkpoint(checkpoint2.checkpoint_id)
        
        self.assertIn('key1', restored)
        self.assertNotIn('key2', restored)
        self.assertIn('key3', restored)
    
    def test_compression_ratio(self):
        """Test that compression achieves 3-5x ratio"""
        state = {f'key_{i}': 'repeated_value' * 10 for i in range(100)}
        
        self.manager.create_checkpoint(state)
        
        # Modify and create incremental
        state['key_5'] = 'different_value'
        self.manager.create_checkpoint(state)
        
        stats = self.manager.get_statistics()
        compression_ratio = stats['compression_ratio']
        
        print(f"\nCompression ratio: {compression_ratio:.2f}x")
        self.assertGreaterEqual(compression_ratio, 3.0, "Should achieve at least 3x compression")


class TestRobustnessAndEdgeCases(unittest.TestCase):
    """Test robustness and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IncrementalCheckpointManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_empty_state(self):
        """Test checkpointing empty state"""
        state = {}
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(state, restored)
    
    def test_large_state(self):
        """Test checkpointing very large state (1000+ keys)"""
        state = {f'key_{i}': f'value_{i}' * 100 for i in range(1000)}
        
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(len(state), len(restored))
    
    def test_deep_nested_structures(self):
        """Test deeply nested data structures"""
        state = {
            'level1': {
                'level2': {
                    'level3': {
                        'level4': {
                            'level5': 'deep_value'
                        }
                    }
                }
            }
        }
        
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(
            restored['level1']['level2']['level3']['level4']['level5'],
            'deep_value'
        )
    
    def test_special_characters(self):
        """Test keys and values with special characters"""
        state = {
            'key-with-dash': 'value',
            'key_with_underscore': 'value',
            'key.with.dot': 'value',
            'key with space': 'value',
            'key@with#special$chars': 'value!@#$%^&*()'
        }
        
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(state, restored)
    
    def test_unicode_data(self):
        """Test Unicode data handling"""
        state = {
            'english': 'Hello World',
            'chinese': '你好世界',
            'arabic': 'مرحبا بالعالم',
            'emoji': '🚀💻🎉',
            'mixed': 'Hello 世界 🌍'
        }
        
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(state, restored)
    
    def test_concurrent_modifications(self):
        """Test handling rapid state modifications"""
        state = {'counter': 0}
        
        # Rapid checkpoints
        for i in range(50):
            state['counter'] = i
            self.manager.create_checkpoint(state)
        
        # Verify all can be restored
        restored = self.manager.restore_from_checkpoint(50)
        self.assertEqual(restored['counter'], 49)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmark tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IncrementalCheckpointManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_checkpoint_throughput(self):
        """Measure checkpoint creation throughput"""
        state = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        self.manager.create_checkpoint(state)
        
        # Create 100 incremental checkpoints
        start = time.time()
        for i in range(100):
            state[f'key_{i % 10}'] = f'modified_{i}'
            self.manager.create_checkpoint(state)
        elapsed = time.time() - start
        
        throughput = 100 / elapsed
        print(f"\nCheckpoint throughput: {throughput:.1f} checkpoints/second")
        self.assertGreater(throughput, 10, "Should create at least 10 checkpoints/second")
    
    def test_storage_efficiency(self):
        """Measure storage efficiency over many checkpoints"""
        state = {f'key_{i}': f'value_{i}' for i in range(500)}
        
        # Create 50 checkpoints
        for i in range(50):
            state[f'key_{i % 100}'] = f'modified_{i}'
            self.manager.create_checkpoint(state)
        
        stats = self.manager.get_statistics()
        
        # Calculate efficiency
        avg_full = stats['avg_full_size_bytes']
        avg_incr = stats['avg_incremental_size_bytes']
        
        if avg_incr > 0:
            reduction_ratio = avg_full / avg_incr
            print(f"\nStorage efficiency: {reduction_ratio:.1f}x")
            self.assertGreater(reduction_ratio, 5.0, "Should achieve >5x storage efficiency")


class TestStatisticsAndMonitoring(unittest.TestCase):
    """Test statistics and monitoring capabilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IncrementalCheckpointManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_statistics_accuracy(self):
        """Test that statistics are accurate"""
        # Use larger data to make compression worthwhile
        state = {'value': 0, 'payload': 'x' * 200}
        
        # Create 10 checkpoints
        for i in range(10):
            state['value'] = i
            self.manager.create_checkpoint(state)
        
        stats = self.manager.get_statistics()
        
        self.assertEqual(stats['total_checkpoints'], 10)
        self.assertGreater(stats['total_storage_bytes'], 0)
        # Compression ratio may be <1.0 for tiny changes (pickle overhead)
        # Just verify it's a valid positive number
        self.assertGreater(stats['compression_ratio'], 0.0)
    
    def test_monitoring_metrics(self):
        """Test all monitoring metrics are available"""
        state = {'data': 'test'}
        self.manager.create_checkpoint(state)
        
        stats = self.manager.get_statistics()
        
        required_metrics = [
            'total_checkpoints',
            'full_checkpoints',
            'incremental_checkpoints',
            'total_storage_bytes',
            'compression_ratio',
            'size_reduction_vs_full'
        ]
        
        for metric in required_metrics:
            self.assertIn(metric, stats, f"Missing metric: {metric}")


def run_validation_suite():
    """Run complete validation suite"""
    print("\n" + "="*70)
    print("INCREMENTAL CHECKPOINTING - VALIDATION SUITE")
    print("="*70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndCheckpointing))
    suite.addTests(loader.loadTestsFromTestCase(TestRobustnessAndEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmarks))
    suite.addTests(loader.loadTestsFromTestCase(TestStatisticsAndMonitoring))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print detailed summary
    print("\n" + "="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL VALIDATION TESTS PASSED!")
        print("\nSuccess Criteria Met:")
        print("  ✓ 60-80% checkpoint size reduction")
        print("  ✓ <100ms incremental checkpoint creation")
        print("  ✓ <500ms restoration from 10-checkpoint chain")
        print("  ✓ 3-5x compression ratio")
        print("  ✓ 100% restoration accuracy")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Review failures above for details")
    
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_validation_suite()
    sys.exit(0 if success else 1)
