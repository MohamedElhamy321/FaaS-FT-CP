"""
Integration Wrapper - Drop-in Replacement for Legacy Checkpoint Systems

This module provides adapters and wrappers that make incremental checkpointing
compatible with existing checkpoint systems, enabling gradual migration.
"""

import json
import os
import pickle
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
import logging

from .enhanced_manager import ProductionCheckpointManager
from .production import BackwardCompatibility


class RolloutStrategy(Enum):
    """Gradual rollout strategies for new checkpoint system"""
    DISABLED = "disabled"  # Use legacy system only
    CANARY_5 = "canary_5"  # 5% of requests use new system
    CANARY_25 = "canary_25"  # 25% of requests
    CANARY_50 = "canary_50"  # 50% of requests
    ENABLED = "enabled"  # 100% use new system


@dataclass
class FeatureFlags:
    """Feature flags for gradual rollout"""
    use_incremental_checkpointing: bool = False
    rollout_percentage: int = 0
    rollout_strategy: RolloutStrategy = RolloutStrategy.DISABLED
    enable_performance_monitoring: bool = True
    enable_health_checks: bool = True
    fallback_to_legacy_on_error: bool = True
    log_performance_comparison: bool = True
    
    # Advanced options
    user_id_based_rollout: bool = False  # Consistent rollout per user
    rollout_whitelist: List[str] = field(default_factory=list)  # Always use new system
    rollout_blacklist: List[str] = field(default_factory=list)  # Never use new system


