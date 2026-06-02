"""
Test Predictive Scheduling with ProductionCheckpointManager
"""

import time
from incremental_checkpoint.enhanced_manager import ProductionCheckpointManager
from incremental_checkpoint.predictive_scheduler import SchedulingStrategy

# Create manager with predictive scheduling enabled
manager = ProductionCheckpointManager(
    storage_path="./test_checkpoints_predictive",
    enable_predictive_scheduling=True,
    scheduling_strategy=SchedulingStrategy.HYBRID,
    base_checkpoint_interval=10.0  # 10 seconds for testing
)

print("=== Predictive Scheduling Test ===\n")
print(f"Predictive scheduling: {manager.enable_predictive_scheduling}")
print(f"Strategy: {manager.predictive_scheduler.strategy.value if manager.predictive_scheduler else 'N/A'}")
print()

# Simulate application state changes
application_state = {
    'counter': 0,
    'data': 'initial state'
}

print("Creating checkpoints with predictive scheduling...")
checkpoints_created = 0
checkpoints_deferred = 0

# Test for 60 seconds
start_time = time.time()
iteration = 0

while time.time() - start_time < 60:
    iteration += 1
    application_state['counter'] = iteration
    application_state['data'] = f'state at iteration {iteration}'
    
    # Try to create checkpoint
    checkpoint = manager.create_checkpoint(application_state, force=False)
    
    if checkpoint:
        checkpoints_created += 1
        print(f"✓ Checkpoint {checkpoint.checkpoint_id} created at iteration {iteration}")
    else:
        checkpoints_deferred += 1
        if iteration % 10 == 0:
            print(f"- Checkpoint deferred at iteration {iteration}")
    
    # Sleep for a bit to simulate work
    time.sleep(0.5)

print(f"\n=== Results ===")
print(f"Total iterations: {iteration}")
print(f"Checkpoints created: {checkpoints_created}")
print(f"Checkpoints deferred: {checkpoints_deferred}")
print(f"Defer rate: {checkpoints_deferred / iteration * 100:.1f}%")

# Get performance report
print(f"\n=== Performance Report ===")
report = manager.get_performance_report()

if 'predictive_scheduling' in report:
    sched_report = report['predictive_scheduling']
    print(f"Strategy: {sched_report.get('strategy', 'N/A')}")
    print(f"Samples collected: {sched_report.get('samples_collected', 0)}")
    
    if 'current_load' in sched_report and sched_report['current_load']:
        load = sched_report['current_load']
        print(f"Current CPU: {load.get('cpu_percent', 0):.1f}%")
        print(f"Current Memory: {load.get('memory_percent', 0):.1f}%")
    
    if 'workload_pattern' in sched_report:
        pattern = sched_report['workload_pattern']
        print(f"Workload pattern: {pattern.get('type', 'unknown')}")
        print(f"Pattern confidence: {pattern.get('confidence', 0):.2f}")
    
    if 'scheduler_statistics' in sched_report:
        stats = sched_report['scheduler_statistics']
        print(f"Scheduler defer rate: {stats.get('defer_rate', 0)*100:.1f}%")
        print(f"Estimated overhead reduction: {stats.get('overhead_reduction_estimate', 0):.1f}%")

# Test forced checkpoint
print(f"\n=== Forced Checkpoint Test ===")
forced_checkpoint = manager.create_checkpoint({'force': 'test'}, force=True)
if forced_checkpoint:
    print(f"✓ Forced checkpoint {forced_checkpoint.checkpoint_id} created successfully")
else:
    print("✗ Forced checkpoint failed")

print("\nTest completed!")
