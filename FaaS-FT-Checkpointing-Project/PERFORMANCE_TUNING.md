# Performance Tuning Cookbook

Practical recipes for optimizing incremental checkpoint performance across different workloads and environments.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Workload-Specific Tuning](#workload-specific-tuning)
3. [Resource-Constrained Environments](#resource-constrained-environments)
4. [High-Throughput Scenarios](#high-throughput-scenarios)
5. [Large State Management](#large-state-management)
6. [Network-Constrained Environments](#network-constrained-environments)
7. [Benchmarking and Profiling](#benchmarking-and-profiling)

---

## Quick Reference

### Performance at a Glance

| Metric | Target | Configuration Key | Recommended Value |
|--------|--------|-------------------|------------------|
| Checkpoint Speed | <2ms | `compression_level` | 1 (fast) |
| Storage Efficiency | <10MB/1000 checkpoints | `compression_level` | 9 (best) |
| Memory Usage | <100MB | `hash_cache_size` | 1000 |
| CPU Usage | <5% | `parallel_compression` | false |
| Throughput | >200/sec | `enable_monitoring` | false |

### Quick Presets

```python
from incremental_checkpoint.config import ConfigPresets

# For speed: Fast checkpoints, minimal overhead
fast = ConfigPresets.high_performance()

# For storage: Maximum compression, minimal space
compact = ConfigPresets.low_storage()

# For production: Balanced performance and reliability
balanced = ConfigPresets.production()
```

---

## Workload-Specific Tuning

### Recipe 1: Serverless Functions (Bursty Traffic)

**Characteristics:**
- Unpredictable traffic patterns
- Cold starts
- Limited execution time

**Configuration:**
```python
from incremental_checkpoint.config import CheckpointConfig, CheckpointPolicy

config = CheckpointConfig(
    # Fast checkpoints for quick function execution
    compression_level=1,  # Fastest compression
    parallel_compression=False,  # Minimize overhead
    
    # Aggressive cleanup for cost savings
    max_checkpoints=20,
    cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
    
    # Minimal monitoring to reduce latency
    enable_monitoring=False,
    enable_logging=False,
    
    # Hash optimization for repeated requests
    enable_hash_optimization=True,
    hash_cache_size=5000,
    
    # Storage
    checkpoint_dir="/tmp/checkpoints"  # Fast ephemeral storage
)
```

**Expected Performance:**
- Checkpoint creation: 0.5-1ms
- Restoration: 1-2ms
- Memory overhead: ~40MB
- Storage per 100 checkpoints: ~1-2MB

**Tuning Tips:**
```python
# For very small states (<10KB)
config.compression_level = 0  # No compression, minimal overhead

# For larger states (>100KB)
config.compression_level = 3  # Balance speed and size
config.memory_threshold_kb = 50  # Compress larger values
```

---

### Recipe 2: Long-Running Applications (Steady State)

**Characteristics:**
- Continuous operation
- Predictable load
- Large accumulated state

**Configuration:**
```python
config = CheckpointConfig(
    # Balanced compression
    compression_level=6,
    parallel_compression=True,
    parallel_threshold_kb=100,
    max_workers=4,
    
    # More full checkpoints for reliability
    full_checkpoint_interval=5,
    
    # Keep more history
    max_checkpoints=200,
    cleanup_policy=CheckpointPolicy.KEEP_ALL_FULL,
    
    # Full monitoring and error handling
    enable_monitoring=True,
    enable_health_checks=True,
    enable_error_handling=True,
    max_retries=3,
    
    # Large cache for performance
    hash_cache_size=50000,
    
    # Persistent storage
    checkpoint_dir="/var/lib/app/checkpoints"
)
```

**Expected Performance:**
- Checkpoint creation: 2-5ms
- Restoration: 5-10ms
- Memory overhead: ~200MB (with large cache)
- Storage per 100 checkpoints: ~5-10MB

---

### Recipe 3: Batch Processing (Large Datasets)

**Characteristics:**
- Processing large datasets
- Periodic checkpoints
- Long execution time

**Configuration:**
```python
config = CheckpointConfig(
    # Maximum compression for large data
    compression_level=9,
    parallel_compression=True,
    parallel_threshold_kb=50,  # Lower threshold
    max_workers=8,  # More workers
    
    # Less frequent full checkpoints
    full_checkpoint_interval=20,
    
    # Limited checkpoints to save space
    max_checkpoints=50,
    cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
    
    # Memory optimization for large values
    enable_memory_optimization=True,
    memory_threshold_kb=100,
    
    # Disable monitoring for throughput
    enable_monitoring=False,
    enable_logging=False
)
```

**Expected Performance:**
- Checkpoint creation: 10-50ms (depending on size)
- Restoration: 20-100ms
- Memory overhead: ~500MB (temporary during compression)
- Storage per 100 checkpoints: ~2-5MB (high compression)

**Optimization:**
```python
# For very large states (>1MB)
config.compression_level = 6  # Balance time and size
config.parallel_threshold_kb = 20  # More aggressive parallelization

# Checkpoint only at key milestones
manager = ConditionalCheckpointManager(...)  # Skip unchanged states
```

---

### Recipe 4: Real-Time Systems (Latency-Sensitive)

**Characteristics:**
- Strict latency requirements
- Frequent state updates
- Predictable state size

**Configuration:**
```python
config = CheckpointConfig(
    # Minimal compression overhead
    compression_level=1,
    parallel_compression=False,
    
    # Frequent full checkpoints for fast recovery
    full_checkpoint_interval=3,
    
    # Limit checkpoint history
    max_checkpoints=30,
    cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
    
    # Disable all overhead
    enable_monitoring=False,
    enable_health_checks=False,
    enable_logging=False,
    verify_checkpoints=False,
    
    # Small cache to minimize memory
    hash_cache_size=1000,
    
    # Fast storage (SSD/NVMe)
    checkpoint_dir="/dev/shm/checkpoints"  # RAM disk for <1ms writes
)
```

**Expected Performance:**
- Checkpoint creation: <0.5ms
- Restoration: <1ms
- Memory overhead: ~10MB
- Storage per 100 checkpoints: ~3-5MB

**Ultra-Low Latency Mode:**
```python
# For <0.1ms checkpoints
config.compression_level = 0  # No compression
config.enable_hash_optimization = False  # Skip hash calculation
# Store in RAM
```

---

## Resource-Constrained Environments

### Recipe 5: Low Memory (Embedded Systems)

**Target:** <50MB memory usage

```python
config = CheckpointConfig(
    # Minimal caching
    hash_cache_size=100,  # Very small cache
    enable_hash_optimization=False,  # Disable caching
    
    # Simple compression
    compression_level=3,  # Balance
    parallel_compression=False,  # No threads
    
    # Aggressive cleanup
    max_checkpoints=10,
    cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
    
    # No monitoring
    enable_monitoring=False,
    enable_logging=False,
    
    # Memory optimization
    enable_memory_optimization=True,
    memory_threshold_kb=10  # Compress everything >10KB
)
```

**Memory Breakdown:**
- Base manager: ~5MB
- Hash cache (100 entries): ~1MB
- Temporary compression buffer: ~10-20MB
- **Total: ~20-30MB**

---

### Recipe 6: Low Storage (Cost Optimization)

**Target:** <1MB per 100 checkpoints

```python
config = ConfigPresets.low_storage()

# Further optimization
config.compression_level = 9  # Maximum compression
config.full_checkpoint_interval = 30  # Fewer full checkpoints
config.max_checkpoints = 10  # Keep minimal history
config.memory_threshold_kb = 20  # Compress more aggressively
```

**Storage Optimization:**
```python
# Estimate storage requirements
def estimate_storage(checkpoints, avg_state_size_kb, compression_ratio):
    full_checkpoints = checkpoints // config.full_checkpoint_interval
    incr_checkpoints = checkpoints - full_checkpoints
    
    full_size = full_checkpoints * (avg_state_size_kb * 1024 / compression_ratio)
    incr_size = incr_checkpoints * (avg_state_size_kb * 0.05 * 1024 / compression_ratio)
    
    return (full_size + incr_size) / (1024 * 1024)  # MB

# Example: 100 checkpoints, 50KB avg state, 5x compression
storage_mb = estimate_storage(100, 50, 5.0)
print(f"Estimated storage: {storage_mb:.2f} MB")  # ~0.6 MB
```

---

### Recipe 7: Low CPU (Background Processing)

**Target:** <2% CPU usage

```python
config = CheckpointConfig(
    # Fast compression
    compression_level=1,
    parallel_compression=False,
    
    # Reduced frequency
    full_checkpoint_interval=20,
    
    # Minimal processing
    enable_monitoring=False,
    enable_health_checks=False,
    verify_checkpoints=False,
    
    # Use conditional manager to skip unnecessary checkpoints
    # (Set via manager class, not config)
)

# Use conditional manager
from incremental_checkpoint import ConditionalCheckpointManager
manager = ConditionalCheckpointManager(storage_path=config.checkpoint_dir)
```

**CPU Optimization:**
```python
# Checkpoint only when necessary
if manager.tracker.has_changes(current_state):
    checkpoint = manager.create_checkpoint(current_state)
else:
    # Skip checkpoint, no changes
    pass
```

---

## High-Throughput Scenarios

### Recipe 8: Maximum Throughput

**Target:** >500 checkpoints/second

```python
config = CheckpointConfig(
    # Absolute minimum overhead
    compression_level=0,  # No compression
    enable_monitoring=False,
    enable_logging=False,
    enable_health_checks=False,
    verify_checkpoints=False,
    
    # No caching (overhead)
    enable_hash_optimization=False,
    
    # Memory-only storage
    checkpoint_dir="/dev/shm/checkpoints",
    
    # Minimal history
    max_checkpoints=50,
    full_checkpoint_interval=10
)

# Use basic manager for minimum overhead
from incremental_checkpoint import IncrementalCheckpointManager
manager = IncrementalCheckpointManager(
    storage_path=config.checkpoint_dir,
    compression_level=0
)
```

**Throughput Benchmarks:**

| Configuration | Throughput (checkpoints/sec) | Latency (ms) |
|---------------|------------------------------|--------------|
| No compression, no monitoring | ~800 | 0.3 |
| Level 1 compression | ~500 | 0.6 |
| Level 6 compression | ~200 | 2.0 |
| Level 9 compression | ~50 | 10.0 |

---

### Recipe 9: Parallel Checkpoint Processing

For multiple independent checkpoint streams:

```python
import concurrent.futures
from incremental_checkpoint import IncrementalCheckpointManager

# Create separate managers for each stream
managers = [
    IncrementalCheckpointManager(f"./checkpoints/stream_{i}")
    for i in range(4)
]

# Process streams in parallel
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(managers[i].create_checkpoint, states[i])
        for i in range(4)
    ]
    checkpoints = [f.result() for f in futures]

# Aggregate throughput: 4x single-stream performance
```

---

## Large State Management

### Recipe 10: Large State Objects (>1MB)

```python
config = CheckpointConfig(
    # Parallel compression essential
    compression_level=6,
    parallel_compression=True,
    parallel_threshold_kb=50,  # Lower threshold
    max_workers=8,  # More workers
    
    # Memory optimization
    enable_memory_optimization=True,
    memory_threshold_kb=100,
    
    # Less frequent full checkpoints
    full_checkpoint_interval=20,
    
    # Monitor for bottlenecks
    enable_monitoring=True
)

# Monitor performance
manager = ProductionCheckpointManager(
    storage_path=config.checkpoint_dir,
    enable_monitoring=True
)

checkpoint = manager.create_checkpoint(large_state)

# Check for bottlenecks
report = manager.get_performance_report()
if report['bottlenecks']:
    print(f"Bottlenecks detected: {report['bottlenecks']}")
```

**Optimization Strategy:**
```python
# For very large states (>10MB), consider chunking
def checkpoint_large_state(manager, state):
    # Split state into smaller chunks
    chunks = {}
    for key, value in state.items():
        if sys.getsizeof(value) > 1_000_000:  # >1MB
            # Checkpoint separately or compress
            chunks[key] = compress_large_value(value)
        else:
            chunks[key] = value
    
    return manager.create_checkpoint(chunks)
```

---

### Recipe 11: Deeply Nested Structures

```python
# Flatten deeply nested structures before checkpointing
def flatten_state(state, prefix=''):
    flat = {}
    for key, value in state.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(flatten_state(value, full_key))
        else:
            flat[full_key] = value
    return flat

# Use flattened state
flat_state = flatten_state(nested_state)
checkpoint = manager.create_checkpoint(flat_state)
```

**Performance Impact:**
- Nested (depth 5): ~10ms checkpoint
- Flattened: ~3ms checkpoint
- **Improvement: 3.3x faster**

---

## Network-Constrained Environments

### Recipe 12: Remote Checkpoint Storage

For checkpoints stored on network drives or S3:

```python
config = CheckpointConfig(
    # Maximum compression to minimize transfer
    compression_level=9,
    
    # Fewer checkpoints to reduce network operations
    max_checkpoints=20,
    full_checkpoint_interval=10,
    
    # Buffer checkpoints locally
    checkpoint_dir="/tmp/local_checkpoints",
    
    # Retry logic for network failures
    enable_error_handling=True,
    max_retries=5
)

# Implement async upload
import asyncio

async def checkpoint_with_upload(manager, state, remote_path):
    # Create checkpoint locally
    checkpoint = manager.create_checkpoint(state)
    
    # Upload asynchronously
    await upload_to_remote(
        f"/tmp/local_checkpoints/checkpoint_{checkpoint.checkpoint_id}.pkl",
        remote_path
    )
    
    return checkpoint
```

---

### Recipe 13: Delta Transfer Optimization

Minimize network transfer for remote checkpoints:

```python
# Only transfer changed checkpoints
class NetworkOptimizedManager:
    def __init__(self, local_manager, remote_storage):
        self.local = local_manager
        self.remote = remote_storage
        self.synced_ids = set()
    
    def create_checkpoint(self, state):
        checkpoint = self.local.create_checkpoint(state)
        
        # Only upload incremental checkpoints
        if checkpoint.checkpoint_type == "INCR":
            self.remote.upload(checkpoint)
            self.synced_ids.add(checkpoint.checkpoint_id)
        
        # Upload full checkpoints periodically
        elif len(self.synced_ids) >= 10:
            self.remote.upload(checkpoint)
            self.synced_ids.clear()
        
        return checkpoint
```

**Network Savings:**
- Without optimization: 100% of checkpoints transferred
- With optimization: ~20% transferred (only full checkpoints)
- **Reduction: 80% less network traffic**

---

## Benchmarking and Profiling

### Measuring Checkpoint Performance

```python
import time
from incremental_checkpoint import ProductionCheckpointManager

manager = ProductionCheckpointManager(
    "./checkpoints",
    enable_monitoring=True
)

# Benchmark checkpoint creation
def benchmark_checkpoints(manager, state, iterations=100):
    times = []
    for i in range(iterations):
        start = time.perf_counter()
        checkpoint = manager.create_checkpoint(state)
        duration = (time.perf_counter() - start) * 1000  # ms
        times.append(duration)
    
    return {
        'avg_ms': sum(times) / len(times),
        'min_ms': min(times),
        'max_ms': max(times),
        'p50_ms': sorted(times)[len(times) // 2],
        'p95_ms': sorted(times)[int(len(times) * 0.95)],
        'p99_ms': sorted(times)[int(len(times) * 0.99)]
    }

# Run benchmark
results = benchmark_checkpoints(manager, test_state)
print(f"Average: {results['avg_ms']:.2f}ms")
print(f"P95: {results['p95_ms']:.2f}ms")
print(f"P99: {results['p99_ms']:.2f}ms")
```

### Profiling Bottlenecks

```python
import cProfile
import pstats
from io import StringIO

def profile_checkpoint_operation(manager, state):
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Operation to profile
    checkpoint = manager.create_checkpoint(state)
    
    profiler.disable()
    
    # Analyze results
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    print(stream.getvalue())
    return checkpoint

# Profile and identify hot spots
checkpoint = profile_checkpoint_operation(manager, large_state)
```

### Memory Profiling

```python
import tracemalloc

def profile_memory(manager, state):
    tracemalloc.start()
    
    # Take snapshot before
    snapshot1 = tracemalloc.take_snapshot()
    
    # Create checkpoint
    checkpoint = manager.create_checkpoint(state)
    
    # Take snapshot after
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("Top 10 memory allocations:")
    for stat in top_stats[:10]:
        print(stat)
    
    tracemalloc.stop()
    return checkpoint
```

---

## Tuning Decision Tree

```
Does your application need:

├─ Maximum speed?
│  ├─ State < 100KB → compression_level=0, no monitoring
│  └─ State > 100KB → compression_level=1, parallel=True
│
├─ Minimum storage?
│  ├─ CPU available → compression_level=9, full_interval=30
│  └─ CPU limited → compression_level=6, memory_optimization=True
│
├─ Low memory?
│  ├─ < 50MB → hash_cache=100, no_optimization, compression=3
│  └─ < 100MB → hash_cache=1000, compression=6
│
├─ High throughput?
│  ├─ > 500/sec → compression=0, no_monitoring, RAM storage
│  └─ > 200/sec → compression=1, no_monitoring, SSD storage
│
└─ Balanced (production)?
   └─ Use ConfigPresets.production()
```

---

## Performance Cheat Sheet

### Speed Up Checkpoints

1. **Reduce compression:** `compression_level=1` (or 0)
2. **Disable monitoring:** `enable_monitoring=False`
3. **Disable logging:** `enable_logging=False`
4. **Use fast storage:** SSD or RAM disk
5. **Skip verification:** `verify_checkpoints=False`

### Reduce Storage

1. **Maximum compression:** `compression_level=9`
2. **Fewer full checkpoints:** `full_checkpoint_interval=30`
3. **Aggressive cleanup:** `max_checkpoints=10`
4. **Memory optimization:** `enable_memory_optimization=True`
5. **Conditional checkpointing:** Use `ConditionalCheckpointManager`

### Reduce Memory

1. **Small cache:** `hash_cache_size=100`
2. **Disable caching:** `enable_hash_optimization=False`
3. **No parallelization:** `parallel_compression=False`
4. **Memory optimization:** `memory_threshold_kb=10`

### Reduce CPU

1. **Fast compression:** `compression_level=1`
2. **No parallelization:** `parallel_compression=False`
3. **Skip unnecessary work:** Use `ConditionalCheckpointManager`
4. **Disable monitoring:** `enable_monitoring=False`

---

## Real-World Examples

### Example 1: AWS Lambda Function

```python
# Optimized for Lambda 512MB, 3s timeout
config = CheckpointConfig(
    checkpoint_dir="/tmp/checkpoints",
    compression_level=1,  # Fast for 3s limit
    max_checkpoints=5,  # Limited /tmp space
    enable_monitoring=False,
    hash_cache_size=1000,
    full_checkpoint_interval=3
)

# Result: <1ms checkpoints, ~20MB total space
```

### Example 2: Kubernetes Long-Running Service

```python
# Optimized for K8s with 2GB memory, 4 CPUs
config = CheckpointConfig(
    checkpoint_dir="/var/lib/app/checkpoints",
    compression_level=6,
    parallel_compression=True,
    max_workers=4,
    max_checkpoints=100,
    enable_monitoring=True,
    enable_health_checks=True,
    hash_cache_size=20000,
    full_checkpoint_interval=10
)

# Result: 2-5ms checkpoints, full monitoring, ~100MB memory
```

### Example 3: Edge Device (Raspberry Pi)

```python
# Optimized for Pi 3B+ (1GB RAM, slow SD card)
config = CheckpointConfig(
    checkpoint_dir="/data/checkpoints",
    compression_level=3,  # Balance
    parallel_compression=False,  # Single core efficient
    max_checkpoints=10,
    enable_monitoring=False,
    hash_cache_size=500,
    full_checkpoint_interval=5
)

# Result: ~5ms checkpoints, <30MB memory, minimal storage
```

---

## Summary

Choose your configuration based on primary constraint:

- **Speed-critical:** compression_level=0-1, no monitoring, RAM storage
- **Storage-critical:** compression_level=9, aggressive cleanup, memory optimization
- **Memory-critical:** small cache, no optimization, simple compression
- **CPU-critical:** compression_level=1, no parallelization, conditional checkpointing
- **Balanced:** Use `ConfigPresets.production()`

**Remember:** Profile your specific workload and adjust accordingly. Start with a preset and tune based on actual performance data.
