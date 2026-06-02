"""
Unit tests for StateChangeTracker
"""

import sys
import os
import time
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.state_tracker import StateChangeTracker


class TestStateChangeTracker(unittest.TestCase):
    """Test cases for StateChangeTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = StateChangeTracker()
    
    def test_initialization(self):
        """Test tracker initializes with empty state"""
        self.assertEqual(len(self.tracker.previous_state_hash), 0)
        self.assertEqual(len(self.tracker.changed_keys), 0)
        self.assertEqual(len(self.tracker.change_log), 0)
        self.assertIsNone(self.tracker.baseline_timestamp)
    
    def test_update_baseline(self):
        """Test baseline update stores state hashes"""
        state = {'key1': 'value1', 'key2': 42, 'key3': [1, 2, 3]}
        self.tracker.update_baseline(state)
        
        self.assertEqual(len(self.tracker.previous_state_hash), 3)
        self.assertIsNotNone(self.tracker.baseline_timestamp)
    
    def test_track_no_changes(self):
        """Test tracking identical state returns empty changes"""
        state = {'key1': 'value1', 'key2': 42}
        self.tracker.update_baseline(state)
        
        changes = self.tracker.track_changes(state)
        self.assertEqual(len(changes), 0)
    
    def test_track_modified_values(self):
        """Test tracking modified values"""
        initial_state = {'counter': 0, 'name': 'test'}
        self.tracker.update_baseline(initial_state)
        
        modified_state = {'counter': 5, 'name': 'test'}
        changes = self.tracker.track_changes(modified_state)
        
        self.assertEqual(len(changes), 1)
        self.assertIn('counter', changes)
        self.assertEqual(changes['counter'], 5)
        self.assertNotIn('name', changes)  # Unchanged
    
    def test_track_added_keys(self):
        """Test tracking new keys"""
        initial_state = {'key1': 'value1'}
        self.tracker.update_baseline(initial_state)
        
        new_state = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        changes = self.tracker.track_changes(new_state)
        
        self.assertEqual(len(changes), 2)
        self.assertIn('key2', changes)
        self.assertIn('key3', changes)
        self.assertEqual(changes['key2'], 'value2')
    
    def test_track_deleted_keys(self):
        """Test tracking deleted keys"""
        initial_state = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
        self.tracker.update_baseline(initial_state)
        
        new_state = {'key1': 'value1'}
        changes = self.tracker.track_changes(new_state)
        
        self.assertIn('__deleted_key2', changes)
        self.assertIn('__deleted_key3', changes)
        self.assertIsNone(changes['__deleted_key2'])
    
    def test_track_mixed_changes(self):
        """Test tracking mixed changes (add, modify, delete)"""
        initial_state = {'key1': 'old', 'key2': 'unchanged', 'key3': 'delete_me'}
        self.tracker.update_baseline(initial_state)
        
        new_state = {'key1': 'new', 'key2': 'unchanged', 'key4': 'added'}
        changes = self.tracker.track_changes(new_state)
        
        # Should have: modified key1, deleted key3, added key4
        self.assertIn('key1', changes)
        self.assertEqual(changes['key1'], 'new')
        self.assertIn('key4', changes)
        self.assertIn('__deleted_key3', changes)
        self.assertNotIn('key2', changes)  # Unchanged
    
    def test_hash_calculation_consistency(self):
        """Test hash calculation is consistent"""
        value = "test_value_123"
        hash1 = self.tracker._calculate_hash(value)
        hash2 = self.tracker._calculate_hash(value)
        
        self.assertEqual(hash1, hash2)
    
    def test_hash_calculation_different_values(self):
        """Test different values produce different hashes"""
        hash1 = self.tracker._calculate_hash("value1")
        hash2 = self.tracker._calculate_hash("value2")
        
        self.assertNotEqual(hash1, hash2)
    
    def test_hash_large_values(self):
        """Test hash calculation handles large values efficiently"""
        large_value = "x" * 20000  # 20KB string
        
        start_time = time.time()
        hash_value = self.tracker._calculate_hash(large_value)
        elapsed = time.time() - start_time
        
        self.assertIsNotNone(hash_value)
        self.assertLess(elapsed, 0.1)  # Should be fast (<100ms)
    
    def test_get_change_statistics_empty(self):
        """Test statistics with no changes"""
        stats = self.tracker.get_change_statistics()
        
        self.assertEqual(stats['total_changes'], 0)
        self.assertEqual(stats['unique_keys_changed'], 0)
        self.assertEqual(stats['changes_by_type']['added'], 0)
        self.assertEqual(stats['changes_by_type']['modified'], 0)
        self.assertEqual(stats['changes_by_type']['deleted'], 0)
    
    def test_get_change_statistics_with_changes(self):
        """Test statistics after tracking changes"""
        initial_state = {'key1': 'old', 'key2': 'delete'}
        self.tracker.update_baseline(initial_state)
        
        new_state = {'key1': 'new', 'key3': 'added'}
        self.tracker.track_changes(new_state)
        
        stats = self.tracker.get_change_statistics()
        
        self.assertEqual(stats['total_changes'], 3)  # 1 modified, 1 deleted, 1 added
        self.assertEqual(stats['unique_keys_changed'], 3)
        self.assertGreater(stats['change_rate'], 0)
    
    def test_get_changed_keys(self):
        """Test getting set of changed keys"""
        initial_state = {'key1': 'old'}
        self.tracker.update_baseline(initial_state)
        
        new_state = {'key1': 'new', 'key2': 'added'}
        self.tracker.track_changes(new_state)
        
        changed_keys = self.tracker.get_changed_keys()
        
        self.assertIn('key1', changed_keys)
        self.assertIn('key2', changed_keys)
        self.assertEqual(len(changed_keys), 2)
    
    def test_has_changes_true(self):
        """Test has_changes returns True when state differs"""
        initial_state = {'key1': 'value1'}
        self.tracker.update_baseline(initial_state)
        
        modified_state = {'key1': 'value2'}
        
        self.assertTrue(self.tracker.has_changes(modified_state))
    
    def test_has_changes_false(self):
        """Test has_changes returns False when state is identical"""
        initial_state = {'key1': 'value1', 'key2': 42}
        self.tracker.update_baseline(initial_state)
        
        same_state = {'key1': 'value1', 'key2': 42}
        
        self.assertFalse(self.tracker.has_changes(same_state))
    
    def test_has_changes_no_baseline(self):
        """Test has_changes returns True when no baseline exists"""
        state = {'key1': 'value1'}
        self.assertTrue(self.tracker.has_changes(state))
    
    def test_reset(self):
        """Test reset clears all tracking data"""
        state = {'key1': 'value1'}
        self.tracker.update_baseline(state)
        self.tracker.track_changes({'key1': 'value2'})
        
        self.tracker.reset()
        
        self.assertEqual(len(self.tracker.previous_state_hash), 0)
        self.assertEqual(len(self.tracker.changed_keys), 0)
        self.assertEqual(len(self.tracker.change_log), 0)
        self.assertIsNone(self.tracker.baseline_timestamp)
    
    def test_complex_data_structures(self):
        """Test tracking changes in complex data structures"""
        initial_state = {
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'tuple': (1, 2, 3),
            'set': {1, 2, 3}
        }
        self.tracker.update_baseline(initial_state)
        
        modified_state = {
            'list': [1, 2, 3, 4],  # Modified
            'dict': {'nested': 'value'},  # Unchanged
            'tuple': (1, 2, 3),  # Unchanged
            'set': {1, 2, 3, 4}  # Modified
        }
        changes = self.tracker.track_changes(modified_state)
        
        self.assertIn('list', changes)
        self.assertIn('set', changes)
        self.assertNotIn('dict', changes)
        self.assertNotIn('tuple', changes)
    
    def test_performance_10k_keys(self):
        """Test performance with 10,000 keys"""
        # Create large state
        large_state = {f'key_{i}': f'value_{i}' for i in range(10000)}
        self.tracker.update_baseline(large_state)
        
        # Modify a few keys
        modified_state = large_state.copy()
        modified_state['key_100'] = 'modified_value'
        modified_state['key_5000'] = 'modified_value'
        
        start_time = time.time()
        changes = self.tracker.track_changes(modified_state)
        elapsed = time.time() - start_time
        
        self.assertEqual(len(changes), 2)
        self.assertLess(elapsed, 0.1)  # Should complete in <100ms
    
    def test_estimate_size(self):
        """Test size estimation"""
        small_value = "test"
        large_value = "x" * 10000
        
        small_size = self.tracker._estimate_size(small_value)
        large_size = self.tracker._estimate_size(large_value)
        
        self.assertGreater(large_size, small_size)
        self.assertGreater(small_size, 0)


class TestStateChangeTrackerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = StateChangeTracker()
    
    def test_empty_state(self):
        """Test tracking empty state"""
        self.tracker.update_baseline({})
        changes = self.tracker.track_changes({})
        
        self.assertEqual(len(changes), 0)
    
    def test_none_values(self):
        """Test handling None values"""
        initial_state = {'key1': None, 'key2': 'value'}
        self.tracker.update_baseline(initial_state)
        
        modified_state = {'key1': 'value', 'key2': None}
        changes = self.tracker.track_changes(modified_state)
        
        self.assertIn('key1', changes)
        self.assertIn('key2', changes)
    
    def test_numeric_types(self):
        """Test different numeric types"""
        initial_state = {'int': 42, 'float': 3.14, 'bool': True}
        self.tracker.update_baseline(initial_state)
        
        # Same values should produce no changes
        same_state = {'int': 42, 'float': 3.14, 'bool': True}
        changes = self.tracker.track_changes(same_state)
        
        self.assertEqual(len(changes), 0)
    
    def test_special_characters_in_keys(self):
        """Test keys with special characters"""
        state = {'key-with-dash': 1, 'key_with_underscore': 2, 'key.with.dot': 3}
        self.tracker.update_baseline(state)
        
        modified_state = {'key-with-dash': 2, 'key_with_underscore': 2, 'key.with.dot': 3}
        changes = self.tracker.track_changes(modified_state)
        
        self.assertIn('key-with-dash', changes)


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestStateChangeTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestStateChangeTrackerEdgeCases))
    
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
