"""
Migration Utilities - Tools for migrating from legacy checkpoint systems

This module provides utilities to help migrate existing applications
from legacy checkpoint systems to incremental checkpointing.
"""

import os
import json
import pickle
import shutil
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from .integration import JSONCheckpointAdapter, PickleCheckpointAdapter
from .enhanced_manager import ProductionCheckpointManager


@dataclass
class MigrationReport:
    """Report of migration operation"""
    total_checkpoints: int = 0
    migrated_successfully: int = 0
    failed_migrations: int = 0
    total_legacy_size: int = 0
    total_incremental_size: int = 0
    space_saved: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def success_rate(self) -> float:
        """Calculate migration success rate"""
        if self.total_checkpoints == 0:
            return 0.0
        return (self.migrated_successfully / self.total_checkpoints) * 100
    
    @property
    def space_savings_pct(self) -> float:
        """Calculate space savings percentage"""
        if self.total_legacy_size == 0:
            return 0.0
        return (self.space_saved / self.total_legacy_size) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'total_checkpoints': self.total_checkpoints,
            'migrated_successfully': self.migrated_successfully,
            'failed_migrations': self.failed_migrations,
            'success_rate': f"{self.success_rate:.1f}%",
            'total_legacy_size': self.total_legacy_size,
            'total_incremental_size': self.total_incremental_size,
            'space_saved': self.space_saved,
            'space_savings_pct': f"{self.space_savings_pct:.1f}%",
            'errors': self.errors
        }


