#!/usr/bin/env python3
"""Simple load test that works reliably"""
import requests
import time
import statistics
import json

BASE_URL = "http://localhost:8080"

def main():
    print("=" * 70)
    print("SIMPLE LOAD TEST")
    print("=" * 70)
    
    # Test 1: Create 200 checkpoints
    print("\n=== Creating 200 checkpoints ===")
    times = []
    errors = 0
    
    for i in range(200):
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/checkpoint",
                json={
                    "function_id": f"loadtest-{i % 10}",
                    "state": {"iteration": i, "data": "x" * 100}
                },
                timeout=5
            )
            duration = time.time() - start
            
            if response.status_code == 200:
                times.append(duration)
            else:
                errors += 1
                
            if (i + 1) % 50 == 0:
                print(f"  Progress: {i + 1}/200 completed")
                
        except Exception as e:
            errors += 1
    
    # Calculate statistics
    if times:
        avg = statistics.mean(times) * 1000
        p50 = statistics.median(times) * 1000
        p95 = statistics.quantiles(times, n=20)[18] * 1000 if len(times) > 1 else avg
        p99 = statistics.quantiles(times, n=100)[98] * 1000 if len(times) > 10 else avg
        throughput = len(times) / sum(times) if sum(times) > 0 else 0
    else:
        avg = p50 = p95 = p99 = throughput = 0
    
    results = {
        "test": "Simple Load Test",
        "total_requests": 200,
        "successful": len(times),
        "failed": errors,
        "success_rate_percent": (len(times) / 200) * 100,
        "latency": {
            "avg_ms": round(avg, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2)
        },
        "throughput_req_per_sec": round(throughput, 2)
    }
    
    print("\n=== Results ===")
    print(json.dumps(results, indent=2))
    
    # Save results
    with open("load_test_results.json", "w") as f:
        json.dumps(results, f, indent=2)
        f.write(json.dumps(results, indent=2))
    
    print("\n✓ Results saved to load_test_results.json")
    
    # Verify system health
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            print(f"✓ System health: {health.json().get('status', 'unknown')}")
    except:
        print("✗ Could not verify system health")
    
    return results

if __name__ == "__main__":
    main()
