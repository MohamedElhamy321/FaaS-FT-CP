"""
Tests for Distributed Checkpoint Coordination
"""

import unittest
import time
from unittest.mock import Mock, MagicMock

from incremental_checkpoint.distributed_coordinator import (
    RaftNode,
    DistributedCheckpointCoordinator,
    DistributedLockManager,
    NodeState,
    MessageType,
    LogEntry,
    CheckpointCoordination
)


class TestRaftNode(unittest.TestCase):
    """Test Raft consensus node"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cluster_nodes = [
            ("node1", "localhost", 5001),
            ("node2", "localhost", 5002),
            ("node3", "localhost", 5003)
        ]
        self.node = RaftNode("node1", self.cluster_nodes, election_timeout_range=(100, 200))
    
    def tearDown(self):
        """Clean up"""
        self.node.stop()
    
    def test_initialization(self):
        """Test node initialization"""
        self.assertEqual(self.node.node_id, "node1")
        self.assertEqual(self.node.state, NodeState.FOLLOWER)
        self.assertEqual(self.node.current_term, 0)
        self.assertIsNone(self.node.voted_for)
        self.assertEqual(len(self.node.cluster_nodes), 3)
    
    def test_start_stop(self):
        """Test starting and stopping node"""
        self.assertFalse(self.node.running)
        
        self.node.start()
        self.assertTrue(self.node.running)
        self.assertIsNotNone(self.node.election_thread)
        
        self.node.stop()
        self.assertFalse(self.node.running)
    
    def test_election_timeout_reset(self):
        """Test election timeout randomization"""
        timeout1 = self.node._reset_election_timeout()
        timeout2 = self.node._reset_election_timeout()
        
        # Should be in range
        self.assertGreaterEqual(timeout1, 0.1)
        self.assertLessEqual(timeout1, 0.2)
        
        # Should be random (might be equal but unlikely)
        # Just check it's callable
        self.assertIsInstance(timeout1, float)
    
    def test_become_leader(self):
        """Test transitioning to leader"""
        self.node._become_leader()
        
        self.assertEqual(self.node.state, NodeState.LEADER)
        self.assertEqual(self.node.leader_id, "node1")
        self.assertEqual(len(self.node.next_index), 2)  # Other nodes
        self.assertEqual(len(self.node.match_index), 2)
    
    def test_receive_heartbeat(self):
        """Test receiving heartbeat"""
        initial_time = self.node.last_heartbeat
        time.sleep(0.01)  # Ensure time difference
        
        self.node.receive_heartbeat(term=1, leader_id="node2")
        
        self.assertEqual(self.node.current_term, 1)
        self.assertEqual(self.node.leader_id, "node2")
        self.assertEqual(self.node.state, NodeState.FOLLOWER)
        self.assertGreaterEqual(self.node.last_heartbeat, initial_time)
    
    def test_is_leader(self):
        """Test leader check"""
        self.assertFalse(self.node.is_leader())
        
        self.node._become_leader()
        self.assertTrue(self.node.is_leader())
    
    def test_append_log_entry(self):
        """Test appending log entries"""
        # Cannot append as follower
        result = self.node.append_log_entry("test", {"data": "value"})
        self.assertFalse(result)
        self.assertEqual(len(self.node.log), 0)
        
        # Can append as leader
        self.node._become_leader()
        result = self.node.append_log_entry("test", {"data": "value"})
        self.assertTrue(result)
        self.assertEqual(len(self.node.log), 1)
        
        entry = self.node.log[0]
        self.assertEqual(entry.command, "test")
        self.assertEqual(entry.data["data"], "value")
        self.assertEqual(entry.index, 1)
    
    def test_initiate_checkpoint(self):
        """Test checkpoint initiation"""
        # Cannot initiate as follower
        result = self.node.initiate_checkpoint("cp1", {"node1", "node2"})
        self.assertIsNone(result)
        
        # Can initiate as leader
        self.node._become_leader()
        result = self.node.initiate_checkpoint("cp1", {"node1", "node2"})
        
        self.assertIsNotNone(result)
        self.assertIn(result, self.node.pending_checkpoints)
        
        coordination = self.node.pending_checkpoints[result]
        self.assertEqual(coordination.checkpoint_id, "cp1")
        self.assertEqual(coordination.coordinator_node, "node1")
        self.assertEqual(coordination.participating_nodes, {"node1", "node2"})
        self.assertEqual(coordination.status, "initiated")
    
    def test_report_checkpoint_complete(self):
        """Test reporting checkpoint completion"""
        self.node._become_leader()
        coord_id = self.node.initiate_checkpoint("cp1", {"node1", "node2"})
        
        # Report completion from nodes
        self.node.report_checkpoint_complete(coord_id, "node1", True)
        coordination = self.node.get_checkpoint_status(coord_id)
        self.assertIn("node1", coordination.completed_nodes)
        self.assertEqual(coordination.status, "initiated")
        
        self.node.report_checkpoint_complete(coord_id, "node2", True)
        coordination = self.node.get_checkpoint_status(coord_id)
        self.assertIn("node2", coordination.completed_nodes)
        self.assertEqual(coordination.status, "completed")
    
    def test_checkpoint_failure(self):
        """Test checkpoint failure handling"""
        self.node._become_leader()
        coord_id = self.node.initiate_checkpoint("cp1", {"node1", "node2"})
        
        # Report failure
        self.node.report_checkpoint_complete(coord_id, "node1", False)
        coordination = self.node.get_checkpoint_status(coord_id)
        self.assertEqual(coordination.status, "failed")


class TestDistributedCheckpointCoordinator(unittest.TestCase):
    """Test distributed checkpoint coordinator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cluster_nodes = [
            ("node1", "localhost", 5001),
            ("node2", "localhost", 5002),
            ("node3", "localhost", 5003)
        ]
        
        # Mock checkpoint manager
        self.checkpoint_manager = Mock()
        self.checkpoint_manager.create_checkpoint = Mock(return_value=Mock(checkpoint_id=1))
        
        self.coordinator = DistributedCheckpointCoordinator(
            "node1",
            self.cluster_nodes,
            self.checkpoint_manager
        )
    
    def tearDown(self):
        """Clean up"""
        self.coordinator.stop()
    
    def test_initialization(self):
        """Test coordinator initialization"""
        self.assertEqual(self.coordinator.node_id, "node1")
        self.assertIsNotNone(self.coordinator.raft_node)
        self.assertEqual(self.coordinator.stats['coordinated_checkpoints'], 0)
    
    def test_start_stop(self):
        """Test starting and stopping"""
        self.coordinator.start()
        self.assertTrue(self.coordinator.raft_node.running)
        
        self.coordinator.stop()
        self.assertFalse(self.coordinator.raft_node.running)
    
    def test_create_coordinated_checkpoint_follower(self):
        """Test checkpoint creation as follower"""
        result = self.coordinator.create_coordinated_checkpoint({"state": "test"})
        
        # Cannot coordinate as follower
        self.assertIsNone(result)
        self.assertEqual(self.coordinator.stats['coordinated_checkpoints'], 0)
    
    def test_create_coordinated_checkpoint_leader(self):
        """Test checkpoint creation as leader"""
        # Make this node the leader
        self.coordinator.raft_node._become_leader()
        
        result = self.coordinator.create_coordinated_checkpoint({"state": "test"})
        
        self.assertIsNotNone(result)
        self.assertEqual(self.coordinator.stats['coordinated_checkpoints'], 1)
        self.checkpoint_manager.create_checkpoint.assert_called_once()
    
    def test_wait_for_coordination(self):
        """Test waiting for coordination completion"""
        # Make leader and create checkpoint
        self.coordinator.raft_node._become_leader()
        coord_id = self.coordinator.create_coordinated_checkpoint(
            {"state": "test"},
            {"node1"}
        )
        
        # Should complete quickly since only this node
        result = self.coordinator.wait_for_coordination(coord_id, timeout=2.0)
        self.assertTrue(result)
        self.assertEqual(self.coordinator.stats['successful_coordinations'], 1)
    
    def test_wait_for_coordination_timeout(self):
        """Test coordination timeout"""
        result = self.coordinator.wait_for_coordination("nonexistent", timeout=0.1)
        self.assertFalse(result)
        self.assertEqual(self.coordinator.stats['failed_coordinations'], 1)
    
    def test_get_cluster_status(self):
        """Test getting cluster status"""
        status = self.coordinator.get_cluster_status()
        
        self.assertEqual(status['node_id'], "node1")
        self.assertIn('is_leader', status)
        self.assertIn('state', status)
        self.assertIn('term', status)
        self.assertIn('cluster_size', status)
        self.assertIn('statistics', status)
        self.assertEqual(status['cluster_size'], 3)
    
    def test_is_leader(self):
        """Test leader check"""
        self.assertFalse(self.coordinator.is_leader())
        
        self.coordinator.raft_node._become_leader()
        self.assertTrue(self.coordinator.is_leader())
    
    def test_get_leader_id(self):
        """Test getting leader ID"""
        self.coordinator.raft_node._become_leader()
        
        leader_id = self.coordinator.get_leader_id()
        self.assertEqual(leader_id, "node1")


