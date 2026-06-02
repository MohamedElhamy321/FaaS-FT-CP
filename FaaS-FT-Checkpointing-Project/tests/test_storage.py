"""
Unit tests for Checkpoint Storage
"""

import sys
import os
import time
import unittest
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from incremental_checkpoint.storage import IncrementalCheckpoint, CheckpointStorageManager


class TestIncrementalCheckpoint(unittest.TestCase):
    """Test cases for IncrementalCheckpoint class"""
    
    def test_create_full_checkpoint(self):
        """Test creating a full checkpoint"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'test_data',
            metadata={'key': 'value'}
        )
        
        self.assertEqual(checkpoint.checkpoint_id, 1)
        self.assertTrue(checkpoint.is_full)
        self.assertIsNone(checkpoint.base_checkpoint_id)
        self.assertEqual(checkpoint.get_type(), 'full')
    
    def test_create_incremental_checkpoint(self):
        """Test creating an incremental checkpoint"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=2,
            is_full=False,
            timestamp=time.time(),
            base_checkpoint_id=1,
            data=b'incremental_data',
            metadata={'changes': 5}
        )
        
        self.assertEqual(checkpoint.checkpoint_id, 2)
        self.assertFalse(checkpoint.is_full)
        self.assertEqual(checkpoint.base_checkpoint_id, 1)
        self.assertEqual(checkpoint.get_type(), 'incremental')
    
    def test_to_dict(self):
        """Test serialization to dictionary"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=123456.789,
            base_checkpoint_id=None,
            data=b'data',
            metadata={'test': True}
        )
        
        data = checkpoint.to_dict()
        
        self.assertEqual(data['checkpoint_id'], 1)
        self.assertTrue(data['is_full'])
        self.assertEqual(data['timestamp'], 123456.789)
        self.assertIsNone(data['base_checkpoint_id'])
        self.assertEqual(data['data'], b'data')
    
    def test_from_dict(self):
        """Test deserialization from dictionary"""
        data = {
            'checkpoint_id': 1,
            'is_full': True,
            'timestamp': 123456.789,
            'base_checkpoint_id': None,
            'data': b'data',
            'metadata': {'test': True},
            'version': '1.0'
        }
        
        checkpoint = IncrementalCheckpoint.from_dict(data)
        
        self.assertEqual(checkpoint.checkpoint_id, 1)
        self.assertTrue(checkpoint.is_full)
        self.assertEqual(checkpoint.timestamp, 123456.789)
    
    def test_get_size(self):
        """Test getting checkpoint size"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'12345',
            metadata={}
        )
        
        self.assertEqual(checkpoint.get_size(), 5)


