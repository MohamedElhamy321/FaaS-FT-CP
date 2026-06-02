import unittest
import torch
import torch.nn as nn
import numpy as np
from main import PaperModel, PaperAlgorithm, create_synthetic_data, run_paper_experiment

class TestPaperModel(unittest.TestCase):
    """Test cases for PaperModel class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.input_size = 784
        self.hidden_size = 128
        self.num_classes = 10
        self.model = PaperModel(self.input_size, self.hidden_size, self.num_classes)
        
    def test_model_initialization(self):
        """Test model initialization"""
        self.assertEqual(self.model.input_size, self.input_size)
        self.assertEqual(self.model.hidden_size, self.hidden_size)
        self.assertEqual(self.model.num_classes, self.num_classes)
        self.assertIsInstance(self.model.layers, nn.Sequential)
    
    def test_forward_pass(self):
        """Test forward pass with different input shapes"""
        batch_sizes = [1, 16, 32]
        
        for batch_size in batch_sizes:
            with self.subTest(batch_size=batch_size):
                input_data = torch.randn(batch_size, self.input_size)
                output = self.model(input_data)
                
                # Check output shape
                self.assertEqual(output.shape, (batch_size, self.num_classes))
                
                # Check output is not NaN
                self.assertFalse(torch.isnan(output).any())
    
    def test_forward_pass_2d_input(self):
        """Test forward pass with 2D input (like images)"""
        batch_size = 8
        height, width = 28, 28
        input_data = torch.randn(batch_size, height, width)
        
        output = self.model(input_data)
        self.assertEqual(output.shape, (batch_size, self.num_classes))
    
    def test_compute_loss(self):
        """Test loss computation"""
        batch_size = 16
        outputs = torch.randn(batch_size, self.num_classes)
        targets = torch.randint(0, self.num_classes, (batch_size,))
        
        loss = self.model.compute_loss(outputs, targets)
        
        # Check loss is scalar
        self.assertEqual(loss.dim(), 0)
        
        # Check loss is positive
        self.assertGreater(loss.item(), 0)

class TestPaperAlgorithm(unittest.TestCase):
    """Test cases for PaperAlgorithm class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.model = PaperModel()
        self.algorithm = PaperAlgorithm(self.model)
        self.batch_size = 8
        self.data = torch.randn(self.batch_size, 784)
        self.targets = torch.randint(0, 10, (self.batch_size,))
    
    def test_algorithm_initialization(self):
        """Test algorithm initialization"""
        self.assertEqual(self.algorithm.model, self.model)
        self.assertEqual(self.algorithm.learning_rate, 0.001)
        self.assertIsInstance(self.algorithm.optimizer, torch.optim.Adam)
        self.assertEqual(len(self.algorithm.training_history), 0)
    
    def test_train_step(self):
        """Test single training step"""
        # Get initial parameters
        initial_params = [p.clone() for p in self.model.parameters()]
        
        # Perform training step
        loss = self.algorithm.train_step(self.data, self.targets)
        
        # Check loss is positive scalar
        self.assertIsInstance(loss, float)
        self.assertGreater(loss, 0)
        
        # Check parameters have changed
        for initial_param, current_param in zip(initial_params, self.model.parameters()):
            self.assertFalse(torch.equal(initial_param, current_param))
    
    def test_evaluate(self):
        """Test evaluation function"""
        loss, accuracy = self.algorithm.evaluate(self.data, self.targets)
        
        # Check return types
        self.assertIsInstance(loss, float)
        self.assertIsInstance(accuracy, float)
        
        # Check value ranges
        self.assertGreater(loss, 0)
        self.assertGreaterEqual(accuracy, 0.0)
        self.assertLessEqual(accuracy, 1.0)
    
    def test_train_epoch(self):
        """Test training for one epoch"""
        # Create data loader
        dataset = torch.utils.data.TensorDataset(self.data, self.targets)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=True)
        
        initial_history_len = len(self.algorithm.training_history)
        avg_loss = self.algorithm.train_epoch(dataloader)
        
        # Check loss is returned
        self.assertIsInstance(avg_loss, float)
        self.assertGreater(avg_loss, 0)
        
        # Check history is updated
        self.assertEqual(len(self.algorithm.training_history), initial_history_len + 1)
        self.assertEqual(self.algorithm.training_history[-1], avg_loss)

