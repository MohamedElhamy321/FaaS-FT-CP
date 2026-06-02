"""
Tests for Predictive Checkpoint Scheduling
"""

import unittest
import time
from unittest.mock import Mock, patch

from incremental_checkpoint.predictive_scheduler import (
    LoadMonitor,
    WorkloadAnalyzer,
    CheckpointPredictor,
    AdaptiveScheduler,
    PredictiveCheckpointManager,
    SystemLoad,
    LoadLevel,
    WorkloadPattern,
    SchedulingStrategy
)


class TestSystemLoad(unittest.TestCase):
    """Test SystemLoad"""
    
    def test_load_level_idle(self):
        """Test idle load level detection"""
        load = SystemLoad(time.time(), cpu_percent=10, memory_percent=15)
        self.assertEqual(load.load_level(), LoadLevel.IDLE)
    
    def test_load_level_high(self):
        """Test high load level detection"""
        load = SystemLoad(time.time(), cpu_percent=70, memory_percent=75)
        self.assertEqual(load.load_level(), LoadLevel.HIGH)
    
    def test_load_level_critical(self):
        """Test critical load level detection"""
        load = SystemLoad(time.time(), cpu_percent=85, memory_percent=90)
        self.assertEqual(load.load_level(), LoadLevel.CRITICAL)
    
    def test_is_suitable_for_checkpoint(self):
        """Test checkpoint suitability"""
        idle_load = SystemLoad(time.time(), cpu_percent=10, memory_percent=15)
        high_load = SystemLoad(time.time(), cpu_percent=85, memory_percent=90)
        
        self.assertTrue(idle_load.is_suitable_for_checkpoint())
        self.assertFalse(high_load.is_suitable_for_checkpoint())


class TestLoadMonitor(unittest.TestCase):
    """Test LoadMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LoadMonitor(history_size=100)
    
    def test_record_load(self):
        """Test recording load samples"""
        load = self.monitor.record_load(request_rate=10.0)
        
        self.assertIsNotNone(load)
        self.assertGreaterEqual(load.cpu_percent, 0)
        self.assertGreaterEqual(load.memory_percent, 0)
        self.assertEqual(load.request_rate, 10.0)
    
    def test_get_current_load(self):
        """Test getting current load"""
        self.assertIsNone(self.monitor.get_current_load())
        
        self.monitor.record_load()
        current = self.monitor.get_current_load()
        
        self.assertIsNotNone(current)
    
    def test_load_history_size_limit(self):
        """Test history size limit"""
        monitor = LoadMonitor(history_size=10)
        
        # Record more than limit
        for i in range(20):
            monitor.record_load(request_rate=float(i))
        
        # Should only keep last 10
        self.assertEqual(len(monitor.load_history), 10)
    
    def test_get_avg_load(self):
        """Test average load calculation"""
        # Record several samples
        for _ in range(5):
            self.monitor.record_load()
            time.sleep(0.01)
        
        avg_load = self.monitor.get_avg_load(window_seconds=60)
        
        self.assertIsNotNone(avg_load)
        self.assertGreaterEqual(avg_load.cpu_percent, 0)
        self.assertGreaterEqual(avg_load.memory_percent, 0)
    
    def test_predict_load_trend_stable(self):
        """Test stable load trend detection"""
        # Create stable load pattern
        for _ in range(15):
            # Mock constant load
            with patch('psutil.cpu_percent', return_value=50.0):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = 50.0
                    self.monitor.record_load()
        
        trend = self.monitor.predict_load_trend()
        self.assertEqual(trend, "stable")
    
    def test_predict_load_trend_increasing(self):
        """Test increasing load trend detection"""
        # Create increasing load pattern
        for i in range(15):
            with patch('psutil.cpu_percent', return_value=float(30 + i * 5)):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = float(30 + i * 5)
                    self.monitor.record_load()
        
        trend = self.monitor.predict_load_trend()
        self.assertEqual(trend, "increasing")


class TestWorkloadAnalyzer(unittest.TestCase):
    """Test WorkloadAnalyzer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LoadMonitor()
        self.analyzer = WorkloadAnalyzer(self.monitor)
    
    def test_insufficient_data(self):
        """Test pattern analysis with insufficient data"""
        pattern = self.analyzer.analyze_patterns()
        
        self.assertEqual(pattern.pattern_type, "insufficient_data")
        self.assertEqual(pattern.confidence, 0.0)
    
    def test_steady_pattern_detection(self):
        """Test steady workload pattern detection"""
        # Create steady load pattern
        for _ in range(150):
            with patch('psutil.cpu_percent', return_value=50.0):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = 50.0
                    self.monitor.record_load(request_rate=100.0)
        
        pattern = self.analyzer.analyze_patterns()
        
        self.assertEqual(pattern.pattern_type, "steady")
        self.assertGreater(pattern.confidence, 0.5)
    
    def test_bursty_pattern_detection(self):
        """Test bursty workload pattern detection"""
        # Create bursty load pattern (high variance)
        for i in range(150):
            load_value = 20.0 if i % 2 == 0 else 80.0
            with patch('psutil.cpu_percent', return_value=load_value):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = load_value
                    self.monitor.record_load()
        
        pattern = self.analyzer.analyze_patterns()
        
        self.assertEqual(pattern.pattern_type, "bursty")
        self.assertGreater(pattern.confidence, 0.5)
    
    def test_identify_idle_periods(self):
        """Test idle period identification"""
        # Create pattern with idle periods
        for i in range(150):
            load_value = 10.0 if i < 50 or i > 100 else 70.0
            with patch('psutil.cpu_percent', return_value=load_value):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = load_value
                    self.monitor.record_load()
        
        idle_periods = self.analyzer.identify_idle_periods()
        
        # Should detect at least some idle periods
        self.assertGreater(len(idle_periods), 0)


