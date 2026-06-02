"""
Enhanced Production-Ready Checkpoint Manager
Combines all optimizations and production features
"""

import time
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from incremental_checkpoint.manager import IncrementalCheckpointManager
from incremental_checkpoint.optimizations import (
    OptimizedHashCalculator,
    PerformanceMonitor,
    MemoryOptimizer
)
from incremental_checkpoint.production import (
    ErrorHandler,
    ProductionLogger,
    HealthChecker,
    BackwardCompatibility
)
from incremental_checkpoint.storage import IncrementalCheckpoint
from incremental_checkpoint.predictive_scheduler import (
    PredictiveCheckpointManager,
    SchedulingStrategy
)
from incremental_checkpoint.distributed_coordinator import (
    DistributedCheckpointCoordinator,
    RaftNode,
    DistributedLockManager
)


class ProductionCheckpointManager(IncrementalCheckpointManager):
    """
    Production-ready checkpoint manager with all optimizations enabled.
    
    Features:
    - Optimized hash calculation (xxhash when available)
    - Comprehensive error handling with retries
    - Performance monitoring and bottleneck detection
    - Backward compatibility with legacy checkpoints
    - Health checking and diagnostics
    - Structured logging
    """
    
    def __init__(
        self,
        storage_path: str,
        full_checkpoint_interval: int = 10,
        enable_optimizations: bool = True,
        enable_monitoring: bool = True,
        max_retries: int = 3,
        enable_predictive_scheduling: bool = False,
        scheduling_strategy: SchedulingStrategy = SchedulingStrategy.HYBRID,
        base_checkpoint_interval: float = 300.0,
        enable_distributed_coordination: bool = False,
        node_id: Optional[str] = None,
        cluster_nodes: Optional[List[Tuple[str, str, int]]] = None
    ):
        """
        Initialize production checkpoint manager.
        
        Args:
            storage_path: Path to store checkpoints
            full_checkpoint_interval: Create full checkpoint every N checkpoints
            enable_optimizations: Enable performance optimizations
            enable_monitoring: Enable performance monitoring
            max_retries: Maximum retry attempts for operations
            enable_predictive_scheduling: Enable predictive checkpoint scheduling
            scheduling_strategy: Strategy for predictive scheduling
            base_checkpoint_interval: Base interval in seconds for predictive scheduling
            enable_distributed_coordination: Enable distributed checkpoint coordination
            node_id: Unique node ID for distributed coordination
            cluster_nodes: List of (node_id, host, port) for cluster nodes
        """
        super().__init__(storage_path, full_checkpoint_interval)
        
        # Initialize optimization components
        self.enable_optimizations = enable_optimizations
        if enable_optimizations:
            self.hash_calculator = OptimizedHashCalculator(use_xxhash=True)
        
        # Initialize production components
        self.error_handler = ErrorHandler(max_retries=max_retries)
        self.logger = ProductionLogger()
        self.health_checker = HealthChecker()
        
        # Initialize monitoring
        self.enable_monitoring = enable_monitoring
        if enable_monitoring:
            self.performance_monitor = PerformanceMonitor()
        
        # Initialize predictive scheduling
        self.enable_predictive_scheduling = enable_predictive_scheduling
        self.predictive_scheduler = None
        if enable_predictive_scheduling:
            self.predictive_scheduler = PredictiveCheckpointManager(
                base_interval=base_checkpoint_interval,
                strategy=scheduling_strategy,
                enable_prediction=True
            )
            # Start background monitoring
            self.predictive_scheduler.start_monitoring(interval=5.0)
            self.logger.logger.info(
                f"Predictive scheduling enabled with {scheduling_strategy.value} strategy"
            )
        
        # Initialize distributed coordination
        self.enable_distributed_coordination = enable_distributed_coordination
        self.distributed_coordinator = None
        if enable_distributed_coordination:
            if not node_id or not cluster_nodes:
                raise ValueError("node_id and cluster_nodes required for distributed coordination")
            self.distributed_coordinator = DistributedCheckpointCoordinator(
                node_id,
                cluster_nodes,
                self
            )
            self.distributed_coordinator.start()
            self.logger.logger.info(
                f"Distributed coordination enabled: node_id={node_id}, cluster_size={len(cluster_nodes)}"
            )
        
        # Backward compatibility handler
        self.compatibility = BackwardCompatibility()
    
    def should_checkpoint(self, force: bool = False) -> bool:
        """
        Check if checkpoint should be created now using predictive scheduling.
        
        Args:
            force: Force checkpoint creation regardless of schedule
            
        Returns:
            True if checkpoint should be created
        """
        if not self.enable_predictive_scheduling or force:
            return True
        
        schedule = self.predictive_scheduler.should_checkpoint_now(force=force)
        
        # Log scheduling decision
        if not schedule.should_checkpoint:
            self.logger.logger.debug(
                f"Checkpoint deferred: {schedule.reason} "
                f"(confidence: {schedule.confidence:.2f}, "
                f"recommended delay: {schedule.recommended_delay_seconds}s)"
            )
        
        return schedule.should_checkpoint
    
    def create_checkpoint(
        self, 
        application_state: dict,
        force: bool = False
    ) -> Optional[IncrementalCheckpoint]:
        """
        Create checkpoint with error handling, monitoring, and predictive scheduling.
        
        Args:
            application_state: Current application state
            force: Force checkpoint creation regardless of schedule
            
        Returns:
            Created checkpoint or None if failed/deferred
        """
        # Check if checkpoint should be created
        if not self.should_checkpoint(force=force):
            return None
        
        start_time = time.time()
        
        try:
            # Use retry logic for checkpoint creation
            checkpoint = self.error_handler.retry_operation(
                super().create_checkpoint,
                "checkpoint_creation",
                application_state
            )
            
            # Record performance metrics
            elapsed_ms = (time.time() - start_time) * 1000
            if self.enable_monitoring:
                self.performance_monitor.record_checkpoint_time(elapsed_ms)
            
            # Log success
            self.logger.log_checkpoint_created(
                checkpoint.checkpoint_id,
                checkpoint.is_full,
                checkpoint.get_size()
            )
            
            # Performance warning if slow
            if elapsed_ms > 100:
                self.logger.log_performance_warning(
                    "checkpoint_creation",
                    elapsed_ms,
                    100.0
                )
            
            return checkpoint
            
        except Exception as e:
            # Handle error
            self.error_handler.handle_checkpoint_creation_error(
                e,
                self.checkpoint_counter
            )
            
            # Try to create a simple full checkpoint as fallback
            try:
                self.logger.logger.warning("Attempting fallback full checkpoint")
                self.checkpoint_counter += 1
                self.last_full_checkpoint_id = self.checkpoint_counter
                checkpoint = self._create_full_checkpoint(application_state, time.time())
                self.storage_manager.store_checkpoint(checkpoint)
                return checkpoint
            except Exception as fallback_error:
                self.logger.log_error(
                    "checkpoint_creation_failed",
                    str(fallback_error),
                    self.checkpoint_counter
                )
                return None
    
    def restore_from_checkpoint(
        self,
        checkpoint_id: int,
        fallback_to_previous: bool = True
    ) -> Optional[dict]:
        """
        Restore from checkpoint with error handling.
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            fallback_to_previous: Try previous checkpoint if restoration fails
            
        Returns:
            Restored state or None if failed
        """
        start_time = time.time()
        
        try:
            # Attempt restoration
            state = super().restore_from_checkpoint(checkpoint_id)
            
            # Record performance
            elapsed_ms = (time.time() - start_time) * 1000
            if self.enable_monitoring:
                self.performance_monitor.record_restoration_time(elapsed_ms)
            
            # Log success
            self.logger.log_checkpoint_restored(checkpoint_id, elapsed_ms)
            
            return state
            
        except Exception as e:
            # Handle error
            fallback_id = checkpoint_id - 1 if fallback_to_previous else None
            self.error_handler.handle_restoration_error(e, checkpoint_id, fallback_id)
            
            # Try fallback
            if fallback_to_previous and checkpoint_id > 1:
                try:
                    self.logger.logger.warning(f"Attempting fallback to checkpoint {checkpoint_id - 1}")
                    return self.restore_from_checkpoint(checkpoint_id - 1, fallback_to_previous=False)
                except Exception:
                    pass
            
            self.logger.log_error(
                "restoration_failed",
                str(e),
                checkpoint_id
            )
            return None
    
    def restore_from_legacy_checkpoint(self, legacy_checkpoint: dict) -> dict:
        """
        Restore from legacy checkpoint format.
        
        Args:
            legacy_checkpoint: Legacy format checkpoint
            
        Returns:
            Restored state
        """
        if self.compatibility.is_legacy_checkpoint(legacy_checkpoint):
            self.logger.logger.info("Converting legacy checkpoint to new format")
            new_checkpoint = self.compatibility.convert_from_legacy(legacy_checkpoint)
            
            # Store converted checkpoint
            self.storage_manager.store_checkpoint(new_checkpoint)
            
            # Return state
            return legacy_checkpoint['state']
        else:
            raise ValueError("Not a legacy checkpoint")
    
    def run_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check.
        
        Returns:
            Health status dictionary
        """
        return self.health_checker.run_all_checks(self)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Performance statistics and recommendations
        """
        if not self.enable_monitoring:
            return {'monitoring_enabled': False}
        
        stats = self.performance_monitor.get_statistics()
        bottlenecks = self.performance_monitor.identify_bottlenecks()
        
        report = {
            'statistics': stats,
            'bottlenecks': bottlenecks,
            'monitoring_enabled': True
        }
        
        # Add optimization status
        if self.enable_optimizations:
            report['optimizations'] = {
                'hash_calculator': self.hash_calculator.get_cache_statistics(),
                'xxhash_available': self.hash_calculator.xxhash_available
            }
        
        # Add predictive scheduling stats
        if self.enable_predictive_scheduling:
            report['predictive_scheduling'] = self.predictive_scheduler.get_performance_report()
        
        return report
    
    def get_scheduling_status(self) -> Dict[str, Any]:
        """
        Get current scheduling status and recommendations.
        
        Returns:
            Scheduling information
        """
        if not self.enable_predictive_scheduling:
            return {
                'enabled': False,
                'message': 'Predictive scheduling is disabled'
            }
        
        return {
            'enabled': True,
            **self.predictive_scheduler.get_performance_report()
        }
    
    def optimize_performance(self):
        """
        Apply performance optimizations.
        
        This method can be called periodically to optimize caches and resources.
        """
        if self.enable_optimizations:
            # Optimize hash cache
            self.hash_calculator.optimize_cache()
            self.logger.logger.info("Performance optimization applied")
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        Get comprehensive diagnostic information.
        
        Returns:
            Diagnostic data for troubleshooting
        """
        diagnostics = {
            'version': '1.1.0',
            'checkpoint_statistics': self.get_statistics(),
            'health_status': self.run_health_check(),
            'recent_errors': [
                {
                    'type': err.error_type.value,
                    'message': err.message,
                    'checkpoint_id': err.checkpoint_id,
                    'recoverable': err.recoverable
                }
                for err in self.error_handler.get_recent_errors(5)
            ]
        }
        
        if self.enable_monitoring:
            diagnostics['performance'] = self.get_performance_report()
        
        return diagnostics
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check system health.
        
        Returns:
            Health status dictionary with status, checkpoint_count, storage_size_mb, and issues
        """
        try:
            health_result = self.health_checker.run_all_checks(self)
            
            # Get storage information
            checkpoints = self.list_checkpoints()
            storage_path = Path(self.storage_manager.storage_path)
            storage_size_mb = 0.0
            
            if storage_path.exists():
                # Calculate total storage used
                for checkpoint_file in storage_path.glob('*.json'):
                    storage_size_mb += checkpoint_file.stat().st_size / (1024 * 1024)
            
            # Collect any issues
            issues = []
            if not health_result.get('healthy', False):
                failed_checks = [k for k, v in health_result.get('checks', {}).items() if not v]
                issues.append(f"Failed health checks: {', '.join(failed_checks)}")
            
            return {
                'status': health_result.get('status', 'unknown'),
                'checkpoint_count': len(checkpoints),
                'storage_size_mb': storage_size_mb,
                'issues': issues
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'checkpoint_count': 0,
                'storage_size_mb': 0.0,
                'issues': [f"Health check error: {str(e)}"]
            }
    
    def cleanup_old_checkpoints(
        self,
        keep_last_n: int = 10,
        keep_all_full: bool = True
    ):
        """
        Cleanup with logging.
        
        Args:
            keep_last_n: Keep last N checkpoints
            keep_all_full: Keep all full checkpoints regardless of age
        """
        checkpoints_before = len(self.list_checkpoints())
        
        super().cleanup_old_checkpoints(keep_last_n, keep_all_full)
        
        checkpoints_after = len(self.list_checkpoints())
        deleted = checkpoints_before - checkpoints_after
        
        self.logger.log_cleanup(deleted, checkpoints_after)
