"""
Incremental Checkpointing System
Version: 1.1.0

A high-performance incremental checkpointing implementation for FaaS applications.
Includes performance optimizations and production-grade error handling.
"""

from .state_tracker import StateChangeTracker
from .compressor import DeltaCompressor, OptimizedDeltaCompressor
from .storage import IncrementalCheckpoint, CheckpointStorageManager
from .manager import IncrementalCheckpointManager, ConditionalCheckpointManager
from .optimizations import (
    OptimizedHashCalculator,
    MemoryOptimizer,
    PerformanceMonitor,
    is_xxhash_available
)
from .production import (
    ErrorHandler,
    BackwardCompatibility,
    ProductionLogger,
    HealthChecker,
    CheckpointError,
    CheckpointErrorType
)
from .enhanced_manager import ProductionCheckpointManager
from .async_checkpoint_manager import AsyncCheckpointManager, CheckpointPriority
from .compression_manager import (
    CompressionManager,
    CompressionAlgorithm,
    ContentType,
    CompressionResult,
    DecompressionResult
)
from .parallel_restoration import (
    ParallelRestoration,
    DependencyGraph,
    RestorationResult
)
from .validation import (
    CheckpointValidator,
    ChecksumCalculator,
    ChecksumAlgorithm,
    ValidationLevel,
    CorruptionType,
    QualityLevel,
    ValidationResult,
    ValidationReport
)
from .tiered_storage import (
    TieredStorageManager,
    StorageTier,
    TierPolicy,
    CheckpointTierMetadata,
    TierStatistics,
    TierMigrator
)
from .predictive_scheduler import (
    PredictiveCheckpointManager,
    SchedulingStrategy,
    LoadLevel,
    SystemLoad,
    WorkloadPattern,
    CheckpointSchedule,
    LoadMonitor,
    WorkloadAnalyzer,
    CheckpointPredictor,
    AdaptiveScheduler
)
from .distributed_coordinator import (
    DistributedCheckpointCoordinator,
    RaftNode,
    DistributedLockManager,
    NodeState,
    MessageType,
    LogEntry,
    CheckpointCoordination,
    NodeInfo
)

# Integration and migration (Step 8)
from .integration import (
    JSONCheckpointAdapter,
    PickleCheckpointAdapter,
    CheckpointContext,
    RolloutStrategy,
    FeatureFlags,
    create_fission_adapter
)
from .migration import CheckpointMigrator, MigrationReport, CodeMigrationHelper, quick_migrate
from .config import (
    CheckpointConfig,
    ConfigPresets,
    ConfigValidator,
    CheckpointPolicy,
    CompressionLevel,
    load_config
)

__version__ = '2.6.0'
__all__ = [
    # Core components
    'StateChangeTracker',
    'DeltaCompressor',
    'OptimizedDeltaCompressor',
    'IncrementalCheckpoint',
    'CheckpointStorageManager',
    'IncrementalCheckpointManager',
    'ConditionalCheckpointManager',
    
    # Enhanced manager
    'ProductionCheckpointManager',
    'AsyncCheckpointManager',
    'CheckpointPriority',
    
    # Compression
    'CompressionManager',
    'CompressionAlgorithm',
    'ContentType',
    'CompressionResult',
    'DecompressionResult',
    
    # Parallel Restoration
    'ParallelRestoration',
    'DependencyGraph',
    'RestorationResult',
    
    # Validation
    'CheckpointValidator',
    'ChecksumCalculator',
    'ChecksumAlgorithm',
    'ValidationLevel',
    'CorruptionType',
    'QualityLevel',
    'ValidationResult',
    'ValidationReport',
    
    # Tiered Storage
    'TieredStorageManager',
    'StorageTier',
    'TierPolicy',
    'CheckpointTierMetadata',
    'TierStatistics',
    'TierMigrator',
    
    # Predictive Scheduling
    'PredictiveCheckpointManager',
    'SchedulingStrategy',
    'LoadLevel',
    'SystemLoad',
    'WorkloadPattern',
    'CheckpointSchedule',
    'LoadMonitor',
    'WorkloadAnalyzer',
    'CheckpointPredictor',
    'AdaptiveScheduler',
    
    # Distributed Coordination
    'DistributedCheckpointCoordinator',
    'RaftNode',
    'DistributedLockManager',
    'NodeState',
    'MessageType',
    'LogEntry',
    'CheckpointCoordination',
    'NodeInfo',
    
    # Optimizations
    'OptimizedHashCalculator',
    'MemoryOptimizer',
    'PerformanceMonitor',
    'is_xxhash_available',
    
    # Production features
    'ErrorHandler',
    'BackwardCompatibility',
    'ProductionLogger',
    'HealthChecker',
    'CheckpointError',
    'CheckpointErrorType',
    
    # Integration and migration (Step 8)
    'JSONCheckpointAdapter',
    'PickleCheckpointAdapter',
    'CheckpointContext',
    'RolloutStrategy',
    'FeatureFlags',
    'create_fission_adapter',
    'CheckpointMigrator',
    'MigrationReport',
    'CodeMigrationHelper',
    'quick_migrate',
    'CheckpointConfig',
    'ConfigPresets',
    'ConfigValidator',
    'CheckpointPolicy',
    'CompressionLevel',
    'load_config',
]