class CheckpointMigrator:
    """
    Utility for migrating legacy checkpoints to incremental format
    """
    
    def __init__(self, 
                 checkpoint_dir: str,
                 backup_dir: Optional[str] = None,
                 verify_migration: bool = True):
        """
        Initialize migrator
        
        Args:
            checkpoint_dir: Directory containing checkpoints
            backup_dir: Directory for backup copies (optional)
            verify_migration: Verify migrated checkpoints match originals
        """
        self.checkpoint_dir = checkpoint_dir
        self.backup_dir = backup_dir or f"{checkpoint_dir}_backup"
        self.verify_migration = verify_migration
        self.logger = logging.getLogger(__name__)
        
        # Initialize incremental manager
        self.manager = ProductionCheckpointManager(checkpoint_dir)
    
    def migrate_json_checkpoints(self, pattern: str = "*.json") -> MigrationReport:
        """
        Migrate JSON checkpoint files to incremental format
        
        Args:
            pattern: Glob pattern for checkpoint files
            
        Returns:
            MigrationReport with results
        """
        import glob
        
        report = MigrationReport()
        
        # Find all JSON checkpoint files
        search_path = os.path.join(self.checkpoint_dir, pattern)
        checkpoint_files = glob.glob(search_path)
        report.total_checkpoints = len(checkpoint_files)
        
        self.logger.info(f"Found {report.total_checkpoints} JSON checkpoints to migrate")
        
        # Create backup directory
        if checkpoint_files and not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            self.logger.info(f"Created backup directory: {self.backup_dir}")
        
        # Migrate each checkpoint
        for checkpoint_file in checkpoint_files:
            try:
                # Backup original file
                backup_path = os.path.join(self.backup_dir, os.path.basename(checkpoint_file))
                shutil.copy2(checkpoint_file, backup_path)
                
                # Load legacy checkpoint
                with open(checkpoint_file, 'r') as f:
                    state = json.load(f)
                
                legacy_size = os.path.getsize(checkpoint_file)
                report.total_legacy_size += legacy_size
                
                # Create incremental checkpoint
                checkpoint = self.manager.create_checkpoint(state)
                report.total_incremental_size += checkpoint.get_size()
                
                # Save mapping
                mapping_file = f"{checkpoint_file}.mapping"
                with open(mapping_file, 'w') as f:
                    json.dump({
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'legacy_file': checkpoint_file,
                        'migrated_at': datetime.now().isoformat()
                    }, f)
                
                # Verify migration if requested
                if self.verify_migration:
                    restored = self.manager.restore_from_checkpoint(checkpoint.checkpoint_id)
                    if restored != state:
                        raise ValueError("Restored state doesn't match original")
                
                report.migrated_successfully += 1
                self.logger.info(
                    f"Migrated {os.path.basename(checkpoint_file)} -> "
                    f"checkpoint {checkpoint.checkpoint_id} "
                    f"(saved {legacy_size - checkpoint.size} bytes)"
                )
                
            except Exception as e:
                report.failed_migrations += 1
                error_msg = f"Failed to migrate {checkpoint_file}: {e}"
                report.errors.append(error_msg)
                self.logger.error(error_msg)
        
        report.space_saved = report.total_legacy_size - report.total_incremental_size
        
        self.logger.info(
            f"Migration complete: {report.migrated_successfully}/{report.total_checkpoints} "
            f"successful, saved {report.space_savings_pct:.1f}% space"
        )
        
        return report
    
    def migrate_pickle_checkpoints(self, pattern: str = "*.pkl") -> MigrationReport:
        """
        Migrate pickle checkpoint files to incremental format
        
        Args:
            pattern: Glob pattern for checkpoint files
            
        Returns:
            MigrationReport with results
        """
        import glob
        
        report = MigrationReport()
        
        # Find all pickle checkpoint files
        search_path = os.path.join(self.checkpoint_dir, pattern)
        checkpoint_files = glob.glob(search_path)
        report.total_checkpoints = len(checkpoint_files)
        
        self.logger.info(f"Found {report.total_checkpoints} pickle checkpoints to migrate")
        
        # Create backup directory
        if checkpoint_files and not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Migrate each checkpoint
        for checkpoint_file in checkpoint_files:
            try:
                # Backup original file
                backup_path = os.path.join(self.backup_dir, os.path.basename(checkpoint_file))
                shutil.copy2(checkpoint_file, backup_path)
                
                # Load legacy checkpoint
                with open(checkpoint_file, 'rb') as f:
                    state = pickle.load(f)
                
                legacy_size = os.path.getsize(checkpoint_file)
                report.total_legacy_size += legacy_size
                
                # Create incremental checkpoint
                checkpoint = self.manager.create_checkpoint(state)
                report.total_incremental_size += checkpoint.get_size()
                
                # Save mapping
                mapping_file = f"{checkpoint_file}.mapping"
                with open(mapping_file, 'w') as f:
                    json.dump({
                        'checkpoint_id': checkpoint.checkpoint_id,
                        'legacy_file': checkpoint_file,
                        'migrated_at': datetime.now().isoformat()
                    }, f)
                
                report.migrated_successfully += 1
                
            except Exception as e:
                report.failed_migrations += 1
                error_msg = f"Failed to migrate {checkpoint_file}: {e}"
                report.errors.append(error_msg)
                self.logger.error(error_msg)
        
        report.space_saved = report.total_legacy_size - report.total_incremental_size
        return report
    
    def rollback_migration(self) -> Tuple[int, int]:
        """
        Rollback migration by restoring backup files
        
        Returns:
            Tuple of (restored_count, failed_count)
        """
        import glob
        
        if not os.path.exists(self.backup_dir):
            self.logger.warning("No backup directory found")
            return 0, 0
        
        restored = 0
        failed = 0
        
        backup_files = glob.glob(os.path.join(self.backup_dir, "*"))
        
        for backup_file in backup_files:
            try:
                original_file = os.path.join(self.checkpoint_dir, os.path.basename(backup_file))
                shutil.copy2(backup_file, original_file)
                
                # Remove mapping file if exists
                mapping_file = f"{original_file}.mapping"
                if os.path.exists(mapping_file):
                    os.remove(mapping_file)
                
                restored += 1
                self.logger.info(f"Restored {os.path.basename(backup_file)}")
                
            except Exception as e:
                failed += 1
                self.logger.error(f"Failed to restore {backup_file}: {e}")
        
        self.logger.info(f"Rollback complete: {restored} restored, {failed} failed")
        return restored, failed
    
    def cleanup_legacy_files(self, keep_backup: bool = True) -> int:
        """
        Clean up legacy checkpoint files after successful migration
        
        Args:
            keep_backup: Keep backup files
            
        Returns:
            Number of files deleted
        """
        import glob
        
        deleted = 0
        
        # Delete legacy checkpoint files (keep mapping files)
        for pattern in ["*.json", "*.pkl"]:
            files = glob.glob(os.path.join(self.checkpoint_dir, pattern))
            for file in files:
                try:
                    os.remove(file)
                    deleted += 1
                    self.logger.info(f"Deleted legacy file: {os.path.basename(file)}")
                except Exception as e:
                    self.logger.error(f"Failed to delete {file}: {e}")
        
        # Optionally delete backup directory
        if not keep_backup and os.path.exists(self.backup_dir):
            try:
                shutil.rmtree(self.backup_dir)
                self.logger.info(f"Deleted backup directory: {self.backup_dir}")
            except Exception as e:
                self.logger.error(f"Failed to delete backup directory: {e}")
        
        return deleted


