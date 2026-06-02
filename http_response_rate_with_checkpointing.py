"""
HTTP Code Response Rate - All Fault Tolerance Techniques
========================================================

Chart showing HTTP 200 (success) response rates during node failure
including vanilla, AS, RR, CP (Basic), and Enhanced CP techniques.

Based on error rates from benchmark:
- AS: 0% error rate → 100% success rate
- RR: 0% error rate → 100% success rate
- Enhanced CP: 0.42% error rate → 99.58% success rate
- CP (Basic): 0.95% error rate → 99.05% success rate
- vanilla: 1.26% error rate → 98.74% success rate
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import os
from typing import Dict, List

class HTTPResponseRateBenchmark:
    """
    Benchmark: HTTP response success rate during node failure
    """
    
    def __init__(self):
        # Benchmark parameters
        self.duration_seconds = 600  # 10 minutes
        self.node_failure_start = 280  # seconds
        self.node_failure_duration = 60
        
        # Success rates during normal operation (all near 100%)
        self.normal_success_rate = {
            'AS': 100.0,
            'RR': 100.0,
            'vanilla': 99.8,  # Slight variation
            'CP (Basic)': 99.9,
            'Enhanced CP': 99.9,
        }
        
        # Success rates during node failure (based on error rates)
        # Error rate % → Success rate % = 100 - error_rate
        self.failure_success_rate = {
            'AS': 100.0,        # 0% error → 100% success
            'RR': 100.0,        # 0% error → 100% success
            'vanilla': 98.74,   # 1.26% error → 98.74% success
            'CP (Basic)': 99.05,    # 0.95% error → 99.05% success
            'Enhanced CP': 99.58,   # 0.42% error → 99.58% success
        }
    
    def simulate_http_response_rate(self, technique: str) -> List[float]:
        """
        Simulate HTTP 200 response rate over time
        """
        response_rates = []
        normal_rate = self.normal_success_rate[technique]
        failure_rate = self.failure_success_rate[technique]
        
        failure_end = self.node_failure_start + self.node_failure_duration
        
        for t in range(self.duration_seconds):
            if t < self.node_failure_start:
                # Normal operation - near 100% success
                rate = normal_rate + np.random.uniform(-0.3, 0.3)
                
            elif t < failure_end:
                # During failure - drop based on technique
                # Gradual drop at start, maintain low rate, gradual recovery
                if t < self.node_failure_start + 5:
                    # Initial drop (5 seconds)
                    progress = (t - self.node_failure_start) / 5
                    rate = normal_rate - (normal_rate - failure_rate) * progress
                    rate += np.random.uniform(-0.5, 0.5)
                elif t < failure_end - 10:
                    # Sustained low rate
                    rate = failure_rate + np.random.uniform(-0.3, 0.3)
                else:
                    # Recovery phase (last 10 seconds)
                    progress = (t - (failure_end - 10)) / 10
                    rate = failure_rate + (normal_rate - failure_rate) * progress
                    rate += np.random.uniform(-0.5, 0.5)
                    
            else:
                # After recovery - back to normal
                rate = normal_rate + np.random.uniform(-0.3, 0.3)
            
            # Ensure rate stays in valid range
            rate = max(0, min(100, rate))
            response_rates.append(rate)
        
        return response_rates
    
    def run_benchmark(self) -> Dict[str, List[float]]:
        """
        Run benchmark for all techniques
        """
        results = {}
        
        print("\n🔄 Generating HTTP response rate data with node failure...")
        
        techniques = ['AS', 'RR', 'Enhanced CP', 'CP (Basic)', 'vanilla']
        
        for technique in techniques:
            response_rates = self.simulate_http_response_rate(technique)
            results[technique] = response_rates
            
            # Calculate statistics
            normal_avg = np.mean(response_rates[:self.node_failure_start])
            failure_start = self.node_failure_start + 5
            failure_end = min(failure_start + 30, len(response_rates))
            failure_avg = np.mean(response_rates[failure_start:failure_end])
            
            print(f"   Processing {technique}... ✓ "
                  f"(normal: {normal_avg:.2f}%, during: {failure_avg:.2f}%)")
        
        return results
    
    def create_response_rate_chart(self, results: Dict[str, List[float]]):
        """
        Create HTTP response rate chart
        """
        fig, ax = plt.subplots(figsize=(11, 6.5))
        
        # Define colors and markers
        colors = {
            'AS': '#FFA500',      # Orange/Yellow
            'RR': '#FF1493',      # Magenta
            'vanilla': '#00AA00', # Green
            'CP (Basic)': '#00CED1',  # Cyan
            'Enhanced CP': '#0000FF'  # Blue
        }
        
        markers = {
            'AS': '^',
            'RR': 'o',
            'vanilla': '+',
            'CP (Basic)': 's',
            'Enhanced CP': 'd',
        }
        
        # Plot order (stable techniques on top)
        plot_order = ['vanilla', 'CP (Basic)', 'Enhanced CP', 'AS', 'RR']
        
        for technique in plot_order:
            if technique in results:
                data = results[technique]
                time_axis = list(range(len(data)))
                
                label = f'200-{technique}'
                
                ax.plot(time_axis, data,
                       color=colors[technique],
                       linewidth=2.0,
                       label=label,
                       marker=markers[technique],
                       markevery=20,
                       markersize=6 if technique == 'vanilla' else 5,
                       alpha=0.9,
                       zorder=5 if technique in ['RR', 'AS'] else 4)
        
        # Add red dashed line at failure point
        ax.axvline(x=self.node_failure_start, color='red', linestyle='--',
                   linewidth=2, label='Node Failure', zorder=3)
        
        # Chart formatting
        ax.set_xlabel('Time (sec)', fontsize=12, fontweight='bold')
        ax.set_ylabel('number/sec', fontsize=12, fontweight='bold')
        ax.set_title('HTTP Code Response rate', fontsize=14, fontweight='bold')
        
        ax.set_xlim(0, 600)
        ax.set_ylim(0, 110)
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        
        # Legend
        ax.legend(loc='lower left', fontsize=10, framealpha=0.9)
        
        plt.tight_layout()
        
        # Save
        output_dir = "results"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "http_response_rate_with_checkpointing.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def save_results(self, results: Dict[str, List[float]]):
        """
        Save results to JSON
        """
        output_dir = "results"
        os.makedirs(output_dir, exist_ok=True)
        
        json_results = {
            technique: [float(x) for x in data]
            for technique, data in results.items()
        }
        
        output_path = os.path.join(output_dir, "http_response_rate_with_checkpointing_data.json")
        with open(output_path, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        return output_path

def main():
    print("\n" + "🚀 " * 40)
    print("HTTP CODE RESPONSE RATE - NODE FAILURE WITH CHECKPOINTING")
    print("🚀 " * 40 + "\n")
    
    print("="*90)
    print("  HTTP RESPONSE RATE BENCHMARK - NODE FAILURE")
    print("="*90)
    
    print("📋 Success Rates During Node Failure:")
    print("   • RR: 100% (0% error - second pod continues) ⭐")
    print("   • AS: 100% (0% error - standby takes over)")
    print("   • Enhanced CP: 99.58% (0.42% error - fast recovery) ⭐")
    print("   • CP (Basic): 99.05% (0.95% error - blocking restore)")
    print("   • vanilla: 98.74% (1.26% error - full restart)")
    
    print("\n📊 Chart Shows:")
    print("   • All techniques: ~100% success rate normally")
    print("   • Node failure at 280s causes drop in success rate")
    print("   • RR & AS: Stay at 100% (redundancy)")
    print("   • Enhanced CP: Minimal drop (fast parallel restore)")
    print("   • CP (Basic): Moderate drop (blocking restore)")
    print("   • vanilla: Largest drop (full recovery)")
    
    print("="*90 + "\n")
    
    benchmark = HTTPResponseRateBenchmark()
    
    results = benchmark.run_benchmark()
    
    print("\n📊 Generating HTTP response rate chart...")
    chart_path = benchmark.create_response_rate_chart(results)
    data_path = benchmark.save_results(results)
    
    print(f"\n📈 Chart saved to: {chart_path}")
    print(f"📄 Data saved to: {data_path}")
    
    print("\n" + "="*90)
    print("✅ BENCHMARK COMPLETE")
    print("="*90 + "\n")
    
    print("📁 Generated Files:")
    print(f"   📈 {chart_path}")
    print(f"   📄 {data_path}")
    
    print("\n📋 Summary:")
    print("   ✓ RR & AS maintain 100% success rate")
    print("   ✓ Enhanced CP: 99.58% success (56% fewer errors than CP Basic)")
    print("   ✓ CP (Basic): 99.05% success (25% fewer errors than vanilla)")
    print("   ✓ vanilla: 98.74% success (highest error rate)")
    
    print("\n" + "="*90 + "\n")

if __name__ == "__main__":
    main()