class TestDataGeneration(unittest.TestCase):
    """Test cases for data generation functions"""
    
    def test_create_synthetic_data(self):
        """Test synthetic data creation"""
        num_samples = 100
        input_size = 784
        num_classes = 10
        
        data, targets = create_synthetic_data(num_samples, input_size, num_classes)
        
        # Check data shape and type
        self.assertEqual(data.shape, (num_samples, input_size))
        self.assertIsInstance(data, torch.Tensor)
        
        # Check targets shape and range
        self.assertEqual(targets.shape, (num_samples,))
        self.assertIsInstance(targets, torch.Tensor)
        self.assertTrue(torch.all(targets >= 0))
        self.assertTrue(torch.all(targets < num_classes))
    
    def test_create_synthetic_data_different_sizes(self):
        """Test synthetic data creation with different parameters"""
        test_configs = [
            (50, 256, 5),
            (200, 1024, 20),
            (10, 100, 2)
        ]
        
        for num_samples, input_size, num_classes in test_configs:
            with self.subTest(num_samples=num_samples, input_size=input_size, num_classes=num_classes):
                data, targets = create_synthetic_data(num_samples, input_size, num_classes)
                
                self.assertEqual(data.shape, (num_samples, input_size))
                self.assertEqual(targets.shape, (num_samples,))
                self.assertTrue(torch.all(targets < num_classes))

class TestPaperExperiment(unittest.TestCase):
    """Test cases for the main paper experiment"""
    
    def test_run_paper_experiment(self):
        """Test running the main experiment"""
        # Run short experiment for testing
        results = run_paper_experiment(num_epochs=2, batch_size=16)
        
        # Check results structure
        expected_keys = ['train_losses', 'test_losses', 'test_accuracies', 'training_time']
        for key in expected_keys:
            self.assertIn(key, results)
        
        # Check results content
        self.assertEqual(len(results['train_losses']), 2)
        self.assertEqual(len(results['test_losses']), 2)
        self.assertEqual(len(results['test_accuracies']), 2)
        
        # Check value ranges
        for loss in results['train_losses']:
            self.assertGreater(loss, 0)
        
        for accuracy in results['test_accuracies']:
            self.assertGreaterEqual(accuracy, 0.0)
            self.assertLessEqual(accuracy, 1.0)
        
        self.assertGreater(results['training_time'], 0)

class TestModelGradients(unittest.TestCase):
    """Test cases for gradient computation"""
    
    def setUp(self):
        self.model = PaperModel()
        self.algorithm = PaperAlgorithm(self.model)
    
    def test_gradients_computed(self):
        """Test that gradients are computed during training"""
        data = torch.randn(4, 784)
        targets = torch.randint(0, 10, (4,))
        
        # Ensure gradients are None initially
        self.algorithm.optimizer.zero_grad()
        for param in self.model.parameters():
            self.assertIsNone(param.grad)
        
        # Perform forward and backward pass
        outputs = self.model(data)
        loss = self.model.compute_loss(outputs, targets)
        loss.backward()
        
        # Check gradients are computed
        for param in self.model.parameters():
            self.assertIsNotNone(param.grad)
            self.assertFalse(torch.isnan(param.grad).any())

def run_tests():
    """Run all tests"""
    print("Running Paper Code Tests...")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPaperModel,
        TestPaperAlgorithm,
        TestDataGeneration,
        TestPaperExperiment,
        TestModelGradients
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
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall: {'PASSED' if success else 'FAILED'}")
    
    return success

if __name__ == "__main__":
    run_tests()
