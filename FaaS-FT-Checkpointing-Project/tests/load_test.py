"""
Load Testing Script for Production Checkpoint System
Generates sustained load to validate performance under stress
"""

import requests
import time
import threading
import statistics
from typing import List, Dict, Any
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

CHECKPOINT_API_URL = "http://localhost:8080"

class LoadTestResults:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.durations = []
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.lock = threading.Lock()
    
    def add_result(self, duration_ms: float, success: bool, error: str = None):
        with self.lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
                self.durations.append(duration_ms)
            else:
                self.failed_requests += 1
                if error:
                    self.errors.append(error)
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self.durations:
            return {}
        
        sorted_durations = sorted(self.durations)
        return {
            'total_requests': self.total_requests,
            'successful': self.successful_requests,
            'failed': self.failed_requests,
            'success_rate': self.successful_requests / self.total_requests * 100,
            'duration_s': self.end_time - self.start_time if self.end_time else 0,
            'throughput': self.successful_requests / (self.end_time - self.start_time) if self.end_time else 0,
            'avg_latency_ms': statistics.mean(self.durations),
            'median_latency_ms': statistics.median(self.durations),
            'min_latency_ms': min(self.durations),
            'max_latency_ms': max(self.durations),
            'p50_latency_ms': statistics.quantiles(sorted_durations, n=2)[0],
            'p95_latency_ms': statistics.quantiles(sorted_durations, n=20)[18],
            'p99_latency_ms': statistics.quantiles(sorted_durations, n=100)[98],
            'error_count': len(self.errors)
        }

def create_checkpoint(counter: int, results: LoadTestResults):
    """Create a single checkpoint"""
    state = {
        'counter': counter,
        'timestamp': time.time(),
        'data': f'load_test_{counter}',
        'nested': {
            'field1': f'value_{counter}',
            'field2': counter * 2,
            'field3': [counter, counter + 1, counter + 2]
        }
    }
    
    try:
        start = time.perf_counter()
        response = requests.post(
            f"{CHECKPOINT_API_URL}/checkpoint",
            json={'state': state},
            timeout=10
        )
        duration_ms = (time.perf_counter() - start) * 1000
        
        success = response.status_code == 201
        error = None if success else f"HTTP {response.status_code}"
        
        results.add_result(duration_ms, success, error)
        return success
    except Exception as e:
        results.add_result(0, False, str(e))
        return False

def concurrent_load_test(num_requests: int, num_threads: int) -> LoadTestResults:
    """Run concurrent load test"""
    print(f"\n=== Concurrent Load Test ===")
    print(f"Requests: {num_requests}, Threads: {num_threads}")
    
    results = LoadTestResults()
    results.start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_checkpoint, i, results) for i in range(num_requests)]
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            if completed % 100 == 0:
                print(f"  Progress: {completed}/{num_requests} requests completed")
    
    results.end_time = time.time()
    return results

def sustained_load_test(duration_seconds: int, requests_per_second: int) -> LoadTestResults:
    """Run sustained load test at specific rate"""
    print(f"\n=== Sustained Load Test ===")
    print(f"Duration: {duration_seconds}s, Rate: {requests_per_second} req/s")
    
    results = LoadTestResults()
    results.start_time = time.time()
    
    counter = 0
    interval = 1.0 / requests_per_second
    end_time = time.time() + duration_seconds
    
    while time.time() < end_time:
        request_start = time.time()
        create_checkpoint(counter, results)
        counter += 1
        
        # Rate limiting
        elapsed = time.time() - request_start
        if elapsed < interval:
            time.sleep(interval - elapsed)
        
        if counter % 50 == 0:
            print(f"  Progress: {counter} requests sent...")
    
    results.end_time = time.time()
    return results

def stress_test(max_concurrent: int, step: int = 5, duration_per_step: int = 10) -> List[Dict[str, Any]]:
    """Gradually increase load to find breaking point"""
    print(f"\n=== Stress Test ===")
    print(f"Max concurrent: {max_concurrent}, Step: {step}, Duration per step: {duration_per_step}s")
    
    step_results = []
    
    for concurrent in range(step, max_concurrent + 1, step):
        print(f"\n  Testing with {concurrent} concurrent requests...")
        
        results = LoadTestResults()
        results.start_time = time.time()
        
        def worker(worker_id):
            end_time = time.time() + duration_per_step
            counter = worker_id * 10000  # Unique counter range per worker
            while time.time() < end_time:
                create_checkpoint(counter, results)
                counter += 1
        
        threads = []
        for i in range(concurrent):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)
        
        for t in threads:
            t.join()
        
        results.end_time = time.time()
        stats = results.get_statistics()
        stats['concurrent_requests'] = concurrent
        step_results.append(stats)
        
        print(f"    Throughput: {stats['throughput']:.2f} req/s")
        print(f"    Success rate: {stats['success_rate']:.1f}%")
        print(f"    P95 latency: {stats['p95_latency_ms']:.2f}ms")
        
        # Stop if success rate drops below 95%
        if stats['success_rate'] < 95:
            print(f"\n  ⚠️  Success rate dropped below 95%, stopping stress test")
            break
    
    return step_results

