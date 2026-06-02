"""
Performance Optimizations Module
Provides optimized implementations for hash calculation and caching
"""

import hashlib
from typing import Any, Dict, Optional
import pickle


class OptimizedHashCalculator:
    """
    Optimized hash calculator with caching and faster algorithms.
    
    Uses xxhash when available (3-5x faster than MD5), falls back to MD5.
    Implements intelligent caching to reduce redundant calculations.
    """
    
    def __init__(self, use_xxhash: bool = True, cache_size_limit: int = 10000):
        """
        Initialize optimized hash calculator.
        
        Args:
            use_xxhash: Try to use xxhash for better performance
            cache_size_limit: Maximum number of cached hashes (prevents memory bloat)
        """
        self.cache_size_limit = cache_size_limit
        self.hash_cache: Dict[int, str] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Try to import xxhash for better performance
        self.use_xxhash = use_xxhash
        self.xxhash_available = False
        
        if use_xxhash:
            try:
                import xxhash
                self.xxhash = xxhash
                self.xxhash_available = True
            except ImportError:
                pass
    
    def calculate_hash(self, value: Any, use_cache: bool = True) -> str:
        """
        Calculate hash of value with optional caching.
        
        Args:
            value: Value to hash
            use_cache: Whether to use cache (disable for frequently changing values)
            
        Returns:
            Hash string
        """
        # Generate cache key from object id
        cache_key = id(value)
        
        # Check cache first
        if use_cache and cache_key in self.hash_cache:
            self.cache_hits += 1
            return self.hash_cache[cache_key]
        
        self.cache_misses += 1
        
        # Serialize value
        try:
            serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            # Fallback for unpicklable objects
            serialized = str(value).encode('utf-8')
        
        # Calculate hash
        if self.xxhash_available:
            # xxhash is 3-5x faster than MD5
            hash_value = self.xxhash.xxh64(serialized).hexdigest()
        else:
            # Fallback to MD5
            hash_value = hashlib.md5(serialized).hexdigest()
        
        # Cache if enabled and within limits
        if use_cache and len(self.hash_cache) < self.cache_size_limit:
            self.hash_cache[cache_key] = hash_value
        
        return hash_value
    
    def clear_cache(self):
        """Clear hash cache to free memory."""
        self.hash_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / max(1, total_requests)) * 100
        
        return {
            'cache_size': len(self.hash_cache),
            'cache_limit': self.cache_size_limit,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': hit_rate,
            'xxhash_enabled': self.xxhash_available
        }
    
    def optimize_cache(self):
        """
        Optimize cache by removing least recently used entries if over limit.
        
        This is a simple optimization - in production, consider LRU cache.
        """
        if len(self.hash_cache) > self.cache_size_limit:
            # Remove oldest 20% of entries
            remove_count = len(self.hash_cache) - int(self.cache_size_limit * 0.8)
            keys_to_remove = list(self.hash_cache.keys())[:remove_count]
            for key in keys_to_remove:
                del self.hash_cache[key]


class MemoryOptimizer:
    """
    Memory optimization utilities for checkpoint management.
    
    Provides tools to reduce memory footprint and prevent memory leaks.
    """
    
    @staticmethod
    def estimate_memory_usage(obj: Any) -> int:
        """
        Estimate memory usage of an object in bytes.
        
        Args:
            obj: Object to analyze
            
        Returns:
            Estimated memory usage in bytes
        """
        try:
            serialized = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
            return len(serialized)
        except Exception:
            # Fallback estimation
            return len(str(obj).encode('utf-8'))
    
    @staticmethod
    def compress_state(state: dict, threshold_bytes: int = 1024) -> dict:
        """
        Compress large values in state to reduce memory.
        
        Args:
            state: State dictionary
            threshold_bytes: Only compress values larger than this
            
        Returns:
            State with large values compressed
        """
        import zlib
        
        compressed_state = {}
        
        for key, value in state.items():
            value_size = MemoryOptimizer.estimate_memory_usage(value)
            
            if value_size > threshold_bytes:
                # Compress large values
                try:
                    serialized = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                    compressed = zlib.compress(serialized, level=6)
                    
                    # Only use compression if it actually reduces size
                    if len(compressed) < len(serialized):
                        compressed_state[key] = {
                            '__compressed__': True,
                            'data': compressed
                        }
                    else:
                        compressed_state[key] = value
                except Exception:
                    compressed_state[key] = value
            else:
                compressed_state[key] = value
        
        return compressed_state
    
    @staticmethod
    def decompress_state(state: dict) -> dict:
        """
        Decompress state that was compressed by compress_state.
        
        Args:
            state: Potentially compressed state
            
        Returns:
            Decompressed state
        """
        import zlib
        
        decompressed_state = {}
        
        for key, value in state.items():
            if isinstance(value, dict) and value.get('__compressed__'):
                # Decompress
                try:
                    compressed = value['data']
                    serialized = zlib.decompress(compressed)
                    decompressed_state[key] = pickle.loads(serialized)
                except Exception:
                    decompressed_state[key] = value
            else:
                decompressed_state[key] = value
        
        return decompressed_state


