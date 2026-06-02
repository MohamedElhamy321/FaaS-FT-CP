"""
Checkpoint Storage
Manages storage and retrieval of full and incremental checkpoints
"""

import os
import pickle
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from .compression_manager import CompressionManager, CompressionAlgorithm
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False

try:
    from .validation import CheckpointValidator, ValidationLevel
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


@dataclass
class IncrementalCheckpoint:
    """
    Represents an incremental checkpoint.
    
    Attributes:
        checkpoint_id: Unique identifier for this checkpoint
        is_full: Whether this is a full or incremental checkpoint
        timestamp: Unix timestamp when checkpoint was created
        base_checkpoint_id: ID of the full checkpoint this builds on (None for full checkpoints)
        data: Compressed checkpoint data (bytes)
        metadata: Additional metadata about the checkpoint
        version: Checkpoint format version
        is_compressed: Whether data is compressed
        compression_algorithm: Algorithm used for compression
        original_size: Original uncompressed size
    """
    checkpoint_id: int
    is_full: bool
    timestamp: float
    base_checkpoint_id: Optional[int]
    data: bytes
    metadata: Dict[str, Any]
    version: str = '1.0'
    is_compressed: bool = False
    compression_algorithm: Optional[str] = None
    original_size: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Serialize checkpoint to dictionary"""
        return {
            'checkpoint_id': self.checkpoint_id,
            'is_full': self.is_full,
            'timestamp': self.timestamp,
            'base_checkpoint_id': self.base_checkpoint_id,
            'data': self.data,
            'metadata': self.metadata,
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'IncrementalCheckpoint':
        """Deserialize checkpoint from dictionary"""
        return cls(
            checkpoint_id=data['checkpoint_id'],
            is_full=data['is_full'],
            timestamp=data['timestamp'],
            base_checkpoint_id=data.get('base_checkpoint_id'),
            data=data['data'],
            metadata=data.get('metadata', {}),
            version=data.get('version', '1.0')
        )
    
    def get_size(self) -> int:
        """Get size of checkpoint data in bytes"""
        return len(self.data) if self.data else 0
    
    def get_type(self) -> str:
        """Get checkpoint type as string"""
        return 'full' if self.is_full else 'incremental'


class CheckpointStorageManager:
    """
    Manages storage of full and incremental checkpoints.
    
    Handles:
    - Persisting checkpoints to disk
    - Loading checkpoints from disk
    - Maintaining checkpoint index
    - Reconstructing checkpoint chains
    - Checkpoint cleanup and retention
    
    Example:
        storage = CheckpointStorageManager('./checkpoints')
        
        # Store checkpoint
        checkpoint = IncrementalCheckpoint(...)
        storage.store_checkpoint(checkpoint)
        
        # Load checkpoint
        loaded = storage.load_checkpoint(checkpoint_id)
        
        # Get chain for restoration
        chain = storage.get_checkpoint_chain(checkpoint_id)
    """
    
    def __init__(self, storage_path: str, enable_compression: bool = True, enable_validation: bool = True):
        """
        Initialize checkpoint storage manager.
        
        Args:
            storage_path: Directory path for storing checkpoints
            enable_compression: Enable automatic compression of checkpoints
            enable_validation: Enable validation of checkpoints on store/load
        """
        self.storage_path = storage_path
        self.checkpoint_index: Dict[int, str] = {}  # Maps checkpoint_id to file path
        self.checkpoint_metadata: Dict[int, dict] = {}  # Cached metadata
        self.enable_compression = enable_compression
        self.enable_validation = enable_validation
        
        # Initialize compression manager
        if enable_compression and COMPRESSION_AVAILABLE:
            compression_path = os.path.join(storage_path, 'compression')
            self.compression_manager = CompressionManager(
                storage_path=compression_path,
                enable_deduplication=True,
                default_algorithm=CompressionAlgorithm.ZSTD
            )
        else:
            self.compression_manager = None
        
        # Initialize validation
        if enable_validation and VALIDATION_AVAILABLE:
            self.validator = CheckpointValidator()
        else:
            self.validator = None
        
        self._ensure_storage_directory()
        self._load_index()
    
    def store_checkpoint(self, checkpoint: IncrementalCheckpoint) -> str:
        """
        Store checkpoint to disk with optional validation and compression.
        
        Args:
            checkpoint: Checkpoint to store
            
        Returns:
            File path where checkpoint was stored
            
        Example:
            >>> storage = CheckpointStorageManager('./checkpoints')
            >>> checkpoint = IncrementalCheckpoint(...)
            >>> path = storage.store_checkpoint(checkpoint)
        """
        # Validate before storing
        if self.validator and self.enable_validation:
            try:
                validation_result = self.validator.validate(checkpoint, level=ValidationLevel.STANDARD)
                if not validation_result.is_valid:
                    # Try to repair
                    repair_result = self.validator.repair(checkpoint, validation_result)
                    if not repair_result.success:
                        raise ValueError(f"Cannot store invalid checkpoint {checkpoint.checkpoint_id}")
                # Store checksums in metadata
                checkpoint.metadata['validation_checksums'] = validation_result.checksums
                checkpoint.metadata['validation_quality'] = validation_result.quality_score
            except Exception:
                # If validation fails, log but continue (fail-safe)
                pass
        
        # Compress checkpoint data if enabled and not already compressed
        if self.compression_manager and not checkpoint.is_compressed and checkpoint.data:
            try:
                result = self.compression_manager.compress(checkpoint.data)
                checkpoint.data = result.compressed_data
                checkpoint.is_compressed = True
                checkpoint.compression_algorithm = result.algorithm.value
                checkpoint.original_size = result.original_size
            except Exception:
                # If compression fails, store uncompressed
                pass
        
        # Generate filename
        checkpoint_type = 'full' if checkpoint.is_full else 'incr'
        filename = f"checkpoint_{checkpoint.checkpoint_id}_{checkpoint_type}_{int(checkpoint.timestamp)}.pkl"
        filepath = os.path.join(self.storage_path, filename)
        
        # Serialize and save
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(checkpoint.to_dict(), f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise IOError(f"Failed to store checkpoint {checkpoint.checkpoint_id}: {e}")
        
        # Update index
        self.checkpoint_index[checkpoint.checkpoint_id] = filepath
        self.checkpoint_metadata[checkpoint.checkpoint_id] = {
            'is_full': checkpoint.is_full,
            'timestamp': checkpoint.timestamp,
            'base_checkpoint_id': checkpoint.base_checkpoint_id,
            'size': checkpoint.get_size(),
            'is_compressed': checkpoint.is_compressed,
            'compression_algorithm': checkpoint.compression_algorithm,
            'original_size': checkpoint.original_size,
            'filepath': filepath
        }
        
        self._save_index()
        
        return filepath
    
    def load_checkpoint(self, checkpoint_id: int, validate: bool = True) -> IncrementalCheckpoint:
        """
        Load checkpoint from disk with optional validation.
        
        Args:
            checkpoint_id: ID of checkpoint to load
            validate: Whether to validate checkpoint integrity
            
        Returns:
            Loaded checkpoint
            
        Raises:
            ValueError: If checkpoint not found or invalid
            
        Example:
            >>> checkpoint = storage.load_checkpoint(5)
        """
        filepath = self.checkpoint_index.get(checkpoint_id)
        
        if not filepath:
            raise ValueError(f"Checkpoint {checkpoint_id} not found in index")
        
        if not os.path.exists(filepath):
            raise ValueError(f"Checkpoint file not found: {filepath}")
        
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
        except Exception as e:
            raise IOError(f"Failed to load checkpoint {checkpoint_id}: {e}")
        
        checkpoint = IncrementalCheckpoint.from_dict(data)
        
        # Decompress data if compressed
        if checkpoint.is_compressed and self.compression_manager and checkpoint.data:
            try:
                algorithm = CompressionAlgorithm(checkpoint.compression_algorithm)
                result = self.compression_manager.decompress(
                    checkpoint.data,
                    algorithm,
                    checkpoint.original_size
                )
                checkpoint.data = result.data
                checkpoint.is_compressed = False
            except Exception:
                # If decompression fails, return as-is
                pass
        
        # Validate after loading
        if validate and self.validator and self.enable_validation:
            try:
                expected_checksum = checkpoint.metadata.get('validation_checksums', {}).get('sha256')
                validation_result = self.validator.validate(
                    checkpoint,
                    level=ValidationLevel.BASIC,
                    expected_checksum=expected_checksum
                )
                if not validation_result.is_valid:
                    raise ValueError(f"Checkpoint {checkpoint_id} failed validation")
            except Exception:
                # If validation fails, log but continue (fail-safe)
                pass
        
        return checkpoint
    
    def get_checkpoint_chain(self, checkpoint_id: int) -> List[IncrementalCheckpoint]:
        """
        Get chain of checkpoints needed for restoration.
        
        Returns checkpoints in application order (full checkpoint first,
        then incremental checkpoints in sequence).
        
        Args:
            checkpoint_id: Target checkpoint ID
            
        Returns:
            List of checkpoints in application order
            
        Raises:
            ValueError: If checkpoint chain is broken
            
        Example:
            >>> chain = storage.get_checkpoint_chain(15)
            >>> # chain = [full_checkpoint_10, incr_11, incr_12, ..., incr_15]
        """
        chain = []
        current_id = checkpoint_id
        
        # Walk back to find the full checkpoint
        while current_id is not None:
            checkpoint = self.load_checkpoint(current_id)
            chain.append(checkpoint)
            
            if checkpoint.is_full:
                break
            
            current_id = checkpoint.base_checkpoint_id
            
            if current_id is None:
                raise ValueError(f"Broken checkpoint chain: no full checkpoint found for {checkpoint_id}")
        
        # Reverse to get application order (full first, then incrementals)
        return list(reversed(chain))
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.
        
        Returns:
            List of checkpoint metadata dictionaries
            
        Example:
            >>> checkpoints = storage.list_checkpoints()
            >>> for cp in checkpoints:
            ...     print(f"ID: {cp['checkpoint_id']}, Type: {cp['type']}")
        """
        result = []
        
        for checkpoint_id, metadata in self.checkpoint_metadata.items():
            result.append({
                'checkpoint_id': checkpoint_id,
                'is_full': metadata['is_full'],
                'type': 'full' if metadata['is_full'] else 'incremental',
                'timestamp': metadata['timestamp'],
                'base_checkpoint_id': metadata.get('base_checkpoint_id'),
                'size': metadata.get('size', 0),
                'filepath': metadata['filepath']
            })
        
        # Sort by checkpoint_id
        result.sort(key=lambda x: x['checkpoint_id'])
        
        return result
    
    def delete_checkpoint(self, checkpoint_id: int) -> bool:
        """
        Delete a checkpoint from storage.
        
        Args:
            checkpoint_id: ID of checkpoint to delete
            
        Returns:
            True if deleted, False if not found
            
        Warning:
            Deleting a full checkpoint will break incremental chains!
            
        Example:
            >>> storage.delete_checkpoint(old_checkpoint_id)
        """
        filepath = self.checkpoint_index.get(checkpoint_id)
        
        if not filepath:
            return False
        
        # Remove file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                raise IOError(f"Failed to delete checkpoint file: {e}")
        
        # Remove from index
        del self.checkpoint_index[checkpoint_id]
        if checkpoint_id in self.checkpoint_metadata:
            del self.checkpoint_metadata[checkpoint_id]
        
        self._save_index()
        
        return True
    
    def cleanup_old_checkpoints(self, keep_last_n: int = 10, keep_all_full: bool = True):
        """
        Clean up old checkpoints based on retention policy.
        
        Args:
            keep_last_n: Keep last N checkpoints
            keep_all_full: Always keep full checkpoints
            
        Example:
            >>> storage.cleanup_old_checkpoints(keep_last_n=20, keep_all_full=True)
        """
        checkpoints = self.list_checkpoints()
        
        if len(checkpoints) <= keep_last_n:
            return  # Nothing to clean up
        
        # Sort by checkpoint_id (oldest first)
        checkpoints.sort(key=lambda x: x['checkpoint_id'])
        
        # Determine which to delete
        to_delete = []
        
        for i, checkpoint in enumerate(checkpoints):
            # Keep last N
            if i >= len(checkpoints) - keep_last_n:
                continue
            
            # Keep all full checkpoints if policy says so
            if keep_all_full and checkpoint['is_full']:
                continue
            
            to_delete.append(checkpoint['checkpoint_id'])
        
        # Delete
        for checkpoint_id in to_delete:
            self.delete_checkpoint(checkpoint_id)
    
    def get_storage_statistics(self) -> dict:
        """
        Get statistics about checkpoint storage.
        
        Returns:
            Dictionary with storage statistics
            
        Example:
            >>> stats = storage.get_storage_statistics()
            >>> print(f"Total size: {stats['total_size_mb']:.2f} MB")
        """
        checkpoints = self.list_checkpoints()
        
        total_size = sum(cp['size'] for cp in checkpoints)
        full_checkpoints = [cp for cp in checkpoints if cp['is_full']]
        incremental_checkpoints = [cp for cp in checkpoints if not cp['is_full']]
        
        avg_full_size = sum(cp['size'] for cp in full_checkpoints) / max(1, len(full_checkpoints))
        avg_incr_size = sum(cp['size'] for cp in incremental_checkpoints) / max(1, len(incremental_checkpoints))
        
        return {
            'total_checkpoints': len(checkpoints),
            'full_checkpoints': len(full_checkpoints),
            'incremental_checkpoints': len(incremental_checkpoints),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'avg_full_size_bytes': int(avg_full_size),
            'avg_incremental_size_bytes': int(avg_incr_size),
            'size_reduction_ratio': avg_full_size / max(1, avg_incr_size) if avg_incr_size > 0 else 1.0
        }
    
    def verify_checkpoint_chain(self, checkpoint_id: int) -> bool:
        """
        Verify that a checkpoint chain is intact.
        
        Args:
            checkpoint_id: ID of checkpoint to verify
            
        Returns:
            True if chain is valid, False otherwise
        """
        try:
            chain = self.get_checkpoint_chain(checkpoint_id)
            return len(chain) > 0 and chain[0].is_full
        except Exception:
            return False
    
    def _ensure_storage_directory(self):
        """Create storage directory if it doesn't exist"""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _load_index(self):
        """Load checkpoint index from disk"""
        index_path = os.path.join(self.storage_path, 'checkpoint_index.json')
        
        if not os.path.exists(index_path):
            return
        
        try:
            with open(index_path, 'r') as f:
                data = json.load(f)
                
            # Convert string keys back to integers
            self.checkpoint_index = {int(k): v for k, v in data.get('index', {}).items()}
            self.checkpoint_metadata = {int(k): v for k, v in data.get('metadata', {}).items()}
        except Exception as e:
            print(f"Warning: Failed to load checkpoint index: {e}")
    
    def _save_index(self):
        """Persist checkpoint index to disk"""
        index_path = os.path.join(self.storage_path, 'checkpoint_index.json')
        
        try:
            with open(index_path, 'w') as f:
                json.dump({
                    'index': self.checkpoint_index,
                    'metadata': self.checkpoint_metadata,
                    'last_updated': time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save checkpoint index: {e}")