class TestDistributedLockManager(unittest.TestCase):
    """Test distributed lock manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        cluster_nodes = [
            ("node1", "localhost", 5001),
            ("node2", "localhost", 5002)
        ]
        self.raft_node = RaftNode("node1", cluster_nodes)
        self.raft_node._become_leader()
        
        self.lock_manager = DistributedLockManager(self.raft_node)
    
    def tearDown(self):
        """Clean up"""
        self.raft_node.stop()
    
    def test_acquire_lock(self):
        """Test acquiring lock"""
        result = self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        
        self.assertTrue(result)
        self.assertTrue(self.lock_manager.is_locked("test_lock"))
        self.assertEqual(self.lock_manager.get_lock_holder("test_lock"), "node1")
    
    def test_acquire_already_held_lock(self):
        """Test acquiring already held lock"""
        # Acquire lock
        self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        
        # Try to acquire again (should succeed for same holder)
        result = self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        self.assertTrue(result)
    
    def test_acquire_lock_contention(self):
        """Test lock contention"""
        # Node1 acquires lock
        self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        
        # Node2 tries to acquire (should timeout)
        result = self.lock_manager.acquire_lock("test_lock", "node2", timeout=0.1)
        self.assertFalse(result)
    
    def test_release_lock(self):
        """Test releasing lock"""
        self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        
        result = self.lock_manager.release_lock("test_lock", "node1")
        self.assertTrue(result)
        self.assertFalse(self.lock_manager.is_locked("test_lock"))
    
    def test_release_not_held_lock(self):
        """Test releasing lock not held"""
        result = self.lock_manager.release_lock("test_lock", "node1")
        self.assertFalse(result)
    
    def test_release_wrong_holder(self):
        """Test releasing lock held by another node"""
        self.lock_manager.acquire_lock("test_lock", "node1", timeout=1.0)
        
        result = self.lock_manager.release_lock("test_lock", "node2")
        self.assertFalse(result)
        self.assertTrue(self.lock_manager.is_locked("test_lock"))
    
    def test_multiple_locks(self):
        """Test managing multiple locks"""
        self.lock_manager.acquire_lock("lock1", "node1", timeout=1.0)
        self.lock_manager.acquire_lock("lock2", "node1", timeout=1.0)
        
        self.assertTrue(self.lock_manager.is_locked("lock1"))
        self.assertTrue(self.lock_manager.is_locked("lock2"))
        
        self.lock_manager.release_lock("lock1", "node1")
        self.assertFalse(self.lock_manager.is_locked("lock1"))
        self.assertTrue(self.lock_manager.is_locked("lock2"))


class TestIntegration(unittest.TestCase):
    """Integration tests for distributed coordination"""
    
    def test_multi_node_coordination(self):
        """Test coordination across multiple nodes"""
        cluster_nodes = [
            ("node1", "localhost", 5001),
            ("node2", "localhost", 5002),
            ("node3", "localhost", 5003)
        ]
        
        # Create coordinators
        manager1 = Mock()
        manager1.create_checkpoint = Mock(return_value=Mock(checkpoint_id=1))
        
        coordinator1 = DistributedCheckpointCoordinator("node1", cluster_nodes, manager1)
        coordinator1.start()
        
        try:
            # Make node1 leader
            coordinator1.raft_node._become_leader()
            
            # Create coordinated checkpoint
            coord_id = coordinator1.create_coordinated_checkpoint(
                {"state": "test"},
                {"node1"}
            )
            
            self.assertIsNotNone(coord_id)
            
            # Wait for completion
            result = coordinator1.wait_for_coordination(coord_id, timeout=2.0)
            self.assertTrue(result)
            
            # Check statistics
            stats = coordinator1.get_cluster_status()
            self.assertEqual(stats['statistics']['coordinated_checkpoints'], 1)
            self.assertEqual(stats['statistics']['successful_coordinations'], 1)
            
        finally:
            coordinator1.stop()


if __name__ == '__main__':
    unittest.main(verbosity=2)