class PerformanceMonitor:
    """
    Monitor performance metrics for optimization.
    
    Tracks timing, memory usage, and identifies bottlenecks.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, list] = {
            'checkpoint_times': [],
            'restoration_times': [],
            'compression_times': [],
            'hash_calculation_times': []
        }
    
    def record_checkpoint_time(self, time_ms: float):
        """Record checkpoint creation time."""
        self.metrics['checkpoint_times'].append(time_ms)
    
    def record_restoration_time(self, time_ms: float):
        """Record restoration time."""
        self.metrics['restoration_times'].append(time_ms)
    
    def record_compression_time(self, time_ms: float):
        """Record compression time."""
        self.metrics['compression_times'].append(time_ms)
    
    def record_hash_calculation_time(self, time_ms: float):
        """Record hash calculation time."""
        self.metrics['hash_calculation_times'].append(time_ms)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        stats = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                stats[metric_name] = {
                    'count': len(values),
                    'avg_ms': sum(values) / len(values),
                    'min_ms': min(values),
                    'max_ms': max(values),
                    'total_ms': sum(values)
                }
            else:
                stats[metric_name] = {
                    'count': 0,
                    'avg_ms': 0.0,
                    'min_ms': 0.0,
                    'max_ms': 0.0,
                    'total_ms': 0.0
                }
        
        return stats
    
    def identify_bottlenecks(self) -> Dict[str, str]:
        """
        Identify performance bottlenecks.
        
        Returns:
            Dictionary describing bottlenecks and recommendations
        """
        stats = self.get_statistics()
        bottlenecks = {}
        
        # Check checkpoint times
        checkpoint_avg = stats['checkpoint_times']['avg_ms']
        if checkpoint_avg > 50:
            bottlenecks['checkpoint_creation'] = (
                f"Average checkpoint time ({checkpoint_avg:.2f}ms) is high. "
                "Consider enabling xxhash or reducing checkpoint frequency."
            )
        
        # Check restoration times
        restoration_avg = stats['restoration_times']['avg_ms']
        if restoration_avg > 100:
            bottlenecks['restoration'] = (
                f"Average restoration time ({restoration_avg:.2f}ms) is high. "
                "Consider reducing chain length with more frequent full checkpoints."
            )
        
        # Check compression times
        compression_avg = stats['compression_times']['avg_ms']
        if compression_avg > 20:
            bottlenecks['compression'] = (
                f"Average compression time ({compression_avg:.2f}ms) is high. "
                "Consider lowering compression level or using parallel compression."
            )
        
        if not bottlenecks:
            bottlenecks['status'] = "No significant bottlenecks detected. Performance is optimal."
        
        return bottlenecks
    
    def reset(self):
        """Reset all metrics."""
        for metric_name in self.metrics:
            self.metrics[metric_name].clear()


# Convenience function to check if xxhash is available
def is_xxhash_available() -> bool:
    """
    Check if xxhash library is available.
    
    Returns:
        True if xxhash can be imported
    """
    try:
        import xxhash
        return True
    except ImportError:
        return False


# Convenience function to install xxhash
def get_xxhash_install_command() -> str:
    """
    Get command to install xxhash.
    
    Returns:
        pip install command
    """
    return "pip install xxhash"
