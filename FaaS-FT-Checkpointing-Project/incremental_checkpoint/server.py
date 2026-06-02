"""
Simple HTTP server for incremental checkpoint system with health and metrics endpoints.
"""

from flask import Flask, jsonify, request, Response
from incremental_checkpoint import ProductionCheckpointManager
from incremental_checkpoint.async_checkpoint_manager import (
    AsyncCheckpointManager,
    CheckpointPriority
)
from incremental_checkpoint.metrics import get_global_exporter, export_metrics
import os
import sys

app = Flask(__name__)

# Initialize checkpoint manager
CHECKPOINT_DIR = os.environ.get('CHECKPOINT_DIR', '/data/checkpoints')
manager = ProductionCheckpointManager(
    storage_path=CHECKPOINT_DIR,
    enable_monitoring=True,
    enable_optimizations=True
)

# Initialize async checkpoint manager
async_manager = AsyncCheckpointManager(
    base_manager=manager,
    max_workers=int(os.environ.get('ASYNC_WORKERS', '4')),
    max_queue_size=int(os.environ.get('ASYNC_QUEUE_SIZE', '100')),
    enable_copy_on_write=True
)

# Get global metrics exporter
metrics_exporter = get_global_exporter()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    try:
        health_status = manager.check_health()
        
        # Update metrics
        is_healthy = health_status['status'] == 'healthy'
        metrics_exporter.update_health_status(is_healthy)
        
        status_code = 200 if is_healthy else 503
        
        return jsonify({
            'status': health_status['status'],
            'version': '2.0.0',
            'checkpoint_count': health_status.get('checkpoint_count', 0),
            'storage_used_mb': health_status.get('storage_size_mb', 0.0),
            'issues': health_status.get('issues', [])
        }), status_code
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint."""
    try:
        # Simple check that manager is initialized
        if manager and os.path.exists(CHECKPOINT_DIR):
            return jsonify({'ready': True}), 200
        return jsonify({'ready': False}), 503
    except:
        return jsonify({'ready': False}), 503


@app.route('/checkpoint', methods=['POST'])
def create_checkpoint():
    """Create checkpoint endpoint."""
    try:
        state = request.get_json()
        
        if not state:
            return jsonify({'error': 'No state provided'}), 400
        
        import time
        start_time = time.perf_counter()
        
        checkpoint = manager.create_checkpoint(state)
        
        duration = time.perf_counter() - start_time
        size_bytes = checkpoint.metadata.get('size_bytes', 0)
        checkpoint_type = 'FULL' if checkpoint.is_full else 'INCR'
        
        # Record metrics
        metrics_exporter.record_checkpoint_creation(
            checkpoint_type=checkpoint_type,
            duration=duration,
            size_bytes=size_bytes,
            success=True
        )
        
        return jsonify({
            'checkpoint_id': checkpoint.checkpoint_id,
            'checkpoint_type': checkpoint_type,
            'is_full': checkpoint.is_full,
            'timestamp': checkpoint.timestamp,
            'duration_ms': duration * 1000,
            'size_bytes': size_bytes
        }), 201
        
    except Exception as e:
        metrics_exporter.record_error(
            error_type=type(e).__name__,
            operation='checkpoint_creation'
        )
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/<checkpoint_id>', methods=['GET'])
def restore_checkpoint(checkpoint_id):
    """Restore checkpoint endpoint."""
    try:
        import time
        start_time = time.perf_counter()
        
        state = manager.restore_state(checkpoint_id)
        
        duration = time.perf_counter() - start_time
        
        # Record metrics
        metrics_exporter.record_checkpoint_restoration(
            duration=duration,
            success=True
        )
        
        return jsonify({
            'checkpoint_id': checkpoint_id,
            'state': state,
            'duration_ms': duration * 1000
        }), 200
        
    except Exception as e:
        metrics_exporter.record_error(
            error_type=type(e).__name__,
            operation='checkpoint_restoration'
        )
        return jsonify({'error': str(e)}), 404


@app.route('/checkpoints', methods=['GET'])
def list_checkpoints():
    """List all checkpoints."""
    try:
        history = manager.get_checkpoint_history()
        
        return jsonify({
            'count': len(history),
            'checkpoints': history
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/async', methods=['POST'])
def create_checkpoint_async():
    """Create checkpoint asynchronously (non-blocking)."""
    try:
        data = request.get_json()
        
        if not data or 'state' not in data:
            return jsonify({'error': 'No state provided'}), 400
        
        state = data['state']
        function_id = data.get('function_id', 'default')
        priority_str = data.get('priority', 'NORMAL').upper()
        
        # Parse priority
        try:
            priority = CheckpointPriority[priority_str]
        except KeyError:
            priority = CheckpointPriority.NORMAL
        
        # Submit async checkpoint (returns immediately)
        task_id = async_manager.create_checkpoint_async(
            function_id=function_id,
            state=state,
            priority=priority
        )
        
        return jsonify({
            'task_id': task_id,
            'status': 'submitted',
            'message': 'Checkpoint is being processed asynchronously',
            'status_url': f'/checkpoint/async/{task_id}'
        }), 202  # 202 Accepted
        
    except RuntimeError as e:
        # Queue full
        return jsonify({
            'error': str(e),
            'queue_stats': async_manager.get_queue_stats()
        }), 503
    except Exception as e:
        metrics_exporter.record_error(
            error_type=type(e).__name__,
            operation='async_checkpoint_submission'
        )
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/async/<task_id>', methods=['GET'])
def get_async_checkpoint_status(task_id):
    """Get status of an async checkpoint task."""
    try:
        result = async_manager.get_task_status(task_id)
        
        if not result:
            return jsonify({
                'error': 'Task not found',
                'task_id': task_id
            }), 404
        
        response = {
            'task_id': result.task_id,
            'is_complete': result.is_complete,
            'success': result.success
        }
        
        if result.is_complete:
            if result.success:
                response.update({
                    'checkpoint_id': result.checkpoint_id,
                    'duration_ms': result.duration_ms,
                    'processing_time_ms': result.processing_time_ms,
                    'checkpoint_size_bytes': result.checkpoint_size_bytes
                })
            else:
                response['error'] = result.error
        else:
            response['status'] = 'processing'
        
        status_code = 200 if result.is_complete else 202
        return jsonify(response), status_code
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/async/stats', methods=['GET'])
def get_async_stats():
    """Get async checkpoint queue and processing statistics."""
    try:
        stats = async_manager.get_queue_stats()
        
        return jsonify({
            'async_checkpoint_stats': stats,
            'utilization_percent': (
                stats['queue_size'] / stats['queue_max_size'] * 100
                if stats['queue_max_size'] > 0 else 0
            )
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        report = manager.get_performance_report()
        health = manager.check_health()
        
        # Include compression stats if available
        compression_stats = None
        if hasattr(manager.storage_manager, 'compression_manager') and manager.storage_manager.compression_manager:
            compression_stats = manager.storage_manager.compression_manager.get_stats()
        
        # Include validation stats if available
        validation_stats = None
        if hasattr(manager.storage_manager, 'validator') and manager.storage_manager.validator:
            validation_stats = manager.storage_manager.validator.get_metrics()
        
        # Include tier stats if available
        tier_stats = None
        if hasattr(manager.storage_manager, 'get_tier_statistics'):
            try:
                tier_stats_raw = manager.storage_manager.get_tier_statistics()
                tier_stats = {
                    tier: {
                        'checkpoints': stats.checkpoint_count,
                        'size_mb': stats.total_size_mb()
                    }
                    for tier, stats in tier_stats_raw.items()
                }
            except:
                pass
        
        return jsonify({
            'performance': report,
            'health': health,
            'compression': compression_stats,
            'validation': validation_stats,
            'tiered_storage': tier_stats,
            'version': '2.4.0'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/<int:checkpoint_id>/validate', methods=['POST'])
def validate_checkpoint(checkpoint_id):
    """Validate checkpoint integrity."""
    try:
        # Get validation level from request
        data = request.get_json() or {}
        level_str = data.get('level', 'STANDARD').upper()
        
        # Load checkpoint
        checkpoint = manager.storage_manager.load_checkpoint(checkpoint_id, validate=False)
        if not checkpoint:
            return jsonify({'error': 'Checkpoint not found'}), 404
        
        # Validate
        validator = manager.storage_manager.validator
        if not validator:
            return jsonify({'error': 'Validation not enabled'}), 503
        
        from incremental_checkpoint.validation import ValidationLevel
        level = ValidationLevel[level_str]
        result = validator.validate(checkpoint, level=level)
        
        return jsonify({
            'checkpoint_id': checkpoint_id,
            'is_valid': result.is_valid,
            'quality_level': result.quality_level.value,
            'quality_score': result.quality_score,
            'validation_time_ms': result.validation_time_ms,
            'critical_issues': [
                {
                    'field': issue.field,
                    'description': issue.description,
                    'corruption_type': issue.corruption_type.value if issue.corruption_type else None
                }
                for issue in result.critical_issues
            ],
            'warnings': [
                {
                    'field': issue.field,
                    'description': issue.description
                }
                for issue in result.warnings
            ],
            'checksums': result.checksums
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/<int:checkpoint_id>/repair', methods=['POST'])
def repair_checkpoint(checkpoint_id):
    """Attempt to repair a corrupted checkpoint."""
    try:
        # Load checkpoint
        checkpoint = manager.storage_manager.load_checkpoint(checkpoint_id, validate=False)
        if not checkpoint:
            return jsonify({'error': 'Checkpoint not found'}), 404
        
        validator = manager.storage_manager.validator
        if not validator:
            return jsonify({'error': 'Validation not enabled'}), 503
        
        # Validate first
        validation_result = validator.validate(checkpoint)
        
        if validation_result.is_valid:
            return jsonify({
                'message': 'Checkpoint is already valid, no repair needed',
                'quality_score': validation_result.quality_score
            }), 200
        
        # Attempt repair
        repair_result = validator.repair(checkpoint, validation_result)
        
        # Re-validate
        new_validation = validator.validate(checkpoint)
        
        return jsonify({
            'checkpoint_id': checkpoint_id,
            'repair_successful': repair_result.success,
            'issues_repaired': repair_result.issues_repaired,
            'issues_failed': repair_result.issues_failed,
            'new_quality_score': new_validation.quality_score,
            'is_valid_now': new_validation.is_valid,
            'details': repair_result.details
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/validation/stats', methods=['GET'])
def get_validation_stats():
    """Get validation system statistics."""
    try:
        validator = manager.storage_manager.validator
        if not validator:
            return jsonify({'error': 'Validation not enabled'}), 503
        
        metrics = validator.get_metrics()
        
        return jsonify({
            'validation_metrics': metrics,
            'validation_enabled': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/tiers/statistics', methods=['GET'])
def get_tier_statistics():
    """Get storage tier statistics."""
    try:
        # Check if tiered storage is enabled
        if not hasattr(manager.storage_manager, 'get_tier_statistics'):
            return jsonify({'error': 'Tiered storage not enabled'}), 503
        
        tier_stats = manager.storage_manager.get_tier_statistics()
        
        # Convert to JSON-serializable format
        stats_dict = {}
        for tier_name, stats in tier_stats.items():
            stats_dict[tier_name] = {
                'checkpoint_count': stats.checkpoint_count,
                'total_size_bytes': stats.total_size_bytes,
                'total_size_mb': stats.total_size_mb(),
                'avg_checkpoint_size_bytes': stats.avg_checkpoint_size_bytes(),
                'access_count': stats.access_count,
                'cost_per_gb_month': stats.cost_per_gb_month,
                'estimated_monthly_cost': stats.estimated_monthly_cost()
            }
        
        return jsonify({
            'tier_statistics': stats_dict,
            'tiered_storage_enabled': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/tiers/cost-report', methods=['GET'])
def get_tier_cost_report():
    """Get tier cost analysis report."""
    try:
        if not hasattr(manager.storage_manager, 'get_cost_report'):
            return jsonify({'error': 'Tiered storage not enabled'}), 503
        
        report = manager.storage_manager.get_cost_report()
        
        return jsonify(report), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/checkpoint/<int:checkpoint_id>/tier', methods=['GET'])
def get_checkpoint_tier_info(checkpoint_id):
    """Get tier information for specific checkpoint."""
    try:
        if not hasattr(manager.storage_manager, 'get_checkpoint_tier'):
            return jsonify({'error': 'Tiered storage not enabled'}), 503
        
        tier = manager.storage_manager.get_checkpoint_tier(checkpoint_id)
        
        if not tier:
            return jsonify({'error': 'Checkpoint not found'}), 404
        
        # Get metadata
        metadata = manager.storage_manager.checkpoint_metadata.get(checkpoint_id)
        
        return jsonify({
            'checkpoint_id': checkpoint_id,
            'current_tier': tier.value,
            'age_hours': metadata.age_hours() if metadata else None,
            'access_count': metadata.access_count if metadata else 0,
            'size_bytes': metadata.size_bytes if metadata else 0,
            'last_access_time': metadata.last_access_time if metadata else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/tiers/migrate', methods=['POST'])
def trigger_tier_migration():
    """Manually trigger tier migration."""
    try:
        if not hasattr(manager.storage_manager, 'auto_migrate_checkpoints'):
            return jsonify({'error': 'Tiered storage not enabled'}), 503
        
        migrations = manager.storage_manager.auto_migrate_checkpoints()
        
        return jsonify({
            'migrations_performed': migrations,
            'message': f'Successfully migrated {migrations} checkpoints'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    return Response(export_metrics(), mimetype='text/plain')


@app.route('/scheduler/status', methods=['GET'])
def scheduler_status():
    """
    Get current predictive scheduling status.
    
    Returns:
        JSON with current load, pattern, and next checkpoint recommendation
    """
    try:
        if not hasattr(manager, 'get_scheduling_status'):
            return jsonify({
                'error': 'Predictive scheduling not available',
                'message': 'Manager does not support predictive scheduling'
            }), 501
        
        status = manager.get_scheduling_status()
        
        return jsonify({
            'status': 'ok',
            'scheduling': status
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/scheduler/statistics', methods=['GET'])
def scheduler_statistics():
    """
    Get predictive scheduling statistics.
    
    Returns:
        JSON with defer rate, overhead reduction, and scheduling metrics
    """
    try:
        if not hasattr(manager, 'enable_predictive_scheduling') or not manager.enable_predictive_scheduling:
            return jsonify({
                'error': 'Predictive scheduling not enabled'
            }), 501
        
        report = manager.predictive_scheduler.get_performance_report()
        
        return jsonify({
            'status': 'ok',
            'statistics': report.get('scheduler_statistics', {}),
            'workload_pattern': report.get('workload_pattern', {}),
            'current_load': report.get('current_load', {})
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/scheduler/adjust', methods=['POST'])
def adjust_scheduler():
    """
    Manually adjust scheduling interval.
    
    Request body:
        {
            "interval": <new_base_interval_seconds>
        }
    
    Returns:
        JSON confirmation
    """
    try:
        if not hasattr(manager, 'enable_predictive_scheduling') or not manager.enable_predictive_scheduling:
            return jsonify({
                'error': 'Predictive scheduling not enabled'
            }), 501
        
        data = request.get_json()
        new_interval = data.get('interval')
        
        if new_interval is None or new_interval < 60:
            return jsonify({
                'error': 'Invalid interval',
                'message': 'Interval must be at least 60 seconds'
            }), 400
        
        # Update scheduler interval
        manager.predictive_scheduler.scheduler.base_interval = float(new_interval)
        manager.predictive_scheduler.scheduler.current_interval = float(new_interval)
        
        return jsonify({
            'status': 'ok',
            'message': f'Base interval updated to {new_interval}s',
            'new_interval': new_interval
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/scheduler/pattern', methods=['GET'])
def workload_pattern():
    """
    Get current workload pattern analysis.
    
    Returns:
        JSON with detected workload pattern and confidence
    """
    try:
        if not hasattr(manager, 'enable_predictive_scheduling') or not manager.enable_predictive_scheduling:
            return jsonify({
                'error': 'Predictive scheduling not enabled'
            }), 501
        
        pattern = manager.predictive_scheduler.workload_analyzer.analyze_patterns()
        
        return jsonify({
            'status': 'ok',
            'pattern': {
                'type': pattern.pattern_type,
                'confidence': pattern.confidence,
                'period_seconds': pattern.period_seconds,
                'peak_hours': pattern.peak_hours,
                'idle_hours': pattern.idle_hours
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/cluster/status', methods=['GET'])
def cluster_status():
    """
    Get distributed cluster status.
    
    Returns:
        JSON with cluster state, leader, and coordination info
    """
    try:
        if not hasattr(manager, 'enable_distributed_coordination') or not manager.enable_distributed_coordination:
            return jsonify({
                'error': 'Distributed coordination not enabled'
            }), 501
        
        status = manager.distributed_coordinator.get_cluster_status()
        
        return jsonify({
            'status': 'ok',
            'cluster': status
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/cluster/coordinated-checkpoint', methods=['POST'])
def coordinated_checkpoint():
    """
    Create coordinated checkpoint across cluster.
    
    Request body:
        {
            "state": <application_state>,
            "nodes": ["node1", "node2"]  // optional
        }
    
    Returns:
        JSON with coordination ID
    """
    try:
        if not hasattr(manager, 'enable_distributed_coordination') or not manager.enable_distributed_coordination:
            return jsonify({
                'error': 'Distributed coordination not enabled'
            }), 501
        
        data = request.get_json()
        application_state = data.get('state', {})
        nodes = data.get('nodes')
        
        if nodes:
            nodes = set(nodes)
        
        coord_id = manager.distributed_coordinator.create_coordinated_checkpoint(
            application_state,
            nodes
        )
        
        if coord_id:
            return jsonify({
                'status': 'ok',
                'coordination_id': coord_id,
                'message': 'Coordinated checkpoint initiated'
            })
        else:
            return jsonify({
                'status': 'error',
                'error': 'Not cluster leader - cannot coordinate'
            }), 403
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/cluster/coordination/<coord_id>', methods=['GET'])
def coordination_status(coord_id: str):
    """
    Get status of coordinated checkpoint.
    
    Returns:
        JSON with coordination progress
    """
    try:
        if not hasattr(manager, 'enable_distributed_coordination') or not manager.enable_distributed_coordination:
            return jsonify({
                'error': 'Distributed coordination not enabled'
            }), 501
        
        coordination = manager.distributed_coordinator.raft_node.get_checkpoint_status(coord_id)
        
        if not coordination:
            return jsonify({
                'status': 'error',
                'error': 'Coordination not found'
            }), 404
        
        return jsonify({
            'status': 'ok',
            'coordination': {
                'checkpoint_id': coordination.checkpoint_id,
                'coordinator_node': coordination.coordinator_node,
                'participating_nodes': list(coordination.participating_nodes),
                'completed_nodes': list(coordination.completed_nodes),
                'status': coordination.status,
                'timestamp': coordination.timestamp,
                'progress': f"{len(coordination.completed_nodes)}/{len(coordination.participating_nodes)}"
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print(f"Starting Incremental Checkpoint Server v2.6.0")
    print(f"Checkpoint directory: {CHECKPOINT_DIR}")
    print(f"Compression enabled: {hasattr(manager.storage_manager, 'compression_manager') and manager.storage_manager.compression_manager is not None}")
    print(f"Validation enabled: {hasattr(manager.storage_manager, 'validator') and manager.storage_manager.validator is not None}")
    print(f"Tiered storage enabled: {hasattr(manager.storage_manager, 'get_tier_statistics')}")
    print(f"Predictive scheduling enabled: {hasattr(manager, 'enable_predictive_scheduling') and manager.enable_predictive_scheduling}")
    print(f"Distributed coordination enabled: {hasattr(manager, 'enable_distributed_coordination') and manager.enable_distributed_coordination}")
    print(f"Metrics endpoint: http://0.0.0.0:9090/metrics")
    print(f"Health endpoint: http://0.0.0.0:8080/health")
    print(f"Tier statistics: http://0.0.0.0:8080/tiers/statistics")
    print(f"Scheduler status: http://0.0.0.0:8080/scheduler/status")
    print(f"Cluster status: http://0.0.0.0:8080/cluster/status")
    
    # Run server
    app.run(host='0.0.0.0', port=8080, debug=False)
