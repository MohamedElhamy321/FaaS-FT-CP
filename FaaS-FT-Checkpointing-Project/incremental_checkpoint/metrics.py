"""
Prometheus Metrics Exporter for Incremental Checkpoint System

Exposes checkpoint metrics in Prometheus format for monitoring and alerting.
"""

from prometheus_client import Counter, Gauge, Histogram, Summary, Info, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry
import time
from typing import Dict, Any, Optional
from functools import wraps
import threading


class CheckpointMetricsExporter:
    """
    Exports checkpoint system metrics in Prometheus format.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics exporter.
        
        Args:
            registry: Prometheus registry (uses default if None)
        """
        self.registry = registry or REGISTRY
        
        # Checkpoint creation metrics
        self.checkpoint_creation_total = Counter(
            'checkpoint_creation_total',
            'Total number of checkpoints created',
            ['checkpoint_type', 'status'],
            registry=self.registry
        )
        
        self.checkpoint_creation_duration = Histogram(
            'checkpoint_creation_duration_seconds',
            'Time to create checkpoint',
            ['checkpoint_type'],
            buckets=(0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        # Checkpoint restoration metrics
        self.checkpoint_restoration_total = Counter(
            'checkpoint_restoration_total',
            'Total number of checkpoint restorations',
            ['status'],
            registry=self.registry
        )
        
        self.checkpoint_restoration_duration = Histogram(
            'checkpoint_restoration_duration_seconds',
            'Time to restore from checkpoint',
            buckets=(0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry
        )
        
        # Storage metrics
        self.checkpoint_size_bytes = Histogram(
            'checkpoint_size_bytes',
            'Size of checkpoint in bytes',
            ['checkpoint_type'],
            buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600),
            registry=self.registry
        )
        
        self.total_storage_used_bytes = Gauge(
            'checkpoint_storage_used_bytes',
            'Total storage used by checkpoints',
            registry=self.registry
        )
        
        self.checkpoint_count = Gauge(
            'checkpoint_count',
            'Current number of checkpoints',
            ['checkpoint_type'],
            registry=self.registry
        )
        
        # Compression metrics
        self.compression_ratio = Histogram(
            'checkpoint_compression_ratio',
            'Compression ratio achieved',
            buckets=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0),
            registry=self.registry
        )
        
        self.compression_duration = Histogram(
            'checkpoint_compression_duration_seconds',
            'Time spent compressing',
            buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5),
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'checkpoint_cache_hits_total',
            'Total number of cache hits',
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'checkpoint_cache_misses_total',
            'Total number of cache misses',
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'checkpoint_cache_size',
            'Current cache size',
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'checkpoint_errors_total',
            'Total number of errors',
            ['error_type', 'operation'],
            registry=self.registry
        )
        
        # Performance metrics
        self.state_changes_detected = Counter(
            'checkpoint_state_changes_detected_total',
            'Total number of state changes detected',
            registry=self.registry
        )
        
        self.hash_calculation_duration = Histogram(
            'checkpoint_hash_calculation_duration_seconds',
            'Time spent calculating hashes',
            buckets=(0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005, 0.01),
            registry=self.registry
        )
        
        # Health metrics
        self.health_status = Gauge(
            'checkpoint_health_status',
            'Health status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )
        
        self.last_checkpoint_timestamp = Gauge(
            'checkpoint_last_created_timestamp_seconds',
            'Timestamp of last checkpoint creation',
            registry=self.registry
        )
        
        # System info
        self.system_info = Info(
            'checkpoint_system',
            'Checkpoint system information',
            registry=self.registry
        )
        
        # Initialize system info
        self.system_info.info({
            'version': '1.3.0',
            'features': 'incremental,compression,optimization,production'
        })
        
        # Set initial health to healthy
        self.health_status.set(1)
    
    def record_checkpoint_creation(self, checkpoint_type: str, duration: float, 
                                   size_bytes: int, success: bool = True):
        """Record checkpoint creation metrics."""
        status = 'success' if success else 'failure'
        self.checkpoint_creation_total.labels(
            checkpoint_type=checkpoint_type,
            status=status
        ).inc()
        
        if success:
            self.checkpoint_creation_duration.labels(
                checkpoint_type=checkpoint_type
            ).observe(duration)
            
            self.checkpoint_size_bytes.labels(
                checkpoint_type=checkpoint_type
            ).observe(size_bytes)
            
            self.last_checkpoint_timestamp.set(time.time())
    
    def record_checkpoint_restoration(self, duration: float, success: bool = True):
        """Record checkpoint restoration metrics."""
        status = 'success' if success else 'failure'
        self.checkpoint_restoration_total.labels(status=status).inc()
        
        if success:
            self.checkpoint_restoration_duration.observe(duration)
    
    def record_compression(self, duration: float, original_size: int, compressed_size: int):
        """Record compression metrics."""
        self.compression_duration.observe(duration)
        
        if original_size > 0:
            ratio = original_size / compressed_size
            self.compression_ratio.observe(ratio)
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.cache_hits_total.inc()
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.cache_misses_total.inc()
    
    def update_cache_size(self, size: int):
        """Update cache size gauge."""
        self.cache_size.set(size)
    
    def record_error(self, error_type: str, operation: str):
        """Record error."""
        self.errors_total.labels(
            error_type=error_type,
            operation=operation
        ).inc()
    
    def record_state_change(self):
        """Record state change detection."""
        self.state_changes_detected.inc()
    
    def record_hash_calculation(self, duration: float):
        """Record hash calculation time."""
        self.hash_calculation_duration.observe(duration)
    
    def update_storage_metrics(self, total_bytes: int, full_count: int, incr_count: int):
        """Update storage metrics."""
        self.total_storage_used_bytes.set(total_bytes)
        self.checkpoint_count.labels(checkpoint_type='FULL').set(full_count)
        self.checkpoint_count.labels(checkpoint_type='INCR').set(incr_count)
    
    def update_health_status(self, is_healthy: bool):
        """Update health status."""
        self.health_status.set(1 if is_healthy else 0)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)


