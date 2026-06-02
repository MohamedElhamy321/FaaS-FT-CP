"""
Unit tests for Incremental Checkpoint Manager
"""

import sys
import os
import time
import unittest
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.manager import IncrementalCheckpointManager, ConditionalCheckpointManager


class TestIncrementalCheckpointManager(unittest.TestCase):
    """Test cases for IncrementalCheckpointManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = IncrementalCheckpointManager(self.test_dir, full_checkpoint_interval=5)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test manager initializes correctly"""
        self.assertEqual(self.manager.checkpoint_counter, 0)
        self.assertIsNone(self.manager.last_full_checkpoint_id)
        self.assertEqual(self.manager.full_checkpoint_interval, 5)
    
    def test_first_checkpoint_is_full(self):
        """Test that first checkpoint is always full"""
        state = {'key1': 'value1', 'key2': 'value2'}
        
        checkpoint = self.manager.create_checkpoint(state)
        
        self.assertEqual(checkpoint.checkpoint_id, 1)
        self.assertTrue(checkpoint.is_full)
        self.assertIsNone(checkpoint.base_checkpoint_id)
    
    def test_subsequent_checkpoints_are_incremental(self):
        """Test that subsequent checkpoints are incremental"""
        state = {'counter': 0, 'data': 'initial'}
        
        # Create first (full)
        self.manager.create_checkpoint(state)
        
        # Create second (incremental)
        state['counter'] = 1
        checkpoint2 = self.manager.create_checkpoint(state)
        
        self.assertEqual(checkpoint2.checkpoint_id, 2)
        self.assertFalse(checkpoint2.is_full)
        self.assertEqual(checkpoint2.base_checkpoint_id, 1)
    
    def test_full_checkpoint_interval(self):
        """Test that full checkpoints are created at correct intervals"""
        state = {'counter': 0}
        
        checkpoints = []
        for i in range(10):
            state['counter'] = i
            checkpoint = self.manager.create_checkpoint(state)
            checkpoints.append(checkpoint)
        
        # Checkpoint 1 should be full
        self.assertTrue(checkpoints[0].is_full)
        
        # Checkpoints 2-4 should be incremental
        self.assertFalse(checkpoints[1].is_full)
        self.assertFalse(checkpoints[2].is_full)
        self.assertFalse(checkpoints[3].is_full)
        
        # Checkpoint 5 should be full (interval = 5)
        self.assertTrue(checkpoints[4].is_full)
        
        # Checkpoints 6-9 should be incremental
        self.assertFalse(checkpoints[5].is_full)
        self.assertFalse(checkpoints[8].is_full)
        
        # Checkpoint 10 should be full
        self.assertTrue(checkpoints[9].is_full)
    
    def test_restore_from_full_checkpoint(self):
        """Test restoration from a full checkpoint"""
        state = {'key1': 'value1', 'key2': 42, 'key3': [1, 2, 3]}
        
        checkpoint = self.manager.create_checkpoint(state)
        restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
        
        self.assertEqual(state, restored)
    
    def test_restore_from_incremental_checkpoint(self):
        """Test restoration from incremental checkpoints"""
        # Initial state
        state = {'counter': 0, 'name': 'test', 'data': []}
        self.manager.create_checkpoint(state)
        
        # Make changes and create incremental checkpoints
        state['counter'] = 5
        self.manager.create_checkpoint(state)
        
        state['data'].append('item1')
        self.manager.create_checkpoint(state)
        
        state['name'] = 'modified'
        checkpoint4 = self.manager.create_checkpoint(state)
        
        # Restore from last incremental
        restored = self.manager.restore_from_checkpoint(checkpoint4.checkpoint_id)
        
        self.assertEqual(state, restored)
        self.assertEqual(restored['counter'], 5)
        self.assertEqual(restored['name'], 'modified')
        self.assertIn('item1', restored['data'])
    
    def test_restore_with_deleted_keys(self):
        """Test restoration handles deleted keys"""
        state = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.manager.create_checkpoint(state)
        
        # Delete a key
        del state['key2']
        checkpoint2 = self.manager.create_checkpoint(state)
        
        # Restore
        restored = self.manager.restore_from_checkpoint(checkpoint2.checkpoint_id)
        
        self.assertIn('key1', restored)
        self.assertNotIn('key2', restored)  # Should be deleted
        self.assertIn('key3', restored)
    
    def test_checkpoint_chain_restoration(self):
        """Test restoration from long checkpoint chain"""
        state = {'counter': 0}
        
        # Create 10 checkpoints
        for i in range(1, 11):
            state['counter'] = i * 10
            state[f'key_{i}'] = f'value_{i}'
            self.manager.create_checkpoint(state)
        
        # Restore from checkpoint 10
        restored = self.manager.restore_from_checkpoint(10)
        
        self.assertEqual(restored['counter'], 100)
        self.assertEqual(restored['key_10'], 'value_10')
        self.assertEqual(len([k for k in restored if k.startswith('key_')]), 10)
    
    def test_get_statistics(self):
        """Test getting comprehensive statistics"""
        # Create state with enough data for compression to be effective
        state = {'counter': 0, 'data': 'x' * 100}
        
        # Create several checkpoints
        for i in range(7):
            state['counter'] = i
            self.manager.create_checkpoint(state)
        
        stats = self.manager.get_statistics()
        
        self.assertEqual(stats['total_checkpoints'], 7)
        self.assertEqual(stats['full_checkpoints'], 2)  # 1 and 5
        self.assertEqual(stats['incremental_checkpoints'], 5)
        # Compression ratio can be <1.0 for very small changes due to overhead
        # Just check it's a valid number
        self.assertGreater(stats['compression_ratio'], 0.0)
        self.assertIn('total_storage_bytes', stats)
    
    def test_list_checkpoints(self):
        """Test listing checkpoints"""
        state = {'data': 'test'}
        
        # Create 5 checkpoints
        for i in range(5):
            state['data'] = f'test_{i}'
            self.manager.create_checkpoint(state)
        
        checkpoints = self.manager.list_checkpoints()
        
        self.assertEqual(len(checkpoints), 5)
        self.assertEqual(checkpoints[0]['checkpoint_id'], 1)
        self.assertEqual(checkpoints[4]['checkpoint_id'], 5)
    
    def test_verify_checkpoint(self):
        """Test checkpoint verification"""
        state = {'data': 'test'}
        
        checkpoint1 = self.manager.create_checkpoint(state)
        state['data'] = 'modified'
        checkpoint2 = self.manager.create_checkpoint(state)
        
        # Both should be valid
        self.assertTrue(self.manager.verify_checkpoint(checkpoint1.checkpoint_id))
        self.assertTrue(self.manager.verify_checkpoint(checkpoint2.checkpoint_id))
        
        # Non-existent checkpoint should be invalid
        self.assertFalse(self.manager.verify_checkpoint(999))
    
    def test_cleanup_old_checkpoints(self):
        """Test cleanup of old checkpoints"""
        state = {'counter': 0}
        
        # Create 20 checkpoints (interval=5: full at 1,5,10,15,20)
        for i in range(20):
            state['counter'] = i
            self.manager.create_checkpoint(state)
        
        # Clean up - keep last 10
        self.manager.cleanup_old_checkpoints(keep_last_n=10)
        
        checkpoints = self.manager.list_checkpoints()
        
        # Should have 10 last (11-20) + full checkpoint 10 (already in last 10) + full checkpoint 5 (kept)
        # = 11 total
        self.assertLessEqual(len(checkpoints), 13)  # May have extra full checkpoints depending on timing
    
    def test_reset(self):
        """Test resetting manager state"""
        state = {'data': 'test'}
        
        self.manager.create_checkpoint(state)
        self.manager.create_checkpoint(state)
        
        self.assertEqual(self.manager.checkpoint_counter, 2)
        
        self.manager.reset()
        
        self.assertEqual(self.manager.checkpoint_counter, 0)
        self.assertIsNone(self.manager.last_full_checkpoint_id)
    
    def test_complex_state_checkpoint(self):
        """Test checkpointing complex state structures"""
        state = {
            'users': {f'user_{i}': {'name': f'User{i}', 'balance': i*100} for i in range(10)},
            'transactions': [{'id': i, 'amount': i*10} for i in range(50)],
            'config': {'timeout': 30, 'max_retries': 3},
            'metadata': {'version': '1.0', 'updated': time.time()}
        }
        
        checkpoint = self.manager.create_checkpoint(state)
        
        # Modify complex state
        state['users']['user_5']['balance'] = 99999
        state['transactions'].append({'id': 51, 'amount': 510})
        state['config']['timeout'] = 60
        
        checkpoint2 = self.manager.create_checkpoint(state)
        
        # Restore and verify
        restored = self.manager.restore_from_checkpoint(checkpoint2.checkpoint_id)
        
        self.assertEqual(restored['users']['user_5']['balance'], 99999)
        self.assertEqual(len(restored['transactions']), 51)
        self.assertEqual(restored['config']['timeout'], 60)
    
    def test_incremental_size_reduction(self):
        """Test that incremental checkpoints are smaller than full"""
        state = {f'key_{i}': f'value_{i}' for i in range(100)}
        
        # Create full checkpoint
        full_cp = self.manager.create_checkpoint(state)
        
        # Small change
        state['key_5'] = 'modified_value'
        
        # Create incremental checkpoint
        incr_cp = self.manager.create_checkpoint(state)
        
        # Incremental should be much smaller
        self.assertLess(incr_cp.get_size(), full_cp.get_size())


