# Troubleshooting Playbook

Diagnostic procedures and solutions for common issues with incremental checkpointing.

## Table of Contents

1. [Quick Diagnostic](#quick-diagnostic)
2. [Performance Issues](#performance-issues)
3. [Storage Issues](#storage-issues)
4. [Memory Issues](#memory-issues)
5. [Checkpoint Corruption](#checkpoint-corruption)
6. [Recovery Failures](#recovery-failures)
7. [Error Code Reference](#error-code-reference)
8. [Monitoring and Alerts](#monitoring-and-alerts)

---

## Quick Diagnostic

### Health Check Command

```python
from incremental_checkpoint import ProductionCheckpointManager

manager = ProductionCheckpointManager(
    "./checkpoints",
    enable_health_checks=True
)

# Run health check
health = manager.check_health()

print(f"Status: {health['status']}")
print(f"Checkpoints: {health['checkpoint_count']}")
print(f"Storage: {health['storage_size_mb']:.2f} MB")

if health['issues']:
    print("Issues detected:")
    for issue in health['issues']:
        print(f"  - {issue}")
```

### System Status Overview

```python
# Get comprehensive status
status = {
    'health': manager.check_health(),
    'performance': manager.get_performance_report(),
    'storage': manager.get_checkpoint_history(),
    'errors': manager.get_recent_errors()
}

# Check for problems
if status['health']['status'] != 'healthy':
    print("⚠️ System unhealthy")
if status['performance']['bottlenecks']:
    print("⚠️ Performance bottlenecks detected")
if status['errors']:
    print(f"⚠️ {len(status['errors'])} recent errors")
```

---

## Performance Issues

### Issue: Slow Checkpoint Creation (>10ms)

**Symptoms:**
- Checkpoint creation takes longer than expected
- Application latency increases
- CPU usage spikes during checkpoints

**Diagnostic:**
```python
# Enable performance monitoring
manager = ProductionCheckpointManager(
    "./checkpoints",
    enable_monitoring=True
)

# Create checkpoint and analyze
checkpoint = manager.create_checkpoint(state)
report = manager.get_performance_report()

print(f"Avg create time: {report['checkpoint_creation']['avg_ms']:.2f}ms")
print(f"Bottlenecks: {report['bottlenecks']}")
```

**Decision Tree:**

```
Is avg_ms > 10ms?
├─ YES
│  ├─ Check compression level
│  │  ├─ If level > 6 → Reduce to 3-6
│  │  └─ If level ≤ 6 → Continue
│  │
│  ├─ Check state size
│  │  ├─ If > 1MB → Enable parallel compression
│  │  └─ If < 1MB → Check for deep nesting
│  │
│  ├─ Check storage speed
│  │  ├─ Network storage? → Use local buffer
│  │  ├─ HDD? → Migrate to SSD
│  │  └─ OK → Continue
│  │
│  └─ Check bottlenecks
│     ├─ "serialization" → Optimize state structure
│     ├─ "compression" → Reduce compression level
│     ├─ "hashing" → Disable hash optimization
│     └─ "io" → Improve storage speed
│
└─ NO → Performance OK
```

**Solutions:**

**Solution 1: Reduce Compression Level**
```python
# If compression is the bottleneck
config.compression_level = 3  # Down from 6+

# Or disable compression entirely
config.compression_level = 0
```

**Solution 2: Enable Parallel Compression**
```python
# For large states (>100KB)
config.parallel_compression = True
config.parallel_threshold_kb = 50
config.max_workers = 4
```

**Solution 3: Optimize State Structure**
```python
# Flatten deeply nested structures
def flatten_state(state):
    flat = {}
    for key, value in state.items():
        if isinstance(value, dict) and len(value) > 10:
            # Flatten large nested dicts
            for subkey, subvalue in value.items():
                flat[f"{key}.{subkey}"] = subvalue
        else:
            flat[key] = value
    return flat

optimized_state = flatten_state(original_state)
checkpoint = manager.create_checkpoint(optimized_state)
```

**Solution 4: Use Faster Storage**
```python
# Move to RAM disk for speed
config.checkpoint_dir = "/dev/shm/checkpoints"  # Linux
config.checkpoint_dir = "R:\\checkpoints"  # Windows (RAM disk)
```

---

### Issue: Low Throughput (<100 checkpoints/sec)

**Symptoms:**
- Cannot process checkpoints fast enough
- Checkpoint queue builds up
- Application becomes unresponsive

**Diagnostic:**
```python
import time

# Measure throughput
def measure_throughput(manager, state, duration_sec=10):
    start = time.time()
    count = 0
    
    while time.time() - start < duration_sec:
        manager.create_checkpoint(state)
        count += 1
    
    throughput = count / duration_sec
    return throughput

current_throughput = measure_throughput(manager, test_state)
print(f"Current throughput: {current_throughput:.1f} checkpoints/sec")
```

**Solutions:**

**Solution 1: Minimize Overhead**
```python
config = CheckpointConfig(
    compression_level=0,  # No compression
    enable_monitoring=False,  # No monitoring
    enable_logging=False,  # No logging
    verify_checkpoints=False,  # No verification
    enable_hash_optimization=False  # No caching overhead
)
```

**Solution 2: Use Conditional Checkpointing**
```python
# Skip unnecessary checkpoints
from incremental_checkpoint import ConditionalCheckpointManager

manager = ConditionalCheckpointManager("./checkpoints")

# Only checkpoint when state changes
if manager.tracker.has_changes(current_state):
    checkpoint = manager.create_checkpoint(current_state)
```

**Solution 3: Batch Processing**
```python
# Process multiple checkpoints in parallel
from concurrent.futures import ThreadPoolExecutor

def batch_checkpoint(states):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(manager.create_checkpoint, state)
            for state in states
        ]
        return [f.result() for f in futures]
```

---

### Issue: High CPU Usage (>20%)

**Symptoms:**
- CPU usage spikes during checkpoints
- Other processes slow down
- Thermal throttling

**Diagnostic:**
```python
import psutil
import os

# Monitor CPU during checkpoint
process = psutil.Process(os.getpid())
cpu_before = process.cpu_percent(interval=1)

checkpoint = manager.create_checkpoint(state)

cpu_after = process.cpu_percent(interval=1)
print(f"CPU usage: {cpu_after - cpu_before:.1f}%")
```

**Solutions:**

**Solution 1: Reduce Compression**
```python
# Compression is CPU-intensive
config.compression_level = 1  # Minimal CPU
# Or disable entirely
config.compression_level = 0
```

**Solution 2: Disable Parallelization**
```python
# Thread overhead may hurt more than help for small states
config.parallel_compression = False
```

**Solution 3: Use Conditional Checkpointing**
```python
# Reduce checkpoint frequency
manager = ConditionalCheckpointManager("./checkpoints")
# Checkpoints only created when state actually changes
```

---

## Storage Issues

### Issue: Checkpoint Directory Growing Too Large

**Symptoms:**
- Disk space running out
- Slow checkpoint operations
- Storage costs increasing

**Diagnostic:**
```python
import os

def analyze_storage(checkpoint_dir):
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(checkpoint_dir):
        for file in files:
            if file.endswith('.pkl'):
                path = os.path.join(root, file)
                total_size += os.path.getsize(path)
                file_count += 1
    
    return {
        'total_mb': total_size / (1024 * 1024),
        'file_count': file_count,
        'avg_size_kb': (total_size / file_count / 1024) if file_count > 0 else 0
    }

storage = analyze_storage("./checkpoints")
print(f"Total size: {storage['total_mb']:.2f} MB")
print(f"Files: {storage['file_count']}")
print(f"Avg size: {storage['avg_size_kb']:.2f} KB")
```

**Solutions:**

**Solution 1: Enable Automatic Cleanup**
```python
config.max_checkpoints = 50  # Keep only last 50
config.cleanup_policy = CheckpointPolicy.KEEP_LAST_N
```

**Solution 2: Increase Compression**
```python
config.compression_level = 9  # Maximum compression
config.enable_memory_optimization = True
config.memory_threshold_kb = 20  # Compress more aggressively
```

**Solution 3: Manual Cleanup**
```python
# Clean up old checkpoints
def cleanup_old_checkpoints(manager, keep_count=50):
    history = manager.get_checkpoint_history()
    
    if len(history) > keep_count:
        to_delete = history[:-keep_count]  # All except last keep_count
        
        for checkpoint_id in to_delete:
            manager.delete_checkpoint(checkpoint_id)
        
        print(f"Deleted {len(to_delete)} old checkpoints")

cleanup_old_checkpoints(manager)
```

**Solution 4: Archive Old Checkpoints**
```python
import shutil
from datetime import datetime, timedelta

def archive_old_checkpoints(checkpoint_dir, archive_dir, days=7):
    cutoff = datetime.now() - timedelta(days=days)
    
    for file in os.listdir(checkpoint_dir):
        if file.endswith('.pkl'):
            path = os.path.join(checkpoint_dir, file)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            
            if mtime < cutoff:
                # Move to archive
                archive_path = os.path.join(archive_dir, file)
                shutil.move(path, archive_path)
                print(f"Archived {file}")
```

---

### Issue: Cannot Write Checkpoints (Disk Full)

**Symptoms:**
- `OSError: No space left on device`
- Checkpoint creation fails
- Application crashes

**Diagnostic:**
```python
import shutil

def check_disk_space(path):
    usage = shutil.disk_usage(path)
    return {
        'total_gb': usage.total / (1024**3),
        'used_gb': usage.used / (1024**3),
        'free_gb': usage.free / (1024**3),
        'percent_used': (usage.used / usage.total) * 100
    }

space = check_disk_space("./checkpoints")
print(f"Free space: {space['free_gb']:.2f} GB ({100-space['percent_used']:.1f}%)")
```

**Solutions:**

**Solution 1: Emergency Cleanup**
```python
# Delete all checkpoints except most recent
def emergency_cleanup(manager):
    history = manager.get_checkpoint_history()
    
    # Keep only last 5 checkpoints
    if len(history) > 5:
        to_delete = history[:-5]
        for checkpoint_id in to_delete:
            try:
                manager.delete_checkpoint(checkpoint_id)
            except Exception as e:
                print(f"Failed to delete {checkpoint_id}: {e}")
        
        print(f"Emergency cleanup: deleted {len(to_delete)} checkpoints")
```

**Solution 2: Move to Different Volume**
```python
# Migrate checkpoints to different disk
import shutil

def migrate_checkpoints(old_dir, new_dir):
    os.makedirs(new_dir, exist_ok=True)
    
    # Copy all checkpoints
    for file in os.listdir(old_dir):
        old_path = os.path.join(old_dir, file)
        new_path = os.path.join(new_dir, file)
        shutil.move(old_path, new_path)
    
    print(f"Migrated checkpoints to {new_dir}")

# Check space on new volume first
new_space = check_disk_space("/mnt/large_volume")
if new_space['free_gb'] > 10:
    migrate_checkpoints("./checkpoints", "/mnt/large_volume/checkpoints")
```

**Solution 3: Implement Disk Space Monitoring**
```python
# Automatically clean up when space is low
def auto_cleanup_on_low_space(manager, checkpoint_dir, min_free_gb=5):
    space = check_disk_space(checkpoint_dir)
    
    if space['free_gb'] < min_free_gb:
        print(f"⚠️ Low disk space: {space['free_gb']:.2f} GB")
        
        # Aggressive cleanup
        history = manager.get_checkpoint_history()
        keep_count = max(10, len(history) // 2)  # Keep at least 10 or half
        
        to_delete = history[:-keep_count]
        for checkpoint_id in to_delete:
            manager.delete_checkpoint(checkpoint_id)
        
        print(f"Auto-cleanup: deleted {len(to_delete)} checkpoints")

# Run before each checkpoint
auto_cleanup_on_low_space(manager, "./checkpoints")
checkpoint = manager.create_checkpoint(state)
```

---

## Memory Issues

### Issue: High Memory Usage (>500MB)

**Symptoms:**
- Application memory grows over time
- Out of memory errors
- Slow garbage collection

**Diagnostic:**
```python
import tracemalloc
import gc

# Track memory usage
tracemalloc.start()
gc.collect()

snapshot1 = tracemalloc.take_snapshot()

# Create checkpoints
for i in range(100):
    checkpoint = manager.create_checkpoint(state)

gc.collect()
snapshot2 = tracemalloc.take_snapshot()

# Analyze growth
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
print("Top memory growth:")
for stat in top_stats[:10]:
    print(stat)

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")

tracemalloc.stop()
```

**Solutions:**

**Solution 1: Reduce Hash Cache Size**
```python
# Large cache uses memory
config.hash_cache_size = 1000  # Down from 10000+
# Or disable caching
config.enable_hash_optimization = False
```

**Solution 2: Enable Memory Optimization**
```python
config.enable_memory_optimization = True
config.memory_threshold_kb = 50  # Compress larger values
```

**Solution 3: Disable Parallel Compression**
```python
# Thread pool uses memory
config.parallel_compression = False
```

**Solution 4: Periodic Garbage Collection**
```python
import gc

# Force garbage collection after checkpoints
def checkpoint_with_cleanup(manager, state):
    checkpoint = manager.create_checkpoint(state)
    gc.collect()  # Force cleanup
    return checkpoint
```

**Solution 5: Clear Cache Periodically**
```python
# For OptimizedHashCalculator
def periodic_cache_clear(manager, checkpoint_interval=100):
    if manager.checkpoint_count % checkpoint_interval == 0:
        # Clear hash cache
        if hasattr(manager, 'compressor'):
            if hasattr(manager.compressor, 'hash_calculator'):
                manager.compressor.hash_calculator.clear_cache()
                print("Cache cleared")
```

---

### Issue: Memory Leaks

**Symptoms:**
- Memory usage grows continuously
- Never releases memory
- Eventually crashes

**Diagnostic:**
```python
import objgraph

# Find memory leaks
def find_leaks():
    # Take snapshot
    objgraph.show_growth(limit=10)
    
    # Create many checkpoints
    for i in range(1000):
        checkpoint = manager.create_checkpoint(state)
    
    # Check growth
    print("\nMemory growth after 1000 checkpoints:")
    objgraph.show_growth(limit=10)
    
    # Show what's holding references
    objgraph.show_backrefs(
        objgraph.by_type('IncrementalCheckpoint')[0],
        max_depth=5,
        filename='leak-backrefs.png'
    )
```

**Solutions:**

**Solution 1: Check for Circular References**
```python
# Ensure proper cleanup
class SafeCheckpointManager:
    def __init__(self, *args, **kwargs):
        self.manager = IncrementalCheckpointManager(*args, **kwargs)
        self.checkpoints = []  # Track references
    
    def create_checkpoint(self, state):
        checkpoint = self.manager.create_checkpoint(state)
        
        # Keep only references to recent checkpoints
        self.checkpoints.append(checkpoint)
        if len(self.checkpoints) > 10:
            self.checkpoints.pop(0)  # Remove oldest
        
        return checkpoint
```

**Solution 2: Explicit Cleanup**
```python
# Clear references explicitly
def checkpoint_with_cleanup(manager, state):
    checkpoint = manager.create_checkpoint(state)
    
    # Clear tracker history
    if hasattr(manager, 'tracker'):
        manager.tracker._history.clear()
    
    # Force GC
    gc.collect()
    
    return checkpoint
```

---

## Checkpoint Corruption

### Issue: Cannot Load Checkpoint

**Symptoms:**
- `pickle.UnpicklingError`
- `EOFError: Ran out of input`
- `ValueError: invalid checkpoint format`

**Diagnostic:**
```python
import pickle

def diagnose_checkpoint(checkpoint_path):
    try:
        # Check file exists
        if not os.path.exists(checkpoint_path):
            return "ERROR: File does not exist"
        
        # Check file size
        size = os.path.getsize(checkpoint_path)
        if size == 0:
            return "ERROR: File is empty"
        
        # Try to load
        with open(checkpoint_path, 'rb') as f:
            checkpoint = pickle.load(f)
        
        # Verify structure
        required_attrs = ['checkpoint_id', 'checkpoint_type', 'timestamp']
        missing = [attr for attr in required_attrs if not hasattr(checkpoint, attr)]
        
        if missing:
            return f"ERROR: Missing attributes: {missing}"
        
        return "OK: Checkpoint is valid"
    
    except pickle.UnpicklingError as e:
        return f"ERROR: Pickle corruption: {e}"
    except EOFError:
        return "ERROR: File truncated (incomplete write)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

# Check all checkpoints
for file in os.listdir("./checkpoints"):
    if file.endswith('.pkl'):
        result = diagnose_checkpoint(f"./checkpoints/{file}")
        print(f"{file}: {result}")
```

**Solutions:**

**Solution 1: Restore from Backup**
```python
# If backup exists
def restore_from_backup(manager, corrupt_id):
    # Find previous full checkpoint
    history = manager.get_checkpoint_history()
    
    for checkpoint_id in reversed(history):
        checkpoint = manager.load_checkpoint(checkpoint_id)
        if checkpoint.checkpoint_type == "FULL":
            print(f"Restored from {checkpoint_id}")
            return checkpoint
    
    raise ValueError("No valid full checkpoint found")
```

**Solution 2: Rebuild from Earlier Checkpoint**
```python
# Replay checkpoints from last known good
def rebuild_from_checkpoint(manager, last_good_id):
    # Load last good checkpoint
    state = manager.restore_state(last_good_id)
    
    # Create new checkpoint
    new_checkpoint = manager.create_checkpoint(state)
    
    print(f"Rebuilt from checkpoint {last_good_id}")
    return new_checkpoint
```

**Solution 3: Enable Verification**
```python
# Prevent future corruption
config.verify_checkpoints = True  # Verify after write

# Custom verification
def verify_checkpoint(checkpoint_path):
    try:
        with open(checkpoint_path, 'rb') as f:
            checkpoint = pickle.load(f)
        return True
    except:
        # Delete corrupt checkpoint
        os.remove(checkpoint_path)
        print(f"Deleted corrupt checkpoint: {checkpoint_path}")
        return False
```

---

### Issue: Checkpoints Not Containing Expected Data

**Symptoms:**
- Restored state missing keys
- Values are incorrect
- State is incomplete

**Diagnostic:**
```python
def validate_checkpoint_contents(manager, checkpoint_id, expected_state):
    restored = manager.restore_state(checkpoint_id)
    
    # Check keys
    missing_keys = set(expected_state.keys()) - set(restored.keys())
    extra_keys = set(restored.keys()) - set(expected_state.keys())
    
    # Check values
    mismatched = []
    for key in expected_state:
        if key in restored:
            if expected_state[key] != restored[key]:
                mismatched.append(key)
    
    report = {
        'missing_keys': list(missing_keys),
        'extra_keys': list(extra_keys),
        'mismatched_values': mismatched
    }
    
    return report

# Validate
report = validate_checkpoint_contents(manager, "checkpoint_100", original_state)
if report['missing_keys']:
    print(f"⚠️ Missing keys: {report['missing_keys']}")
if report['mismatched_values']:
    print(f"⚠️ Mismatched values: {report['mismatched_values']}")
```

**Solutions:**

**Solution 1: Force Full Checkpoint**
```python
# Create full checkpoint to ensure all data
def create_full_checkpoint(manager, state):
    # Temporarily force full checkpoint
    old_interval = manager.full_checkpoint_interval
    manager.full_checkpoint_interval = 1
    
    checkpoint = manager.create_checkpoint(state)
    
    # Restore interval
    manager.full_checkpoint_interval = old_interval
    
    return checkpoint
```

**Solution 2: Check State Serialization**
```python
# Some objects may not serialize correctly
def check_serialization(state):
    import pickle
    
    for key, value in state.items():
        try:
            pickle.dumps(value)
        except Exception as e:
            print(f"⚠️ Cannot serialize {key}: {e}")
            print(f"   Type: {type(value)}")
```

---

## Recovery Failures

### Issue: Cannot Restore State

**Symptoms:**
- `restore_state()` raises exception
- Restored state is None
- Application crashes after restoration

**Diagnostic:**
```python
def diagnose_restoration(manager, checkpoint_id):
    try:
        # Try to load checkpoint
        checkpoint = manager.load_checkpoint(checkpoint_id)
        print(f"✓ Checkpoint loaded: {checkpoint.checkpoint_type}")
        
        # Check if incremental
        if checkpoint.checkpoint_type == "INCR":
            # Check base checkpoint exists
            base_id = checkpoint.metadata.get('base_checkpoint_id')
            if base_id:
                try:
                    base = manager.load_checkpoint(base_id)
                    print(f"✓ Base checkpoint exists: {base_id}")
                except:
                    print(f"✗ Base checkpoint missing: {base_id}")
                    return "ERROR: Missing base checkpoint"
        
        # Try to restore
        state = manager.restore_state(checkpoint_id)
        print(f"✓ State restored ({len(state)} keys)")
        
        return "OK"
    
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"

result = diagnose_restoration(manager, "checkpoint_100")
print(result)
```

**Solutions:**

**Solution 1: Restore from Earlier Checkpoint**
```python
# Try earlier checkpoints
def restore_from_any(manager):
    history = manager.get_checkpoint_history()
    
    # Try checkpoints from newest to oldest
    for checkpoint_id in reversed(history):
        try:
            state = manager.restore_state(checkpoint_id)
            print(f"✓ Restored from {checkpoint_id}")
            return state
        except Exception as e:
            print(f"✗ Failed {checkpoint_id}: {e}")
            continue
    
    raise ValueError("No valid checkpoint found")
```

**Solution 2: Restore from Full Checkpoint**
```python
# Skip incremental checkpoints
def restore_from_full(manager):
    history = manager.get_checkpoint_history()
    
    for checkpoint_id in reversed(history):
        checkpoint = manager.load_checkpoint(checkpoint_id)
        if checkpoint.checkpoint_type == "FULL":
            state = manager.restore_state(checkpoint_id)
            print(f"✓ Restored from full checkpoint {checkpoint_id}")
            return state
    
    raise ValueError("No full checkpoint found")
```

**Solution 3: Manual State Reconstruction**
```python
# Manually apply deltas
def manual_restore(manager, target_id):
    # Find base full checkpoint
    base_state = None
    checkpoints_to_apply = []
    
    history = manager.get_checkpoint_history()
    target_index = history.index(target_id)
    
    # Work backwards to find full checkpoint
    for i in range(target_index, -1, -1):
        checkpoint = manager.load_checkpoint(history[i])
        checkpoints_to_apply.insert(0, checkpoint)
        
        if checkpoint.checkpoint_type == "FULL":
            base_state = checkpoint.full_state
            break
    
    if base_state is None:
        raise ValueError("No base full checkpoint found")
    
    # Apply deltas
    current_state = base_state.copy()
    for checkpoint in checkpoints_to_apply[1:]:  # Skip full checkpoint
        if checkpoint.checkpoint_type == "INCR":
            # Apply changes
            for key, value in checkpoint.delta.changed.items():
                current_state[key] = value
            # Remove deleted keys
            for key in checkpoint.delta.removed:
                current_state.pop(key, None)
    
    return current_state
```

---

## Error Code Reference

### Storage Errors

**Error:** `StorageError: Failed to save checkpoint`
- **Cause:** Disk full, permission denied, or storage unavailable
- **Solution:** Check disk space, verify permissions, check storage health

**Error:** `StorageError: Checkpoint file not found`
- **Cause:** Checkpoint was deleted or moved
- **Solution:** Restore from backup or earlier checkpoint

**Error:** `StorageError: Invalid checkpoint format`
- **Cause:** Corrupted file or wrong version
- **Solution:** Delete corrupt checkpoint, restore from backup

### Compression Errors

**Error:** `CompressionError: Failed to compress data`
- **Cause:** Data too large or contains non-serializable objects
- **Solution:** Reduce compression level, check state for problematic objects

**Error:** `CompressionError: Decompression failed`
- **Cause:** Corrupted compressed data
- **Solution:** Restore from uncorrupted checkpoint

### State Tracking Errors

**Error:** `StateTrackingError: Unable to detect changes`
- **Cause:** State contains unhashable types
- **Solution:** Convert unhashable types (lists→tuples, sets→frozensets)

**Error:** `StateTrackingError: Hash calculation failed`
- **Cause:** State contains objects that cannot be hashed
- **Solution:** Implement custom `__hash__` or exclude from checkpointing

### Recovery Errors

**Error:** `RecoveryError: Missing base checkpoint`
- **Cause:** Base full checkpoint was deleted before dependent incremental checkpoint
- **Solution:** Restore from earlier full checkpoint, adjust cleanup policy

**Error:** `RecoveryError: Delta application failed`
- **Cause:** Incompatible state versions or corrupted delta
- **Solution:** Restore from full checkpoint

### Configuration Errors

**Error:** `ConfigError: Invalid configuration`
- **Cause:** Configuration values out of range or incompatible
- **Solution:** Use `ConfigValidator.validate()` before applying

**Error:** `ConfigError: Missing required configuration`
- **Cause:** Required config parameter not provided
- **Solution:** Use `ConfigPresets` or provide missing values

---

## Monitoring and Alerts

### Setting Up Health Monitoring

```python
import time
import logging

class CheckpointHealthMonitor:
    def __init__(self, manager):
        self.manager = manager
        self.logger = logging.getLogger(__name__)
        self.thresholds = {
            'max_create_time_ms': 10.0,
            'max_restore_time_ms': 20.0,
            'min_free_space_gb': 5.0,
            'max_error_rate': 0.05  # 5%
        }
    
    def check_and_alert(self):
        alerts = []
        
        # Check performance
        report = self.manager.get_performance_report()
        if report['checkpoint_creation']['avg_ms'] > self.thresholds['max_create_time_ms']:
            alerts.append({
                'level': 'WARNING',
                'message': f"Slow checkpoint creation: {report['checkpoint_creation']['avg_ms']:.2f}ms"
            })
        
        # Check disk space
        space = check_disk_space(self.manager.storage_path)
        if space['free_gb'] < self.thresholds['min_free_space_gb']:
            alerts.append({
                'level': 'CRITICAL',
                'message': f"Low disk space: {space['free_gb']:.2f}GB"
            })
        
        # Check error rate
        errors = self.manager.get_recent_errors()
        total_ops = self.manager.checkpoint_count
        if total_ops > 0:
            error_rate = len(errors) / total_ops
            if error_rate > self.thresholds['max_error_rate']:
                alerts.append({
                    'level': 'WARNING',
                    'message': f"High error rate: {error_rate:.1%}"
                })
        
        # Log alerts
        for alert in alerts:
            if alert['level'] == 'CRITICAL':
                self.logger.error(alert['message'])
            else:
                self.logger.warning(alert['message'])
        
        return alerts

# Use monitor
monitor = CheckpointHealthMonitor(manager)

# Periodic monitoring
while True:
    alerts = monitor.check_and_alert()
    if alerts:
        print(f"⚠️ {len(alerts)} alerts")
        for alert in alerts:
            print(f"  [{alert['level']}] {alert['message']}")
    
    time.sleep(60)  # Check every minute
```

### Prometheus Metrics Export

```python
from prometheus_client import Gauge, Counter, Histogram

# Define metrics
checkpoint_creation_time = Histogram(
    'checkpoint_creation_seconds',
    'Time to create checkpoint'
)
checkpoint_size_bytes = Gauge(
    'checkpoint_size_bytes',
    'Size of checkpoint in bytes'
)
checkpoint_errors = Counter(
    'checkpoint_errors_total',
    'Total number of checkpoint errors'
)

# Instrument checkpoint operations
def monitored_create_checkpoint(manager, state):
    with checkpoint_creation_time.time():
        try:
            checkpoint = manager.create_checkpoint(state)
            
            # Record size
            size = os.path.getsize(
                f"{manager.storage_path}/checkpoint_{checkpoint.checkpoint_id}.pkl"
            )
            checkpoint_size_bytes.set(size)
            
            return checkpoint
        except Exception as e:
            checkpoint_errors.inc()
            raise
```

### Alerting Rules (Prometheus)

```yaml
# prometheus-alerts.yml
groups:
  - name: checkpoint_alerts
    interval: 30s
    rules:
      - alert: SlowCheckpointCreation
        expr: checkpoint_creation_seconds > 0.010
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Checkpoint creation is slow"
          description: "Checkpoint creation taking >10ms"
      
      - alert: HighCheckpointErrorRate
        expr: rate(checkpoint_errors_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High checkpoint error rate"
          description: "Error rate > 5%"
      
      - alert: LargCheckpointSize
        expr: checkpoint_size_bytes > 10485760  # 10MB
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Checkpoint size is large"
          description: "Checkpoint >10MB"
```

---

## Common Issues Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Slow checkpoints (>10ms) | High compression | Reduce compression level to 1-3 |
| High memory (>500MB) | Large hash cache | Reduce `hash_cache_size` to 1000 |
| Disk full | Too many checkpoints | Set `max_checkpoints=50` |
| Cannot restore | Missing base checkpoint | Restore from full checkpoint |
| Corrupt checkpoint | Write interrupted | Enable `verify_checkpoints=True` |
| High CPU (>20%) | Compression overhead | Set `compression_level=1` |
| State incomplete | Serialization issue | Check for non-serializable objects |
| Memory leak | Circular references | Clear tracker history periodically |

---

## Emergency Procedures

### Complete System Reset

```python
# When everything fails, reset the system
def emergency_reset(manager):
    import shutil
    
    # 1. Stop all operations
    print("Stopping operations...")
    
    # 2. Backup current checkpoints
    backup_dir = f"./checkpoints_backup_{int(time.time())}"
    if os.path.exists(manager.storage_path):
        shutil.copytree(manager.storage_path, backup_dir)
        print(f"Backed up to {backup_dir}")
    
    # 3. Clear checkpoint directory
    if os.path.exists(manager.storage_path):
        shutil.rmtree(manager.storage_path)
        os.makedirs(manager.storage_path)
        print("Cleared checkpoint directory")
    
    # 4. Reinitialize manager
    new_manager = ProductionCheckpointManager(
        manager.storage_path,
        **ConfigPresets.production()
    )
    print("Reinitialized manager")
    
    # 5. Create fresh full checkpoint
    print("Create new full checkpoint from current state")
    
    return new_manager
```

### Data Recovery

```python
# Attempt to recover as much data as possible
def attempt_recovery(checkpoint_dir):
    recovered_states = []
    
    for file in sorted(os.listdir(checkpoint_dir)):
        if file.endswith('.pkl'):
            path = os.path.join(checkpoint_dir, file)
            
            try:
                with open(path, 'rb') as f:
                    checkpoint = pickle.load(f)
                
                if checkpoint.checkpoint_type == "FULL":
                    recovered_states.append({
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'state': checkpoint.full_state,
                        'timestamp': checkpoint.timestamp
                    })
                    print(f"✓ Recovered {file}")
            except Exception as e:
                print(f"✗ Failed {file}: {e}")
    
    if recovered_states:
        # Return most recent recovered state
        latest = max(recovered_states, key=lambda x: x['timestamp'])
        print(f"\nRecovered {len(recovered_states)} states")
        print(f"Latest: {latest['checkpoint_id']} from {latest['timestamp']}")
        return latest['state']
    
    return None
```

---

**Remember:** Always test recovery procedures before production deployment!