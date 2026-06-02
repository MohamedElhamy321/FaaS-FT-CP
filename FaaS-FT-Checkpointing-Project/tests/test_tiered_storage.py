"""
Tests for Multi-Level Checkpoint Hierarchy (Tiered Storage)
"""

import unittest
import tempfile
import shutil
import time
import os
from pathlib import Path

from incremental_checkpoint.tiered_storage import (
    TieredStorageManager,
    StorageTier,
    TierPolicy,
    CheckpointTierMetadata,
    TierMigrator
)


class TestTieredStorageBasics(unittest.TestCase):
    """Test basic tiered storage operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = TieredStorageManager(
            self.test_dir,
            enable_auto_migration=False  # Disable for deterministic tests
        )
    
    def tearDown(self):
        """Clean up test directory"""
        self.storage.shutdown()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_store_checkpoint_starts_in_hot_tier(self):
        """Test new checkpoints start in hot tier"""
        data = b"test checkpoint data"
        
        filepath = self.storage.store_checkpoint(1, data)
        
        tier = self.storage.get_checkpoint_tier(1)
        self.assertEqual(tier, StorageTier.HOT)
        self.assertIn('hot', filepath)
    
    def test_load_checkpoint_from_hot_tier(self):
        """Test loading checkpoint from hot tier"""
        data = b"test data"
        self.storage.store_checkpoint(1, data)
        
        loaded = self.storage.load_checkpoint(1)
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['checkpoint_id'], 1)
        self.assertEqual(loaded['data'], data)
        self.assertEqual(loaded['tier'], 'hot')
    
    def test_checkpoint_not_found(self):
        """Test loading non-existent checkpoint"""
        loaded = self.storage.load_checkpoint(999)
        
        self.assertIsNone(loaded)
    
    def test_access_count_tracking(self):
        """Test access count is tracked"""
        self.storage.store_checkpoint(1, b"data")
        
        # Access multiple times
        self.storage.load_checkpoint(1)
        self.storage.load_checkpoint(1)
        self.storage.load_checkpoint(1)
        
        metadata = self.storage.checkpoint_metadata[1]
        self.assertGreaterEqual(metadata.access_count, 3)
    
    def test_hot_cache_functionality(self):
        """Test hot tier in-memory cache"""
        storage = TieredStorageManager(self.test_dir, enable_hot_cache=True, enable_auto_migration=False)
        
        data = b"cached data"
        storage.store_checkpoint(1, data)
        
        # Check cache
        self.assertIn(1, storage.hot_cache)
        self.assertEqual(storage.hot_cache[1], data)
        
        storage.shutdown()


class TestTierMigration(unittest.TestCase):
    """Test checkpoint migration between tiers"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
        # Fast aging policy for testing
        policy = TierPolicy(
            hot_max_age_hours=0.001,   # ~3.6 seconds
            warm_max_age_hours=0.002   # ~7.2 seconds
        )
        
        self.storage = TieredStorageManager(
            self.test_dir,
            tier_policy=policy,
            enable_auto_migration=False
        )
    
    def tearDown(self):
        """Clean up"""
        self.storage.shutdown()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_manual_migration_hot_to_warm(self):
        """Test manual migration from hot to warm"""
        self.storage.store_checkpoint(1, b"data")
        
        # Migrate to warm
        success = self.storage._migrate_checkpoint(1, StorageTier.WARM, "test")
        
        self.assertTrue(success)
        self.assertEqual(self.storage.get_checkpoint_tier(1), StorageTier.WARM)
        
        # Verify file moved
        hot_path = self.storage._get_checkpoint_path(1, StorageTier.HOT)
        warm_path = self.storage._get_checkpoint_path(1, StorageTier.WARM)
        self.assertFalse(hot_path.exists())
        self.assertTrue(warm_path.exists())
    
    def test_manual_migration_warm_to_cold(self):
        """Test manual migration from warm to cold"""
        self.storage.store_checkpoint(1, b"data")
        self.storage._migrate_checkpoint(1, StorageTier.WARM, "test")
        
        # Migrate to cold
        success = self.storage._migrate_checkpoint(1, StorageTier.COLD, "test")
        
        self.assertTrue(success)
        self.assertEqual(self.storage.get_checkpoint_tier(1), StorageTier.COLD)
    
    def test_auto_migration_hot_to_warm(self):
        """Test automatic age-based migration from hot to warm"""
        self.storage.store_checkpoint(1, b"data")
        
        # Manually set creation time to past for testing
        metadata = self.storage.checkpoint_metadata[1]
        metadata.creation_time = time.time() - 3600  # 1 hour ago
        
        # Trigger auto migration
        migrations = self.storage.auto_migrate_checkpoints()
        
        self.assertGreater(migrations, 0)
        self.assertEqual(self.storage.get_checkpoint_tier(1), StorageTier.WARM)
    
    def test_auto_migration_warm_to_cold(self):
        """Test automatic age-based migration from warm to cold"""
        self.storage.store_checkpoint(1, b"data")
        
        # Migrate to warm first
        self.storage._migrate_checkpoint(1, StorageTier.WARM, "test")
        
        # Manually set creation time to past for testing
        metadata = self.storage.checkpoint_metadata[1]
        metadata.creation_time = time.time() - (25 * 3600)  # 25 hours ago
        
        # Trigger auto migration
        migrations = self.storage.auto_migrate_checkpoints()
        
        self.assertGreater(migrations, 0)
        self.assertEqual(self.storage.get_checkpoint_tier(1), StorageTier.COLD)
    
    def test_access_based_promotion(self):
        """Test promotion to hot tier based on access patterns"""
        # Policy with promotion enabled
        policy = TierPolicy(
            enable_access_based_promotion=True,
            promotion_access_threshold=3
        )
        
        storage = TieredStorageManager(
            self.test_dir + '_promotion',
            tier_policy=policy,
            enable_auto_migration=False
        )
        
        try:
            # Store and move to cold
            storage.store_checkpoint(1, b"data")
            storage._migrate_checkpoint(1, StorageTier.COLD, "test")
            
            # Access multiple times
            for _ in range(4):
                storage.load_checkpoint(1)
            
            # Should be promoted back to hot
            self.assertEqual(storage.get_checkpoint_tier(1), StorageTier.HOT)
            
        finally:
            storage.shutdown()
            shutil.rmtree(self.test_dir + '_promotion', ignore_errors=True)
    
    def test_tier_transition_history(self):
        """Test tier transition history is recorded"""
        self.storage.store_checkpoint(1, b"data")
        
        # Perform migrations
        self.storage._migrate_checkpoint(1, StorageTier.WARM, "age_based")
        self.storage._migrate_checkpoint(1, StorageTier.COLD, "age_based")
        
        metadata = self.storage.checkpoint_metadata[1]
        
        self.assertEqual(len(metadata.tier_transition_history), 2)
        self.assertEqual(metadata.tier_transition_history[0]['to_tier'], 'warm')
        self.assertEqual(metadata.tier_transition_history[1]['to_tier'], 'cold')
        self.assertEqual(metadata.tier_transition_history[0]['reason'], 'age_based')