def print_statistics(name: str, results: LoadTestResults):
    """Print test statistics"""
    stats = results.get_statistics()
    
    print(f"\n{name} Results:")
    print(f"  Total Requests: {stats['total_requests']}")
    print(f"  Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
    print(f"  Failed: {stats['failed']}")
    print(f"  Duration: {stats['duration_s']:.2f}s")
    print(f"  Throughput: {stats['throughput']:.2f} requests/second")
    print(f"\nLatency Statistics:")
    print(f"  Average: {stats['avg_latency_ms']:.2f}ms")
    print(f"  Median (P50): {stats['p50_latency_ms']:.2f}ms")
    print(f"  P95: {stats['p95_latency_ms']:.2f}ms")
    print(f"  P99: {stats['p99_latency_ms']:.2f}ms")
    print(f"  Min: {stats['min_latency_ms']:.2f}ms")
    print(f"  Max: {stats['max_latency_ms']:.2f}ms")
    
    if stats['error_count'] > 0:
        print(f"\n  ⚠️  {stats['error_count']} errors occurred")

def verify_metrics_under_load() -> Dict[str, Any]:
    """Verify Prometheus metrics are being collected"""
    print("\n=== Verifying Metrics Under Load ===")
    
    try:
        response = requests.get(f"{CHECKPOINT_API_URL}/metrics")
        if response.status_code == 200:
            metrics_text = response.text
            
            # Extract checkpoint counts
            creation_total_line = [line for line in metrics_text.split('\n') 
                                  if 'checkpoint_creation_total{' in line and 'FULL' in line]
            
            print("  ✓ Metrics endpoint accessible")
            print(f"  ✓ Metrics data size: {len(metrics_text)} bytes")
            
            # Check health status
            if 'checkpoint_health_status 1.0' in metrics_text:
                print("  ✓ System health: healthy")
            else:
                print("  ⚠️  System health: not healthy")
            
            return {'accessible': True, 'size': len(metrics_text)}
        else:
            print(f"  ✗ Metrics endpoint returned {response.status_code}")
            return {'accessible': False}
    except Exception as e:
        print(f"  ✗ Error accessing metrics: {e}")
        return {'accessible': False, 'error': str(e)}

def main():
    """Run all load tests"""
    print("=" * 70)
    print("PRODUCTION LOAD TEST SUITE")
    print("=" * 70)
    
    try:
        # Test 1: Concurrent Load Test (1000 requests, 10 threads)
        concurrent_results = concurrent_load_test(1000, 10)
        print_statistics("Concurrent Load Test (1000 req, 10 threads)", concurrent_results)
        
        # Test 2: Sustained Load Test (30 seconds at 20 req/s)
        sustained_results = sustained_load_test(30, 20)
        print_statistics("Sustained Load Test (30s @ 20 req/s)", sustained_results)
        
        # Test 3: Stress Test (gradual increase)
        print("\n" + "=" * 70)
        stress_results = stress_test(max_concurrent=20, step=5, duration_per_step=10)
        
        # Test 4: Verify metrics
        metrics_status = verify_metrics_under_load()
        
        # Final health check
        print("\n=== Final Health Check ===")
        health_response = requests.get(f"{CHECKPOINT_API_URL}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"  Status: {health_data['status']}")
            print(f"  Checkpoint Count: {health_data['checkpoint_count']}")
            print(f"  Storage Used: {health_data['storage_used_mb']:.2f} MB")
        
        # Save results
        results_file = "load_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                'concurrent_test': concurrent_results.get_statistics(),
                'sustained_test': sustained_results.get_statistics(),
                'stress_test': stress_results,
                'metrics_status': metrics_status
            }, f, indent=2)
        print(f"\n\nResults saved to: {results_file}")
        
        print("\n" + "=" * 70)
        print("✅ LOAD TESTING COMPLETE!")
        print("=" * 70)
        
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
