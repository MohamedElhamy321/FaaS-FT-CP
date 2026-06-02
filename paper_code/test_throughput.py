import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from throughput_benchmark import ThroughputBenchmark, generate_realistic_throughput_data

class TestThroughputBenchmark(unittest.TestCase):
    """Test cases for throughput benchmark"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.benchmark = ThroughputBenchmark()
    
    def test_benchmark_initialization(self):
        """Test benchmark initialization"""
        self.assertIsNotNone(self.benchmark.model)
        self.assertIsNotNone(self.benchmark.test_data)
        self.assertEqual(len(self.benchmark.techniques), 4)
        
        # Check all techniques are present
        expected_techniques = {'RR', 'AS', 'vanilla', 'CP'}
        self.assertEqual(set(self.benchmark.techniques.keys()), expected_techniques)
    
    def test_failure_injection(self):
        """Test failure injection behavior"""
        # Test different techniques' failure responses
        vanilla_rate = self.benchmark.inject_failure('vanilla')
        rr_rate = self.benchmark.inject_failure('RR')
        as_rate = self.benchmark.inject_failure('AS')
        cp_rate = self.benchmark.inject_failure('CP')
        
        # Vanilla should have the worst failure response
        self.assertLess(vanilla_rate, rr_rate)
        self.assertLess(vanilla_rate, as_rate)
        self.assertLess(vanilla_rate, cp_rate)
        
        # All rates should be between 0 and 1
        for rate in [vanilla_rate, rr_rate, as_rate, cp_rate]:
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)
    
    def test_measure_throughput_short(self):
        """Test throughput measurement for short duration"""
        # Test with very short duration for quick testing
        throughput_data = self.benchmark.measure_throughput('RR', duration=2.0)
        
        # Should have some throughput measurements
        self.assertGreater(len(throughput_data), 0)
        
        # All measurements should be non-negative
        for measurement in throughput_data:
            self.assertGreaterEqual(measurement, 0)

class TestThroughputDataGeneration(unittest.TestCase):
    """Test cases for throughput data generation"""
    
    def test_generate_realistic_data(self):
        """Test realistic throughput data generation"""
        results = generate_realistic_throughput_data()
        
        # Check all techniques are present
        expected_techniques = {'RR', 'AS', 'vanilla', 'CP'}
        self.assertEqual(set(results.keys()), expected_techniques)
        
        # Check data length (should be 600 seconds)
        for technique, data in results.items():
            self.assertEqual(len(data), 600)
            
            # All throughput values should be non-negative
            for value in data:
                self.assertGreaterEqual(value, 0)
    
    def test_failure_impact_on_vanilla(self):
        """Test that vanilla shows significant impact during failure"""
        results = generate_realistic_throughput_data()
        
        vanilla_data = results['vanilla']
        
        # Pre-failure period (0-280s)
        pre_failure = vanilla_data[:280]
        pre_failure_mean = np.mean(pre_failure)
        
        # During failure period (280-310s)
        during_failure = vanilla_data[280:310]
        during_failure_mean = np.mean(during_failure)
        
        # Vanilla should show significant throughput drop during failure
        throughput_ratio = during_failure_mean / pre_failure_mean
        self.assertLess(throughput_ratio, 0.5)  # Should drop to less than 50%
    
    def test_fault_tolerance_resilience(self):
        """Test that fault-tolerant techniques maintain better throughput"""
        results = generate_realistic_throughput_data()
        
        # During failure period (280-310s)
        failure_period = slice(280, 310)
        
        vanilla_failure = np.mean(results['vanilla'][failure_period])
        rr_failure = np.mean(results['RR'][failure_period])
        as_failure = np.mean(results['AS'][failure_period])
        cp_failure = np.mean(results['CP'][failure_period])
        
        # Fault-tolerant techniques should maintain higher throughput than vanilla
        self.assertGreater(rr_failure, vanilla_failure)
        self.assertGreater(as_failure, vanilla_failure)
        self.assertGreater(cp_failure, vanilla_failure)

def run_throughput_tests():
    """Run all throughput tests"""
    print("Running Throughput Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestThroughputBenchmark,
        TestThroughputDataGeneration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"Overall: {'PASSED' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    run_throughput_tests()