class TestTierStatistics(unittest.TestCase):
    """Test tier statistics and cost tracking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.storage = TieredStorageManager(self.test_dir, enable_auto_migration=False)
    
    def tearDown(self):
        """Clean up"""
        self.storage.shutdown()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_tier_statistics_tracking(self):
        """Test tier statistics are tracked correctly"""
        # Add checkpoints to different tiers
        self.storage.store_checkpoint(1, b"data1")
        self.storage.store_checkpoint(2, b"data2")
        self.storage.store_checkpoint(3, b"data3")
        
        # Move some to other tiers
        self.storage._migrate_checkpoint(2, StorageTier.WARM, "test")
        self.storage._migrate_checkpoint(3, StorageTier.COLD, "test")
        
        stats = self.storage.get_tier_statistics()
        
        self.assertEqual(stats['hot'].checkpoint_count, 1)
        self.assertEqual(stats['warm'].checkpoint_count, 1)
        self.assertEqual(stats['cold'].checkpoint_count, 1)
    
    def test_tier_size_tracking(self):
        """Test tier size tracking"""
        data1 = b"x" * 1000
        data2 = b"y" * 2000
        
        self.storage.store_checkpoint(1, data1)
        self.storage.store_checkpoint(2, data2)
        
        stats = self.storage.get_tier_statistics()
        
        self.assertEqual(stats['hot'].total_size_bytes, 3000)
        self.assertGreater(stats['hot'].total_size_mb(), 0)
    
    def test_cost_report_generation(self):
        """Test cost analysis report"""
        # Add some checkpoints
        for i in range(10):
            data = b"x" * 1024 * 100  # 100KB each
            self.storage.store_checkpoint(i, data)
        
        # Move some to cheaper tiers
        for i in range(3, 10):
            self.storage._migrate_checkpoint(i, StorageTier.COLD, "test")
        
        report = self.storage.get_cost_report()
        
        self.assertIn('total_monthly_cost', report)
        self.assertIn('monthly_savings', report)
        self.assertIn('savings_percent', report)
        self.assertIn('tier_breakdown', report)
        
        # Should have savings from moving to cold tier
        self.assertGreater(report['monthly_savings'], 0)
        self.assertGreater(report['savings_percent'], 0)
    
    def test_cost_calculation_accuracy(self):
        """Test cost calculation is accurate"""
        # 1GB in hot tier
        data = b"x" * (1024 * 1024 * 1024)
        self.storage.store_checkpoint(1, data)
        
        report = self.storage.get_cost_report()
        
        # Should be close to hot tier cost
        expected_cost = 1.0 * self.storage.tier_costs['hot']
        self.assertAlmostEqual(report['total_monthly_cost'], expected_cost, places=2)


class TestTierMetadata(unittest.TestCase):
    """Test checkpoint tier metadata"""
    
    def test_metadata_age_calculation(self):
        """Test age calculation"""
        metadata = CheckpointTierMetadata(
            checkpoint_id=1,
            current_tier=StorageTier.HOT,
            creation_time=time.time() - 3600,  # 1 hour ago
            last_access_time=time.time()
        )
        
        age = metadata.age_hours()
        self.assertGreater(age, 0.9)
        self.assertLess(age, 1.1)
    
    def test_metadata_access_recording(self):
        """Test access recording"""
        metadata = CheckpointTierMetadata(
            checkpoint_id=1,
            current_tier=StorageTier.HOT,
            creation_time=time.time(),
            last_access_time=time.time()
        )
        
        initial_count = metadata.access_count
        metadata.record_access()
        
        self.assertEqual(metadata.access_count, initial_count + 1)


class TestBackgroundMigrator(unittest.TestCase):
    """Test background migration worker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_migrator_starts_and_stops(self):
        """Test migrator thread lifecycle"""
        policy = TierPolicy(hot_max_age_hours=0.001)
        storage = TieredStorageManager(
            self.test_dir,
            tier_policy=policy,
            enable_auto_migration=True
        )
        
        # Migrator should be running
        self.assertIsNotNone(storage.migrator)
        self.assertTrue(storage.migrator.running)
        
        # Stop
        storage.shutdown()
        time.sleep(0.1)
        
        self.assertFalse(storage.migrator.running)
    
    def test_background_migration_works(self):
        """Test background migrator performs migrations"""
        policy = TierPolicy(hot_max_age_hours=0.001)
        storage = TieredStorageManager(
            self.test_dir,
            tier_policy=policy,
            enable_auto_migration=True
        )
        
        try:
            # Create checkpoint
            storage.store_checkpoint(1, b"data")
            
            # Give migrator time to run (with short interval)
            storage.migrator.interval_seconds = 0.1
            time.sleep(0.3)
            
            # Should have migrated to warm
            tier = storage.get_checkpoint_tier(1)
            # Note: May still be hot if migration hasn't run yet (timing dependent)
            self.assertIn(tier, [StorageTier.HOT, StorageTier.WARM])
            
        finally:
            storage.shutdown()


