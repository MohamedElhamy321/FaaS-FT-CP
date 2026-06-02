"""
Production Performance Testing
Tests the deployed checkpoint system for performance validation
"""

import requests
import time
import statistics
from typing import List, Dict, Any
import json

CHECKPOINT_API_URL = "http://localhost:8080"

def test_health():
    """Test health endpoint"""
    print("\n=== Health Check ===")
    response = requests.get(f"{CHECKPOINT_API_URL}/health")
    data = response.json()
    print(f"Status: {data['status']}")
    print(f"Version: {data['version']}")
    print(f"Checkpoint Count: {data['checkpoint_count']}")
    print(f"Storage Used: {data['storage_used_mb']:.2f} MB")
    return response.status_code == 200

def test_checkpoint_creation_performance(num_checkpoints: int = 100) -> Dict[str, Any]:
    """Test checkpoint creation performance"""
    print(f"\n=== Checkpoint Creation Performance ({num_checkpoints} checkpoints) ===")
    
    durations = []
    full_count = 0
    incr_count = 0
    
    for i in range(num_checkpoints):
        state = {
            'counter': i,
            'data': f'test_data_{i}',
            'nested': {
                'field1': f'value_{i}',
                'field2': i * 2
            }
        }
        
        start = time.perf_counter()
        response = requests.post(
            f"{CHECKPOINT_API_URL}/checkpoint",
            json={'state': state}
        )
        duration = time.perf_counter() - start
        
        if response.status_code == 201:
            data = response.json()
            durations.append(duration * 1000)  # Convert to ms
            if data['is_full']:
                full_count += 1
            else:
                incr_count += 1
        
        if (i + 1) % 20 == 0:
            print(f"  Created {i + 1}/{num_checkpoints} checkpoints...")
    
    # Calculate statistics
    avg_duration = statistics.mean(durations)
    median_duration = statistics.median(durations)
    p95_duration = statistics.quantiles(durations, n=20)[18]  # 95th percentile
    p99_duration = statistics.quantiles(durations, n=100)[98]  # 99th percentile
    
    print(f"\nResults:")
    print(f"  Total Checkpoints: {num_checkpoints}")
    print(f"  Full Checkpoints: {full_count}")
    print(f"  Incremental Checkpoints: {incr_count}")
    print(f"  Average Duration: {avg_duration:.2f} ms")
    print(f"  Median Duration: {median_duration:.2f} ms")
    print(f"  P95 Duration: {p95_duration:.2f} ms")
    print(f"  P99 Duration: {p99_duration:.2f} ms")
    print(f"  Min Duration: {min(durations):.2f} ms")
    print(f"  Max Duration: {max(durations):.2f} ms")
    
    return {
        'total': num_checkpoints,
        'full_count': full_count,
        'incr_count': incr_count,
        'avg_ms': avg_duration,
        'median_ms': median_duration,
        'p95_ms': p95_duration,
        'p99_ms': p99_duration,
        'min_ms': min(durations),
        'max_ms': max(durations)
    }

def test_checkpoint_restoration_performance() -> Dict[str, Any]:
    """Test checkpoint restoration performance"""
    print("\n=== Checkpoint Restoration Performance ===")
    
    # Get list of checkpoints
    response = requests.get(f"{CHECKPOINT_API_URL}/checkpoints")
    if response.status_code != 200:
        print("  Failed to get checkpoint list")
        return {}
    
    checkpoint_ids = response.json()['checkpoint_ids']
    if not checkpoint_ids:
        print("  No checkpoints available for restoration test")
        return {}
    
    durations = []
    test_count = min(20, len(checkpoint_ids))
    
    for checkpoint_id in checkpoint_ids[:test_count]:
        start = time.perf_counter()
        response = requests.get(f"{CHECKPOINT_API_URL}/checkpoint/{checkpoint_id}")
        duration = time.perf_counter() - start
        
        if response.status_code == 200:
            durations.append(duration * 1000)
    
    if durations:
        avg_duration = statistics.mean(durations)
        median_duration = statistics.median(durations)
        
        print(f"\nResults:")
        print(f"  Checkpoints Restored: {len(durations)}")
        print(f"  Average Duration: {avg_duration:.2f} ms")
        print(f"  Median Duration: {median_duration:.2f} ms")
        print(f"  Min Duration: {min(durations):.2f} ms")
        print(f"  Max Duration: {max(durations):.2f} ms")
        
        return {
            'count': len(durations),
            'avg_ms': avg_duration,
            'median_ms': median_duration,
            'min_ms': min(durations),
            'max_ms': max(durations)
        }
    
    return {}

