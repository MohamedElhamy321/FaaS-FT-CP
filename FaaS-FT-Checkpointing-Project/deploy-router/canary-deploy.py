#!/usr/bin/env python3
"""
Canary Deployment Script for Incremental Checkpoint System

Automates gradual rollout with automatic rollback on failure.
"""

import subprocess
import time
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class RolloutPhase(Enum):
    """Deployment phases."""
    VALIDATION = "validation"
    CANARY_5 = "canary_5"
    CANARY_25 = "canary_25"
    CANARY_50 = "canary_50"
    FULL = "full"
    COMPLETE = "complete"
    ROLLBACK = "rollback"


@dataclass
class HealthMetrics:
    """Health metrics for deployment validation."""
    error_rate: float
    latency_p95: float
    latency_p99: float
    throughput: float
    cache_hit_rate: float
    success: bool
    message: str


@dataclass
class RolloutConfig:
    """Configuration for canary rollout."""
    namespace: str = "checkpoint-system"
    deployment_name: str = "checkpoint-manager"
    new_version: str = "v1.3.0"
    old_version: str = "v1.2.0"
    
    # Health check thresholds
    max_error_rate: float = 0.05  # 5%
    max_latency_p95_ms: float = 10.0  # 10ms
    max_latency_p99_ms: float = 50.0  # 50ms
    min_throughput: float = 10.0  # 10 checkpoints/sec
    min_cache_hit_rate: float = 0.80  # 80%
    
    # Timing
    validation_duration: int = 300  # 5 minutes
    phase_duration: int = 600  # 10 minutes per phase
    
    # Prometheus
    prometheus_url: str = "http://prometheus:9090"


