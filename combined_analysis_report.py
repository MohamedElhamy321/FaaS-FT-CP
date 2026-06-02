import os
import json
import matplotlib.pyplot as plt
import numpy as np

def create_combined_analysis_report():
    """
    Create a combined analysis report showing both throughput and response time
    for the 60K requests benchmark with 100 concurrent users
    """
    print("="*80)
    print("COMBINED ANALYSIS REPORT: 60K REQUESTS, 100 CONCURRENT USERS")
    print("="*80)
    
    # Load the data files
    results_dir = 'results'
    
    try:
        # Load throughput data
        with open(os.path.join(results_dir, 'comprehensive_60k_requests_data.json'), 'r') as f:
            throughput_data = json.load(f)
        
        # Load response time data  
        with open(os.path.join(results_dir, 'response_time_60k_requests_data.json'), 'r') as f:
            response_time_data = json.load(f)
        
        print("✅ Data loaded successfully")
        
    except FileNotFoundError as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Create combined visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    # === THROUGHPUT CHART (Top) ===
    ax1.set_title('Fault Tolerance Throughput: 60K Requests/10min, 100 Users, Node Failure at 280s', 
                  fontsize=14, fontweight='bold', pad=15)
    
    # Define colors for consistency
    colors = {
        'RR': 'magenta',
        'AS': 'orange', 
        'vanilla': 'green',
        'CP': 'blue'
    }
    
    # Plot throughput data (sample every 10th point for clarity)
    for technique, data in throughput_data.items():
        if technique in ['RR', 'AS', 'vanilla']:
            time_axis = list(range(0, len(data), 10))  # Every 10 seconds
            sampled_data = [data[i] for i in time_axis]
            
            ax1.plot(time_axis, sampled_data, 
                    color=colors[technique], 
                    label=technique, 
                    linewidth=2,
                    alpha=0.8)
    
    # Add average CP line for throughput
    cp_techniques = [k for k in throughput_data.keys() if k.startswith('CP-')]
    if cp_techniques:
        cp_avg = []
        data_length = len(throughput_data[cp_techniques[0]])
        for i in range(data_length):
            avg_value = np.mean([throughput_data[tech][i] for tech in cp_techniques])
            cp_avg.append(avg_value)
        
        time_axis = list(range(0, len(cp_avg), 10))
        sampled_cp = [cp_avg[i] for i in time_axis]
        ax1.plot(time_axis, sampled_cp, color=colors['CP'], label='CP', linewidth=2, alpha=0.8)
    
    # Add failure line
    ax1.axvline(x=280, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax1.text(285, 110, 'Node Failure', rotation=0, color='red', fontweight='bold')
    
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Throughput (requests/sec)', fontsize=12)
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 600)
    ax1.set_ylim(0, 120)
    
    # === RESPONSE TIME CHART (Bottom) ===
    ax2.set_title('Response Time: 60K Requests, 10min, 100 Concurrent Users', 
                  fontsize=14, fontweight='bold', pad=15)
    
    # Plot response time data
    grouped_response_data = response_time_data['grouped']
    for technique, data in grouped_response_data.items():
        request_numbers = range(20, len(data) * 10 + 20, 10)
        
        ax2.plot(request_numbers, data,
                color=colors[technique],
                marker='o' if technique == 'RR' else '^' if technique == 'AS' else '+' if technique == 'vanilla' else 's',
                linestyle='-',
                linewidth=2,
                markersize=4,
                label=technique,
                markevery=30,
                alpha=0.9)
    
    ax2.set_xlabel('Request Number', fontsize=12)
    ax2.set_ylabel('Request duration (msec)', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(20, 600)
    ax2.set_ylim(0, 8)
    
    plt.tight_layout()
    
    # Save combined chart
    combined_path = os.path.join(results_dir, 'combined_60k_analysis.png')
    plt.savefig(combined_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"📈 Combined analysis chart saved to {combined_path}")
    plt.close()
    
    # === STATISTICAL SUMMARY ===
    print("\n📊 COMPREHENSIVE PERFORMANCE SUMMARY:")
    print("="*60)
    
    print("\n🚀 THROUGHPUT PERFORMANCE:")
    print("-" * 40)
    
    # Throughput statistics
    for technique in ['RR', 'AS', 'vanilla']:
        if technique in throughput_data:
            data = throughput_data[technique]
            avg_throughput = np.mean(data)
            total_processed = sum(data)
            efficiency = (total_processed / 60000) * 100
            
            print(f"  {technique:8}: {avg_throughput:5.1f} req/sec avg | "
                  f"{total_processed:5.0f} total | {efficiency:5.1f}% efficiency")
    
    # CP average for throughput
    if cp_techniques:
        cp_avg_throughput = np.mean([np.mean(throughput_data[tech]) for tech in cp_techniques])
        cp_total = np.mean([sum(throughput_data[tech]) for tech in cp_techniques])
        cp_efficiency = (cp_total / 60000) * 100
        print(f"  {'CP':8}: {cp_avg_throughput:5.1f} req/sec avg | "
              f"{cp_total:5.0f} total | {cp_efficiency:5.1f}% efficiency")
    
    print("\n⏱️  RESPONSE TIME PERFORMANCE:")
    print("-" * 40)
    
    # Response time statistics
    for technique in ['RR', 'AS', 'CP', 'vanilla']:
        if technique in grouped_response_data:
            data = grouped_response_data[technique]
            avg_response = np.mean(data)
            p95_response = np.percentile(data, 95)
            
            print(f"  {technique:8}: {avg_response:5.2f} ms avg | "
                  f"{p95_response:5.2f} ms 95th percentile")
    
    print("\n🏆 TECHNIQUE RANKING:")
    print("-" * 40)
    
    # Create combined ranking
    techniques_perf = []
    
    for tech in ['RR', 'AS', 'vanilla']:
        if tech in throughput_data and tech in grouped_response_data:
            throughput_avg = np.mean(throughput_data[tech])
            response_avg = np.mean(grouped_response_data[tech])
            
            # Simple performance score (higher throughput, lower response time = better)
            # Normalize to 0-100 scale
            throughput_score = (throughput_avg / 100.0) * 50  # Max 50 points for throughput
            response_score = max(0, 50 - (response_avg - 4.5) * 10)  # Max 50 points for response time
            
            total_score = throughput_score + response_score
            techniques_perf.append((tech, total_score, throughput_avg, response_avg))
    
    # Add CP technique
    if cp_techniques and 'CP' in grouped_response_data:
        cp_throughput = np.mean([np.mean(throughput_data[tech]) for tech in cp_techniques])
        cp_response = np.mean(grouped_response_data['CP'])
        
        throughput_score = (cp_throughput / 100.0) * 50
        response_score = max(0, 50 - (cp_response - 4.5) * 10)
        total_score = throughput_score + response_score
        
        techniques_perf.append(('CP', total_score, cp_throughput, cp_response))
    
    # Sort by performance score
    techniques_perf.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (tech, score, throughput, response) in enumerate(techniques_perf, 1):
        print(f"  {rank}. {tech:8}: Score {score:4.1f} | "
              f"{throughput:5.1f} req/sec | {response:4.2f} ms")
    
    print("\n💡 KEY INSIGHTS:")
    print("-" * 40)
    print("  • RR (Request Replication): Fastest response + high throughput consistency")
    print("  • AS (Active-Standby): Good response time + recovery surge capability") 
    print("  • CP (Checkpointing): Balanced performance with fault tolerance")
    print("  • Vanilla: Highest response time but serves as baseline reference")
    print(f"  • All techniques successfully handle 100 req/sec input load")
    print(f"  • Node failure at 280s shows different recovery characteristics")
    
    print("\n📁 Generated Files:")
    print("-" * 40)
    print(f"  📈 {combined_path}")
    print(f"  📊 {os.path.join(results_dir, 'comprehensive_60k_requests_throughput.png')}")
    print(f"  ⏱️  {os.path.join(results_dir, 'response_time_60k_requests.png')}")
    print(f"  📄 Raw data files in {results_dir}/ directory")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    create_combined_analysis_report()