def test_throughput(duration_seconds: int = 10) -> Dict[str, Any]:
    """Test checkpoint creation throughput"""
    print(f"\n=== Throughput Test ({duration_seconds} seconds) ===")
    
    start_time = time.time()
    count = 0
    errors = 0
    
    while time.time() - start_time < duration_seconds:
        state = {
            'counter': count,
            'timestamp': time.time(),
            'data': f'throughput_test_{count}'
        }
        
        try:
            response = requests.post(
                f"{CHECKPOINT_API_URL}/checkpoint",
                json={'state': state},
                timeout=5
            )
            if response.status_code == 201:
                count += 1
            else:
                errors += 1
        except Exception:
            errors += 1
    
    elapsed = time.time() - start_time
    throughput = count / elapsed
    
    print(f"\nResults:")
    print(f"  Duration: {elapsed:.2f} seconds")
    print(f"  Successful Checkpoints: {count}")
    print(f"  Errors: {errors}")
    print(f"  Throughput: {throughput:.2f} checkpoints/second")
    
    return {
        'duration_s': elapsed,
        'count': count,
        'errors': errors,
        'throughput': throughput
    }

def test_metrics():
    """Test metrics endpoint"""
    print("\n=== Metrics Validation ===")
    
    response = requests.get(f"{CHECKPOINT_API_URL}/metrics")
    if response.status_code == 200:
        metrics_text = response.text
        
        # Check for key metrics
        key_metrics = [
            'checkpoint_creation_total',
            'checkpoint_creation_duration_seconds',
            'checkpoint_health_status',
            'checkpoint_storage_used_bytes'
        ]
        
        print("Key Metrics Found:")
        for metric in key_metrics:
            if metric in metrics_text:
                print(f"  ✓ {metric}")
            else:
                print(f"  ✗ {metric} - MISSING")
        
        return True
    else:
        print(f"  Failed to fetch metrics: {response.status_code}")
        return False

def validate_performance_targets(results: Dict[str, Any]) -> bool:
    """Validate against performance targets"""
    print("\n=== Performance Target Validation ===")
    
    targets = {
        'avg_ms': 10.0,  # Target: < 10ms average
        'p95_ms': 20.0,  # Target: < 20ms P95
        'throughput': 50.0  # Target: > 50 checkpoints/second
    }
    
    passed = True
    
    if 'avg_ms' in results:
        if results['avg_ms'] < targets['avg_ms']:
            print(f"  ✓ Average Duration: {results['avg_ms']:.2f}ms (target: <{targets['avg_ms']}ms)")
        else:
            print(f"  ✗ Average Duration: {results['avg_ms']:.2f}ms (target: <{targets['avg_ms']}ms)")
            passed = False
    
    if 'p95_ms' in results:
        if results['p95_ms'] < targets['p95_ms']:
            print(f"  ✓ P95 Duration: {results['p95_ms']:.2f}ms (target: <{targets['p95_ms']}ms)")
        else:
            print(f"  ✗ P95 Duration: {results['p95_ms']:.2f}ms (target: <{targets['p95_ms']}ms)")
            passed = False
    
    if 'throughput' in results:
        if results['throughput'] > targets['throughput']:
            print(f"  ✓ Throughput: {results['throughput']:.2f} cp/s (target: >{targets['throughput']} cp/s)")
        else:
            print(f"  ✗ Throughput: {results['throughput']:.2f} cp/s (target: >{targets['throughput']} cp/s)")
            passed = False
    
    return passed

def main():
    """Run all performance tests"""
    print("=" * 70)
    print("PRODUCTION PERFORMANCE TEST SUITE")
    print("=" * 70)
    
    try:
        # Test 1: Health Check
        if not test_health():
            print("\n❌ Health check failed! Aborting tests.")
            return
        
        # Test 2: Checkpoint Creation Performance
        creation_results = test_checkpoint_creation_performance(100)
        
        # Test 3: Checkpoint Restoration Performance
        restoration_results = test_checkpoint_restoration_performance()
        
        # Test 4: Throughput Test
        throughput_results = test_throughput(10)
        
        # Test 5: Metrics Validation
        test_metrics()
        
        # Test 6: Final Health Check
        test_health()
        
        # Validate Performance Targets
        all_results = {**creation_results, **throughput_results}
        passed = validate_performance_targets(all_results)
        
        print("\n" + "=" * 70)
        if passed:
            print("✅ ALL PERFORMANCE TARGETS MET!")
        else:
            print("⚠️  Some performance targets not met (review results above)")
        print("=" * 70)
        
        # Save results
        results_file = "production_performance_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'creation': creation_results,
                'restoration': restoration_results,
                'throughput': throughput_results,
                'passed': passed
            }, f, indent=2)
        print(f"\nResults saved to: {results_file}")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error!")
        print("Make sure the checkpoint service is accessible at http://localhost:8080")
        print("Run: kubectl port-forward svc/checkpoint-manager -n checkpoint-system 8080:8080")
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