class LegacyCheckpointInterface:
    """
    Interface that mimics legacy checkpoint systems.
    Drop-in replacement for existing checkpoint code.
    """
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Load checkpoint from file (legacy interface)"""
        raise NotImplementedError
    
    def save_checkpoint(self, state: Dict[str, Any], checkpoint_path: str) -> None:
        """Save checkpoint to file (legacy interface)"""
        raise NotImplementedError
    
    def checkpoint_exists(self, checkpoint_path: str) -> bool:
        """Check if checkpoint exists"""
        raise NotImplementedError


class JSONCheckpointAdapter(LegacyCheckpointInterface):
    """
    Adapter for JSON-based checkpoint systems (like Fission example).
    Provides legacy interface while using incremental checkpointing underneath.
    """
    
    def __init__(self, 
                 checkpoint_dir: str = "/tmp/checkpoints",
                 feature_flags: Optional[FeatureFlags] = None):
        """
        Initialize the adapter
        
        Args:
            checkpoint_dir: Directory for checkpoint storage
            feature_flags: Feature flags for gradual rollout
        """
        self.checkpoint_dir = checkpoint_dir
        self.feature_flags = feature_flags or FeatureFlags()
        self.logger = logging.getLogger(__name__)
        
        # Initialize incremental checkpoint manager if enabled
        self.incremental_manager: Optional[ProductionCheckpointManager] = None
        if self._should_use_incremental():
            try:
                self.incremental_manager = ProductionCheckpointManager(
                    storage_path=checkpoint_dir,
                    enable_monitoring=self.feature_flags.enable_performance_monitoring
                )
                self.logger.info("Incremental checkpointing enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize incremental manager: {e}")
                if not self.feature_flags.fallback_to_legacy_on_error:
                    raise
        
        # Compatibility layer for legacy format conversion
        self.compatibility = BackwardCompatibility()
    
    def _should_use_incremental(self, request_id: Optional[str] = None) -> bool:
        """
        Determine if incremental checkpointing should be used for this request
        
        Args:
            request_id: Optional request/user ID for consistent rollout
            
        Returns:
            True if incremental checkpointing should be used
        """
        flags = self.feature_flags
        
        # Check if feature is disabled
        if not flags.use_incremental_checkpointing:
            return False
        
        # Check rollout strategy
        if flags.rollout_strategy == RolloutStrategy.DISABLED:
            return False
        elif flags.rollout_strategy == RolloutStrategy.ENABLED:
            return True
        
        # Check whitelist/blacklist
        if request_id:
            if request_id in flags.rollout_whitelist:
                return True
            if request_id in flags.rollout_blacklist:
                return False
        
        # Canary rollout based on percentage
        if flags.user_id_based_rollout and request_id:
            # Consistent rollout based on hash of request_id
            hash_val = hash(request_id) % 100
            return hash_val < flags.rollout_percentage
        else:
            # Random rollout (non-deterministic)
            import random
            return random.random() * 100 < flags.rollout_percentage
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """
        Load checkpoint from file (legacy interface)
        
        Args:
            checkpoint_path: Path to checkpoint file
            
        Returns:
            Checkpoint data as dictionary
        """
        # Try incremental system first if enabled
        if self.incremental_manager and self._should_use_incremental():
            try:
                # Extract checkpoint ID from path
                checkpoint_id = self._extract_checkpoint_id(checkpoint_path)
                if checkpoint_id:
                    state = self.incremental_manager.restore_from_checkpoint(checkpoint_id)
                    self.logger.info(f"Loaded checkpoint {checkpoint_id} using incremental system")
                    return state
            except Exception as e:
                self.logger.warning(f"Incremental checkpoint load failed: {e}")
                if not self.feature_flags.fallback_to_legacy_on_error:
                    raise
        
        # Fallback to legacy JSON loading
        if os.path.exists(checkpoint_path):
            try:
                with open(checkpoint_path, "r") as f:
                    data = json.load(f)
                self.logger.info(f"Loaded checkpoint from {checkpoint_path} (legacy)")
                return data
            except json.JSONDecodeError as e:
                self.logger.error(f"Checkpoint file corrupted: {e}")
                return {}
        
        return {}
    
    def save_checkpoint(self, state: Dict[str, Any], checkpoint_path: str) -> None:
        """
        Save checkpoint to file (legacy interface)
        
        Args:
            state: State to checkpoint
            checkpoint_path: Path to save checkpoint
        """
        # Try incremental system first if enabled
        if self.incremental_manager and self._should_use_incremental():
            try:
                checkpoint = self.incremental_manager.create_checkpoint(state)
                self.logger.info(f"Saved checkpoint {checkpoint.checkpoint_id} using incremental system")
                
                # Also save mapping from legacy path to checkpoint ID
                self._save_checkpoint_mapping(checkpoint_path, checkpoint.checkpoint_id)
                
                # Log performance comparison if enabled
                if self.feature_flags.log_performance_comparison:
                    self._log_performance_comparison(state, checkpoint)
                
                return
            except Exception as e:
                self.logger.warning(f"Incremental checkpoint save failed: {e}")
                if not self.feature_flags.fallback_to_legacy_on_error:
                    raise
        
        # Fallback to legacy JSON saving
        os.makedirs(os.path.dirname(checkpoint_path) or ".", exist_ok=True)
        with open(checkpoint_path, "w") as f:
            json.dump(state, f)
        self.logger.info(f"Saved checkpoint to {checkpoint_path} (legacy)")
    
    def checkpoint_exists(self, checkpoint_path: str) -> bool:
        """
        Check if checkpoint exists
        
        Args:
            checkpoint_path: Path to checkpoint file
            
        Returns:
            True if checkpoint exists
        """
        # Check incremental system first if enabled
        if self.incremental_manager and self._should_use_incremental():
            checkpoint_id = self._extract_checkpoint_id(checkpoint_path)
            if checkpoint_id:
                checkpoints = self.incremental_manager.list_checkpoints()
                return any(cp.checkpoint_id == checkpoint_id for cp in checkpoints)
        
        # Fallback to legacy file check
        return os.path.exists(checkpoint_path)
    
    def _extract_checkpoint_id(self, checkpoint_path: str) -> Optional[int]:
        """Extract checkpoint ID from mapping file"""
        mapping_path = f"{checkpoint_path}.mapping"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r") as f:
                    data = json.load(f)
                    return data.get("checkpoint_id")
            except:
                pass
        return None
    
    def _save_checkpoint_mapping(self, checkpoint_path: str, checkpoint_id: int) -> None:
        """Save mapping from legacy path to checkpoint ID"""
        mapping_path = f"{checkpoint_path}.mapping"
        os.makedirs(os.path.dirname(mapping_path) or ".", exist_ok=True)
        with open(mapping_path, "w") as f:
            json.dump({"checkpoint_id": checkpoint_id, "path": checkpoint_path}, f)
    
    def _log_performance_comparison(self, state: Dict[str, Any], checkpoint) -> None:
        """Log performance comparison between legacy and incremental"""
        try:
            # Estimate legacy checkpoint size
            legacy_size = len(json.dumps(state).encode())
            
            # Get incremental checkpoint size
            incremental_size = checkpoint.get_size()
            
            # Calculate savings
            savings_pct = ((legacy_size - incremental_size) / legacy_size * 100) if legacy_size > 0 else 0
            
            self.logger.info(
                f"Checkpoint comparison - Legacy: {legacy_size} bytes, "
                f"Incremental: {incremental_size} bytes, "
                f"Savings: {savings_pct:.1f}%"
            )
        except Exception as e:
            self.logger.debug(f"Performance comparison failed: {e}")
    
    def migrate_legacy_checkpoint(self, legacy_path: str) -> Optional[int]:
        """
        Migrate a legacy checkpoint to incremental format
        
        Args:
            legacy_path: Path to legacy checkpoint file
            
        Returns:
            New checkpoint ID if successful, None otherwise
        """
        if not self.incremental_manager:
            self.logger.error("Incremental manager not initialized")
            return None
        
        try:
            # Load legacy checkpoint
            if not os.path.exists(legacy_path):
                self.logger.error(f"Legacy checkpoint not found: {legacy_path}")
                return None
            
            with open(legacy_path, "r") as f:
                state = json.load(f)
            
            # Create new incremental checkpoint
            checkpoint = self.incremental_manager.create_checkpoint(state)
            
            # Save mapping
            self._save_checkpoint_mapping(legacy_path, checkpoint.checkpoint_id)
            
            self.logger.info(f"Migrated legacy checkpoint {legacy_path} to ID {checkpoint.checkpoint_id}")
            return checkpoint.checkpoint_id
        
        except Exception as e:
            self.logger.error(f"Failed to migrate legacy checkpoint: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get checkpoint statistics"""
        if self.incremental_manager:
            return self.incremental_manager.get_statistics()
        return {}
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run health check on checkpoint system"""
        if self.incremental_manager:
            return self.incremental_manager.run_health_check()
        return {"status": "legacy_mode", "healthy": True}


class PickleCheckpointAdapter(LegacyCheckpointInterface):
    """
    Adapter for pickle-based checkpoint systems.
    Provides legacy interface while using incremental checkpointing underneath.
    """
    
    def __init__(self, 
                 checkpoint_dir: str = "/tmp/checkpoints",
                 feature_flags: Optional[FeatureFlags] = None):
        """
        Initialize the adapter
        
        Args:
            checkpoint_dir: Directory for checkpoint storage
            feature_flags: Feature flags for gradual rollout
        """
        self.checkpoint_dir = checkpoint_dir
        self.feature_flags = feature_flags or FeatureFlags()
        self.logger = logging.getLogger(__name__)
        
        # Initialize incremental checkpoint manager if enabled
        self.incremental_manager: Optional[ProductionCheckpointManager] = None
        if self.feature_flags.use_incremental_checkpointing:
            try:
                self.incremental_manager = ProductionCheckpointManager(
                    storage_path=checkpoint_dir,
                    enable_monitoring=self.feature_flags.enable_performance_monitoring
                )
                self.logger.info("Incremental checkpointing enabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize incremental manager: {e}")
                if not self.feature_flags.fallback_to_legacy_on_error:
                    raise
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Load checkpoint from pickle file"""
        # Try incremental system first if enabled
        if self.incremental_manager:
            checkpoint_id = self._extract_checkpoint_id(checkpoint_path)
            if checkpoint_id:
                try:
                    state = self.incremental_manager.restore_from_checkpoint(checkpoint_id)
                    return state
                except Exception as e:
                    self.logger.warning(f"Incremental restore failed: {e}")
        
        # Fallback to legacy pickle loading
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, "rb") as f:
                return pickle.load(f)
        return {}
    
    def save_checkpoint(self, state: Dict[str, Any], checkpoint_path: str) -> None:
        """Save checkpoint to pickle file"""
        # Try incremental system first if enabled
        if self.incremental_manager:
            try:
                checkpoint = self.incremental_manager.create_checkpoint(state)
                self._save_checkpoint_mapping(checkpoint_path, checkpoint.checkpoint_id)
                return
            except Exception as e:
                self.logger.warning(f"Incremental save failed: {e}")
        
        # Fallback to legacy pickle saving
        os.makedirs(os.path.dirname(checkpoint_path) or ".", exist_ok=True)
        with open(checkpoint_path, "wb") as f:
            pickle.dump(state, f)
    
    def checkpoint_exists(self, checkpoint_path: str) -> bool:
        """Check if checkpoint exists"""
        return os.path.exists(checkpoint_path)
    
    def _extract_checkpoint_id(self, checkpoint_path: str) -> Optional[int]:
        """Extract checkpoint ID from mapping file"""
        mapping_path = f"{checkpoint_path}.mapping"
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r") as f:
                    data = json.load(f)
                    return data.get("checkpoint_id")
            except:
                pass
        return None
    
    def _save_checkpoint_mapping(self, checkpoint_path: str, checkpoint_id: int) -> None:
        """Save mapping from legacy path to checkpoint ID"""
        mapping_path = f"{checkpoint_path}.mapping"
        with open(mapping_path, "w") as f:
            json.dump({"checkpoint_id": checkpoint_id}, f)