class TestCheckpointStorageManager(unittest.TestCase):
    """Test cases for CheckpointStorageManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = CheckpointStorageManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test storage manager initializes correctly"""
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertEqual(len(self.storage.checkpoint_index), 0)
    
    def test_store_and_load_checkpoint(self):
        """Test storing and loading a checkpoint"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'test_checkpoint_data',
            metadata={'version': '1.0'}
        )
        
        # Store
        filepath = self.storage.store_checkpoint(checkpoint)
        self.assertTrue(os.path.exists(filepath))
        
        # Load
        loaded = self.storage.load_checkpoint(1)
        self.assertEqual(loaded.checkpoint_id, checkpoint.checkpoint_id)
        self.assertEqual(loaded.data, checkpoint.data)
        self.assertEqual(loaded.metadata, checkpoint.metadata)
    
    def test_load_nonexistent_checkpoint(self):
        """Test loading a checkpoint that doesn't exist"""
        with self.assertRaises(ValueError):
            self.storage.load_checkpoint(999)
    
    def test_checkpoint_chain(self):
        """Test getting checkpoint chain"""
        # Create proper chain: full checkpoint 1, then incrementals 2, 3, 4
        # Each incremental references the previous checkpoint (forming a linked chain)
        checkpoints = [
            IncrementalCheckpoint(1, True, time.time(), None, b'full_1', {}),
            IncrementalCheckpoint(2, False, time.time(), 1, b'incr_2', {}),  # references 1
            IncrementalCheckpoint(3, False, time.time(), 2, b'incr_3', {}),  # references 2
            IncrementalCheckpoint(4, False, time.time(), 3, b'incr_4', {})   # references 3
        ]
        
        for cp in checkpoints:
            self.storage.store_checkpoint(cp)
        
        # Get chain for checkpoint 4
        chain = self.storage.get_checkpoint_chain(4)
        
        # Should return [full_1, incr_2, incr_3, incr_4]
        self.assertEqual(len(chain), 4)
        self.assertTrue(chain[0].is_full)
        self.assertEqual(chain[0].checkpoint_id, 1)
        self.assertEqual(chain[-1].checkpoint_id, 4)
    
    def test_checkpoint_chain_broken(self):
        """Test getting chain when it's broken"""
        # Create incremental without base
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=2,
            is_full=False,
            timestamp=time.time(),
            base_checkpoint_id=1,  # Doesn't exist
            data=b'incr_2',
            metadata={}
        )
        
        self.storage.store_checkpoint(checkpoint)
        
        with self.assertRaises(ValueError):
            self.storage.get_checkpoint_chain(2)
    
    def test_list_checkpoints(self):
        """Test listing all checkpoints"""
        # Create multiple checkpoints
        checkpoints = [
            IncrementalCheckpoint(1, True, time.time(), None, b'data1', {}),
            IncrementalCheckpoint(2, False, time.time(), 1, b'data2', {}),
            IncrementalCheckpoint(3, False, time.time(), 1, b'data3', {})
        ]
        
        for cp in checkpoints:
            self.storage.store_checkpoint(cp)
        
        listed = self.storage.list_checkpoints()
        
        self.assertEqual(len(listed), 3)
        self.assertEqual(listed[0]['checkpoint_id'], 1)
        self.assertEqual(listed[0]['type'], 'full')
        self.assertEqual(listed[1]['type'], 'incremental')
    
    def test_delete_checkpoint(self):
        """Test deleting a checkpoint"""
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'data',
            metadata={}
        )
        
        filepath = self.storage.store_checkpoint(checkpoint)
        self.assertTrue(os.path.exists(filepath))
        
        # Delete
        result = self.storage.delete_checkpoint(1)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(filepath))
        
        # Try to load - should fail
        with self.assertRaises(ValueError):
            self.storage.load_checkpoint(1)
    
    def test_delete_nonexistent_checkpoint(self):
        """Test deleting a checkpoint that doesn't exist"""
        result = self.storage.delete_checkpoint(999)
        self.assertFalse(result)
    
    def test_cleanup_old_checkpoints(self):
        """Test cleanup of old checkpoints"""
        # Create 15 checkpoints
        for i in range(1, 16):
            checkpoint = IncrementalCheckpoint(
                checkpoint_id=i,
                is_full=(i % 5 == 0),  # Every 5th is full
                timestamp=time.time() + i,
                base_checkpoint_id=None if (i % 5 == 0) else ((i // 5) * 5),
                data=f'data_{i}'.encode(),
                metadata={}
            )
            self.storage.store_checkpoint(checkpoint)
        
        # Keep last 10, keep all full
        self.storage.cleanup_old_checkpoints(keep_last_n=10, keep_all_full=True)
        
        remaining = self.storage.list_checkpoints()
        
        # Should have: checkpoints 6-15 (10 last) + checkpoint 5 (full, kept even though old)
        # = 11 total (6,7,8,9,10,11,12,13,14,15 + 5)
        self.assertEqual(len(remaining), 11)
        
        # Full checkpoints should still exist
        ids = [cp['checkpoint_id'] for cp in remaining]
        self.assertIn(5, ids)  # Full checkpoint kept despite being outside last 10
        self.assertIn(10, ids)
        self.assertIn(15, ids)
    
    def test_get_storage_statistics(self):
        """Test getting storage statistics"""
        # Create checkpoints
        full_data = b'x' * 1000
        incr_data = b'x' * 100
        
        checkpoints = [
            IncrementalCheckpoint(1, True, time.time(), None, full_data, {}),
            IncrementalCheckpoint(2, False, time.time(), 1, incr_data, {}),
            IncrementalCheckpoint(3, False, time.time(), 1, incr_data, {})
        ]
        
        for cp in checkpoints:
            self.storage.store_checkpoint(cp)
        
        stats = self.storage.get_storage_statistics()
        
        self.assertEqual(stats['total_checkpoints'], 3)
        self.assertEqual(stats['full_checkpoints'], 1)
        self.assertEqual(stats['incremental_checkpoints'], 2)
        self.assertEqual(stats['total_size_bytes'], 1200)
        self.assertGreater(stats['size_reduction_ratio'], 1.0)
    
    def test_verify_checkpoint_chain(self):
        """Test verifying checkpoint chain"""
        # Valid chain
        checkpoints = [
            IncrementalCheckpoint(1, True, time.time(), None, b'data1', {}),
            IncrementalCheckpoint(2, False, time.time(), 1, b'data2', {})
        ]
        
        for cp in checkpoints:
            self.storage.store_checkpoint(cp)
        
        self.assertTrue(self.storage.verify_checkpoint_chain(2))
        
        # Invalid chain (missing base)
        invalid = IncrementalCheckpoint(
            checkpoint_id=10,
            is_full=False,
            timestamp=time.time(),
            base_checkpoint_id=99,  # Doesn't exist
            data=b'data',
            metadata={}
        )
        self.storage.store_checkpoint(invalid)
        
        self.assertFalse(self.storage.verify_checkpoint_chain(10))
    
    def test_index_persistence(self):
        """Test that index persists across instances"""
        # Create checkpoint
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'data',
            metadata={}
        )
        
        self.storage.store_checkpoint(checkpoint)
        
        # Create new storage instance with same path
        new_storage = CheckpointStorageManager(self.test_dir)
        
        # Should be able to load checkpoint
        loaded = new_storage.load_checkpoint(1)
        self.assertEqual(loaded.checkpoint_id, 1)
    
    def test_multiple_checkpoint_chains(self):
        """Test managing multiple checkpoint chains"""
        # Chain 1: 1 (full) -> 2 -> 3 (each references previous)
        # Chain 2: 10 (full) -> 11 -> 12 (each references previous)
        
        chain1 = [
            IncrementalCheckpoint(1, True, time.time(), None, b'full_1', {}),
            IncrementalCheckpoint(2, False, time.time(), 1, b'incr_2', {}),   # references 1
            IncrementalCheckpoint(3, False, time.time(), 2, b'incr_3', {})    # references 2
        ]
        
        chain2 = [
            IncrementalCheckpoint(10, True, time.time(), None, b'full_10', {}),
            IncrementalCheckpoint(11, False, time.time(), 10, b'incr_11', {}),  # references 10
            IncrementalCheckpoint(12, False, time.time(), 11, b'incr_12', {})   # references 11
        ]
        
        for cp in chain1 + chain2:
            self.storage.store_checkpoint(cp)
        
        # Verify both chains
        chain1_loaded = self.storage.get_checkpoint_chain(3)
        self.assertEqual(len(chain1_loaded), 3)
        self.assertEqual(chain1_loaded[0].checkpoint_id, 1)
        
        chain2_loaded = self.storage.get_checkpoint_chain(12)
        self.assertEqual(len(chain2_loaded), 3)
        self.assertEqual(chain2_loaded[0].checkpoint_id, 10)


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalCheckpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestCheckpointStorageManager))
    
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
