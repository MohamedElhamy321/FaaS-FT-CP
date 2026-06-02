"""
Configuration Management - Centralized configuration for incremental checkpointing

This module provides configuration management with validation, environment variable
support, and preset configurations for common use cases.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging


class CheckpointPolicy(Enum):
    """Checkpoint retention policies"""
    KEEP_ALL = "keep_all"  # Keep all checkpoints
    KEEP_LAST_N = "keep_last_n"  # Keep last N checkpoints
    KEEP_ALL_FULL = "keep_all_full"  # Keep all full, cleanup incremental


class CompressionLevel(Enum):
    """Compression level presets"""
    NONE = 0
    FAST = 1
    BALANCED = 6
    BEST = 9


@dataclass
class CheckpointConfig:
    """
    Comprehensive configuration for incremental checkpointing system
    """
    
    # Storage configuration
    checkpoint_dir: str = "/tmp/checkpoints"
    max_checkpoints: int = 100
    cleanup_policy: CheckpointPolicy = CheckpointPolicy.KEEP_ALL_FULL
    
    # Checkpoint behavior
    full_checkpoint_interval: int = 10
    skip_unchanged: bool = False
    auto_checkpoint_on_exit: bool = False
    
    # Compression settings
    compression_level: int = 6
    parallel_compression: bool = True
    parallel_threshold_kb: int = 100
    max_workers: int = 4
    
    # Performance optimization
    enable_hash_optimization: bool = True
    hash_cache_size: int = 10000
    enable_memory_optimization: bool = True
    memory_threshold_kb: int = 100
    
    # Production features
    enable_error_handling: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    enable_health_checks: bool = True
    enable_monitoring: bool = True
    enable_logging: bool = True
    
    # Integration features
    use_incremental_checkpointing: bool = True
    rollout_percentage: int = 100
    fallback_to_legacy_on_error: bool = True
    log_performance_comparison: bool = True
    
    # Advanced options
    verify_checkpoints: bool = False
    enable_backward_compatibility: bool = True
    checkpoint_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate configuration values"""
        errors = []
        
        # Validate numeric ranges
        if self.compression_level < 0 or self.compression_level > 9:
            errors.append("compression_level must be between 0 and 9")
        
        if self.full_checkpoint_interval < 1:
            errors.append("full_checkpoint_interval must be at least 1")
        
        if self.max_checkpoints < 1:
            errors.append("max_checkpoints must be at least 1")
        
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
        
        if self.rollout_percentage < 0 or self.rollout_percentage > 100:
            errors.append("rollout_percentage must be between 0 and 100")
        
        if self.hash_cache_size < 0:
            errors.append("hash_cache_size must be non-negative")
        
        # Validate directory
        if not self.checkpoint_dir:
            errors.append("checkpoint_dir cannot be empty")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['cleanup_policy'] = self.cleanup_policy.value
        return data
    
    def to_json(self) -> str:
        """Convert configuration to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointConfig':
        """Create configuration from dictionary"""
        # Convert policy string to enum
        if 'cleanup_policy' in data and isinstance(data['cleanup_policy'], str):
            data['cleanup_policy'] = CheckpointPolicy(data['cleanup_policy'])
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CheckpointConfig':
        """Create configuration from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, config_file: str) -> 'CheckpointConfig':
        """Load configuration from JSON file"""
        with open(config_file, 'r') as f:
            return cls.from_json(f.read())
    
    def save_to_file(self, config_file: str) -> None:
        """Save configuration to JSON file"""
        os.makedirs(os.path.dirname(config_file) or ".", exist_ok=True)
        with open(config_file, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def from_environment(cls, prefix: str = "CHECKPOINT_") -> 'CheckpointConfig':
        """
        Create configuration from environment variables
        
        Args:
            prefix: Prefix for environment variables
            
        Returns:
            CheckpointConfig instance
            
        Example:
            export CHECKPOINT_DIR=/data/checkpoints
            export CHECKPOINT_COMPRESSION_LEVEL=9
            export CHECKPOINT_ENABLE_MONITORING=true
        """
        config = cls()
        
        # Map environment variables to config fields
        env_mappings = {
            f"{prefix}DIR": ("checkpoint_dir", str),
            f"{prefix}MAX_CHECKPOINTS": ("max_checkpoints", int),
            f"{prefix}CLEANUP_POLICY": ("cleanup_policy", lambda x: CheckpointPolicy(x)),
            f"{prefix}FULL_INTERVAL": ("full_checkpoint_interval", int),
            f"{prefix}COMPRESSION_LEVEL": ("compression_level", int),
            f"{prefix}ENABLE_MONITORING": ("enable_monitoring", lambda x: x.lower() == 'true'),
            f"{prefix}ENABLE_LOGGING": ("enable_logging", lambda x: x.lower() == 'true'),
            f"{prefix}MAX_RETRIES": ("max_retries", int),
            f"{prefix}ROLLOUT_PERCENTAGE": ("rollout_percentage", int),
        }
        
        for env_var, (field_name, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    setattr(config, field_name, converter(value))
                except Exception as e:
                    logging.warning(f"Failed to parse {env_var}={value}: {e}")
        
        return config


class ConfigPresets:
    """Preset configurations for common use cases"""
    
    @staticmethod
    def development() -> CheckpointConfig:
        """Development configuration - verbose logging, no optimization"""
        return CheckpointConfig(
            checkpoint_dir="/tmp/dev_checkpoints",
            max_checkpoints=50,
            cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
            compression_level=1,  # Fast compression
            enable_hash_optimization=False,  # Easier debugging
            enable_monitoring=True,
            enable_logging=True,
            verify_checkpoints=True,  # Extra validation
            rollout_percentage=100,  # Always use incremental
        )
    
    @staticmethod
    def production() -> CheckpointConfig:
        """Production configuration - optimized for performance and reliability"""
        return CheckpointConfig(
            checkpoint_dir="/var/lib/checkpoints",
            max_checkpoints=100,
            cleanup_policy=CheckpointPolicy.KEEP_ALL_FULL,
            compression_level=6,  # Balanced
            enable_hash_optimization=True,
            enable_memory_optimization=True,
            enable_error_handling=True,
            enable_health_checks=True,
            enable_monitoring=True,
            enable_logging=True,
            fallback_to_legacy_on_error=True,
            rollout_percentage=100,
        )
    
    @staticmethod
    def high_performance() -> CheckpointConfig:
        """High performance configuration - optimized for speed"""
        return CheckpointConfig(
            checkpoint_dir="/tmp/checkpoints",
            max_checkpoints=200,
            cleanup_policy=CheckpointPolicy.KEEP_ALL_FULL,
            compression_level=1,  # Fast compression
            parallel_compression=True,
            parallel_threshold_kb=50,
            max_workers=8,
            enable_hash_optimization=True,
            hash_cache_size=50000,  # Large cache
            enable_memory_optimization=True,
            enable_monitoring=False,  # Reduce overhead
            enable_logging=False,
            rollout_percentage=100,
        )
    
    @staticmethod
    def low_storage() -> CheckpointConfig:
        """Low storage configuration - optimized for minimal disk usage"""
        return CheckpointConfig(
            checkpoint_dir="/tmp/checkpoints",
            max_checkpoints=20,  # Keep few checkpoints
            cleanup_policy=CheckpointPolicy.KEEP_LAST_N,
            full_checkpoint_interval=20,  # Fewer full checkpoints
            compression_level=9,  # Best compression
            enable_memory_optimization=True,
            memory_threshold_kb=50,  # Compress more aggressively
            rollout_percentage=100,
        )
    
    @staticmethod
    def testing() -> CheckpointConfig:
        """Testing configuration - suitable for automated tests"""
        return CheckpointConfig(
            checkpoint_dir="/tmp/test_checkpoints",
            max_checkpoints=10,
            cleanup_policy=CheckpointPolicy.KEEP_ALL,
            compression_level=1,
            enable_monitoring=False,
            enable_logging=False,
            verify_checkpoints=True,
            rollout_percentage=100,
        )
    
    @staticmethod
    def canary_rollout(percentage: int = 5) -> CheckpointConfig:
        """Canary rollout configuration - for gradual deployment"""
        return CheckpointConfig(
            checkpoint_dir="/var/lib/checkpoints",
            max_checkpoints=100,
            cleanup_policy=CheckpointPolicy.KEEP_ALL_FULL,
            compression_level=6,
            enable_error_handling=True,
            enable_monitoring=True,
            enable_logging=True,
            fallback_to_legacy_on_error=True,
            log_performance_comparison=True,
            rollout_percentage=percentage,
        )


class ConfigValidator:
    """Validate and provide recommendations for configurations"""
    
    @staticmethod
    def validate_config(config: CheckpointConfig) -> Dict[str, Any]:
        """
        Validate configuration and provide recommendations
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dictionary with validation results and recommendations
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        try:
            config.validate()
        except ValueError as e:
            results['valid'] = False
            results['errors'].append(str(e))
            return results
        
        # Performance recommendations
        if config.compression_level > 6 and not config.parallel_compression:
            results['recommendations'].append(
                "Consider enabling parallel_compression for better performance with high compression levels"
            )
        
        if config.enable_hash_optimization and config.hash_cache_size < 1000:
            results['warnings'].append(
                "Hash cache size is small - consider increasing for better performance"
            )
        
        # Storage recommendations
        if config.max_checkpoints > 1000:
            results['warnings'].append(
                "Large max_checkpoints value may use significant disk space"
            )
        
        if config.cleanup_policy == CheckpointPolicy.KEEP_ALL:
            results['recommendations'].append(
                "KEEP_ALL policy will never delete checkpoints - monitor disk usage"
            )
        
        # Production readiness
        if not config.enable_error_handling:
            results['warnings'].append(
                "Error handling is disabled - not recommended for production"
            )
        
        if not config.enable_health_checks:
            results['recommendations'].append(
                "Consider enabling health_checks for production deployments"
            )
        
        # Rollout recommendations
        if config.rollout_percentage < 100 and not config.fallback_to_legacy_on_error:
            results['warnings'].append(
                "Partial rollout without fallback may cause failures"
            )
        
        return results
    
    @staticmethod
    def suggest_preset(use_case: str) -> Optional[CheckpointConfig]:
        """
        Suggest preset configuration based on use case
        
        Args:
            use_case: One of 'development', 'production', 'high_performance',
                     'low_storage', 'testing', or 'canary'
            
        Returns:
            Suggested configuration or None if use case not recognized
        """
        presets = {
            'development': ConfigPresets.development,
            'dev': ConfigPresets.development,
            'production': ConfigPresets.production,
            'prod': ConfigPresets.production,
            'high_performance': ConfigPresets.high_performance,
            'performance': ConfigPresets.high_performance,
            'low_storage': ConfigPresets.low_storage,
            'storage': ConfigPresets.low_storage,
            'testing': ConfigPresets.testing,
            'test': ConfigPresets.testing,
            'canary': ConfigPresets.canary_rollout,
        }
        
        preset_fn = presets.get(use_case.lower())
        if preset_fn:
            return preset_fn()
        return None


def load_config(config_source: Optional[str] = None,
               preset: Optional[str] = None,
               use_environment: bool = True) -> CheckpointConfig:
    """
    Load configuration from various sources with priority
    
    Priority order:
    1. Config file (if specified)
    2. Preset (if specified)
    3. Environment variables (if use_environment=True)
    4. Default configuration
    
    Args:
        config_source: Path to JSON config file
        preset: Preset name ('development', 'production', etc.)
        use_environment: Load from environment variables
        
    Returns:
        CheckpointConfig instance
    """
    config = None
    
    # Start with default
    config = CheckpointConfig()
    
    # Apply preset if specified
    if preset:
        preset_config = ConfigValidator.suggest_preset(preset)
        if preset_config:
            config = preset_config
    
    # Load from environment if requested
    if use_environment:
        env_config = CheckpointConfig.from_environment()
        # Merge non-default values
        for key, value in asdict(env_config).items():
            if value != getattr(CheckpointConfig(), key):
                setattr(config, key, value)
    
    # Load from file if specified (highest priority)
    if config_source and os.path.exists(config_source):
        config = CheckpointConfig.from_file(config_source)
    
    # Validate final configuration
    config.validate()
    
    return config
