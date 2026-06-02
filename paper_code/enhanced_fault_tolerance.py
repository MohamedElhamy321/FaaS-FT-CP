import torch
import torch.nn as nn
import time
import random
import copy
import json
import os
import pickle
import threading
from typing import List, Tuple, Dict, Optional, Any
import numpy as np
from main import PaperModel

class FileBasedCheckpointing:
    """
    File-based checkpointing technique inspired by the FaaS project
    """
    def __init__(self, model: PaperModel, checkpoint_frequency: int = 10, checkpoint_dir: str = "checkpoints"):
        self.model = model
        self.checkpoint_frequency = checkpoint_frequency
        self.checkpoint_dir = checkpoint_dir
        self.step_count = 0
        self.checkpoint_id = 0
        self.recovery_time = 0.0
        
        # Create checkpoint directory
        os.makedirs(checkpoint_dir, exist_ok=True)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with file-based checkpointing overhead"""
        start_time = time.time()
        
        # Create checkpoint periodically
        if self.step_count % self.checkpoint_frequency == 0:
            self._save_checkpoint()
            # File I/O overhead - realistic for disk operations
            time.sleep(0.0005)  # 0.5ms overhead for file write
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def _save_checkpoint(self):
        """Save model checkpoint to file"""
        checkpoint_data = {
            'state_dict': self.model.state_dict(),
            'step_count': self.step_count,
            'timestamp': time.time(),
            'checkpoint_id': self.checkpoint_id
        }
        
        checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{self.checkpoint_id}.pt")
        torch.save(checkpoint_data, checkpoint_file)
        self.checkpoint_id += 1
    
    def restore_from_failure(self):
        """Restore from latest checkpoint after failure"""
        start_restore = time.time()
        
        # Find latest checkpoint
        checkpoint_files = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("checkpoint_")]
        if not checkpoint_files:
            self.recovery_time = time.time() - start_restore
            return False
        
        # Load latest checkpoint
        latest_checkpoint = sorted(checkpoint_files, key=lambda x: int(x.split('_')[1].split('.')[0]))[-1]
        checkpoint_path = os.path.join(self.checkpoint_dir, latest_checkpoint)
        
        # Simulate file loading time
        time.sleep(0.002)  # 2ms for file read and model restoration
        
        checkpoint_data = torch.load(checkpoint_path)
        self.model.load_state_dict(checkpoint_data['state_dict'])
        self.step_count = checkpoint_data['step_count']
        
        self.recovery_time = time.time() - start_restore
        return True
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time including checkpointing overhead"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000

class MemoryBasedCheckpointing:
    """
    Memory-based checkpointing technique - faster but less persistent
    """
    def __init__(self, model: PaperModel, checkpoint_frequency: int = 5):
        self.model = model
        self.checkpoint_frequency = checkpoint_frequency
        self.step_count = 0
        self.memory_checkpoints = {}
        self.max_checkpoints = 5  # Keep only recent checkpoints in memory
        self.recovery_time = 0.0
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with memory-based checkpointing"""
        start_time = time.time()
        
        # Create checkpoint periodically
        if self.step_count % self.checkpoint_frequency == 0:
            self._save_checkpoint()
            # Memory operations are much faster than file I/O
            time.sleep(0.0001)  # 0.1ms overhead for memory operations
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def _save_checkpoint(self):
        """Save model checkpoint to memory"""
        # Deep copy of model state
        checkpoint_data = {
            'state_dict': copy.deepcopy(self.model.state_dict()),
            'step_count': self.step_count,
            'timestamp': time.time()
        }
        
        self.memory_checkpoints[self.step_count] = checkpoint_data
        
        # Remove old checkpoints to manage memory
        if len(self.memory_checkpoints) > self.max_checkpoints:
            oldest_step = min(self.memory_checkpoints.keys())
            del self.memory_checkpoints[oldest_step]
    
    def restore_from_failure(self):
        """Restore from latest memory checkpoint after failure"""
        start_restore = time.time()
        
        if not self.memory_checkpoints:
            self.recovery_time = time.time() - start_restore
            return False
        
        # Get latest checkpoint from memory
        latest_step = max(self.memory_checkpoints.keys())
        checkpoint_data = self.memory_checkpoints[latest_step]
        
        # Memory restoration is very fast
        time.sleep(0.0005)  # 0.5ms for memory restoration
        
        self.model.load_state_dict(checkpoint_data['state_dict'])
        self.step_count = checkpoint_data['step_count']
        
        self.recovery_time = time.time() - start_restore
        return True
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time including memory checkpointing overhead"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000

