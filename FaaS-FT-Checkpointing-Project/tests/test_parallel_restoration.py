"""
Tests for Parallel Checkpoint Restoration
"""

import unittest
import time
import pickle
import tempfile
from incremental_checkpoint.parallel_restoration import (
    ParallelRestoration,
    DependencyGraph,
    RestorationTask
)
from incremental_checkpoint import IncrementalCheckpoint


class TestDependencyGraph(unittest.TestCase):
    """Test dependency graph analysis"""
    
    def test_simple_dependency_chain(self):
        """Test linear dependency chain"""
        graph = DependencyGraph()
        
        # Add checkpoints: 1 -> 2 -> 3
        graph.add_checkpoint(1, {'key1'}, set())
        graph.add_checkpoint(2, {'key2'}, {1})
        graph.add_checkpoint(3, {'key3'}, {2})
        
        groups = graph.get_parallelizable_groups()
        
        # Should have 3 sequential groups
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0], [1])
        self.assertEqual(groups[1], [2])
        self.assertEqual(groups[2], [3])
    
    def test_parallel_independent_checkpoints(self):
        """Test independent checkpoints can run in parallel"""
        graph = DependencyGraph()
        
        # Add independent checkpoints modifying different keys
        graph.add_checkpoint(1, {'key1'}, set())
        graph.add_checkpoint(2, {'key2'}, set())
        graph.add_checkpoint(3, {'key3'}, set())
        
        groups = graph.get_parallelizable_groups()
        
        # Should have 1 group with all 3 checkpoints
        self.assertEqual(len(groups), 1)
        self.assertEqual(set(groups[0]), {1, 2, 3})
    
    def test_conflicting_keys(self):
        """Test checkpoints with conflicting keys run sequentially"""
        graph = DependencyGraph()
        
        # Add checkpoints modifying same key
        graph.add_checkpoint(1, {'key1'}, set())
        graph.add_checkpoint(2, {'key1'}, set())
        
        groups = graph.get_parallelizable_groups()
        
        # Should have 2 sequential groups
        self.assertEqual(len(groups), 2)
    
    def test_mixed_dependencies(self):
        """Test mixed parallel and sequential execution"""
        graph = DependencyGraph()
        
        # 1 (key1) and 2 (key2) are independent
        # 3 (key3) depends on 1
        # 4 (key4) depends on 2
        graph.add_checkpoint(1, {'key1'}, set())
        graph.add_checkpoint(2, {'key2'}, set())
        graph.add_checkpoint(3, {'key3'}, {1})
        graph.add_checkpoint(4, {'key4'}, {2})
        
        groups = graph.get_parallelizable_groups()
        
        # Group 1: [1, 2] (parallel)
        # Group 2: [3, 4] (parallel)
        self.assertEqual(len(groups), 2)
        self.assertEqual(set(groups[0]), {1, 2})
        self.assertEqual(set(groups[1]), {3, 4})
    
    def test_parallelism_analysis(self):
        """Test parallelism potential analysis"""
        graph = DependencyGraph()
        
        graph.add_checkpoint(1, {'key1'}, set())
        graph.add_checkpoint(2, {'key2'}, set())
        graph.add_checkpoint(3, {'key1'}, {1})
        
        analysis = graph.analyze_parallelism_potential()
        
        self.assertEqual(analysis['total_checkpoints'], 3)
        self.assertEqual(analysis['total_groups'], 2)
        self.assertGreater(analysis['parallel_checkpoints'], 0)


