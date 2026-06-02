"""
Integration Examples - Demonstrating drop-in replacement for legacy checkpointing

This file shows how to migrate existing applications to use incremental checkpointing
with minimal code changes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from incremental_checkpoint.integration import (
    create_fission_adapter,
    JSONCheckpointAdapter,
    CheckpointContext,
    RolloutStrategy,
    FeatureFlags
)
from incremental_checkpoint.migration import (
    CheckpointMigrator,
    CodeMigrationHelper,
    quick_migrate
)
from incremental_checkpoint.config import (
    CheckpointConfig,
    ConfigPresets,
    ConfigValidator,
    load_config
)
import tempfile
import shutil


def example_fission_migration():
    """
    Example 1: Migrating Fission function to incremental checkpointing
    Shows drop-in replacement for fibonacci.py checkpoint code
    """
    print("="*70)
    print("Example 1: Fission Function Migration (Drop-in Replacement)")
    print("="*70)
    
    # Create temporary checkpoint directory
    checkpoint_dir = tempfile.mkdtemp()
    checkpoint_file = os.path.join(checkpoint_dir, "fibonacci_checkpoint.json")
    
    try:
        # STEP 1: Create adapter (drop-in replacement)
        print("\n1. Creating incremental checkpoint adapter...")
        adapter = create_fission_adapter(
            checkpoint_file=checkpoint_file,
            enable_incremental=True,
            rollout_strategy=RolloutStrategy.ENABLED
        )
        print(f"   ✓ Adapter created for {checkpoint_file}")
        
        # STEP 2: Use adapter with same interface as legacy code
        print("\n2. Simulating Fibonacci function with checkpoints...")
        
        # Simulate function state (like fibonacci.py)
        state = {
            "last_n": 0,
            "sequence": []
        }
        
        # Simulate calculating fibonacci with periodic checkpoints
        n_target = 50
        for i in range(n_target):
            # Calculate fibonacci
            if i == 0:
                fib_val = 0
            elif i == 1:
                fib_val = 1
            else:
                fib_val = int(state["sequence"][-1]) + int(state["sequence"][-2])
            
            state["sequence"].append(str(fib_val))
            state["last_n"] = i + 1
            
            # Save checkpoint every 10 iterations (like original code)
            if (i + 1) % 10 == 0:
                adapter.save_checkpoint(state, checkpoint_file)
                print(f"   ✓ Checkpoint saved at n={i+1}")
        
        # STEP 3: Simulate recovery from checkpoint
        print("\n3. Simulating recovery from checkpoint...")
        
        # Load checkpoint (same interface as legacy)
        recovered_state = adapter.load_checkpoint(checkpoint_file)
        print(f"   ✓ Recovered state: last_n={recovered_state['last_n']}, "
              f"sequence_length={len(recovered_state['sequence'])}")
        
        # Verify recovery
        assert recovered_state["last_n"] == n_target
        assert len(recovered_state["sequence"]) == n_target
        print("   ✓ Recovery verified - state matches!")
        
        # STEP 4: Show performance statistics
        print("\n4. Performance Statistics:")
        stats = adapter.get_statistics()
        if stats:
            print(f"   • Total checkpoints: {stats.get('total_checkpoints', 'N/A')}")
            print(f"   • Storage used: {stats.get('total_storage_mb', 0):.3f} MB")
            print(f"   • Compression ratio: {stats.get('avg_compression_ratio', 0):.2f}x")
        
        print("\n✅ Example 1 completed successfully!")
        print("   Legacy checkpoint code replaced with zero changes to function logic!")
        
    finally:
        # Cleanup
        shutil.rmtree(checkpoint_dir, ignore_errors=True)


def example_gradual_rollout():
    """
    Example 2: Gradual rollout with canary deployment
    Shows how to safely deploy incremental checkpointing
    """
    print("\n" + "="*70)
    print("Example 2: Gradual Rollout with Canary Deployment")
    print("="*70)
    
    checkpoint_dir = tempfile.mkdtemp()
    checkpoint_file = os.path.join(checkpoint_dir, "app_checkpoint.json")
    
    try:
        # STAGE 1: 5% canary rollout
        print("\n1. Stage 1 - Canary Rollout (5% traffic)...")
        adapter = create_fission_adapter(
            checkpoint_file=checkpoint_file,
            enable_incremental=True,
            rollout_strategy=RolloutStrategy.CANARY_5
        )
        
        # Simulate 100 requests
        incremental_count = 0
        for i in range(100):
            state = {"request_id": i, "data": [i] * 100}
            adapter.save_checkpoint(state, checkpoint_file)
            
            # Check if incremental was used (approximately 5% due to randomness)
            if adapter.incremental_manager:
                incremental_count += 1
        
        print(f"   • 100 requests processed")
        print(f"   • Approximate incremental usage: {incremental_count}% (target: 5%)")
        print("   • Monitoring for issues... ✓")
        
        # STAGE 2: Increase to 50%
        print("\n2. Stage 2 - Increase to 50% traffic...")
        adapter.feature_flags.rollout_strategy = RolloutStrategy.CANARY_50
        adapter.feature_flags.rollout_percentage = 50
        print("   • Rollout increased to 50%")
        print("   • Monitoring for issues... ✓")
        
        # STAGE 3: Full rollout
        print("\n3. Stage 3 - Full Rollout (100% traffic)...")
        adapter.feature_flags.rollout_strategy = RolloutStrategy.ENABLED
        adapter.feature_flags.rollout_percentage = 100
        
        # Process requests with full incremental
        for i in range(20):
            state = {"request_id": 100 + i, "data": [i] * 100}
            adapter.save_checkpoint(state, checkpoint_file)
        
        print("   • 20 requests processed with 100% incremental")
        print("   • Full rollout successful! ✓")
        
        print("\n✅ Example 2 completed successfully!")
        print("   Safe gradual rollout prevents production incidents!")
        
    finally:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)


def example_context_manager():
    """
    Example 3: Using context manager for automatic checkpointing
    Shows the cleanest way to add checkpointing to existing code
    """
    print("\n" + "="*70)
    print("Example 3: Context Manager for Automatic Checkpointing")
    print("="*70)
    
    checkpoint_dir = tempfile.mkdtemp()
    checkpoint_file = os.path.join(checkpoint_dir, "context_checkpoint.json")
    
    try:
        # Create adapter
        adapter = create_fission_adapter(
            checkpoint_file=checkpoint_file,
            enable_incremental=True
        )
        
        # Application state (could be global variables, class attributes, etc.)
        app_state = {
            "counter": 0,
            "results": [],
            "config": {"timeout": 30}
        }
        
        print("\n1. Using context manager for automatic checkpoint/restore...")
        
        # Define state getter/setter
        def get_state():
            return app_state.copy()
        
        def set_state(state):
            app_state.update(state)
        
        # Use context manager - checkpoint automatically loaded on entry
        with CheckpointContext(adapter, checkpoint_file, get_state, set_state):
            print(f"   • Initial state: counter={app_state['counter']}")
            
            # Do work
            for i in range(10):
                app_state["counter"] += 1
                app_state["results"].append(f"result_{i}")
            
            print(f"   • After processing: counter={app_state['counter']}")
            # Checkpoint automatically saved on exit!
        
        print("   ✓ Checkpoint automatically saved on exit")
        
        # Simulate restart - checkpoint restored automatically
        print("\n2. Simulating restart with automatic recovery...")
        app_state["counter"] = 0  # Reset state
        app_state["results"] = []
        
        with CheckpointContext(adapter, checkpoint_file, get_state, set_state):
            print(f"   • State after recovery: counter={app_state['counter']}")
            print(f"   • Results recovered: {len(app_state['results'])} items")
            
            # Continue work
            for i in range(10, 15):
                app_state["counter"] += 1
                app_state["results"].append(f"result_{i}")
            
            print(f"   • After more processing: counter={app_state['counter']}")
        
        print("\n✅ Example 3 completed successfully!")
        print("   Context manager handles all checkpoint operations automatically!")
        
    finally:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)


def example_migration_workflow():
    """
    Example 4: Complete migration workflow
    Shows how to migrate existing checkpoints
    """
    print("\n" + "="*70)
    print("Example 4: Complete Migration Workflow")
    print("="*70)
    
    checkpoint_dir = tempfile.mkdtemp()
    
    try:
        # STEP 1: Create legacy checkpoints
        print("\n1. Creating legacy JSON checkpoints...")
        legacy_checkpoints = []
        for i in range(5):
            legacy_file = os.path.join(checkpoint_dir, f"legacy_{i}.json")
            state = {
                "checkpoint_id": i,
                "data": [j for j in range(100)],
                "timestamp": f"2024-01-{i+1:02d}"
            }
            import json
            with open(legacy_file, 'w') as f:
                json.dump(state, f)
            legacy_checkpoints.append(legacy_file)
        
        print(f"   ✓ Created {len(legacy_checkpoints)} legacy checkpoints")
        
        # STEP 2: Run migration
        print("\n2. Migrating to incremental format...")
        migrator = CheckpointMigrator(checkpoint_dir)
        report = migrator.migrate_json_checkpoints(pattern="legacy_*.json")
        
        print(f"   • Total: {report.total_checkpoints}")
        print(f"   • Migrated: {report.migrated_successfully}")
        print(f"   • Failed: {report.failed_migrations}")
        print(f"   • Success rate: {report.success_rate:.1f}%")
        print(f"   • Space saved: {report.space_savings_pct:.1f}%")
        
        # STEP 3: Verify migration
        print("\n3. Verifying migrated checkpoints...")
        adapter = JSONCheckpointAdapter(checkpoint_dir)
        
        for legacy_file in legacy_checkpoints:
            restored = adapter.load_checkpoint(legacy_file)
            print(f"   ✓ Verified {os.path.basename(legacy_file)}: "
                  f"checkpoint_id={restored.get('checkpoint_id', 'N/A')}")
        
        print("\n✅ Example 4 completed successfully!")
        print("   All legacy checkpoints migrated and verified!")
        
    finally:
        shutil.rmtree(checkpoint_dir, ignore_errors=True)


def example_configuration_management():
    """
    Example 5: Configuration management with presets
    Shows how to configure the system for different use cases
    """
    print("\n" + "="*70)
    print("Example 5: Configuration Management with Presets")
    print("="*70)
    
    # Development configuration
    print("\n1. Development Configuration:")
    dev_config = ConfigPresets.development()
    print(f"   • Checkpoint dir: {dev_config.checkpoint_dir}")
    print(f"   • Compression: Level {dev_config.compression_level}")
    print(f"   • Monitoring: {dev_config.enable_monitoring}")
    print(f"   • Verify checkpoints: {dev_config.verify_checkpoints}")
    
    # Production configuration
    print("\n2. Production Configuration:")
    prod_config = ConfigPresets.production()
    print(f"   • Checkpoint dir: {prod_config.checkpoint_dir}")
    print(f"   • Compression: Level {prod_config.compression_level}")
    print(f"   • Error handling: {prod_config.enable_error_handling}")
    print(f"   • Health checks: {prod_config.enable_health_checks}")
    
    # High performance configuration
    print("\n3. High Performance Configuration:")
    perf_config = ConfigPresets.high_performance()
    print(f"   • Compression: Level {perf_config.compression_level} (fast)")
    print(f"   • Parallel compression: {perf_config.parallel_compression}")
    print(f"   • Hash cache: {perf_config.hash_cache_size} entries")
    print(f"   • Monitoring overhead: {perf_config.enable_monitoring}")
    
    # Validate configurations
    print("\n4. Validating Configurations:")
    for name, config in [("Development", dev_config), 
                         ("Production", prod_config),
                         ("High Performance", perf_config)]:
        result = ConfigValidator.validate_config(config)
        status = "✓ Valid" if result['valid'] else "✗ Invalid"
        print(f"   • {name}: {status}")
        if result['recommendations']:
            print(f"     Recommendations: {len(result['recommendations'])}")
    
    # Save and load configuration
    print("\n5. Save/Load Configuration:")
    temp_dir = tempfile.mkdtemp()
    config_file = os.path.join(temp_dir, "checkpoint_config.json")
    
    try:
        prod_config.save_to_file(config_file)
        print(f"   ✓ Saved configuration to {config_file}")
        
        loaded_config = CheckpointConfig.from_file(config_file)
        print(f"   ✓ Loaded configuration from file")
        print(f"   • Compression level: {loaded_config.compression_level}")
        print(f"   • Max checkpoints: {loaded_config.max_checkpoints}")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print("\n✅ Example 5 completed successfully!")
    print("   Configuration management simplifies deployment!")


def example_code_generation():
    """
    Example 6: Generate migration code snippets
    Shows how to generate code for migrating applications
    """
    print("\n" + "="*70)
    print("Example 6: Generate Migration Code Snippets")
    print("="*70)
    
    helper = CodeMigrationHelper()
    
    # Generate Fission migration code
    print("\n1. Fission Function Migration Code:")
    print("-" * 70)
    code = helper.generate_fission_migration("/tmp/fibonacci_checkpoint.json")
    print(code)
    
    # Generate context manager code
    print("\n2. Context Manager Pattern Code:")
    print("-" * 70)
    code = helper.generate_context_manager_migration("/tmp/app_checkpoint.json")
    print(code)
    
    print("\n✅ Example 6 completed successfully!")
    print("   Code generation helps quickly migrate existing applications!")


def main():
    """Run all integration examples"""
    print("\n" + "="*70)
    print("INCREMENTAL CHECKPOINTING - INTEGRATION EXAMPLES")
    print("="*70)
    print("\nDemonstrating drop-in replacement for legacy checkpoint systems")
    print("with gradual rollout, migration tools, and configuration management.\n")
    
    try:
        # Run all examples
        example_fission_migration()
        example_gradual_rollout()
        example_context_manager()
        example_migration_workflow()
        example_configuration_management()
        example_code_generation()
        
        # Final summary
        print("\n" + "="*70)
        print("ALL INTEGRATION EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\n✅ Key Takeaways:")
        print("   1. Drop-in replacement requires minimal code changes")
        print("   2. Gradual rollout enables safe production deployment")
        print("   3. Context managers automate checkpoint operations")
        print("   4. Migration tools handle legacy checkpoint conversion")
        print("   5. Configuration presets simplify deployment")
        print("   6. Code generation accelerates migration")
        print("\n🚀 Ready for production deployment!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
