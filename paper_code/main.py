import torch
import torch.nn as nn
import numpy as np
from typing import List, Tuple, Optional
import time

class PaperModel(nn.Module):
    """
    Implementation of the paper's main model/algorithm
    """
    def __init__(self, input_size: int = 784, hidden_size: int = 128, num_classes: int = 10):
        super(PaperModel, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_classes = num_classes
        
        # Define layers based on paper architecture
        self.layers = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the model"""
        batch_size = x.size(0)
        x = x.view(batch_size, -1)
        return self.layers(x)
    
    def compute_loss(self, outputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Compute loss function as described in paper"""
        criterion = nn.CrossEntropyLoss()
        return criterion(outputs, targets)

class PaperAlgorithm:
    """
    Main algorithm implementation from the paper
    """
    def __init__(self, model: PaperModel, learning_rate: float = 0.001):
        self.model = model
        self.learning_rate = learning_rate
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.training_history = []
    
    def train_step(self, data: torch.Tensor, targets: torch.Tensor) -> float:
        """Single training step"""
        self.model.train()
        self.optimizer.zero_grad()
        
        outputs = self.model(data)
        loss = self.model.compute_loss(outputs, targets)
        
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def evaluate(self, data: torch.Tensor, targets: torch.Tensor) -> Tuple[float, float]:
        """Evaluate model performance"""
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(data)
            loss = self.model.compute_loss(outputs, targets)
            
            _, predicted = torch.max(outputs.data, 1)
            accuracy = (predicted == targets).float().mean()
            
        return loss.item(), accuracy.item()
    
    def train_epoch(self, dataloader) -> float:
        """Train for one epoch"""
        total_loss = 0.0
        num_batches = 0
        
        for batch_data, batch_targets in dataloader:
            loss = self.train_step(batch_data, batch_targets)
            total_loss += loss
            num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        self.training_history.append(avg_loss)
        return avg_loss

def create_synthetic_data(num_samples: int = 1000, input_size: int = 784, num_classes: int = 10) -> Tuple[torch.Tensor, torch.Tensor]:
    """Create synthetic dataset for testing"""
    data = torch.randn(num_samples, input_size)
    targets = torch.randint(0, num_classes, (num_samples,))
    return data, targets

def run_paper_experiment(num_epochs: int = 10, batch_size: int = 32) -> dict:
    """
    Run the main experiment from the paper
    """
    print("Starting Paper Code Experiment...")
    
    # Initialize model and algorithm
    model = PaperModel()
    algorithm = PaperAlgorithm(model)
    
    # Create synthetic dataset
    train_data, train_targets = create_synthetic_data(1000)
    test_data, test_targets = create_synthetic_data(200)
    
    # Create data loader
    train_dataset = torch.utils.data.TensorDataset(train_data, train_targets)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # Training loop
    results = {
        'train_losses': [],
        'test_losses': [],
        'test_accuracies': [],
        'training_time': 0
    }
    
    start_time = time.time()
    
    for epoch in range(num_epochs):
        # Train
        train_loss = algorithm.train_epoch(train_loader)
        
        # Evaluate
        test_loss, test_accuracy = algorithm.evaluate(test_data, test_targets)
        
        results['train_losses'].append(train_loss)
        results['test_losses'].append(test_loss)
        results['test_accuracies'].append(test_accuracy)
        
        print(f"Epoch {epoch+1}/{num_epochs}: Train Loss: {train_loss:.4f}, Test Loss: {test_loss:.4f}, Test Acc: {test_accuracy:.4f}")
    
    results['training_time'] = time.time() - start_time
    print(f"Training completed in {results['training_time']:.2f} seconds")
    
    return results

if __name__ == "__main__":
    results = run_paper_experiment()
    print("\nExperiment Results:")
    print(f"Final Test Accuracy: {results['test_accuracies'][-1]:.4f}")
    print(f"Final Test Loss: {results['test_losses'][-1]:.4f}")
