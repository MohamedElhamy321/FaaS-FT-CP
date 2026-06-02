import torch
import torch.nn as nn
import time
import random
import copy
from typing import List, Tuple, Dict, Optional
import numpy as np
from main import PaperModel

class RequestReplication:
    """
    Request Replication (RR) technique - sends requests to multiple replicas
    """
    def __init__(self, model: PaperModel, num_replicas: int = 3):
        self.primary_model = model
        self.replicas = [copy.deepcopy(model) for _ in range(num_replicas)]
        self.num_replicas = num_replicas
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with request replication"""
        start_time = time.time()
        
        # Send request to all replicas
        outputs = []
        for replica in self.replicas:
            replica.eval()
            with torch.no_grad():
                output = replica(x)
                outputs.append(output)
        
        # Use majority voting or averaging
        final_output = torch.stack(outputs).mean(dim=0)
        
        # Simulate network and coordination overhead
        time.sleep(0.0001)  # Small overhead for coordination
        
        return final_output
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time for RR technique"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds

class ActiveStandby:
    """
    Active-Standby (AS) technique - maintains active and standby replicas
    """
    def __init__(self, model: PaperModel, num_standbys: int = 2):
        self.active_model = model
        self.standby_models = [copy.deepcopy(model) for _ in range(num_standbys)]
        self.num_standbys = num_standbys
        self.failure_probability = 0.01  # 1% chance of failure
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with active-standby failover"""
        start_time = time.time()
        
        # Try active model first
        if random.random() > self.failure_probability:
            self.active_model.eval()
            with torch.no_grad():
                output = self.active_model(x)
        else:
            # Failover to standby
            standby = random.choice(self.standby_models)
            standby.eval()
            with torch.no_grad():
                output = standby(x)
            
            # Simulate failover overhead
            time.sleep(0.0002)
        
        # Simulate state synchronization overhead
        time.sleep(0.0001)
        
        return output
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time for AS technique"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds

class VanillaExecution:
    """
    Vanilla execution without fault tolerance
    """
    def __init__(self, model: PaperModel):
        self.model = model
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Standard forward pass"""
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        return output
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time for vanilla execution"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds

class CheckpointingTechnique:
    """
    Checkpointing technique from the checkpointing project
    """
    def __init__(self, model: PaperModel, checkpoint_frequency: int = 10):
        self.model = model
        self.checkpoint_frequency = checkpoint_frequency
        self.checkpoints = {}
        self.step_count = 0
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with checkpointing overhead"""
        start_time = time.time()
        
        # Create checkpoint periodically
        if self.step_count % self.checkpoint_frequency == 0:
            self.create_checkpoint()
            # Simulate checkpoint I/O overhead
            time.sleep(0.0003)
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def create_checkpoint(self):
        """Create model checkpoint"""
        self.checkpoints[self.step_count] = {
            'state_dict': copy.deepcopy(self.model.state_dict()),
            'timestamp': time.time()
        }
    
    def restore_checkpoint(self, checkpoint_id: int):
        """Restore from checkpoint"""
        if checkpoint_id in self.checkpoints:
            self.model.load_state_dict(self.checkpoints[checkpoint_id]['state_dict'])
            # Simulate restore overhead
            time.sleep(0.0002)
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time for checkpointing technique"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds
