# API Reference - Incremental Checkpointing

Complete API documentation for all classes, methods, and functions in the incremental checkpointing system.

## Table of Contents

1. [Core Components](#core-components)
2. [Production Components](#production-components)
3. [Integration Components](#integration-components)
4. [Configuration](#configuration)
5. [Migration Tools](#migration-tools)
6. [Utility Functions](#utility-functions)

---

## Core Components

### StateChangeTracker

Tracks changes between application states for incremental checkpointing.

```python
from incremental_checkpoint import StateChangeTracker

tracker = StateChangeTracker()
```

#### Methods

##### `update_baseline(state: Dict[str, Any]) -> None`

Update the baseline state for comparison.

**Parameters:**
- `state`: Dictionary representing current application state

**Example:**
```python
tracker.update_baseline({'counter': 0, 'cache': {}})
```

##### `track_changes(current_state: Dict[str, Any]) -> Dict[str, Any]`

Detect changes between current state and baseline.

**Parameters:**
- `current_state`: Current application state

**Returns:**
- Dictionary containing `added`, `modified`, `deleted` keys with changed data

**Example:**
```python
changes = tracker.track_changes({'counter': 5, 'cache': {'key': 'value'}})
# Returns: {'added': {'cache': {...}}, 'modified': {'counter': 5}, 'deleted': {}}
```

##### `has_changes(current_state: Dict[str, Any]) -> bool`

Check if state has changed since baseline.

**Parameters:**
- `current_state`: State to check

**Returns:**
- `True` if changes detected, `False` otherwise

##### `get_changed_keys(current_state: Dict[str, Any]) -> Set[str]`

Get set of changed keys.

**Returns:**
- Set of key names that changed

##### `get_change_statistics() -> Dict[str, int]`

Get statistics about tracked changes.

**Returns:**
- Dictionary with `added_count`, `modified_count`, `deleted_count`, `total_keys`

##### `reset() -> None`

Clear all tracking data.

---

### DeltaCompressor

Compress state changes using zlib compression.

```python
from incremental_checkpoint import DeltaCompressor

compressor = DeltaCompressor(compression_level=6)
```

#### Constructor Parameters

- `compression_level` (int, default=6): zlib compression level (0-9)

#### Methods

##### `compress(data: Dict[str, Any]) -> bytes`

Compress dictionary data.

**Parameters:**
- `data`: Dictionary to compress

**Returns:**
- Compressed bytes

**Example:**
```python
compressed = compressor.compress({'key': 'value'})
```

##### `decompress(compressed_data: bytes) -> Dict[str, Any]`

Decompress data back to dictionary.

**Parameters:**
- `compressed_data`: Compressed bytes

**Returns:**
- Original dictionary

##### `get_compression_ratio() -> float`

Get average compression ratio across all operations.

**Returns:**
- Compression ratio (e.g., 5.0 means 5x compression)

##### `get_statistics() -> Dict[str, Any]`

Get compression statistics.

**Returns:**
```python
{
    'total_compressions': int,
    'total_original_bytes': int,
    'total_compressed_bytes': int,
    'average_compression_ratio': float,
    'average_compression_time_ms': float
}
```

---

### OptimizedDeltaCompressor

Enhanced compressor with parallel processing for large data.

```python
from incremental_checkpoint import OptimizedDeltaCompressor

compressor = OptimizedDeltaCompressor(
    compression_level=6,
    max_workers=4,
    parallel_threshold_kb=100
)
```

#### Constructor Parameters

- `compression_level` (int): Compression level (0-9)
- `max_workers` (int, default=4): Number of parallel workers
- `parallel_threshold_kb` (int, default=100): Use parallel compression above this size

#### Methods

Inherits all methods from `DeltaCompressor` plus:

##### `compress_parallel(data: Dict[str, Any]) -> bytes`

Compress large data using parallel processing.

**Parameters:**
- `data`: Large dictionary to compress

**Returns:**
- Compressed bytes

**Example:**
```python
# Automatically uses parallel compression for large data
large_data = {f'key_{i}': f'value_{i}' * 1000 for i in range(1000)}
compressed = compressor.compress(large_data)
```

---

### IncrementalCheckpoint

Represents a single checkpoint (full or incremental).

```python
from incremental_checkpoint import IncrementalCheckpoint

# Usually created by manager, not directly
checkpoint = IncrementalCheckpoint(
    checkpoint_id=1,
    checkpoint_type="FULL",
    state_data=b'...',
    previous_checkpoint_id=None,
    timestamp=datetime.now()
)
```

#### Attributes

- `checkpoint_id` (int): Unique checkpoint identifier
- `checkpoint_type` (str): "FULL" or "INCR"
- `state_data` (bytes): Compressed checkpoint data
- `previous_checkpoint_id` (Optional[int]): Reference to previous checkpoint
- `timestamp` (datetime): Creation timestamp
- `metadata` (Dict): Additional metadata

#### Methods

##### `get_size() -> int`

Get checkpoint size in bytes.

**Returns:**
- Size in bytes

##### `to_dict() -> Dict[str, Any]`

Serialize checkpoint to dictionary.

##### `from_dict(data: Dict[str, Any]) -> IncrementalCheckpoint`

Deserialize checkpoint from dictionary.

---

### CheckpointStorageManager

Manages checkpoint storage and retrieval.

```python
from incremental_checkpoint import CheckpointStorageManager

storage = CheckpointStorageManager(storage_path="./checkpoints")
```

#### Constructor Parameters

- `storage_path` (str): Directory for checkpoint storage

#### Methods

##### `store_checkpoint(checkpoint: IncrementalCheckpoint) -> None`

Store checkpoint to disk.

**Parameters:**
- `checkpoint`: Checkpoint to store

##### `load_checkpoint(checkpoint_id: int) -> IncrementalCheckpoint`

Load checkpoint from disk.

**Parameters:**
- `checkpoint_id`: ID of checkpoint to load

**Returns:**
- Loaded checkpoint

**Raises:**
- `FileNotFoundError`: If checkpoint doesn't exist

##### `list_checkpoints() -> List[IncrementalCheckpoint]`

Get all stored checkpoints.

**Returns:**
- List of checkpoint objects

##### `delete_checkpoint(checkpoint_id: int) -> None`

Delete checkpoint from disk.

##### `get_checkpoint_chain(checkpoint_id: int) -> List[IncrementalCheckpoint]`

Get chain of checkpoints needed to restore state.

**Parameters:**
- `checkpoint_id`: Target checkpoint ID

**Returns:**
- List of checkpoints from last full checkpoint to target

##### `verify_checkpoint_chain(checkpoint_id: int) -> bool`

Verify checkpoint chain is complete.

**Returns:**
- `True` if chain is valid

##### `get_storage_statistics() -> Dict[str, Any]`

Get storage statistics.

**Returns:**
```python
{
    'total_checkpoints': int,
    'total_storage_bytes': int,
    'oldest_checkpoint': datetime,
    'newest_checkpoint': datetime
}
```

---

### IncrementalCheckpointManager

Main checkpoint manager coordinating all components.

```python
from incremental_checkpoint import IncrementalCheckpointManager

manager = IncrementalCheckpointManager(
    storage_path="./checkpoints",
    full_checkpoint_interval=10,
    compression_level=6
)
```

#### Constructor Parameters

- `storage_path` (str): Directory for checkpoints
- `full_checkpoint_interval` (int, default=10): Create full checkpoint every N checkpoints
- `compression_level` (int, default=6): Compression level (0-9)
- `cleanup_policy` (str, default="keep_all_full"): Cleanup policy
- `max_checkpoints` (int, default=100): Maximum checkpoints to keep

#### Methods

##### `create_checkpoint(state: Dict[str, Any]) -> IncrementalCheckpoint`

Create new checkpoint (full or incremental).

**Parameters:**
- `state`: Current application state

**Returns:**
- Created checkpoint object

**Example:**
```python
checkpoint = manager.create_checkpoint({
    'counter': 42,
    'cache': {'key': 'value'}
})
print(f"Created checkpoint {checkpoint.checkpoint_id}")
```

##### `restore_from_checkpoint(checkpoint_id: int) -> Dict[str, Any]`

Restore application state from checkpoint.

**Parameters:**
- `checkpoint_id`: ID of checkpoint to restore

**Returns:**
- Restored state dictionary

**Example:**
```python
state = manager.restore_from_checkpoint(15)
print(f"Restored state: {state}")
```

##### `list_checkpoints() -> List[IncrementalCheckpoint]`

Get all checkpoints.

**Returns:**
- List of checkpoints ordered by ID

##### `delete_checkpoint(checkpoint_id: int) -> None`

Delete specific checkpoint.

##### `cleanup_old_checkpoints() -> int`

Clean up old checkpoints based on policy.

**Returns:**
- Number of checkpoints deleted

##### `verify_checkpoint(checkpoint_id: int) -> bool`

Verify checkpoint integrity.

**Returns:**
- `True` if checkpoint is valid

##### `get_statistics() -> Dict[str, Any]`

Get comprehensive statistics.

**Returns:**
```python
{
    'total_checkpoints': int,
    'full_checkpoints': int,
    'incremental_checkpoints': int,
    'total_storage_mb': float,
    'avg_checkpoint_size_bytes': int,
    'avg_compression_ratio': float,
    'compression_time_ms': float
}
```

##### `reset() -> None`

Reset manager state (does not delete stored checkpoints).

---

### ConditionalCheckpointManager

Manager that skips checkpoints when state unchanged.

```python
from incremental_checkpoint import ConditionalCheckpointManager

manager = ConditionalCheckpointManager(
    storage_path="./checkpoints",
    full_checkpoint_interval=10
)
```

Inherits all methods from `IncrementalCheckpointManager` with modified behavior:

- `create_checkpoint()`: Returns `None` if state unchanged since last checkpoint

---

## Production Components

### ProductionCheckpointManager

All-in-one manager with optimizations and production features.

```python
from incremental_checkpoint import ProductionCheckpointManager

manager = ProductionCheckpointManager(
    storage_path="./checkpoints",
    full_checkpoint_interval=10,
    enable_optimizations=True,
    enable_monitoring=True,
    max_retries=3
)
```

#### Constructor Parameters

- `storage_path` (str): Checkpoint directory
- `full_checkpoint_interval` (int, default=10): Full checkpoint interval
- `enable_optimizations` (bool, default=True): Enable hash caching and memory optimization
- `enable_monitoring` (bool, default=True): Enable performance monitoring
- `max_retries` (int, default=3): Maximum retry attempts

#### Methods

All methods from `IncrementalCheckpointManager` plus:

##### `run_health_check() -> Dict[str, Any]`

Run system health check.

**Returns:**
```python
{
    'status': 'HEALTHY' | 'UNHEALTHY',
    'storage_health': bool,
    'compression_health': bool,
    'error_count': int,
    'timestamp': datetime
}
```

##### `get_performance_report() -> Dict[str, Any]`

Get performance metrics and bottleneck analysis.

**Returns:**
```python
{
    'checkpoint_stats': {...},
    'restoration_stats': {...},
    'compression_stats': {...},
    'bottlenecks': [...]
}
```

##### `optimize_performance() -> None`

Run performance optimizations (e.g., cache cleanup).

##### `get_diagnostic_info() -> Dict[str, Any]`

Get comprehensive diagnostic information.

**Returns:**
```python
{
    'version': str,
    'checkpoints': int,
    'storage_mb': float,
    'compression_ratio': float,
    'errors': int,
    'optimizations_enabled': bool,
    'monitoring_enabled': bool
}
```

##### `restore_from_legacy_checkpoint(checkpoint_data: Dict[str, Any]) -> Dict[str, Any]`

Restore from legacy checkpoint format.

**Parameters:**
- `checkpoint_data`: Legacy checkpoint data

**Returns:**
- Restored state

---

### OptimizedHashCalculator

Optimized hash calculation with caching.

```python
from incremental_checkpoint import OptimizedHashCalculator

calculator = OptimizedHashCalculator(
    use_xxhash=True,
    cache_size=10000
)
```

#### Constructor Parameters

- `use_xxhash` (bool, default=True): Use xxhash (requires installation)
- `cache_size` (int, default=10000): Maximum cache entries

#### Methods

##### `calculate_hash(value: Any) -> str`

Calculate hash of value with caching.

**Parameters:**
- `value`: Any Python object

**Returns:**
- Hash string

##### `get_cache_stats() -> Dict[str, Any]`

Get cache statistics.

**Returns:**
```python
{
    'size': int,
    'hits': int,
    'misses': int,
    'hit_rate': float
}
```

##### `clear_cache() -> None`

Clear hash cache.

##### `optimize_cache() -> int`

Remove least-used entries.

**Returns:**
- Number of entries removed

---

### PerformanceMonitor

Monitor checkpoint operation performance.

```python
from incremental_checkpoint import PerformanceMonitor

monitor = PerformanceMonitor()
```

#### Methods

##### `record_checkpoint_time(duration_ms: float) -> None`

Record checkpoint creation time.

##### `record_restoration_time(duration_ms: float) -> None`

Record restoration time.

##### `get_statistics() -> Dict[str, Any]`

Get performance statistics.

**Returns:**
```python
{
    'checkpoint_times': {'avg': float, 'min': float, 'max': float},
    'restoration_times': {...},
    'total_operations': int
}
```

##### `identify_bottlenecks(threshold_ms: float = 100.0) -> List[str]`

Identify performance bottlenecks.

**Parameters:**
- `threshold_ms`: Threshold for slow operations

**Returns:**
- List of bottleneck descriptions

---

### ErrorHandler

Retry logic and error recovery.

```python
from incremental_checkpoint import ErrorHandler

handler = ErrorHandler(max_retries=3, retry_delay=1.0)
```

#### Constructor Parameters

- `max_retries` (int, default=3): Maximum retry attempts
- `retry_delay` (float, default=1.0): Base delay between retries (exponential backoff)

#### Methods

##### `retry_operation(operation: Callable, *args, **kwargs) -> Any`

Execute operation with retry logic.

**Parameters:**
- `operation`: Function to execute
- `*args, **kwargs`: Arguments for operation

**Returns:**
- Operation result

**Raises:**
- Exception from last retry if all attempts fail

**Example:**
```python
result = handler.retry_operation(
    manager.create_checkpoint,
    application_state
)
```

##### `handle_checkpoint_creation_error(error: Exception, state: Dict) -> Optional[IncrementalCheckpoint]`

Handle checkpoint creation errors with fallback strategies.

##### `get_error_history() -> List[Dict[str, Any]]`

Get history of handled errors.

---

### ProductionLogger

Structured logging for checkpoint operations.

```python
from incremental_checkpoint import ProductionLogger

logger = ProductionLogger(name="checkpoint_system")
```

#### Methods

##### `log_checkpoint_created(checkpoint_id: int, type: str, size: int) -> None`

Log checkpoint creation.

##### `log_checkpoint_restored(checkpoint_id: int, duration_ms: float) -> None`

Log checkpoint restoration.

##### `log_performance_warning(operation: str, duration_ms: float) -> None`

Log performance warnings.

##### `log_cleanup(deleted: int, kept: int) -> None`

Log cleanup operations.

##### `log_error(error: Exception, context: Dict[str, Any]) -> None`

Log errors with context.

---

### HealthChecker

System health monitoring.

```python
from incremental_checkpoint import HealthChecker

checker = HealthChecker(manager)
```

#### Constructor Parameters

- `manager`: CheckpointManager instance to check

#### Methods

##### `check_storage_health() -> bool`

Check if storage is accessible and working.

##### `check_compression_health() -> bool`

Check if compression is working correctly.

##### `run_all_checks() -> Dict[str, bool]`

Run all health checks.

**Returns:**
```python
{
    'storage': bool,
    'compression': bool,
    'overall': bool
}
```

##### `get_health_status() -> str`

Get overall health status.

**Returns:**
- "HEALTHY" or "UNHEALTHY"

---

## Integration Components

### JSONCheckpointAdapter

Drop-in replacement for JSON checkpoint systems.

```python
from incremental_checkpoint.integration import JSONCheckpointAdapter, FeatureFlags

flags = FeatureFlags(
    use_incremental_checkpointing=True,
    rollout_percentage=100,
    enable_performance_monitoring=True
)

adapter = JSONCheckpointAdapter(
    checkpoint_dir="/tmp/checkpoints",
    feature_flags=flags
)
```

#### Constructor Parameters

- `checkpoint_dir` (str): Checkpoint directory
- `feature_flags` (FeatureFlags): Configuration flags

#### Methods

##### `load_checkpoint(checkpoint_path: str) -> Dict[str, Any]`

Load checkpoint (legacy interface).

##### `save_checkpoint(state: Dict[str, Any], checkpoint_path: str) -> None`

Save checkpoint (legacy interface).

##### `checkpoint_exists(checkpoint_path: str) -> bool`

Check if checkpoint exists.

##### `migrate_legacy_checkpoint(legacy_path: str) -> Optional[int]`

Migrate legacy checkpoint to incremental format.

##### `get_statistics() -> Dict[str, Any]`

Get checkpoint statistics.

##### `run_health_check() -> Dict[str, Any]`

Run health check.

---

### CheckpointContext

Context manager for automatic checkpointing.

```python
from incremental_checkpoint.integration import CheckpointContext

with CheckpointContext(adapter, checkpoint_path, get_state, set_state):
    # Your code here
    # Checkpoint automatically loaded on entry
    # Checkpoint automatically saved on exit
    pass
```

#### Constructor Parameters

- `adapter`: Checkpoint adapter
- `checkpoint_path` (str): Path to checkpoint file
- `state_getter` (Callable): Function that returns current state
- `state_setter` (Callable): Function that restores state

---

### RolloutStrategy

Gradual deployment strategies.

```python
from incremental_checkpoint.integration import RolloutStrategy

strategy = RolloutStrategy.CANARY_5  # 5% traffic
strategy = RolloutStrategy.CANARY_25  # 25% traffic
strategy = RolloutStrategy.CANARY_50  # 50% traffic
strategy = RolloutStrategy.ENABLED  # 100% traffic
strategy = RolloutStrategy.DISABLED  # 0% traffic
```

---

### create_fission_adapter()

Convenience function for Fission functions.

```python
from incremental_checkpoint.integration import create_fission_adapter, RolloutStrategy

adapter = create_fission_adapter(
    checkpoint_file="/tmp/checkpoint.json",
    enable_incremental=True,
    rollout_strategy=RolloutStrategy.CANARY_5
)
```

#### Parameters

- `checkpoint_file` (str): Checkpoint file path
- `enable_incremental` (bool): Enable incremental checkpointing
- `rollout_strategy` (RolloutStrategy): Gradual rollout strategy

#### Returns

- Configured `JSONCheckpointAdapter`

---

## Configuration

### CheckpointConfig

Centralized configuration management.

```python
from incremental_checkpoint.config import CheckpointConfig

config = CheckpointConfig(
    checkpoint_dir="/var/lib/checkpoints",
    max_checkpoints=100,
    compression_level=6,
    enable_monitoring=True
)

# Validate configuration
config.validate()

# Save to file
config.save_to_file("/etc/checkpoint_config.json")

# Load from file
config = CheckpointConfig.from_file("/etc/checkpoint_config.json")

# Load from environment
config = CheckpointConfig.from_environment(prefix="CHECKPOINT_")
```

#### Configuration Options

See [Configuration Management](INTEGRATION_GUIDE.md#configuration-management) for complete list.

---

### ConfigPresets

Predefined configurations.

```python
from incremental_checkpoint.config import ConfigPresets

dev_config = ConfigPresets.development()
prod_config = ConfigPresets.production()
perf_config = ConfigPresets.high_performance()
storage_config = ConfigPresets.low_storage()
test_config = ConfigPresets.testing()
canary_config = ConfigPresets.canary_rollout(percentage=5)
```

---

## Migration Tools

### CheckpointMigrator

Automated migration from legacy checkpoints.

```python
from incremental_checkpoint.migration import CheckpointMigrator

migrator = CheckpointMigrator(
    checkpoint_dir="/var/lib/checkpoints",
    backup_dir="/var/lib/checkpoints_backup",
    verify_migration=True
)

# Migrate JSON checkpoints
report = migrator.migrate_json_checkpoints()

# Migrate pickle checkpoints
report = migrator.migrate_pickle_checkpoints()

# Rollback if needed
migrator.rollback_migration()

# Cleanup legacy files
migrator.cleanup_legacy_files(keep_backup=True)
```

#### Methods

See [Migration Tools](INTEGRATION_GUIDE.md#migration-tools) documentation.

---

### quick_migrate()

Single-function migration.

```python
from incremental_checkpoint.migration import quick_migrate

report = quick_migrate(
    checkpoint_dir="/var/lib/checkpoints",
    checkpoint_type="json",  # or "pickle"
    verify=True,
    cleanup=False
)

print(f"Migrated: {report.migrated_successfully}/{report.total_checkpoints}")
print(f"Space saved: {report.space_savings_pct:.1f}%")
```

---

## Utility Functions

### is_xxhash_available()

Check if xxhash library is available.

```python
from incremental_checkpoint import is_xxhash_available

if is_xxhash_available():
    print("xxhash is available - 3-5x faster hashing")
else:
    print("xxhash not available - using MD5 fallback")
```

**Returns:**
- `True` if xxhash is installed, `False` otherwise

---

### load_config()

Load configuration from multiple sources.

```python
from incremental_checkpoint.config import load_config

# Priority: file > preset > environment > default
config = load_config(
    config_source="/etc/checkpoint_config.json",
    preset="production",
    use_environment=True
)
```

**Parameters:**
- `config_source` (Optional[str]): Path to config file (highest priority)
- `preset` (Optional[str]): Preset name (fallback)
- `use_environment` (bool): Load from environment variables

**Returns:**
- `CheckpointConfig` instance

---

## Complete Usage Example

```python
from incremental_checkpoint import ProductionCheckpointManager
from incremental_checkpoint.config import ConfigPresets

# 1. Load configuration
config = ConfigPresets.production()

# 2. Create manager
manager = ProductionCheckpointManager(
    storage_path=config.checkpoint_dir,
    full_checkpoint_interval=config.full_checkpoint_interval,
    enable_optimizations=config.enable_hash_optimization,
    enable_monitoring=config.enable_monitoring
)

# 3. Create checkpoints
for i in range(20):
    state = {
        'invocation_count': i,
        'cache': {f'key_{j}': f'value_{j}' for j in range(i)}
    }
    checkpoint = manager.create_checkpoint(state)
    print(f"Created checkpoint {checkpoint.checkpoint_id}")

# 4. Restore from checkpoint
restored_state = manager.restore_from_checkpoint(15)
print(f"Restored: {restored_state}")

# 5. Run health check
health = manager.run_health_check()
print(f"System health: {health['status']}")

# 6. Get performance report
report = manager.get_performance_report()
print(f"Avg checkpoint time: {report['checkpoint_stats']['avg_ms']:.2f}ms")

# 7. Cleanup old checkpoints
deleted = manager.cleanup_old_checkpoints()
print(f"Cleaned up {deleted} old checkpoints")

# 8. Get statistics
stats = manager.get_statistics()
print(f"Total storage: {stats['total_storage_mb']:.3f} MB")
print(f"Compression ratio: {stats['avg_compression_ratio']:.2f}x")
```

---

## Error Handling

All checkpoint operations can raise exceptions. Recommended error handling:

```python
from incremental_checkpoint import ProductionCheckpointManager
from incremental_checkpoint.production import CheckpointError

manager = ProductionCheckpointManager("./checkpoints")

try:
    checkpoint = manager.create_checkpoint(state)
except Exception as e:
    print(f"Checkpoint failed: {e}")
    # Application continues but may lose state on failure

try:
    state = manager.restore_from_checkpoint(checkpoint_id)
except FileNotFoundError:
    print("Checkpoint not found")
    state = {}  # Start with empty state
except Exception as e:
    print(f"Restoration failed: {e}")
    state = {}
```

For production use with automatic retry:

```python
from incremental_checkpoint import ProductionCheckpointManager, ErrorHandler

manager = ProductionCheckpointManager("./checkpoints", max_retries=3)
handler = ErrorHandler(max_retries=3)

# Automatic retry on failure
checkpoint = handler.retry_operation(
    manager.create_checkpoint,
    application_state
)
```

---

## Performance Considerations

### Memory Usage

- Hash cache: ~8 bytes per entry × cache_size
- Checkpoint chain: Stored on disk, minimal memory
- Compression: Temporary memory during compression

**Recommendation:** For memory-constrained environments, use `ConfigPresets.low_storage()` or set `hash_cache_size=1000`.

### CPU Usage

- Compression: CPU-intensive for large states
- Parallel compression: Uses multiple cores
- Hash calculation: Fast with xxhash, slower with MD5

**Recommendation:** For CPU-constrained environments, use `compression_level=1` or disable parallel compression.

### Disk I/O

- Sequential writes for checkpoints
- Random reads during restoration
- Index file updated after each checkpoint

**Recommendation:** Use SSD storage for best performance. On HDD, increase `full_checkpoint_interval` to reduce writes.

---

## Version Compatibility

- **Version 1.0.0**: Core implementation (Steps 1-4)
- **Version 1.1.0**: Optimizations and production features (Steps 6-7)
- **Version 1.2.0**: Integration and migration tools (Step 8)
- **Version 1.3.0**: Complete documentation (Step 9)

### Breaking Changes

None. All versions are backward compatible. Legacy checkpoints can be converted using `CheckpointMigrator`.

---

## See Also

- [Integration Guide](INTEGRATION_GUIDE.md) - How to integrate with existing applications
- [Testing Guide](TESTING_GUIDE.md) - Testing and validation
- [Optimization Guide](OPTIMIZATION_GUIDE.md) - Performance tuning
- [Project Status](PROJECT_STATUS.md) - Current implementation status