class CheckpointContext:
    """
    Context manager for automatic checkpointing.
    Makes it easy to add checkpointing to existing code.
    """
    
    def __init__(self, 
                 adapter: LegacyCheckpointInterface,
                 checkpoint_path: str,
                 state_getter: Callable[[], Dict[str, Any]],
                 state_setter: Callable[[Dict[str, Any]], None]):
        """
        Initialize checkpoint context
        
        Args:
            adapter: Checkpoint adapter to use
            checkpoint_path: Path for checkpoint file
            state_getter: Function that returns current state
            state_setter: Function that restores state
        """
        self.adapter = adapter
        self.checkpoint_path = checkpoint_path
        self.state_getter = state_getter
        self.state_setter = state_setter
    
    def __enter__(self):
        """Load checkpoint on entry"""
        if self.adapter.checkpoint_exists(self.checkpoint_path):
            state = self.adapter.load_checkpoint(self.checkpoint_path)
            self.state_setter(state)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save checkpoint on exit (even if exception occurred)"""
        state = self.state_getter()
        self.adapter.save_checkpoint(state, self.checkpoint_path)
        return False  # Don't suppress exceptions


def create_fission_adapter(checkpoint_file: str = "/tmp/fibonacci_checkpoint.json",
                          enable_incremental: bool = False,
                          rollout_strategy: RolloutStrategy = RolloutStrategy.DISABLED) -> JSONCheckpointAdapter:
    """
    Convenience function to create adapter configured for Fission functions
    
    Args:
        checkpoint_file: Path to checkpoint file
        enable_incremental: Enable incremental checkpointing
        rollout_strategy: Gradual rollout strategy
        
    Returns:
        Configured JSONCheckpointAdapter
    """
    # Extract directory from file path
    checkpoint_dir = os.path.dirname(checkpoint_file) or "/tmp"
    
    # Configure feature flags
    flags = FeatureFlags(
        use_incremental_checkpointing=enable_incremental,
        rollout_strategy=rollout_strategy,
        rollout_percentage=_get_rollout_percentage(rollout_strategy),
        enable_performance_monitoring=True,
        enable_health_checks=True,
        fallback_to_legacy_on_error=True,
        log_performance_comparison=True
    )
    
    return JSONCheckpointAdapter(checkpoint_dir=checkpoint_dir, feature_flags=flags)


def _get_rollout_percentage(strategy: RolloutStrategy) -> int:
    """Get percentage for rollout strategy"""
    strategy_map = {
        RolloutStrategy.DISABLED: 0,
        RolloutStrategy.CANARY_5: 5,
        RolloutStrategy.CANARY_25: 25,
        RolloutStrategy.CANARY_50: 50,
        RolloutStrategy.ENABLED: 100
    }
    return strategy_map.get(strategy, 0)