class MetricsDecorator:
    """
    Decorator for automatic metrics collection.
    """
    
    def __init__(self, exporter: CheckpointMetricsExporter):
        self.exporter = exporter
    
    def track_creation(self, checkpoint_type: str):
        """Decorator to track checkpoint creation."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                success = False
                size_bytes = 0
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    
                    # Try to get size from result
                    if hasattr(result, 'metadata'):
                        size_bytes = result.metadata.get('size_bytes', 0)
                    
                    return result
                except Exception as e:
                    self.exporter.record_error(
                        error_type=type(e).__name__,
                        operation='checkpoint_creation'
                    )
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    self.exporter.record_checkpoint_creation(
                        checkpoint_type=checkpoint_type,
                        duration=duration,
                        size_bytes=size_bytes,
                        success=success
                    )
            
            return wrapper
        return decorator
    
    def track_restoration(self):
        """Decorator to track checkpoint restoration."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                success = False
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                except Exception as e:
                    self.exporter.record_error(
                        error_type=type(e).__name__,
                        operation='checkpoint_restoration'
                    )
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    self.exporter.record_checkpoint_restoration(
                        duration=duration,
                        success=success
                    )
            
            return wrapper
        return decorator
    
    def track_compression(self):
        """Decorator to track compression."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Try to extract sizes from args/result
                    original_size = 0
                    compressed_size = 0
                    
                    if len(args) > 0:
                        import sys
                        original_size = sys.getsizeof(args[0])
                    
                    if isinstance(result, bytes):
                        compressed_size = len(result)
                    
                    duration = time.perf_counter() - start_time
                    
                    if original_size > 0 and compressed_size > 0:
                        self.exporter.record_compression(
                            duration=duration,
                            original_size=original_size,
                            compressed_size=compressed_size
                        )
                    
                    return result
                except Exception as e:
                    self.exporter.record_error(
                        error_type=type(e).__name__,
                        operation='compression'
                    )
                    raise
            
            return wrapper
        return decorator


# Global exporter instance
_global_exporter = None
_exporter_lock = threading.Lock()


def get_global_exporter() -> CheckpointMetricsExporter:
    """Get or create global metrics exporter."""
    global _global_exporter
    
    with _exporter_lock:
        if _global_exporter is None:
            _global_exporter = CheckpointMetricsExporter()
        return _global_exporter


def export_metrics() -> bytes:
    """Export metrics in Prometheus format."""
    exporter = get_global_exporter()
    return exporter.get_metrics()


# Example usage with Flask
def create_metrics_endpoint(app, path: str = '/metrics'):
    """
    Create Prometheus metrics endpoint in Flask app.
    
    Args:
        app: Flask application
        path: Endpoint path (default: /metrics)
    """
    @app.route(path)
    def metrics():
        from flask import Response
        return Response(export_metrics(), mimetype='text/plain')


# Example usage with FastAPI
def create_fastapi_metrics_endpoint(app, path: str = '/metrics'):
    """
    Create Prometheus metrics endpoint in FastAPI app.
    
    Args:
        app: FastAPI application
        path: Endpoint path (default: /metrics)
    """
    from fastapi import Response
    
    @app.get(path)
    async def metrics():
        return Response(
            content=export_metrics(),
            media_type='text/plain'
        )


if __name__ == "__main__":
    # Example: Export metrics
    exporter = CheckpointMetricsExporter()
    
    # Simulate some metrics
    exporter.record_checkpoint_creation('FULL', 0.005, 102400, True)
    exporter.record_checkpoint_creation('INCR', 0.002, 1024, True)
    exporter.record_compression(0.001, 102400, 20480)
    exporter.record_cache_hit()
    exporter.update_storage_metrics(1048576, 10, 90)
    
    # Print metrics
    print(exporter.get_metrics().decode('utf-8'))
