"""
Multi-Level Checkpoint Hierarchy - Tiered Storage System

Implements hot/warm/cold storage tiers for cost optimization and performance.
Checkpoints automatically age and migrate between tiers based on access patterns.

Storage Tiers:
- HOT: Recent/frequently accessed (<1 hour old), memory + SSD, <10ms access
- WARM: Recent checkpoints (1-24 hours old), SSD, <100ms access
- COLD: Old checkpoints (>24 hours old), HDD/S3, <1s access

Target: 50% storage cost reduction while maintaining performance
"""

import os
import time
import pickle
import threading
import shutil
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json


class StorageTier(Enum):
    """Storage tier levels"""
    HOT = "hot"      # In-memory + SSD, <10ms access, most recent
    WARM = "warm"    # SSD only, <100ms access, recent
    COLD = "cold"    # HDD/S3, <1s access, archived


class AccessPattern(Enum):
    """Checkpoint access patterns"""
    FREQUENT = "frequent"      # Accessed often
    OCCASIONAL = "occasional"  # Accessed sometimes
    RARE = "rare"             # Rarely accessed
    NEVER = "never"           # Never accessed after creation


@dataclass
class TierPolicy:
    """
    Policy for tier transitions.
    
    Attributes:
        hot_max_age_hours: Max age in hours before moving from hot to warm
        warm_max_age_hours: Max age in hours before moving from warm to cold
        hot_access_threshold: Min accesses to stay in hot tier
        enable_access_based_promotion: Promote to higher tier based on access
    """
    hot_max_age_hours: float = 1.0
    warm_max_age_hours: float = 24.0
    hot_access_threshold: int = 5
    enable_access_based_promotion: bool = True
    promotion_access_threshold: int = 10  # Accesses to promote from cold/warm to hot
    

@dataclass
class CheckpointTierMetadata:
    """
    Metadata for checkpoint tier management.
    
    Tracks tier location, access patterns, and transition history.
    """
    checkpoint_id: int
    current_tier: StorageTier
    creation_time: float
    last_access_time: float
    access_count: int = 0
    tier_transition_history: List[Dict[str, Any]] = field(default_factory=list)
    size_bytes: int = 0
    
    def age_hours(self) -> float:
        """Get age in hours"""
        return (time.time() - self.creation_time) / 3600.0
    
    def time_since_last_access_hours(self) -> float:
        """Get hours since last access"""
        return (time.time() - self.last_access_time) / 3600.0
    
    def record_access(self):
        """Record an access"""
        self.access_count += 1
        self.last_access_time = time.time()
    
    def record_tier_transition(self, from_tier: StorageTier, to_tier: StorageTier, reason: str):
        """Record a tier transition"""
        self.tier_transition_history.append({
            'timestamp': time.time(),
            'from_tier': from_tier.value,
            'to_tier': to_tier.value,
            'reason': reason
        })
        self.current_tier = to_tier


@dataclass
class TierStatistics:
    """Statistics for a storage tier"""
    tier: StorageTier
    checkpoint_count: int = 0
    total_size_bytes: int = 0
    avg_access_time_ms: float = 0.0
    access_count: int = 0
    cost_per_gb_month: float = 0.0  # Estimated storage cost
    
    def avg_checkpoint_size_bytes(self) -> int:
        """Average checkpoint size"""
        return self.total_size_bytes // self.checkpoint_count if self.checkpoint_count > 0 else 0
    
    def total_size_mb(self) -> float:
        """Total size in MB"""
        return self.total_size_bytes / (1024 * 1024)
    
    def estimated_monthly_cost(self) -> float:
        """Estimated monthly storage cost"""
        return (self.total_size_bytes / (1024**3)) * self.cost_per_gb_month


class TierMigrator(threading.Thread):
    """
    Background worker for automatic tier migrations.
    
    Periodically checks checkpoint ages and access patterns to migrate
    checkpoints between tiers according to aging policies.
    """
    
    def __init__(self, storage_manager: 'TieredStorageManager', interval_seconds: int = 300):
        """
        Initialize tier migrator.
        
        Args:
            storage_manager: TieredStorageManager instance
            interval_seconds: How often to run migration checks (default: 5 minutes)
        """
        super().__init__(daemon=True)
        self.storage_manager = storage_manager
        self.interval_seconds = interval_seconds
        self.running = False
        self._stop_event = threading.Event()
    
    def run(self):
        """Main migration loop"""
        self.running = True
        
        while not self._stop_event.is_set():
            try:
                # Run migration cycle
                migrations = self.storage_manager.auto_migrate_checkpoints()
                
                if migrations > 0:
                    print(f"[TierMigrator] Migrated {migrations} checkpoints")
                
            except Exception as e:
                print(f"[TierMigrator] Error during migration: {e}")
            
            # Wait for next interval
            self._stop_event.wait(self.interval_seconds)
    
    def stop(self):
        """Stop the migrator"""
        self.running = False
        self._stop_event.set()