class TestParallelRestoration(unittest.TestCase):
    """Test parallel restoration engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.restoration = ParallelRestoration(max_workers=4)
    
    def _create_checkpoint(self, checkpoint_id, is_full, state_or_delta):
        """Helper to create checkpoint"""
        data = pickle.dumps(state_or_delta)
        return IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=is_full,
            timestamp=time.time(),
            base_checkpoint_id=None if is_full else checkpoint_id - 1,
            data=data,
            metadata={}
        )
    
    def test_empty_checkpoint_chain(self):
        """Test restoration with empty checkpoint chain"""
        result = self.restoration.restore_checkpoint_chain([])
        
        self.assertEqual(result.final_state, {})
        self.assertEqual(result.checkpoints_applied, 0)
        self.assertEqual(result.speedup, 1.0)
    
    def test_single_full_checkpoint(self):
        """Test restoration with single full checkpoint"""
        checkpoint = self._create_checkpoint(1, True, {'key1': 'value1', 'key2': 'value2'})
        
        result = self.restoration.restore_checkpoint_chain([checkpoint])
        
        self.assertEqual(result.final_state, {'key1': 'value1', 'key2': 'value2'})
        self.assertEqual(result.checkpoints_applied, 1)
    
    def test_full_plus_incremental(self):
        """Test restoration with full + incremental checkpoint"""
        full_cp = self._create_checkpoint(1, True, {'key1': 'value1'})
        incr_cp = self._create_checkpoint(2, False, {'key2': 'value2'})
        
        result = self.restoration.restore_checkpoint_chain([full_cp, incr_cp])
        
        self.assertEqual(result.final_state, {'key1': 'value1', 'key2': 'value2'})
        self.assertEqual(result.checkpoints_applied, 2)
    
    def test_incremental_updates(self):
        """Test incremental updates are applied correctly"""
        full_cp = self._create_checkpoint(1, True, {'key1': 'v1', 'key2': 'v2'})
        incr1 = self._create_checkpoint(2, False, {'key1': 'v1_updated'})
        incr2 = self._create_checkpoint(3, False, {'key3': 'v3'})
        
        result = self.restoration.restore_checkpoint_chain([full_cp, incr1, incr2])
        
        self.assertEqual(result.final_state, {
            'key1': 'v1_updated',  # Updated by incr1
            'key2': 'v2',          # From full
            'key3': 'v3'           # Added by incr2
        })
        self.assertEqual(result.checkpoints_applied, 3)
    
    def test_parallel_execution_speedup(self):
        """Test parallel execution provides speedup"""
        # Create chain with independent incrementals
        full_cp = self._create_checkpoint(1, True, {'base': 'value'})
        
        # These should be parallelizable (different keys)
        incr_checkpoints = [
            self._create_checkpoint(i, False, {f'key{i}': f'value{i}'})
            for i in range(2, 10)
        ]
        
        checkpoints = [full_cp] + incr_checkpoints
        
        result = self.restoration.restore_checkpoint_chain(checkpoints)
        
        # Check state is correct
        expected_state = {'base': 'value'}
        expected_state.update({f'key{i}': f'value{i}' for i in range(2, 10)})
        self.assertEqual(result.final_state, expected_state)
        
        # Should have some parallel tasks
        self.assertGreater(result.parallel_tasks, 0)
    
    def test_conflicting_updates_sequential(self):
        """Test conflicting updates run sequentially"""
        full_cp = self._create_checkpoint(1, True, {'key1': 'v1'})
        
        # Both update same key - must be sequential
        incr1 = self._create_checkpoint(2, False, {'key1': 'v2'})
        incr2 = self._create_checkpoint(3, False, {'key1': 'v3'})
        
        result = self.restoration.restore_checkpoint_chain([full_cp, incr1, incr2])
        
        # Final value should be from last checkpoint
        self.assertEqual(result.final_state['key1'], 'v3')
        self.assertEqual(result.checkpoints_applied, 3)
    
    def test_large_checkpoint_chain(self):
        """Test performance with large checkpoint chain"""
        full_cp = self._create_checkpoint(1, True, {'base': 'value'})
        
        # Create 100 incremental checkpoints
        checkpoints = [full_cp]
        for i in range(2, 102):
            # Every 10th checkpoint updates same key (forces some sequencing)
            key = f'key{i % 10}'
            checkpoints.append(self._create_checkpoint(i, False, {key: f'value{i}'}))
        
        start_time = time.time()
        result = self.restoration.restore_checkpoint_chain(checkpoints)
        elapsed_ms = (time.time() - start_time) * 1000
        
        self.assertEqual(result.checkpoints_applied, 101)
        self.assertLess(elapsed_ms, 1000)  # Should complete within 1 second
    
    def test_metrics_tracking(self):
        """Test metrics are tracked correctly"""
        checkpoint = self._create_checkpoint(1, True, {'key1': 'value1'})
        
        # Reset metrics
        self.restoration.reset_metrics()
        
        # Perform restoration
        self.restoration.restore_checkpoint_chain([checkpoint])
        
        metrics = self.restoration.get_metrics()
        
        self.assertEqual(metrics['total_restorations'], 1)
        self.assertGreater(metrics['avg_time_ms'], 0)
    
    def test_base_state_provided(self):
        """Test restoration with provided base state"""
        base_state = {'existing': 'data'}
        incr_cp = self._create_checkpoint(1, False, {'new': 'data'})
        
        result = self.restoration.restore_checkpoint_chain([incr_cp], base_state)
        
        self.assertEqual(result.final_state, {
            'existing': 'data',
            'new': 'data'
        })
    
    def test_error_handling(self):
        """Test restoration handles errors gracefully"""
        # Create checkpoint with invalid data
        invalid_checkpoint = IncrementalCheckpoint(
            checkpoint_id=1,
            is_full=True,
            timestamp=time.time(),
            base_checkpoint_id=None,
            data=b'invalid_pickle_data',
            metadata={}
        )
        
        # Should not crash
        result = self.restoration.restore_checkpoint_chain([invalid_checkpoint])
        
        # Should return empty state (couldn't restore)
        self.assertIsInstance(result.final_state, dict)


class TestRestorationPerformance(unittest.TestCase):
    """Performance benchmarks for parallel restoration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.restoration = ParallelRestoration(max_workers=4)
    
    def _create_checkpoint(self, checkpoint_id, is_full, state_or_delta):
        """Helper to create checkpoint"""
        data = pickle.dumps(state_or_delta)
        return IncrementalCheckpoint(
            checkpoint_id=checkpoint_id,
            is_full=is_full,
            timestamp=time.time(),
            base_checkpoint_id=None if is_full else checkpoint_id - 1,
            data=data,
            metadata={}
        )
    
    def test_speedup_with_independent_checkpoints(self):
        """Test speedup with many independent checkpoints"""
        full_cp = self._create_checkpoint(1, True, {})
        
        # Create 50 independent checkpoints (different keys)
        checkpoints = [full_cp]
        for i in range(2, 52):
            checkpoints.append(self._create_checkpoint(i, False, {f'key{i}': f'value{i}'}))
        
        result = self.restoration.restore_checkpoint_chain(checkpoints)
        
        print(f"\n[Performance Test: Independent Checkpoints]")
        print(f"  Checkpoints: {result.checkpoints_applied}")
        print(f"  Total time: {result.total_time_ms:.2f}ms")
        print(f"  Parallel tasks: {result.parallel_tasks}")
        print(f"  Sequential tasks: {result.sequential_tasks}")
        print(f"  Speedup: {result.speedup:.2f}x")
        
        # Should achieve significant speedup
        self.assertGreater(result.speedup, 1.5)
        self.assertGreater(result.parallel_tasks, result.sequential_tasks)
    
    def test_speedup_with_mixed_dependencies(self):
        """Test speedup with mixed parallel and sequential"""
        full_cp = self._create_checkpoint(1, True, {})
        
        checkpoints = [full_cp]
        for i in range(2, 32):
            # Every 5th checkpoint updates shared key (creates dependencies)
            if i % 5 == 0:
                key = 'shared_key'
            else:
                key = f'key{i}'
            checkpoints.append(self._create_checkpoint(i, False, {key: f'value{i}'}))
        
        result = self.restoration.restore_checkpoint_chain(checkpoints)
        
        print(f"\n[Performance Test: Mixed Dependencies]")
        print(f"  Checkpoints: {result.checkpoints_applied}")
        print(f"  Total time: {result.total_time_ms:.2f}ms")
        print(f"  Parallel tasks: {result.parallel_tasks}")
        print(f"  Sequential tasks: {result.sequential_tasks}")
        print(f"  Speedup: {result.speedup:.2f}x")
        print(f"  Conflicts: {result.conflicts_detected}")
        
        # Should still achieve speedup despite some dependencies
        self.assertGreater(result.speedup, 1.0)
    
    def test_restoration_time_reasonable(self):
        """Test restoration time is reasonable"""
        full_cp = self._create_checkpoint(1, True, {'data': 'x' * 1000})
        
        checkpoints = [full_cp]
        for i in range(2, 21):
            checkpoints.append(self._create_checkpoint(i, False, {f'key{i}': 'x' * 100}))
        
        start_time = time.time()
        result = self.restoration.restore_checkpoint_chain(checkpoints)
        elapsed_ms = (time.time() - start_time) * 1000
        
        print(f"\n[Performance Test: Restoration Time]")
        print(f"  Checkpoints: {result.checkpoints_applied}")
        print(f"  Total time: {elapsed_ms:.2f}ms")
        print(f"  Avg per checkpoint: {elapsed_ms / result.checkpoints_applied:.2f}ms")
        
        # Should complete quickly
        self.assertLess(elapsed_ms, 500)  # Less than 500ms for 20 checkpoints


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