class DistributedCheckpointing:
    """
    Distributed checkpointing technique - checkpoints across multiple nodes
    """
    def __init__(self, model: PaperModel, checkpoint_frequency: int = 8, num_replicas: int = 3):
        self.model = model
        self.checkpoint_frequency = checkpoint_frequency
        self.step_count = 0
        self.num_replicas = num_replicas
        self.distributed_checkpoints = {}
        self.recovery_time = 0.0
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with distributed checkpointing"""
        start_time = time.time()
        
        # Create checkpoint periodically
        if self.step_count % self.checkpoint_frequency == 0:
            self._save_distributed_checkpoint()
            # Network overhead for distributed operations
            time.sleep(0.0003)  # 0.3ms overhead for network synchronization
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def _save_distributed_checkpoint(self):
        """Save checkpoint across multiple replica nodes"""
        checkpoint_data = {
            'state_dict': copy.deepcopy(self.model.state_dict()),
            'step_count': self.step_count,
            'timestamp': time.time()
        }
        
        # Simulate replicating across multiple nodes
        for replica_id in range(self.num_replicas):
            replica_key = f"replica_{replica_id}_step_{self.step_count}"
            self.distributed_checkpoints[replica_key] = copy.deepcopy(checkpoint_data)
    
    def restore_from_failure(self):
        """Restore from distributed checkpoints after failure"""
        start_restore = time.time()
        
        # Find latest checkpoint across all replicas
        latest_step = 0
        latest_checkpoint = None
        
        for key, checkpoint in self.distributed_checkpoints.items():
            if checkpoint['step_count'] > latest_step:
                latest_step = checkpoint['step_count']
                latest_checkpoint = checkpoint
        
        if latest_checkpoint is None:
            self.recovery_time = time.time() - start_restore
            return False
        
        # Network delay for fetching from remote replica
        time.sleep(0.001)  # 1ms for network fetch and consensus
        
        self.model.load_state_dict(latest_checkpoint['state_dict'])
        self.step_count = latest_checkpoint['step_count']
        
        self.recovery_time = time.time() - start_restore
        return True
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time including distributed checkpointing overhead"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000

class HybridCheckpointing:
    """
    Hybrid checkpointing combining memory and file-based approaches
    """
    def __init__(self, model: PaperModel, memory_frequency: int = 5, file_frequency: int = 20):
        self.model = model
        self.memory_frequency = memory_frequency
        self.file_frequency = file_frequency
        self.step_count = 0
        self.memory_checkpoints = {}
        self.checkpoint_dir = "hybrid_checkpoints"
        self.recovery_time = 0.0
        
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with hybrid checkpointing strategy"""
        start_time = time.time()
        
        # Memory checkpoint (frequent, fast)
        if self.step_count % self.memory_frequency == 0:
            self._save_memory_checkpoint()
            time.sleep(0.0001)  # 0.1ms for memory operations
        
        # File checkpoint (less frequent, persistent)
        if self.step_count % self.file_frequency == 0:
            self._save_file_checkpoint()
            time.sleep(0.0004)  # 0.4ms for file operations
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def _save_memory_checkpoint(self):
        """Save checkpoint to memory"""
        self.memory_checkpoints[self.step_count] = {
            'state_dict': copy.deepcopy(self.model.state_dict()),
            'step_count': self.step_count,
            'timestamp': time.time()
        }
        
        # Keep only recent memory checkpoints
        if len(self.memory_checkpoints) > 3:
            oldest = min(self.memory_checkpoints.keys())
            del self.memory_checkpoints[oldest]
    
    def _save_file_checkpoint(self):
        """Save checkpoint to file"""
        checkpoint_data = {
            'state_dict': self.model.state_dict(),
            'step_count': self.step_count,
            'timestamp': time.time()
        }
        
        checkpoint_file = os.path.join(self.checkpoint_dir, f"checkpoint_{self.step_count}.pt")
        torch.save(checkpoint_data, checkpoint_file)
    
    def restore_from_failure(self):
        """Restore from best available checkpoint (memory first, then file)"""
        start_restore = time.time()
        
        # Try memory checkpoint first (fastest)
        if self.memory_checkpoints:
            latest_step = max(self.memory_checkpoints.keys())
            checkpoint_data = self.memory_checkpoints[latest_step]
            time.sleep(0.0005)  # 0.5ms for memory restoration
            self.model.load_state_dict(checkpoint_data['state_dict'])
            self.step_count = checkpoint_data['step_count']
            self.recovery_time = time.time() - start_restore
            return True
        
        # Fall back to file checkpoint
        checkpoint_files = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("checkpoint_")]
        if checkpoint_files:
            latest_file = sorted(checkpoint_files, key=lambda x: int(x.split('_')[1].split('.')[0]))[-1]
            checkpoint_path = os.path.join(self.checkpoint_dir, latest_file)
            time.sleep(0.002)  # 2ms for file restoration
            checkpoint_data = torch.load(checkpoint_path)
            self.model.load_state_dict(checkpoint_data['state_dict'])
            self.step_count = checkpoint_data['step_count']
            self.recovery_time = time.time() - start_restore
            return True
        
        self.recovery_time = time.time() - start_restore
        return False
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time including hybrid checkpointing overhead"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000