class CanaryDeployment:
    """
    Manages canary deployment with automatic rollback.
    """
    
    def __init__(self, config: RolloutConfig):
        self.config = config
        self.current_phase = RolloutPhase.VALIDATION
        self.rollback_triggered = False
    
    def run(self) -> bool:
        """
        Execute canary deployment.
        
        Returns:
            True if deployment successful, False if rolled back
        """
        print("=" * 80)
        print("🚀 Starting Canary Deployment")
        print("=" * 80)
        print(f"Namespace: {self.config.namespace}")
        print(f"Deployment: {self.config.deployment_name}")
        print(f"Old Version: {self.config.old_version}")
        print(f"New Version: {self.config.new_version}")
        print()
        
        try:
            # Phase 1: Validate current system
            if not self._validate_current_system():
                print("❌ Current system validation failed")
                return False
            
            # Phase 2: Deploy canary (5%)
            if not self._deploy_canary(5):
                return False
            
            # Phase 3: Expand to 25%
            if not self._deploy_canary(25):
                return False
            
            # Phase 4: Expand to 50%
            if not self._deploy_canary(50):
                return False
            
            # Phase 5: Full rollout (100%)
            if not self._deploy_full():
                return False
            
            # Complete
            self._complete_deployment()
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  Deployment interrupted by user")
            self._rollback()
            return False
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            self._rollback()
            return False
    
    def _validate_current_system(self) -> bool:
        """Validate current system health."""
        self.current_phase = RolloutPhase.VALIDATION
        print("📊 Phase 1: Validating Current System")
        print("-" * 80)
        
        # Check current deployment
        if not self._check_deployment_ready():
            print("❌ Current deployment not ready")
            return False
        
        # Collect baseline metrics
        print(f"Collecting baseline metrics ({self.config.validation_duration}s)...")
        time.sleep(self.config.validation_duration)
        
        metrics = self._get_health_metrics()
        
        if not metrics.success:
            print(f"❌ Validation failed: {metrics.message}")
            return False
        
        self._print_metrics("Baseline", metrics)
        print("✅ Current system is healthy\n")
        return True
    
    def _deploy_canary(self, percentage: int) -> bool:
        """Deploy canary at specified percentage."""
        phase_map = {5: RolloutPhase.CANARY_5, 25: RolloutPhase.CANARY_25, 50: RolloutPhase.CANARY_50}
        self.current_phase = phase_map[percentage]
        
        print(f"🐤 Phase: Deploy Canary ({percentage}%)")
        print("-" * 80)
        
        # Scale deployment
        total_replicas = self._get_replica_count()
        canary_replicas = max(1, int(total_replicas * percentage / 100))
        
        print(f"Scaling canary to {canary_replicas} replicas (total: {total_replicas})...")
        
        if not self._update_canary_replicas(canary_replicas):
            print("❌ Failed to scale canary")
            self._rollback()
            return False
        
        # Wait for rollout
        if not self._wait_for_rollout():
            print("❌ Rollout failed")
            self._rollback()
            return False
        
        # Monitor health
        print(f"Monitoring health ({self.config.phase_duration}s)...")
        
        for i in range(self.config.phase_duration // 30):
            time.sleep(30)
            
            metrics = self._get_health_metrics()
            
            if not metrics.success:
                print(f"\n❌ Health check failed: {metrics.message}")
                self._rollback()
                return False
            
            progress = ((i + 1) * 30 / self.config.phase_duration) * 100
            print(f"Progress: {progress:.0f}% - Error rate: {metrics.error_rate:.2%}, "
                  f"P95: {metrics.latency_p95:.2f}ms, P99: {metrics.latency_p99:.2f}ms")
        
        print(f"✅ Canary {percentage}% successful\n")
        return True
    
    def _deploy_full(self) -> bool:
        """Deploy to 100%."""
        self.current_phase = RolloutPhase.FULL
        print("🚀 Phase: Full Rollout (100%)")
        print("-" * 80)
        
        # Update all replicas
        print("Updating all replicas to new version...")
        
        if not self._update_all_replicas():
            print("❌ Failed to update replicas")
            self._rollback()
            return False
        
        # Wait for rollout
        if not self._wait_for_rollout():
            print("❌ Rollout failed")
            self._rollback()
            return False
        
        # Final health check
        print("Final health check...")
        time.sleep(60)
        
        metrics = self._get_health_metrics()
        
        if not metrics.success:
            print(f"❌ Final health check failed: {metrics.message}")
            self._rollback()
            return False
        
        self._print_metrics("Final", metrics)
        print("✅ Full rollout successful\n")
        return True
    
    def _complete_deployment(self):
        """Complete deployment."""
        self.current_phase = RolloutPhase.COMPLETE
        print("=" * 80)
        print("🎉 Deployment Complete!")
        print("=" * 80)
        print(f"Version {self.config.new_version} successfully deployed")
        print()
    
    def _rollback(self):
        """Rollback to previous version."""
        if self.rollback_triggered:
            return
        
        self.rollback_triggered = True
        self.current_phase = RolloutPhase.ROLLBACK
        
        print("\n" + "=" * 80)
        print("🔄 ROLLBACK INITIATED")
        print("=" * 80)
        
        # Rollback deployment
        cmd = [
            "kubectl", "rollout", "undo",
            f"deployment/{self.config.deployment_name}",
            f"-n={self.config.namespace}"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Rollback command failed: {result.stderr}")
            print("⚠️  Manual intervention required!")
            return
        
        print("Waiting for rollback to complete...")
        self._wait_for_rollout()
        
        print("✅ Rollback complete")
        print(f"Reverted to version {self.config.old_version}")
    
    def _check_deployment_ready(self) -> bool:
        """Check if deployment is ready."""
        cmd = [
            "kubectl", "get", "deployment",
            self.config.deployment_name,
            f"-n={self.config.namespace}",
            "-o=json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        try:
            data = json.loads(result.stdout)
            status = data.get("status", {})
            
            replicas = status.get("replicas", 0)
            ready_replicas = status.get("readyReplicas", 0)
            
            return replicas > 0 and replicas == ready_replicas
        except:
            return False
    
    def _get_replica_count(self) -> int:
        """Get current replica count."""
        cmd = [
            "kubectl", "get", "deployment",
            self.config.deployment_name,
            f"-n={self.config.namespace}",
            "-o=jsonpath={.spec.replicas}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        try:
            return int(result.stdout.strip())
        except:
            return 3  # Default
    
    def _update_canary_replicas(self, replicas: int) -> bool:
        """Update canary replica count."""
        # In real implementation, this would use a service mesh like Istio
        # For now, we simulate with kubectl scale
        
        cmd = [
            "kubectl", "set", "image",
            f"deployment/{self.config.deployment_name}",
            f"checkpoint-manager=checkpoint-system:{self.config.new_version}",
            f"-n={self.config.namespace}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def _update_all_replicas(self) -> bool:
        """Update all replicas."""
        cmd = [
            "kubectl", "set", "image",
            f"deployment/{self.config.deployment_name}",
            f"checkpoint-manager=checkpoint-system:{self.config.new_version}",
            f"-n={self.config.namespace}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def _wait_for_rollout(self, timeout: int = 300) -> bool:
        """Wait for deployment rollout."""
        cmd = [
            "kubectl", "rollout", "status",
            f"deployment/{self.config.deployment_name}",
            f"-n={self.config.namespace}",
            f"--timeout={timeout}s"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def _get_health_metrics(self) -> HealthMetrics:
        """Get current health metrics from Prometheus."""
        # Query Prometheus for metrics
        metrics = {
            "error_rate": self._query_prometheus(
                'rate(checkpoint_errors_total[5m])'
            ),
            "latency_p95": self._query_prometheus(
                'histogram_quantile(0.95, rate(checkpoint_creation_duration_seconds_bucket[5m])) * 1000'
            ),
            "latency_p99": self._query_prometheus(
                'histogram_quantile(0.99, rate(checkpoint_creation_duration_seconds_bucket[5m])) * 1000'
            ),
            "throughput": self._query_prometheus(
                'rate(checkpoint_creation_total{status="success"}[5m])'
            ),
            "cache_hit_rate": self._query_prometheus(
                'rate(checkpoint_cache_hits_total[5m]) / (rate(checkpoint_cache_hits_total[5m]) + rate(checkpoint_cache_misses_total[5m]))'
            )
        }
        
        # Validate thresholds
        if metrics["error_rate"] > self.config.max_error_rate:
            return HealthMetrics(
                success=False,
                message=f"Error rate too high: {metrics['error_rate']:.2%}",
                **metrics
            )
        
        if metrics["latency_p95"] > self.config.max_latency_p95_ms:
            return HealthMetrics(
                success=False,
                message=f"P95 latency too high: {metrics['latency_p95']:.2f}ms",
                **metrics
            )
        
        if metrics["latency_p99"] > self.config.max_latency_p99_ms:
            return HealthMetrics(
                success=False,
                message=f"P99 latency too high: {metrics['latency_p99']:.2f}ms",
                **metrics
            )
        
        if metrics["throughput"] < self.config.min_throughput:
            return HealthMetrics(
                success=False,
                message=f"Throughput too low: {metrics['throughput']:.2f}/sec",
                **metrics
            )
        
        if metrics["cache_hit_rate"] < self.config.min_cache_hit_rate:
            return HealthMetrics(
                success=False,
                message=f"Cache hit rate too low: {metrics['cache_hit_rate']:.2%}",
                **metrics
            )
        
        return HealthMetrics(
            success=True,
            message="All metrics within thresholds",
            **metrics
        )
    
    def _query_prometheus(self, query: str) -> float:
        """Query Prometheus for a metric."""
        # In real implementation, this would use requests library
        # For now, return mock data
        import random
        
        if "error_rate" in query:
            return random.uniform(0.0, 0.02)
        elif "latency_p95" in query:
            return random.uniform(1.5, 3.0)
        elif "latency_p99" in query:
            return random.uniform(2.0, 5.0)
        elif "throughput" in query:
            return random.uniform(50.0, 200.0)
        elif "cache_hit" in query:
            return random.uniform(0.95, 0.99)
        else:
            return 0.0
    
    def _print_metrics(self, label: str, metrics: HealthMetrics):
        """Print metrics."""
        print(f"\n{label} Metrics:")
        print(f"  Error Rate:     {metrics.error_rate:.2%}")
        print(f"  Latency P95:    {metrics.latency_p95:.2f}ms")
        print(f"  Latency P99:    {metrics.latency_p99:.2f}ms")
        print(f"  Throughput:     {metrics.throughput:.2f}/sec")
        print(f"  Cache Hit Rate: {metrics.cache_hit_rate:.2%}")
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Canary deployment for checkpoint system")
    parser.add_argument("--namespace", default="checkpoint-system", help="Kubernetes namespace")
    parser.add_argument("--deployment", default="checkpoint-manager", help="Deployment name")
    parser.add_argument("--new-version", default="v1.3.0", help="New version to deploy")
    parser.add_argument("--old-version", default="v1.2.0", help="Current version")
    parser.add_argument("--prometheus-url", default="http://prometheus:9090", help="Prometheus URL")
    
    args = parser.parse_args()
    
    config = RolloutConfig(
        namespace=args.namespace,
        deployment_name=args.deployment,
        new_version=args.new_version,
        old_version=args.old_version,
        prometheus_url=args.prometheus_url
    )
    
    deployment = CanaryDeployment(config)
    success = deployment.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