class TieredStorageManager:
    """
    Manages checkpoints across hot/warm/cold storage tiers.
    
    Provides transparent tier management with automatic aging and migration.
    Optimizes costs by moving old/rarely-accessed checkpoints to cheaper storage.
    
    Example:
        storage = TieredStorageManager('./checkpoints')
        
        # Store checkpoint (automatically goes to hot tier)
        storage.store_checkpoint(checkpoint)
        
        # Load checkpoint (tier is transparent to caller)
        checkpoint = storage.load_checkpoint(checkpoint_id)
        
        # Get tier statistics
        stats = storage.get_tier_statistics()
    """
    
    def __init__(
        self,
        base_path: str,
        tier_policy: Optional[TierPolicy] = None,
        enable_auto_migration: bool = True,
        hot_tier_costs: Dict[str, float] = None,
        enable_hot_cache: bool = True
    ):
        """
        Initialize tiered storage manager.
        
        Args:
            base_path: Base directory for all storage tiers
            tier_policy: Aging and migration policy
            enable_auto_migration: Enable automatic background migration
            hot_tier_costs: Cost per GB/month for each tier (for tracking)
            enable_hot_cache: Enable in-memory cache for hot tier
        """
        self.base_path = Path(base_path)
        self.tier_policy = tier_policy or TierPolicy()
        self.enable_auto_migration = enable_auto_migration
        self.enable_hot_cache = enable_hot_cache
        
        # Storage costs ($/GB/month) - defaults
        self.tier_costs = hot_tier_costs or {
            'hot': 0.20,   # SSD + memory overhead
            'warm': 0.10,  # SSD
            'cold': 0.02   # HDD/S3
        }
        
        # Initialize tier directories
        self.tier_paths = {
            StorageTier.HOT: self.base_path / 'hot',
            StorageTier.WARM: self.base_path / 'warm',
            StorageTier.COLD: self.base_path / 'cold'
        }
        
        for tier_path in self.tier_paths.values():
            tier_path.mkdir(parents=True, exist_ok=True)
        
        # Metadata tracking
        self.metadata_file = self.base_path / 'tier_metadata.json'
        self.checkpoint_metadata: Dict[int, CheckpointTierMetadata] = {}
        self._metadata_lock = threading.Lock()
        
        # Hot tier in-memory cache
        self.hot_cache: Dict[int, bytes] = {} if enable_hot_cache else None
        self._cache_lock = threading.Lock() if enable_hot_cache else None
        
        # Load existing metadata
        self._load_metadata()
        
        # Start background migrator
        self.migrator = None
        if enable_auto_migration:
            self.migrator = TierMigrator(self)
            self.migrator.start()
    
    def store_checkpoint(self, checkpoint_id: int, data: bytes, metadata: Dict[str, Any] = None) -> str:
        """
        Store checkpoint (always starts in hot tier).
        
        Args:
            checkpoint_id: Checkpoint ID
            data: Checkpoint data
            metadata: Optional metadata
            
        Returns:
            Path where checkpoint was stored
        """
        # Create tier metadata
        tier_metadata = CheckpointTierMetadata(
            checkpoint_id=checkpoint_id,
            current_tier=StorageTier.HOT,
            creation_time=time.time(),
            last_access_time=time.time(),
            access_count=1,
            size_bytes=len(data)
        )
        
        # Store in hot tier
        filepath = self._get_checkpoint_path(checkpoint_id, StorageTier.HOT)
        
        checkpoint_data = {
            'checkpoint_id': checkpoint_id,
            'data': data,
            'metadata': metadata or {},
            'tier_metadata': {
                'tier': StorageTier.HOT.value,
                'creation_time': tier_metadata.creation_time
            }
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(checkpoint_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Update cache if enabled
        if self.hot_cache is not None:
            with self._cache_lock:
                self.hot_cache[checkpoint_id] = data
        
        # Update metadata
        with self._metadata_lock:
            self.checkpoint_metadata[checkpoint_id] = tier_metadata
            self._save_metadata()
        
        return str(filepath)
    
    def load_checkpoint(self, checkpoint_id: int) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint from any tier (transparent to caller).
        
        Records access for tier management decisions.
        
        Args:
            checkpoint_id: Checkpoint ID to load
            
        Returns:
            Checkpoint data dictionary or None if not found
        """
        # Check metadata
        with self._metadata_lock:
            tier_metadata = self.checkpoint_metadata.get(checkpoint_id)
        
        if not tier_metadata:
            return None
        
        # Check hot cache first
        if self.hot_cache is not None and checkpoint_id in self.hot_cache:
            with self._cache_lock:
                data = self.hot_cache[checkpoint_id]
            
            # Record access
            with self._metadata_lock:
                tier_metadata.record_access()
                self._save_metadata()
            
            return {
                'checkpoint_id': checkpoint_id,
                'data': data,
                'metadata': {},
                'tier': tier_metadata.current_tier.value
            }
        
        # Load from tier storage
        start_time = time.time()
        filepath = self._get_checkpoint_path(checkpoint_id, tier_metadata.current_tier)
        
        if not filepath.exists():
            return None
        
        try:
            with open(filepath, 'rb') as f:
                checkpoint_data = pickle.load(f)
        except Exception as e:
            print(f"Error loading checkpoint {checkpoint_id}: {e}")
            return None
        
        access_time_ms = (time.time() - start_time) * 1000
        
        # Record access
        with self._metadata_lock:
            tier_metadata.record_access()
            self._save_metadata()
        
        # Consider promotion based on access pattern
        if (self.tier_policy.enable_access_based_promotion and
            tier_metadata.access_count >= self.tier_policy.promotion_access_threshold and
            tier_metadata.current_tier != StorageTier.HOT):
            
            self._promote_checkpoint(checkpoint_id, "frequent_access")
        
        checkpoint_data['tier'] = tier_metadata.current_tier.value
        checkpoint_data['access_time_ms'] = access_time_ms
        
        return checkpoint_data
    
    def get_checkpoint_tier(self, checkpoint_id: int) -> Optional[StorageTier]:
        """Get current tier for checkpoint"""
        with self._metadata_lock:
            metadata = self.checkpoint_metadata.get(checkpoint_id)
            return metadata.current_tier if metadata else None
    
    def auto_migrate_checkpoints(self) -> int:
        """
        Automatically migrate checkpoints based on aging policy.
        
        Returns:
            Number of checkpoints migrated
        """
        migrations = 0
        
        with self._metadata_lock:
            checkpoints = list(self.checkpoint_metadata.items())
        
        for checkpoint_id, metadata in checkpoints:
            # Check for demotion (hot -> warm -> cold)
            if metadata.current_tier == StorageTier.HOT:
                if metadata.age_hours() > self.tier_policy.hot_max_age_hours:
                    if self._migrate_checkpoint(checkpoint_id, StorageTier.WARM, "age_based"):
                        migrations += 1
            
            elif metadata.current_tier == StorageTier.WARM:
                if metadata.age_hours() > self.tier_policy.warm_max_age_hours:
                    if self._migrate_checkpoint(checkpoint_id, StorageTier.COLD, "age_based"):
                        migrations += 1
        
        return migrations
    
    def _migrate_checkpoint(self, checkpoint_id: int, target_tier: StorageTier, reason: str) -> bool:
        """
        Migrate checkpoint to target tier.
        
        Args:
            checkpoint_id: Checkpoint to migrate
            target_tier: Target tier
            reason: Reason for migration
            
        Returns:
            True if migration successful
        """
        with self._metadata_lock:
            metadata = self.checkpoint_metadata.get(checkpoint_id)
            
            if not metadata or metadata.current_tier == target_tier:
                return False
            
            source_tier = metadata.current_tier
            source_path = self._get_checkpoint_path(checkpoint_id, source_tier)
            target_path = self._get_checkpoint_path(checkpoint_id, target_tier)
            
            # Move file
            try:
                if source_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
                    
                    # Update cache
                    if source_tier == StorageTier.HOT and self.hot_cache is not None:
                        with self._cache_lock:
                            self.hot_cache.pop(checkpoint_id, None)
                    
                    # Record transition
                    metadata.record_tier_transition(source_tier, target_tier, reason)
                    self._save_metadata()
                    
                    return True
                    
            except Exception as e:
                print(f"Error migrating checkpoint {checkpoint_id}: {e}")
                return False
        
        return False
    
    def _promote_checkpoint(self, checkpoint_id: int, reason: str) -> bool:
        """Promote checkpoint to hot tier"""
        return self._migrate_checkpoint(checkpoint_id, StorageTier.HOT, reason)
    
    def _get_checkpoint_path(self, checkpoint_id: int, tier: StorageTier) -> Path:
        """Get filesystem path for checkpoint in tier"""
        filename = f"checkpoint_{checkpoint_id}.pkl"
        return self.tier_paths[tier] / filename
    
    def get_tier_statistics(self) -> Dict[str, TierStatistics]:
        """
        Get statistics for all tiers.
        
        Returns:
            Dictionary mapping tier name to TierStatistics
        """
        stats = {
            'hot': TierStatistics(StorageTier.HOT, cost_per_gb_month=self.tier_costs['hot']),
            'warm': TierStatistics(StorageTier.WARM, cost_per_gb_month=self.tier_costs['warm']),
            'cold': TierStatistics(StorageTier.COLD, cost_per_gb_month=self.tier_costs['cold'])
        }
        
        with self._metadata_lock:
            for checkpoint_id, metadata in self.checkpoint_metadata.items():
                tier_key = metadata.current_tier.value
                stats[tier_key].checkpoint_count += 1
                stats[tier_key].total_size_bytes += metadata.size_bytes
                stats[tier_key].access_count += metadata.access_count
        
        return stats
    
    def get_cost_report(self) -> Dict[str, Any]:
        """
        Generate cost analysis report.
        
        Returns:
            Cost breakdown and savings analysis
        """
        tier_stats = self.get_tier_statistics()
        
        total_size_bytes = sum(s.total_size_bytes for s in tier_stats.values())
        total_monthly_cost = sum(s.estimated_monthly_cost() for s in tier_stats.values())
        
        # Calculate cost if everything was in hot tier
        hot_tier_cost = (total_size_bytes / (1024**3)) * self.tier_costs['hot']
        
        savings = hot_tier_cost - total_monthly_cost
        savings_percent = (savings / hot_tier_cost * 100) if hot_tier_cost > 0 else 0
        
        return {
            'total_size_gb': total_size_bytes / (1024**3),
            'total_monthly_cost': total_monthly_cost,
            'cost_if_all_hot': hot_tier_cost,
            'monthly_savings': savings,
            'savings_percent': savings_percent,
            'tier_breakdown': {
                tier_name: {
                    'checkpoints': stats.checkpoint_count,
                    'size_gb': stats.total_size_bytes / (1024**3),
                    'monthly_cost': stats.estimated_monthly_cost()
                }
                for tier_name, stats in tier_stats.items()
            }
        }
    
    def _load_metadata(self):
        """Load tier metadata from disk"""
        if not self.metadata_file.exists():
            return
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            for checkpoint_id_str, meta_dict in data.items():
                checkpoint_id = int(checkpoint_id_str)
                
                metadata = CheckpointTierMetadata(
                    checkpoint_id=checkpoint_id,
                    current_tier=StorageTier(meta_dict['current_tier']),
                    creation_time=meta_dict['creation_time'],
                    last_access_time=meta_dict['last_access_time'],
                    access_count=meta_dict.get('access_count', 0),
                    tier_transition_history=meta_dict.get('tier_transition_history', []),
                    size_bytes=meta_dict.get('size_bytes', 0)
                )
                
                self.checkpoint_metadata[checkpoint_id] = metadata
                
        except Exception as e:
            print(f"Error loading tier metadata: {e}")
    
    def _save_metadata(self):
        """Save tier metadata to disk"""
        try:
            data = {}
            for checkpoint_id, metadata in self.checkpoint_metadata.items():
                data[str(checkpoint_id)] = {
                    'current_tier': metadata.current_tier.value,
                    'creation_time': metadata.creation_time,
                    'last_access_time': metadata.last_access_time,
                    'access_count': metadata.access_count,
                    'tier_transition_history': metadata.tier_transition_history,
                    'size_bytes': metadata.size_bytes
                }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving tier metadata: {e}")
    
    def shutdown(self):
        """Shutdown tiered storage (stop migrator)"""
        if self.migrator:
            self.migrator.stop()
            self.migrator.join(timeout=5)
