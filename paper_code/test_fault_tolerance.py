import unittest
import torch
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import PaperModel
from fault_tolerance import RequestReplication, ActiveStandby, VanillaExecution, CheckpointingTechnique

class TestFaultToleranceTechniques(unittest.TestCase):
    """Test cases for fault tolerance techniques"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = PaperModel(input_size=784, hidden_size=64, num_classes=10)
        self.test_data = torch.randn(8, 784)
        
    def test_request_replication_initialization(self):
        """Test RequestReplication initialization"""
        rr = RequestReplication(self.model, num_replicas=3)
        
        self.assertEqual(len(rr.replicas), 3)
        self.assertEqual(rr.num_replicas, 3)
        self.assertIsNotNone(rr.primary_model)
    
    def test_request_replication_forward(self):
        """Test RequestReplication forward pass"""
        rr = RequestReplication(self.model, num_replicas=2)
        
        output = rr.forward(self.test_data)
        
        # Check output shape
        self.assertEqual(output.shape, (8, 10))
        
        # Check output is not NaN
        self.assertFalse(torch.isnan(output).any())
    
    def test_request_replication_response_time(self):
        """Test RequestReplication response time measurement"""
        rr = RequestReplication(self.model, num_replicas=2)
        
        response_time = rr.get_response_time(self.test_data)
        
        # Response time should be positive
        self.assertGreater(response_time, 0)
        
        # Response time should be reasonable (< 1000ms)
        self.assertLess(response_time, 1000)
    
    def test_active_standby_initialization(self):
        """Test ActiveStandby initialization"""
        as_system = ActiveStandby(self.model, num_standbys=2)
        
        self.assertEqual(len(as_system.standby_models), 2)
        self.assertEqual(as_system.num_standbys, 2)
        self.assertIsNotNone(as_system.active_model)
    
    def test_active_standby_forward(self):
        """Test ActiveStandby forward pass"""
        as_system = ActiveStandby(self.model, num_standbys=1)
        
        output = as_system.forward(self.test_data)
        
        # Check output shape
        self.assertEqual(output.shape, (8, 10))
        
        # Check output is not NaN
        self.assertFalse(torch.isnan(output).any())
    
    def test_active_standby_response_time(self):
        """Test ActiveStandby response time measurement"""
        as_system = ActiveStandby(self.model, num_standbys=1)
        
        response_time = as_system.get_response_time(self.test_data)
        
        # Response time should be positive
        self.assertGreater(response_time, 0)
        
        # Response time should be reasonable
        self.assertLess(response_time, 1000)
    
    def test_vanilla_execution(self):
        """Test VanillaExecution"""
        vanilla = VanillaExecution(self.model)
        
        output = vanilla.forward(self.test_data)
        response_time = vanilla.get_response_time(self.test_data)
        
        # Check output shape
        self.assertEqual(output.shape, (8, 10))
        
        # Check response time
        self.assertGreater(response_time, 0)
        self.assertLess(response_time, 1000)
    
    def test_checkpointing_technique(self):
        """Test CheckpointingTechnique"""
        cp = CheckpointingTechnique(self.model, checkpoint_frequency=5)
        
        # Test forward pass
        output = cp.forward(self.test_data)
        self.assertEqual(output.shape, (8, 10))
        
        # Test checkpointing
        initial_checkpoints = len(cp.checkpoints)
        
        # Run multiple forward passes to trigger checkpoint
        for _ in range(6):
            cp.forward(self.test_data)
        
        # Should have created at least one checkpoint
        self.assertGreater(len(cp.checkpoints), initial_checkpoints)
    
    def test_checkpointing_restore(self):
        """Test checkpoint restoration"""
        cp = CheckpointingTechnique(self.model, checkpoint_frequency=1)
        
        # Create checkpoint
        cp.forward(self.test_data)
        checkpoint_id = list(cp.checkpoints.keys())[0]
        
        # Modify model state
        original_state = cp.model.state_dict()
        with torch.no_grad():
            for param in cp.model.parameters():
                param.add_(torch.randn_like(param))
        
        # Restore checkpoint
        cp.restore_checkpoint(checkpoint_id)
        
        # Check if state is restored (approximately, due to potential floating point differences)
        restored_state = cp.model.state_dict()
        for key in original_state:
            self.assertTrue(torch.allclose(original_state[key], restored_state[key], rtol=1e-5))

class TestPerformanceComparison(unittest.TestCase):
    """Test performance characteristics of different techniques"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = PaperModel(input_size=784, hidden_size=32, num_classes=10)
        self.test_data = torch.randn(4, 784)
        
        self.techniques = {
            'RR': RequestReplication(self.model, num_replicas=2),
            'AS': ActiveStandby(self.model, num_standbys=1),
            'vanilla': VanillaExecution(self.model),
            'CP': CheckpointingTechnique(self.model, checkpoint_frequency=5)
        }
    
    def test_all_techniques_produce_valid_outputs(self):
        """Test that all techniques produce valid outputs"""
        for name, technique in self.techniques.items():
            with self.subTest(technique=name):
                output = technique.forward(self.test_data)
                
                # Check shape
                self.assertEqual(output.shape, (4, 10))
                
                # Check no NaN values
                self.assertFalse(torch.isnan(output).any())
                
                # Check no infinite values
                self.assertFalse(torch.isinf(output).any())
    
    def test_response_time_measurements(self):
        """Test response time measurement for all techniques"""
        response_times = {}
        
        for name, technique in self.techniques.items():
            with self.subTest(technique=name):
                response_time = technique.get_response_time(self.test_data)
                response_times[name] = response_time
                
                # Response time should be positive
                self.assertGreater(response_time, 0)
                
                # Response time should be reasonable (< 1000ms for small test)
                self.assertLess(response_time, 1000)
        
        # Print response times for manual verification
        print(f"\nResponse Times: {response_times}")

def run_fault_tolerance_tests():
    """Run all fault tolerance tests"""
    print("Running Fault Tolerance Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFaultToleranceTechniques,
        TestPerformanceComparison
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
    run_fault_tolerance_tests()
