"""
Incremental Checkpoint Manager
Orchestrates all components for end-to-end incremental checkpointing
"""

import time
from typing import Dict, Optional, Any
from .state_tracker import StateChangeTracker
from .compressor import DeltaCompressor
from .storage import IncrementalCheckpoint, CheckpointStorageManager


class IncrementalCheckpointManager:
    """
    Main manager for incremental checkpointing system.
    
    Orchestrates:
    - State change tracking
    - Delta compression
    - Checkpoint storage
    - State restoration
    
    Implements policy for when to create full vs incremental checkpoints.
    
    Example:
        manager = IncrementalCheckpointManager('./checkpoints', full_checkpoint_interval=10)
        
        # Create checkpoints
        for i in range(20):
            state = get_application_state()
            checkpoint = manager.create_checkpoint(state)
            print(f"Created checkpoint {checkpoint.checkpoint_id}")
        
        # Restore from checkpoint
        restored_state = manager.restore_from_checkpoint(15)
    """
    
    def __init__(self, storage_path: str, full_checkpoint_interval: int = 10,
                 compression_level: int = 6):
        """
        Initialize incremental checkpoint manager.
        
        Args:
            storage_path: Directory for storing checkpoints
            full_checkpoint_interval: Create full checkpoint every N checkpoints
            compression_level: zlib compression level (1-9)
        """
        self.storage_path = storage_path
        self.full_checkpoint_interval = full_checkpoint_interval
        
        # Initialize components
        self.state_tracker = StateChangeTracker()
        self.delta_compressor = DeltaCompressor(compression_level=compression_level)
        self.storage_manager = CheckpointStorageManager(storage_path)
        
        # State management
        self.checkpoint_counter = 0
        self.last_full_checkpoint_id: Optional[int] = None
        self.last_checkpoint_time: Optional[float] = None
        
    def create_checkpoint(self, application_state: dict) -> IncrementalCheckpoint:
        """
        Create full or incremental checkpoint based on policy.
        
        Args:
            application_state: Current application state to checkpoint
            
        Returns:
            Created checkpoint object
            
        Example:
            >>> manager = IncrementalCheckpointManager('./checkpoints')
            >>> state = {'counter': 100, 'data': 'value'}
            >>> checkpoint = manager.create_checkpoint(state)
            >>> print(f"Created checkpoint {checkpoint.checkpoint_id}")
        """
        self.checkpoint_counter += 1
        current_time = time.time()
        
        # Decide if this should be a full checkpoint
        is_full = self._should_create_full_checkpoint()
        
        if is_full:
            checkpoint = self._create_full_checkpoint(application_state, current_time)
            self.last_full_checkpoint_id = checkpoint.checkpoint_id
        else:
            checkpoint = self._create_incremental_checkpoint(application_state, current_time)
        
        # Store checkpoint
        self.storage_manager.store_checkpoint(checkpoint)
        
        # Update baseline for next incremental checkpoint
        self.state_tracker.update_baseline(application_state)
        self.last_checkpoint_time = current_time
        
        return checkpoint
    
    def restore_from_checkpoint(self, checkpoint_id: int) -> dict:
        """
        Restore application state from checkpoint.
        
        Handles both full and incremental checkpoints by reconstructing
        the checkpoint chain and applying changes in order.
        
        Args:
            checkpoint_id: ID of checkpoint to restore from
            
        Returns:
            Restored application state
            
        Raises:
            ValueError: If checkpoint not found or chain is broken
            
        Example:
            >>> state = manager.restore_from_checkpoint(15)
            >>> print(f"Restored state: {state}")
        """
        # Get checkpoint chain
        checkpoint_chain = self.storage_manager.get_checkpoint_chain(checkpoint_id)
        
        if not checkpoint_chain:
            raise ValueError(f"No checkpoint chain found for ID {checkpoint_id}")
        
        # Start with full checkpoint
        full_checkpoint = checkpoint_chain[0]
        if not full_checkpoint.is_full:
            raise ValueError("First checkpoint in chain must be full checkpoint")
        
        # Decompress base state
        state = self.delta_compressor.decompress_delta(full_checkpoint.data)
        
        # Apply incremental checkpoints in order
        for checkpoint in checkpoint_chain[1:]:
            changes = self.delta_compressor.decompress_delta(checkpoint.data)
            state = self._apply_changes(state, changes)
        
        return state
    
    def get_statistics(self) -> dict:
        """
        Get comprehensive checkpointing statistics.
        
        Returns:
            Dictionary with statistics from all components
            
        Example:
            >>> stats = manager.get_statistics()
            >>> print(f"Total checkpoints: {stats['total_checkpoints']}")
            >>> print(f"Avg compression ratio: {stats['compression_ratio']:.2f}x")
        """
        storage_stats = self.storage_manager.get_storage_statistics()
        compression_stats = self.delta_compressor.get_statistics()
        change_stats = self.state_tracker.get_change_statistics()
        
        return {
            # Checkpoint counts
            'total_checkpoints': self.checkpoint_counter,
            'full_checkpoints': storage_stats['full_checkpoints'],
            'incremental_checkpoints': storage_stats['incremental_checkpoints'],
            
            # Storage
            'total_storage_bytes': storage_stats['total_size_bytes'],
            'total_storage_mb': storage_stats['total_size_mb'],
            'avg_full_size_bytes': storage_stats['avg_full_size_bytes'],
            'avg_incremental_size_bytes': storage_stats['avg_incremental_size_bytes'],
            
            # Compression
            'compression_ratio': compression_stats['average_compression_ratio'],
            'total_compressions': compression_stats['total_compressions'],
            'compression_savings_percent': compression_stats['total_savings_percent'],
            
            # Change tracking
            'total_changes_tracked': change_stats['total_changes'],
            'unique_keys_changed': change_stats['unique_keys_changed'],
            'change_rate': change_stats['change_rate'],
            
            # Efficiency
            'size_reduction_vs_full': storage_stats['size_reduction_ratio'],
            'last_checkpoint_time': self.last_checkpoint_time
        }
    
    def cleanup_old_checkpoints(self, keep_last_n: int = 20, 
                                keep_all_full: bool = True):
        """
        Clean up old checkpoints based on retention policy.
        
        Args:
            keep_last_n: Keep last N checkpoints
            keep_all_full: Always keep full checkpoints
            
        Example:
            >>> manager.cleanup_old_checkpoints(keep_last_n=50)
        """
        self.storage_manager.cleanup_old_checkpoints(
            keep_last_n=keep_last_n,
            keep_all_full=keep_all_full
        )
    
    def list_checkpoints(self) -> list:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint metadata
        """
        return self.storage_manager.list_checkpoints()
    
    def verify_checkpoint(self, checkpoint_id: int) -> bool:
        """
        Verify that a checkpoint and its chain are intact.
        
        Args:
            checkpoint_id: ID of checkpoint to verify
            
        Returns:
            True if checkpoint is valid and restorable
        """
        return self.storage_manager.verify_checkpoint_chain(checkpoint_id)
    
    def reset(self):
        """
        Reset the checkpoint manager state.
        
        Does not delete stored checkpoints, only resets in-memory state.
        """
        self.state_tracker.reset()
        self.delta_compressor.reset_statistics()
        self.checkpoint_counter = 0
        self.last_full_checkpoint_id = None
        self.last_checkpoint_time = None
    
    def _should_create_full_checkpoint(self) -> bool:
        """
        Determine if a full checkpoint should be created.
        
        Creates full checkpoint if:
        - This is the first checkpoint
        - Checkpoint counter is a multiple of full_checkpoint_interval
        """
        if self.last_full_checkpoint_id is None:
            return True
        
        if self.checkpoint_counter % self.full_checkpoint_interval == 0:
            return True
        
        return False
    
    def _create_full_checkpoint(self, state: dict, timestamp: float) -> IncrementalCheckpoint:
        """Create a full checkpoint"""
        compressed_data = self.delta_compressor.compress_delta(state)
        
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=self.checkpoint_counter,
            is_full=True,
            timestamp=timestamp,
            base_checkpoint_id=None,
            data=compressed_data,
            metadata={
                'type': 'full',
                'state_size_bytes': len(str(state)),
                'compressed_size_bytes': len(compressed_data),
                'num_keys': len(state),
                'compression_ratio': len(str(state)) / max(1, len(compressed_data))
            }
        )
        
        return checkpoint
    
    def _create_incremental_checkpoint(self, state: dict, timestamp: float) -> IncrementalCheckpoint:
        """Create an incremental checkpoint"""
        # Track changes since last checkpoint
        changes = self.state_tracker.track_changes(state)
        
        compressed_data = self.delta_compressor.compress_delta(changes)
        
        # Incremental checkpoint references the previous checkpoint (not necessarily the last full)
        # This allows proper chain reconstruction
        base_checkpoint_id = self.checkpoint_counter - 1 if self.checkpoint_counter > 1 else self.last_full_checkpoint_id
        
        checkpoint = IncrementalCheckpoint(
            checkpoint_id=self.checkpoint_counter,
            is_full=False,
            timestamp=timestamp,
            base_checkpoint_id=base_checkpoint_id,
            data=compressed_data,
            metadata={
                'type': 'incremental',
                'changes_size_bytes': len(str(changes)),
                'compressed_size_bytes': len(compressed_data),
                'num_changes': len(changes),
                'base_checkpoint': base_checkpoint_id,
                'root_full_checkpoint_id': self.last_full_checkpoint_id,
                'compression_ratio': len(str(changes)) / max(1, len(compressed_data))
            }
        )
        
        return checkpoint
    
    def _apply_changes(self, state: dict, changes: dict) -> dict:
        """
        Apply incremental changes to state.
        
        Handles:
        - Modified keys
        - New keys
        - Deleted keys (marked with __deleted_ prefix)
        """
        state = state.copy()
        
        for key, value in changes.items():
            if key.startswith("__deleted_"):
                # Handle deleted keys
                original_key = key.replace("__deleted_", "")
                state.pop(original_key, None)
            else:
                # Update or add key
                state[key] = value
        
        return state


class ConditionalCheckpointManager(IncrementalCheckpointManager):
    """
    Extended manager that only creates checkpoints when state has changed.
    
    Useful for optimizing checkpoint frequency when state changes are sparse.
    
    Example:
        manager = ConditionalCheckpointManager('./checkpoints')
        
        # Only creates checkpoint if state changed
        checkpoint = manager.create_checkpoint_if_changed(state)
        if checkpoint:
            print(f"Created checkpoint {checkpoint.checkpoint_id}")
        else:
            print("State unchanged, skipped checkpoint")
    """
    
    def __init__(self, storage_path: str, full_checkpoint_interval: int = 10,
                 compression_level: int = 6, min_change_threshold: int = 1):
        """
        Initialize conditional checkpoint manager.
        
        Args:
            storage_path: Directory for storing checkpoints
            full_checkpoint_interval: Create full checkpoint every N checkpoints
            compression_level: zlib compression level (1-9)
            min_change_threshold: Minimum number of changes to trigger checkpoint
        """
        super().__init__(storage_path, full_checkpoint_interval, compression_level)
        self.min_change_threshold = min_change_threshold
        self.skipped_checkpoints = 0
    
    def create_checkpoint_if_changed(self, application_state: dict) -> Optional[IncrementalCheckpoint]:
        """
        Create checkpoint only if state has changed.
        
        Args:
            application_state: Current application state
            
        Returns:
            Created checkpoint or None if no changes detected
        """
        # Check if state has changes
        if not self.state_tracker.has_changes(application_state):
            self.skipped_checkpoints += 1
            return None
        
        # Check if enough changes to warrant checkpoint
        if self.checkpoint_counter > 0:  # Skip check for first checkpoint
            changes = self.state_tracker.track_changes(application_state)
            if len(changes) < self.min_change_threshold:
                self.skipped_checkpoints += 1
                return None
        
        # Create checkpoint normally
        return self.create_checkpoint(application_state)
    
    def get_statistics(self) -> dict:
        """Get statistics including skipped checkpoints"""
        stats = super().get_statistics()
        stats['skipped_checkpoints'] = self.skipped_checkpoints
        stats['checkpoint_efficiency'] = (
            self.checkpoint_counter / max(1, self.checkpoint_counter + self.skipped_checkpoints)
        )
        return stats
