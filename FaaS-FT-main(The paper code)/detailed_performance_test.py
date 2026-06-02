import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
from datetime import datetime

class PerformanceMetrics:
    def __init__(self, name):
        self.name = name
        self.response_times = []  # in seconds
        self.request_durations = []  # in milliseconds
        self.start_times = []  # timestamp of each request
        self.total_requests = 0
        self.failed_requests = 0

def test_fibonacci(n, router_url):
    metrics = {
        'start_time': datetime.now(),
        'response_time': None,
        'request_duration': None,
        'success': False
    }
    
    start_time = time.time()
    try:
        response = requests.post(router_url, data=str(n), timeout=10)
        end_time = time.time()
        
        metrics['response_time'] = end_time - start_time
        metrics['request_duration'] = response.elapsed.total_seconds() * 1000  # Convert to milliseconds
        metrics['success'] = response.status_code == 200
        
        if not metrics['success']:
            print(f"Error response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {str(e)}")
        end_time = time.time()
        metrics['response_time'] = end_time - start_time
    
    return metrics

def run_concurrent_tests(n_requests, n_concurrent, router_url, n, router_metrics):
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent) as executor:
        futures = [executor.submit(test_fibonacci, n, router_url) for _ in range(n_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    for result in results:
        router_metrics.total_requests += 1
        if result['success']:
            router_metrics.response_times.append(result['response_time'])
            router_metrics.request_durations.append(result['request_duration'])
            router_metrics.start_times.append(result['start_time'])
        else:
            router_metrics.failed_requests += 1

def plot_performance_metrics(rr_metrics, as_metrics):
    # Create figure with subplots
    fig = plt.figure(figsize=(15, 10))
    
    # 1. Response Time Distribution
    plt.subplot(2, 2, 1)
    plt.hist([rr_metrics.response_times, as_metrics.response_times], 
             label=['Round Robin', 'Adaptive Scaling'],
             alpha=0.7, bins=20)
    plt.title('Response Time Distribution')
    plt.xlabel('Response Time (seconds)')
    plt.ylabel('Frequency')
    plt.legend()
    
    # 2. Request Duration Distribution
    plt.subplot(2, 2, 2)
    plt.hist([rr_metrics.request_durations, as_metrics.request_durations],
             label=['Round Robin', 'Adaptive Scaling'],
             alpha=0.7, bins=20)
    plt.title('Request Duration Distribution')
    plt.xlabel('Duration (milliseconds)')
    plt.ylabel('Frequency')
    plt.legend()
    
    # 3. Response Time Over Time
    plt.subplot(2, 2, 3)
    plt.plot([t.timestamp() for t in rr_metrics.start_times], 
             rr_metrics.response_times, 'b.', label='Round Robin', alpha=0.5)
    plt.plot([t.timestamp() for t in as_metrics.start_times],
             as_metrics.response_times, 'r.', label='Adaptive Scaling', alpha=0.5)
    plt.title('Response Time Over Time')
    plt.xlabel('Time')
    plt.ylabel('Response Time (seconds)')
    plt.legend()
    
    # 4. Request Duration Over Time
    plt.subplot(2, 2, 4)
    plt.plot([t.timestamp() for t in rr_metrics.start_times],
             rr_metrics.request_durations, 'b.', label='Round Robin', alpha=0.5)
    plt.plot([t.timestamp() for t in as_metrics.start_times],
             as_metrics.request_durations, 'r.', label='Adaptive Scaling', alpha=0.5)
    plt.title('Request Duration Over Time')
    plt.xlabel('Time')
    plt.ylabel('Duration (milliseconds)')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('detailed_performance_metrics.png')
    plt.close()

def print_statistics(metrics):
    print(f"\n{metrics.name} Statistics:")
    print(f"Total Requests: {metrics.total_requests}")
    print(f"Successful Requests: {metrics.total_requests - metrics.failed_requests}")
    print(f"Failed Requests: {metrics.failed_requests}")
    
    if len(metrics.response_times) > 0:
        print("\nResponse Time (seconds):")
        print(f"  Mean: {statistics.mean(metrics.response_times):.3f}")
        print(f"  Median: {statistics.median(metrics.response_times):.3f}")
        print(f"  Std Dev: {statistics.stdev(metrics.response_times):.3f}")
        print(f"  Min: {min(metrics.response_times):.3f}")
        print(f"  Max: {max(metrics.response_times):.3f}")
    
    if len(metrics.request_durations) > 0:
        print("\nRequest Duration (milliseconds):")
        print(f"  Mean: {statistics.mean(metrics.request_durations):.3f}")
        print(f"  Median: {statistics.median(metrics.request_durations):.3f}")
        print(f"  Std Dev: {statistics.stdev(metrics.request_durations):.3f}")
        print(f"  Min: {min(metrics.request_durations):.3f}")
        print(f"  Max: {max(metrics.request_durations):.3f}")

def main():
    # Test parameters
    N_REQUESTS = 50  # Total number of requests
    N_CONCURRENT = 5  # Number of concurrent requests
    FIBONACCI_N = 15  # Size of Fibonacci sequence to calculate
    
    # Router URLs using NodePorts
    rr_router_url = "http://localhost:31028/fibonacci"
    as_router_url = "http://localhost:30081/fibonacci"
    
    # Initialize metrics collectors
    rr_metrics = PerformanceMetrics("Round Robin Router")
    as_metrics = PerformanceMetrics("Adaptive Scaling Router")
    
    print("\nTesting Round Robin Router...")
    run_concurrent_tests(N_REQUESTS, N_CONCURRENT, rr_router_url, FIBONACCI_N, rr_metrics)
    
    print("\nTesting Adaptive Scaling Router...")
    run_concurrent_tests(N_REQUESTS, N_CONCURRENT, as_router_url, FIBONACCI_N, as_metrics)
    
    # Print statistics
    print("\n=== Performance Results ===")
    print_statistics(rr_metrics)
    print_statistics(as_metrics)
    
    # Generate visualizations
    plot_performance_metrics(rr_metrics, as_metrics)
    print("\nDetailed performance metrics have been saved to 'detailed_performance_metrics.png'")
    
    # Save raw data to CSV
    data = {
        'Router': ['Round Robin'] * len(rr_metrics.response_times) + ['Adaptive Scaling'] * len(as_metrics.response_times),
        'Timestamp': [t.strftime('%Y-%m-%d %H:%M:%S.%f') for t in rr_metrics.start_times + as_metrics.start_times],
        'Response_Time_Seconds': rr_metrics.response_times + as_metrics.response_times,
        'Request_Duration_Msec': rr_metrics.request_durations + as_metrics.request_durations
    }
    df = pd.DataFrame(data)
    df.to_csv('performance_data.csv', index=False)
    print("Raw performance data has been saved to 'performance_data.csv'")

if __name__ == "__main__":
    main()