class CodeMigrationHelper:
    """
    Helper to generate code snippets for migrating application code
    """
    
    @staticmethod
    def generate_fission_migration(checkpoint_file: str = "/tmp/fibonacci_checkpoint.json") -> str:
        """
        Generate code snippet for migrating Fission function
        
        Args:
            checkpoint_file: Path to checkpoint file
            
        Returns:
            Code snippet as string
        """
        return f'''
# Replace legacy checkpoint code with incremental checkpointing adapter

# OLD CODE:
# import json
# CHECKPOINT_FILE = "{checkpoint_file}"
# 
# def load_checkpoint():
#     if os.path.exists(CHECKPOINT_FILE):
#         with open(CHECKPOINT_FILE, "r") as f:
#             return json.load(f)
#     return {{}}
# 
# def save_checkpoint(state):
#     with open(CHECKPOINT_FILE, "w") as f:
#         json.dump(state, f)

# NEW CODE:
from incremental_checkpoint.integration import create_fission_adapter, RolloutStrategy

# Create adapter with gradual rollout
adapter = create_fission_adapter(
    checkpoint_file="{checkpoint_file}",
    enable_incremental=True,
    rollout_strategy=RolloutStrategy.CANARY_5  # Start with 5% traffic
)

def load_checkpoint():
    return adapter.load_checkpoint("{checkpoint_file}")

def save_checkpoint(state):
    adapter.save_checkpoint(state, "{checkpoint_file}")

# Gradual rollout steps:
# 1. Deploy with CANARY_5 (5% traffic)
# 2. Monitor for issues
# 3. Increase to CANARY_25 (25% traffic)
# 4. Increase to CANARY_50 (50% traffic)
# 5. Enable fully with RolloutStrategy.ENABLED
'''
    
    @staticmethod
    def generate_context_manager_migration(checkpoint_file: str) -> str:
        """
        Generate code snippet using context manager pattern
        
        Args:
            checkpoint_file: Path to checkpoint file
            
        Returns:
            Code snippet as string
        """
        return f'''
# Use context manager for automatic checkpointing

from incremental_checkpoint.integration import create_fission_adapter, CheckpointContext

adapter = create_fission_adapter(
    checkpoint_file="{checkpoint_file}",
    enable_incremental=True
)

# Define state getter/setter
def get_state():
    return {{'counter': counter, 'data': data}}

def set_state(state):
    global counter, data
    counter = state.get('counter', 0)
    data = state.get('data', [])

# Use context manager
with CheckpointContext(adapter, "{checkpoint_file}", get_state, set_state):
    # Your function logic here
    # Checkpoint is automatically loaded on entry
    # and saved on exit (even if exception occurs)
    counter += 1
    data.append(result)
'''
    
    @staticmethod
    def generate_migration_script(checkpoint_dir: str) -> str:
        """
        Generate complete migration script
        
        Args:
            checkpoint_dir: Directory containing checkpoints
            
        Returns:
            Migration script as string
        """
        return f'''#!/usr/bin/env python3
"""
Checkpoint Migration Script
Migrates legacy checkpoints to incremental format
"""

import logging
from incremental_checkpoint.migration import CheckpointMigrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Initialize migrator
    migrator = CheckpointMigrator(
        checkpoint_dir="{checkpoint_dir}",
        backup_dir="{checkpoint_dir}_backup",
        verify_migration=True  # Verify each migration
    )
    
    # Migrate JSON checkpoints
    print("Migrating JSON checkpoints...")
    json_report = migrator.migrate_json_checkpoints()
    print(f"JSON Migration: {{json_report.migrated_successfully}}/{{json_report.total_checkpoints}} successful")
    print(f"Space saved: {{json_report.space_savings_pct:.1f}}%")
    
    # Migrate pickle checkpoints (if any)
    print("\\nMigrating pickle checkpoints...")
    pickle_report = migrator.migrate_pickle_checkpoints()
    print(f"Pickle Migration: {{pickle_report.migrated_successfully}}/{{pickle_report.total_checkpoints}} successful")
    
    # Print summary
    total_migrated = json_report.migrated_successfully + pickle_report.migrated_successfully
    total_checkpoints = json_report.total_checkpoints + pickle_report.total_checkpoints
    
    print(f"\\n{'='*60}")
    print(f"MIGRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total checkpoints: {{total_checkpoints}}")
    print(f"Successfully migrated: {{total_migrated}}")
    print(f"Failed: {{json_report.failed_migrations + pickle_report.failed_migrations}}")
    print(f"Space saved: {{json_report.space_saved + pickle_report.space_saved:,}} bytes")
    print(f"{'='*60}")
    
    # Optionally cleanup legacy files after verification
    # print("\\nCleaning up legacy files...")
    # deleted = migrator.cleanup_legacy_files(keep_backup=True)
    # print(f"Deleted {{deleted}} legacy checkpoint files")

if __name__ == "__main__":
    main()
'''


def quick_migrate(checkpoint_dir: str,
                 checkpoint_type: str = "json",
                 verify: bool = True,
                 cleanup: bool = False) -> MigrationReport:
    """
    Quick migration utility function
    
    Args:
        checkpoint_dir: Directory containing checkpoints
        checkpoint_type: Type of checkpoints ('json' or 'pickle')
        verify: Verify migrations
        cleanup: Clean up legacy files after migration
        
    Returns:
        MigrationReport with results
    """
    migrator = CheckpointMigrator(checkpoint_dir, verify_migration=verify)
    
    if checkpoint_type == "json":
        report = migrator.migrate_json_checkpoints()
    elif checkpoint_type == "pickle":
        report = migrator.migrate_pickle_checkpoints()
    else:
        raise ValueError(f"Unknown checkpoint type: {checkpoint_type}")
    
    if cleanup and report.failed_migrations == 0:
        deleted = migrator.cleanup_legacy_files(keep_backup=True)
        logging.info(f"Cleaned up {deleted} legacy files")
    
    return report
