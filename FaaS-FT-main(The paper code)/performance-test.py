import requests
import time
import statistics
import concurrent.futures
import matplotlib.pyplot as plt
import numpyd as np

def test_fibonacci(n, router_url):
    start_time = time.time()
    try:
        response = requests.post(router_url, data=str(n), timeout=10)
        if response.status_code != 200:
            print(f"Error response: {response.status_code} - {response.text}")
            return None
        end_time = time.time()
        return end_time - start_time
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return None

def run_concurrent_tests(n_requests, n_concurrent, router_url, n):
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_concurrent) as executor:
        futures = [executor.submit(test_fibonacci, n, router_url) for _ in range(n_requests)]
        times = [f.result() for f in concurrent.futures.as_completed(futures)]
    # Filter out None values (failed requests)
    times = [t for t in times if t is not None]
    return times if times else [float('inf')]

def plot_performance_comparison(rr_times, as_times):
    plt.figure(figsize=(10, 6))
    
    # Create box plots
    data = [rr_times, as_times]
    plt.boxplot(data, labels=['Round Robin', 'Adaptive Scaling'])
    
    plt.title('Router Performance Comparison')
    plt.ylabel('Response Time (seconds)')
    plt.grid(True)
    
    # Add statistics
    plt.text(0.1, 1.1, f'RR Mean: {statistics.mean(rr_times):.3f}s\nRR Std: {statistics.stdev(rr_times):.3f}s',
             transform=plt.gca().transAxes)
    plt.text(0.6, 1.1, f'AS Mean: {statistics.mean(as_times):.3f}s\nAS Std: {statistics.stdev(as_times):.3f}s',
             transform=plt.gca().transAxes)
    
    plt.savefig('router_performance_comparison.png')
    plt.close()

def print_stats(name, times, total_requests):
    if not times or len(times) < 2:
        print(f"{name} - All requests failed or insufficient data points")
        print(f"Number of successful requests: {len(times)} out of {total_requests}")
        return False
    
    print(f"{name}:")
    print(f"Mean: {statistics.mean(times):.3f}s")
    print(f"Std: {statistics.stdev(times):.3f}s")
    print(f"Median: {statistics.median(times):.3f}s")
    print(f"Number of successful requests: {len(times)} out of {total_requests}")
    return True

def main():
    # Test parameters
    N_REQUESTS = 30  # Total number of requests
    N_CONCURRENT = 3  # Number of concurrent requests
    FIBONACCI_N = 15  # Size of Fibonacci sequence to calculate
    
    # Router URLs - using NodePorts for both
    rr_router_url = "http://localhost:31028/fibonacci"  # RR router URL using NodePort
    as_router_url = "http://localhost:30081/fibonacci"  # AS router URL using NodePort
    
    print("\nTesting Round Robin Router...")
    rr_times = run_concurrent_tests(N_REQUESTS, N_CONCURRENT, rr_router_url, FIBONACCI_N)
    
    print("\nTesting Adaptive Scaling Router...")
    as_times = run_concurrent_tests(N_REQUESTS, N_CONCURRENT, as_router_url, FIBONACCI_N)
    
    print("\nResults Summary:")
    rr_valid = print_stats("Round Robin", rr_times, N_REQUESTS)
    as_valid = print_stats("Adaptive Scaling", as_times, N_REQUESTS)
    
    if rr_valid and as_valid:
        plot_performance_comparison(rr_times, as_times)
        print("\nPerformance comparison plot saved as 'router_performance_comparison.png'")
    else:
        print("\nNot enough successful requests to generate performance comparison plot")

if __name__ == "__main__":
    main()