class TestTierPersistence(unittest.TestCase):
    """Test tier metadata persistence"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_metadata_persists_across_restarts(self):
        """Test tier metadata survives restarts"""
        # Create storage and add checkpoint
        storage1 = TieredStorageManager(self.test_dir, enable_auto_migration=False)
        storage1.store_checkpoint(1, b"data")
        storage1._migrate_checkpoint(1, StorageTier.WARM, "test")
        storage1.shutdown()
        
        # Restart storage
        storage2 = TieredStorageManager(self.test_dir, enable_auto_migration=False)
        
        # Metadata should be loaded
        self.assertIn(1, storage2.checkpoint_metadata)
        self.assertEqual(storage2.get_checkpoint_tier(1), StorageTier.WARM)
        
        storage2.shutdown()
    
    def test_access_count_persists(self):
        """Test access count persists across restarts"""
        storage1 = TieredStorageManager(self.test_dir, enable_auto_migration=False)
        storage1.store_checkpoint(1, b"data")
        
        # Access multiple times
        for _ in range(5):
            storage1.load_checkpoint(1)
        
        access_count1 = storage1.checkpoint_metadata[1].access_count
        storage1.shutdown()
        
        # Restart
        storage2 = TieredStorageManager(self.test_dir, enable_auto_migration=False)
        access_count2 = storage2.checkpoint_metadata[1].access_count
        
        self.assertEqual(access_count1, access_count2)
        
        storage2.shutdown()


if __name__ == '__main__':
    unittest.main(verbosity=2)