class TestCheckpointPredictor(unittest.TestCase):
    """Test CheckpointPredictor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LoadMonitor()
        self.analyzer = WorkloadAnalyzer(self.monitor)
        self.predictor = CheckpointPredictor(self.monitor, self.analyzer)
    
    def test_minimum_interval_enforcement(self):
        """Test minimum interval is enforced"""
        schedule = self.predictor.predict_optimal_time(min_interval=60.0)
        
        self.assertFalse(schedule.should_checkpoint)
        self.assertIn("Too soon", schedule.reason)
    
    def test_checkpoint_allowed_after_interval(self):
        """Test checkpoint allowed after minimum interval"""
        # Simulate time passing
        self.predictor.last_checkpoint_time = time.time() - 120.0
        
        # Mock suitable load
        with patch('psutil.cpu_percent', return_value=30.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 30.0
                self.monitor.record_load()
        
        schedule = self.predictor.predict_optimal_time(min_interval=60.0)
        
        self.assertTrue(schedule.should_checkpoint)
    
    def test_defer_during_high_load(self):
        """Test checkpoint deferred during high load"""
        self.predictor.last_checkpoint_time = time.time() - 120.0
        
        # Mock high load
        with patch('psutil.cpu_percent', return_value=85.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 85.0
                self.monitor.record_load()
        
        schedule = self.predictor.predict_optimal_time(min_interval=60.0)
        
        self.assertFalse(schedule.should_checkpoint)
        self.assertIn("high", schedule.reason.lower())
        self.assertGreater(schedule.recommended_delay_seconds, 0)
    
    def test_checkpoint_during_idle(self):
        """Test checkpoint recommended during idle"""
        self.predictor.last_checkpoint_time = time.time() - 120.0
        
        # Create bursty pattern
        for i in range(150):
            load_value = 20.0 if i % 2 == 0 else 80.0
            with patch('psutil.cpu_percent', return_value=load_value):
                with patch('psutil.virtual_memory') as mock_mem:
                    mock_mem.return_value.percent = load_value
                    self.monitor.record_load()
        
        # Now simulate idle period
        with patch('psutil.cpu_percent', return_value=10.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 10.0
                self.monitor.record_load()
        
        schedule = self.predictor.predict_optimal_time(min_interval=60.0)
        
        # Should recommend checkpoint during idle
        if schedule.should_checkpoint:
            self.assertIn("Idle", schedule.reason)


class TestAdaptiveScheduler(unittest.TestCase):
    """Test AdaptiveScheduler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = LoadMonitor()
        self.analyzer = WorkloadAnalyzer(self.monitor)
        self.predictor = CheckpointPredictor(self.monitor, self.analyzer)
        self.scheduler = AdaptiveScheduler(
            self.predictor,
            base_interval=300.0,
            min_interval=60.0,
            max_interval=600.0
        )
    
    def test_forced_checkpoint(self):
        """Test forced checkpoint"""
        schedule = self.scheduler.should_checkpoint(force=True)
        
        self.assertTrue(schedule.should_checkpoint)
        self.assertEqual(schedule.reason, "Forced checkpoint")
        self.assertEqual(schedule.priority, "critical")
    
    def test_statistics_tracking(self):
        """Test statistics are tracked"""
        initial_stats = self.scheduler.get_statistics()
        initial_scheduled = initial_stats['checkpoints_scheduled']
        
        # Mock suitable load
        self.predictor.last_checkpoint_time = time.time() - 120.0
        with patch('psutil.cpu_percent', return_value=30.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value.percent = 30.0
                self.monitor.record_load()
        
        # Request checkpoint
        self.scheduler.should_checkpoint()
        
        stats = self.scheduler.get_statistics()
        
        self.assertGreaterEqual(stats['checkpoints_scheduled'] + stats['checkpoints_deferred'], 
                               initial_scheduled + 1)
    
    def test_interval_adjustment_steady(self):
        """Test interval adjustment for steady workload"""
        pattern = WorkloadPattern(pattern_type="steady", confidence=0.8)
        
        initial_interval = self.scheduler.current_interval
        self.scheduler.adjust_interval(pattern)
        
        # Should increase interval for steady workload
        self.assertGreater(self.scheduler.current_interval, initial_interval)
    
    def test_interval_adjustment_bursty(self):
        """Test interval adjustment for bursty workload"""
        pattern = WorkloadPattern(pattern_type="bursty", confidence=0.8)
        
        self.scheduler.current_interval = 300.0
        self.scheduler.adjust_interval(pattern)
        
        # Should decrease interval for bursty workload
        self.assertLess(self.scheduler.current_interval, 300.0)
    
    def test_overhead_reduction_estimate(self):
        """Test overhead reduction calculation"""
        # Simulate some deferrals
        self.scheduler.checkpoints_scheduled = 70
        self.scheduler.checkpoints_deferred = 30
        
        stats = self.scheduler.get_statistics()
        
        self.assertAlmostEqual(stats['defer_rate'], 0.3)
        self.assertAlmostEqual(stats['overhead_reduction_estimate'], 30.0)


class TestPredictiveCheckpointManager(unittest.TestCase):
    """Test PredictiveCheckpointManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = PredictiveCheckpointManager(
            base_interval=300.0,
            strategy=SchedulingStrategy.HYBRID,
            enable_prediction=True
        )
    
    def tearDown(self):
        """Clean up"""
        self.manager.stop_monitoring()
    
    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsNotNone(self.manager.load_monitor)
        self.assertIsNotNone(self.manager.workload_analyzer)
        self.assertIsNotNone(self.manager.predictor)
        self.assertIsNotNone(self.manager.scheduler)
    
    def test_monitoring_start_stop(self):
        """Test monitoring lifecycle"""
        self.assertFalse(self.manager._monitoring)
        
        self.manager.start_monitoring(interval=0.1)
        self.assertTrue(self.manager._monitoring)
        
        # Wait for some samples
        time.sleep(0.3)
        
        # Should have collected samples
        self.assertGreater(len(self.manager.load_monitor.load_history), 0)
        
        self.manager.stop_monitoring()
        self.assertFalse(self.manager._monitoring)
    
    def test_should_checkpoint_with_prediction(self):
        """Test checkpoint decision with prediction enabled"""
        schedule = self.manager.should_checkpoint_now()
        
        self.assertIsNotNone(schedule)
        self.assertIsNotNone(schedule.reason)
    
    def test_should_checkpoint_without_prediction(self):
        """Test checkpoint decision without prediction"""
        manager = PredictiveCheckpointManager(enable_prediction=False)
        
        schedule = manager.should_checkpoint_now()
        
        self.assertTrue(schedule.should_checkpoint)
        self.assertIn("disabled", schedule.reason.lower())
    
    def test_performance_report(self):
        """Test performance report generation"""
        # Collect some samples first
        for _ in range(5):
            self.manager.load_monitor.record_load()
        
        report = self.manager.get_performance_report()
        
        self.assertIn('strategy', report)
        self.assertIn('prediction_enabled', report)
        self.assertIn('current_load', report)
        self.assertIn('workload_pattern', report)
        self.assertIn('scheduler_statistics', report)
        self.assertEqual(report['strategy'], 'hybrid')
        self.assertTrue(report['prediction_enabled'])


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_end_to_end_scheduling(self):
        """Test complete scheduling workflow"""
        manager = PredictiveCheckpointManager(base_interval=10.0)
        
        try:
            # Start monitoring
            manager.start_monitoring(interval=0.1)
            
            # Wait for data collection
            time.sleep(0.5)
            
            # Make scheduling decisions
            decisions = []
            for _ in range(5):
                schedule = manager.should_checkpoint_now()
                decisions.append(schedule)
                time.sleep(0.1)
            
            # Should have made decisions
            self.assertEqual(len(decisions), 5)
            
            # Get performance report
            report = manager.get_performance_report()
            
            self.assertGreater(report['samples_collected'], 0)
            self.assertIn('scheduler_statistics', report)
            
        finally:
            manager.stop_monitoring()


if __name__ == '__main__':
    unittest.main(verbosity=2)
