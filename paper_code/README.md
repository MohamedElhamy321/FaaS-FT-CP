# Paper Code Implementation

This project implements the algorithm described in the research paper with comprehensive testing and experiment infrastructure.

## Project Structure

```
paper_code/
├── main.py                 # Core implementation (PaperModel, PaperAlgorithm)
├── test_paper_code.py      # Comprehensive test suite
├── run_experiments.py      # Experiment runner with plotting
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## How to Run

### 1. Run Tests (Recommended First)
```bash
# Run all tests with verbose output
python test_paper_code.py

# Or use unittest directly
python -m unittest test_paper_code.py -v
```

### 2. Run Basic Experiment
```bash
# Run with default parameters (10 epochs, batch_size=32)
python main.py

# This will output training progress and final results
```

### 3. Run Advanced Experiments
```bash
# Run experiment with custom parameters
python run_experiments.py --epochs 50 --batch_size 64

# Run with result saving and plotting
python run_experiments.py --epochs 30 --save_results --plot

# This creates a 'results/' directory with:
# - experiment_results.json (numerical results)
# - training_plots.png (loss and accuracy plots)
```

### 4. Command Line Options
```bash
python run_experiments.py --help

Options:
  --epochs INT        Number of training epochs (default: 20)
  --batch_size INT    Batch size (default: 32)
  --save_results      Save results to JSON file
  --plot             Generate training plots
```

## Testing

The test suite includes:
- **Model Tests**: Forward pass, loss computation, gradient flow
- **Algorithm Tests**: Training steps, evaluation, epoch training
- **Data Tests**: Synthetic data generation with various parameters
- **Integration Tests**: Full experiment pipeline
- **Gradient Tests**: Proper gradient computation verification

Run specific test classes:
```bash
python -m unittest test_paper_code.TestPaperModel -v
python -m unittest test_paper_code.TestPaperAlgorithm -v
```

## Expected Output

### Test Run:
```
Running Paper Code Tests...
==================================================
test_algorithm_initialization ... ok
test_compute_loss ... ok
test_evaluate ... ok
...
==================================================
Tests run: 15
Failures: 0
Errors: 0

Overall: PASSED
```

### Experiment Run:
```
Starting Paper Code Experiment...
Epoch 1/20: Train Loss: 2.3456, Test Loss: 2.3123, Test Acc: 0.1200
Epoch 2/20: Train Loss: 2.1234, Test Loss: 2.0987, Test Acc: 0.2400
...
Epoch 20/20: Train Loss: 0.4567, Test Loss: 0.5234, Test Acc: 0.8500
Training completed in 15.23 seconds

Experiment Results:
Final Test Accuracy: 0.8500
Final Test Loss: 0.5234
```

## Customization

### Modify Model Architecture
Edit the `PaperModel` class in `main.py` to change:
- Input/hidden/output dimensions
- Network architecture
- Loss functions

### Adjust Training Parameters
Modify `PaperAlgorithm` class to change:
- Optimizer type and parameters
- Learning rate scheduling
- Training procedures

### Add New Tests
Add test methods to existing test classes in `test_paper_code.py` following the pattern:
```python
def test_new_functionality(self):
    """Test description"""
    # Test implementation
    self.assertEqual(expected, actual)
```
