import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from node_failure_throughput_benchmark import generate_node_failure_throughput_data, analyze_node_failure_impact

class TestNodeFailureBenchmark(unittest.TestCase):
    """Test cases for node failure throughput benchmark"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.results, self.time_points = generate_node_failure_throughput_data()
    
    def test_data_generation(self):
        """Test that data generation produces expected structure"""
        # Check all techniques are present
        expected_techniques = {'AS', 'RR', 'vanilla', 'CP'}
        self.assertEqual(set(self.results.keys()), expected_techniques)
        
        # Check data length (600 seconds)
        for technique, data in self.results.items():
            self.assertEqual(len(data), 600)
        
        # Check time points
        self.assertEqual(len(self.time_points), 600)
        self.assertEqual(self.time_points[0], 0)
        self.assertEqual(self.time_points[-1], 599)
    
    def test_as_spike_behavior(self):
        """Test that AS shows the characteristic spike during failure"""
        as_data = self.results['AS']
        
        # Pre-failure period (0-280s)
        pre_failure = as_data[:280]
        pre_failure_mean = np.mean(pre_failure)
        
        # During failure period (280-320s)
        during_failure = as_data[280:320]
        max_spike = max(during_failure)
        
        # AS should show significant spike (at least 5x normal)
        spike_ratio = max_spike / pre_failure_mean
        self.assertGreater(spike_ratio, 5.0, 
                          f"AS spike ratio {spike_ratio:.1f}x should be > 5x")
        
        # Spike should be substantial (over 500 req/sec)
        self.assertGreater(max_spike, 500, 
                          f"AS max spike {max_spike:.1f} should be > 500 req/sec")
    
    def test_rr_stability(self):
        """Test that RR maintains stable throughput"""
        rr_data = self.results['RR']
        
        # Calculate coefficient of variation (std/mean) for entire period
        rr_mean = np.mean(rr_data)
        rr_std = np.std(rr_data)
        cv = rr_std / rr_mean
        
        # RR should be relatively stable (CV < 0.1)
        self.assertLess(cv, 0.1, 
                       f"RR coefficient of variation {cv:.3f} should be < 0.1")
        
        # RR should not have extreme values
        rr_max = max(rr_data)
        rr_min = min(rr_data)
        range_ratio = (rr_max - rr_min) / rr_mean
        self.assertLess(range_ratio, 0.5,
                       f"RR range ratio {range_ratio:.3f} should be < 0.5")
    
    def test_vanilla_degradation(self):
        """Test that vanilla shows degradation during failure"""
        vanilla_data = self.results['vanilla']
        
        # Pre-failure period
        pre_failure = vanilla_data[:280]
        pre_failure_mean = np.mean(pre_failure)
        
        # During failure period
        during_failure = vanilla_data[280:320]
        during_failure_mean = np.mean(during_failure)
        
        # Vanilla should show degradation
        degradation_ratio = during_failure_mean / pre_failure_mean
        self.assertLess(degradation_ratio, 0.95,
                       f"Vanilla should show degradation, ratio {degradation_ratio:.3f}")
    
    def test_cp_recovery_pattern(self):
        """Test that CP shows appropriate recovery pattern"""
        cp_data = self.results['CP']
        
        # Pre-failure period
        pre_failure = cp_data[:280]
        pre_failure_mean = np.mean(pre_failure)
        
        # Post-recovery period (after 320s)
        post_recovery = cp_data[320:]
        post_recovery_mean = np.mean(post_recovery)
        
        # CP should recover to near pre-failure levels
        recovery_ratio = post_recovery_mean / pre_failure_mean
        self.assertGreater(recovery_ratio, 0.9,
                          f"CP should recover well, ratio {recovery_ratio:.3f}")
        self.assertLess(recovery_ratio, 1.1,
                       f"CP should not exceed pre-failure significantly")
    
    def test_all_positive_values(self):
        """Test that all throughput values are positive"""
        for technique, data in self.results.items():
            with self.subTest(technique=technique):
                for i, value in enumerate(data):
                    self.assertGreaterEqual(value, 0,
                                           f"{technique} has negative value {value} at time {i}")
    
    def test_reasonable_throughput_ranges(self):
        """Test that throughput values are in reasonable ranges"""
        for technique, data in self.results.items():
            with self.subTest(technique=technique):
                max_value = max(data)
                min_value = min(data)
                
                # Should not exceed 2000 req/sec (even for spikes)
                self.assertLessEqual(max_value, 2000,
                                    f"{technique} max {max_value:.1f} exceeds reasonable limit")
                
                # Should not go below 0
                self.assertGreaterEqual(min_value, 0,
                                       f"{technique} min {min_value:.1f} below zero")

def run_node_failure_tests():
    """Run all node failure tests"""
    print("Running Node Failure Benchmark Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    tests = loader.loadTestsFromTestCase(TestNodeFailureBenchmark)
    suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"Overall: {'PASSED' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    run_node_failure_tests()