# Legacy checkpointing technique from the original implementation
class LegacyCheckpointing:
    """
    Legacy checkpointing technique from the original fault_tolerance.py
    """
    def __init__(self, model: PaperModel, checkpoint_frequency: int = 10):
        self.model = model
        self.checkpoint_frequency = checkpoint_frequency
        self.checkpoints = {}
        self.step_count = 0
        self.recovery_time = 0.0
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with checkpointing overhead"""
        start_time = time.time()
        
        # Create checkpoint periodically
        if self.step_count % self.checkpoint_frequency == 0:
            self._create_checkpoint()
            # Simulate checkpoint I/O overhead
            time.sleep(0.0003)
        
        self.model.eval()
        with torch.no_grad():
            output = self.model(x)
        
        self.step_count += 1
        return output
    
    def _create_checkpoint(self):
        """Create model checkpoint"""
        self.checkpoints[self.step_count] = {
            'state_dict': copy.deepcopy(self.model.state_dict()),
            'timestamp': time.time()
        }
    
    def restore_from_failure(self):
        """Restore from checkpoint"""
        start_restore = time.time()
        
        if not self.checkpoints:
            self.recovery_time = time.time() - start_restore
            return False
        
        latest_step = max(self.checkpoints.keys())
        checkpoint_data = self.checkpoints[latest_step]
        
        # Simulate restore overhead
        time.sleep(0.0002)
        
        self.model.load_state_dict(checkpoint_data['state_dict'])
        self.step_count = latest_step
        
        self.recovery_time = time.time() - start_restore
        return True
    
    def get_response_time(self, x: torch.Tensor) -> float:
        """Measure response time for checkpointing technique"""
        start_time = time.time()
        _ = self.forward(x)
        end_time = time.time()
        return (end_time - start_time) * 1000

# Import existing techniques
from fault_tolerance import RequestReplication, ActiveStandby, VanillaExecution