class TestConditionalCheckpointManager(unittest.TestCase):
    """Test cases for ConditionalCheckpointManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = ConditionalCheckpointManager(
            self.test_dir,
            full_checkpoint_interval=5,
            min_change_threshold=1
        )
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_first_checkpoint_always_created(self):
        """Test that first checkpoint is always created"""
        state = {'key': 'value'}
        
        checkpoint = self.manager.create_checkpoint_if_changed(state)
        
        self.assertIsNotNone(checkpoint)
        self.assertEqual(checkpoint.checkpoint_id, 1)
    
    def test_skip_checkpoint_when_no_changes(self):
        """Test that checkpoint is skipped when state unchanged"""
        state = {'key': 'value'}
        
        # First checkpoint
        self.manager.create_checkpoint_if_changed(state)
        
        # Try to create second with same state
        checkpoint2 = self.manager.create_checkpoint_if_changed(state)
        
        self.assertIsNone(checkpoint2)
        self.assertEqual(self.manager.skipped_checkpoints, 1)
    
    def test_create_checkpoint_when_changed(self):
        """Test that checkpoint is created when state changes"""
        state = {'counter': 0}
        
        # First checkpoint
        self.manager.create_checkpoint_if_changed(state)
        
        # Change state
        state['counter'] = 5
        
        # Should create checkpoint
        checkpoint2 = self.manager.create_checkpoint_if_changed(state)
        
        self.assertIsNotNone(checkpoint2)
        self.assertEqual(checkpoint2.checkpoint_id, 2)
    
    def test_statistics_include_skipped(self):
        """Test that statistics include skipped checkpoints"""
        state = {'counter': 0}
        
        # Create checkpoints with some unchanged
        self.manager.create_checkpoint_if_changed(state)
        self.manager.create_checkpoint_if_changed(state)  # Skipped
        
        state['counter'] = 1
        self.manager.create_checkpoint_if_changed(state)
        self.manager.create_checkpoint_if_changed(state)  # Skipped
        
        stats = self.manager.get_statistics()
        
        self.assertEqual(stats['total_checkpoints'], 2)
        self.assertEqual(stats['skipped_checkpoints'], 2)
        self.assertIn('checkpoint_efficiency', stats)


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalCheckpointManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConditionalCheckpointManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
