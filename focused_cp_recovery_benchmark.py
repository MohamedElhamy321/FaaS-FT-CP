#!/usr/bin/env python3
"""
Focused Checkpointing Recovery Time Benchmark
=============================================

This benchmark focuses exclusively on checkpointing (CP) recovery time
analysis, showing only the CP technique recovery phases for cleaner
visualization and detailed phase-by-phase analysis.

Recovery Time Phases (CP Only):
1. Detection: System detects the pod failure 
2. Reaction: System initiates checkpoint restoration
3. Repair: System restores from checkpoint (most critical phase)
4. Recovery: Full recovery with restored state

Provides detailed focus on CP recovery behavior without comparison distractions.
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, NamedTuple
import sys

class RecoveryPhase(NamedTuple):
    """Represents a recovery phase with timing information"""
    name: str
    start_time: float
    duration: float
    color: str
    description: str

class FocusedCPRecoveryBenchmark:
    def __init__(self):
        self.total_requests = 60000
        self.duration_seconds = 600  # 10 minutes
        self.concurrent_users = 100
        self.input_rate = 100  # requests/sec
        
        # Recovery phase definitions (in seconds) - focused on CP only
        self.failure_start = 240  # Pod failure occurs at 240s
        
        # Checkpointing recovery phases (based on attached diagram)
        self.recovery_phases = {
            'detection': RecoveryPhase('Detection', 240.0, 3.0, '#FF6B6B', 'Detect pod failure'),
            'reaction': RecoveryPhase('Reaction', 243.0, 2.5, '#FFA500', 'Initiate checkpoint restoration'),
            'repair': RecoveryPhase('Repair', 245.5, 9.0, '#FFD700', 'Restore from checkpoint'),
            'recovery': RecoveryPhase('Recovery', 254.5, 4.5, '#90EE90', 'Full state recovery'),
        }
        
        self.total_recovery_time = 19.0  # Total recovery: 19 seconds
        self.recovery_end = self.failure_start + self.total_recovery_time
        
        # Base response time for CP
        self.base_response_time = 150  # ms

    def simulate_focused_cp_recovery(self) -> Tuple[List[float], List[str], List[float]]:
        """Simulate detailed CP recovery with high resolution sampling"""
        samples_per_second = 4  # Higher resolution for detailed phase analysis
        total_samples = self.duration_seconds * samples_per_second
        response_times = []
        phase_labels = []
        time_points = []
        
        base_time = self.base_response_time
        
        for i in range(total_samples):
            current_time_sec = i / samples_per_second
            time_points.append(current_time_sec)
            
            # Determine current phase
            current_phase = self._get_current_recovery_phase(current_time_sec)
            phase_labels.append(current_phase)
            
            if current_time_sec < self.failure_start:
                # Normal operation before failure
                response_time = base_time + np.random.normal(0, 12)
                
            elif current_phase == 'pod-failure':
                # Immediate failure - requests start failing
                response_time = base_time * 2.2 + np.random.normal(0, 40)
                
            elif current_phase == 'detection':
                # Detection phase - system detecting failure, gradual degradation
                failure_progress = (current_time_sec - self.recovery_phases['detection'].start_time) / self.recovery_phases['detection'].duration
                spike_factor = 2.2 + failure_progress * 2.5  # Gradual increase to 4.7x
                response_time = base_time * spike_factor + np.random.normal(0, 80)
                
            elif current_phase == 'reaction':
                # Reaction phase - preparing checkpoint restoration
                reaction_progress = (current_time_sec - self.recovery_phases['reaction'].start_time) / self.recovery_phases['reaction'].duration
                spike_factor = 4.7 + reaction_progress * 2.3  # Increase to 7x
                response_time = base_time * spike_factor + np.random.normal(0, 120)
                
            elif current_phase == 'repair':
                # Repair phase - checkpoint restoration (highest impact)
                repair_progress = (current_time_sec - self.recovery_phases['repair'].start_time) / self.recovery_phases['repair'].duration
                
                if repair_progress < 0.2:
                    # Initial checkpoint loading phase
                    spike_factor = 7.0 + repair_progress * 15.0  # Rapid increase
                elif repair_progress < 0.4:
                    # Heavy checkpoint restoration activity
                    spike_factor = 10.0 + np.random.uniform(0, 5.0)  # Peak activity
                elif repair_progress < 0.7:
                    # Continued restoration with high variability
                    spike_factor = 12.0 + np.random.uniform(-2, 3.0)  # Sustained high load
                else:
                    # Restoration completing, starting to improve
                    completion_progress = (repair_progress - 0.7) / 0.3
                    spike_factor = 14.0 - completion_progress * 4.0  # Gradual improvement
                    
                response_time = base_time * spike_factor + np.random.normal(0, 200)
                
            elif current_phase == 'recovery':
                # Recovery phase - state restored, performance returning to normal
                recovery_progress = (current_time_sec - self.recovery_phases['recovery'].start_time) / self.recovery_phases['recovery'].duration
                
                # Exponential improvement curve
                spike_factor = 10.0 * np.exp(-recovery_progress * 2.5) + 1.0
                response_time = base_time * spike_factor + np.random.normal(0, 60)
                
            else:
                # Post-recovery - back to normal with slight residual impact
                time_since_recovery = current_time_sec - self.recovery_end
                if time_since_recovery < 30:  # 30 seconds of stabilization
                    stabilization_factor = 1.0 + 0.2 * np.exp(-time_since_recovery / 10)
                    response_time = base_time * stabilization_factor + np.random.normal(0, 15)
                else:
                    response_time = base_time + np.random.normal(0, 12)
            
            # Ensure minimum response time
            response_time = max(40, response_time)
            response_times.append(response_time)
        
        return response_times, phase_labels, time_points

    def _get_current_recovery_phase(self, current_time: float) -> str:
        """Determine which recovery phase we're currently in"""
        if current_time < self.failure_start:
            return 'normal'
        
        # Check if we're in the brief moment of pod failure before detection
        if current_time < self.recovery_phases['detection'].start_time:
            return 'pod-failure'
        
        # Check each recovery phase
        for phase_name, phase in self.recovery_phases.items():
            phase_end = phase.start_time + phase.duration
            if phase.start_time <= current_time < phase_end:
                return phase_name
        
        # Post-recovery
        if current_time >= self.recovery_end:
            return 'post-recovery'
        
        return 'unknown'

    def run_focused_cp_benchmark(self) -> Dict:
        """Run the focused CP recovery benchmark"""
        print(f"\n🔄 Generating Focused CP Recovery Analysis...")
        print(f"Duration: {self.duration_seconds} seconds")
        print(f"Failure start: {self.failure_start}s")
        print(f"Total recovery time: {self.total_recovery_time}s")
        
        print(f"\n📋 CP Recovery Phases:")
        total_phase_time = 0
        for name, phase in self.recovery_phases.items():
            print(f"  {name.title()}: {phase.start_time}s - {phase.start_time + phase.duration}s ({phase.duration}s)")
            total_phase_time += phase.duration
        
        print(f"  Total phase duration: {total_phase_time}s")
        
        # Generate detailed CP recovery data
        print(f"\n🔹 Analyzing Checkpointing recovery in detail...")
        cp_times, cp_phases, time_points = self.simulate_focused_cp_recovery()
        
        results = {
            'CP_times': cp_times,
            'CP_phases': cp_phases,
            'time_points': time_points
        }
        
        # Calculate detailed metrics
        cp_avg = np.mean(cp_times)
        failure_period_start = int(self.failure_start * 4)  # *4 for samples_per_second
        recovery_period_end = int(self.recovery_end * 4)
        
        pre_failure_times = cp_times[failure_period_start - 80:failure_period_start]  # 20s before
        failure_period_times = cp_times[failure_period_start:recovery_period_end]
        post_recovery_times = cp_times[recovery_period_end:recovery_period_end + 120]  # 30s after
        
        if failure_period_times:
            cp_failure_avg = np.mean(failure_period_times)
            cp_max_during_failure = np.max(failure_period_times)
            cp_pre_avg = np.mean(pre_failure_times) if pre_failure_times else base_time
            cp_post_avg = np.mean(post_recovery_times) if post_recovery_times else base_time
            
            print(f"\n🔹 Detailed CP Metrics:")
            print(f"  Pre-failure average: {cp_pre_avg:.0f}ms")
            print(f"  During recovery: {cp_failure_avg:.0f}ms avg, {cp_max_during_failure:.0f}ms max")
            print(f"  Post-recovery average: {cp_post_avg:.0f}ms")
            print(f"  Recovery impact: {cp_failure_avg/cp_pre_avg:.1f}x avg, {cp_max_during_failure/cp_pre_avg:.1f}x peak")
            print(f"  Recovery duration: {self.total_recovery_time}s")
        
        return results

def create_focused_cp_recovery_chart(results: Dict, benchmark: FocusedCPRecoveryBenchmark) -> str:
    """Create focused CP recovery chart showing only checkpointing behavior"""
    
    # Create figure with subplots - focused layout
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    
    # Extract data
    cp_times = results['CP_times']
    cp_phases = results['CP_phases']
    time_points = results['time_points']
    
    # Focus on recovery window for detailed view
    recovery_window_start = 220
    recovery_window_end = 300
    
    # Filter data for focused view
    focused_indices = [i for i, t in enumerate(time_points) 
                      if recovery_window_start <= t <= recovery_window_end]
    focused_times = [time_points[i] for i in focused_indices]
    focused_responses = [cp_times[i] for i in focused_indices]
    focused_phases = [cp_phases[i] for i in focused_indices]
    
    # Top subplot - Detailed response times during recovery
    ax1.plot(focused_times, focused_responses, 
            color='#8A2BE2', linewidth=3, label='CP Response Time', alpha=0.8)
    
    # Add phase background colors
    phase_colors = {
        'detection': '#FF6B6B',
        'reaction': '#FFA500', 
        'repair': '#FFD700',
        'recovery': '#90EE90'
    }
    
    y_max = max(focused_responses)
    
    for phase_name, phase in benchmark.recovery_phases.items():
        phase_end = phase.start_time + phase.duration
        ax1.axvspan(phase.start_time, phase_end, 
                   alpha=0.2, color=phase_colors[phase_name])
        
        # Add phase labels
        phase_center = phase.start_time + phase.duration / 2
        ax1.text(phase_center, y_max * 0.9, phase_name.title(), 
                ha='center', va='center', fontweight='bold', 
                fontsize=11, bbox=dict(boxstyle="round,pad=0.3", 
                facecolor=phase_colors[phase_name], alpha=0.7))
    
    # Add failure indicator
    ax1.axvline(x=benchmark.failure_start, color='red', linestyle='--', 
               linewidth=3, alpha=0.8, label='Pod Failure')
    
    # Mark recovery completion
    ax1.axvline(x=benchmark.recovery_end, color='green', linestyle='--', 
               linewidth=2, alpha=0.8, label='Recovery Complete')
    
    ax1.set_title('Checkpointing Recovery Time - Detailed Phase Analysis', 
                 fontsize=16, fontweight='bold', pad=20)
    ax1.set_xlabel('Time (sec)', fontsize=12)
    ax1.set_ylabel('Response Time (ms)', fontsize=12)
    ax1.set_xlim(recovery_window_start, recovery_window_end)
    ax1.set_ylim(0, y_max * 1.1)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=11)
    
    # Bottom subplot - Recovery phase timeline with detailed timing
    ax2.set_xlim(recovery_window_start, recovery_window_end)
    ax2.set_ylim(-1, len(benchmark.recovery_phases))
    
    # Draw detailed recovery timeline
    phases_list = list(benchmark.recovery_phases.keys())
    
    for i, phase_name in enumerate(phases_list):
        phase = benchmark.recovery_phases[phase_name]
        phase_end = phase.start_time + phase.duration
        
        # Draw phase bar with enhanced styling
        bar = ax2.barh(i, phase.duration, left=phase.start_time, height=0.7,
                      color=phase_colors[phase_name], alpha=0.8, 
                      edgecolor='black', linewidth=1.5)
        
        # Add detailed phase information
        phase_center = phase.start_time + phase.duration / 2
        ax2.text(phase_center, i, 
                f'{phase_name.title()}\n{phase.duration}s\n{phase.description}', 
                ha='center', va='center', fontweight='bold', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    
    # Add failure and recovery markers
    ax2.axvline(x=benchmark.failure_start, color='red', linestyle='--', 
               linewidth=3, alpha=0.8)
    ax2.text(benchmark.failure_start - 1, len(phases_list) - 0.5, 'Failure', 
             rotation=90, ha='right', va='center', color='red', fontweight='bold')
    
    ax2.axvline(x=benchmark.recovery_end, color='green', linestyle='--', 
               linewidth=2, alpha=0.8)
    ax2.text(benchmark.recovery_end + 1, len(phases_list) - 0.5, 'Recovery\nComplete', 
             rotation=90, ha='left', va='center', color='green', fontweight='bold')
    
    # Customize timeline subplot
    ax2.set_yticks(range(len(phases_list)))
    ax2.set_yticklabels([f'Phase {i+1}' for i in range(len(phases_list))])
    ax2.set_xlabel('Time (sec)', fontsize=12)
    ax2.set_title('Recovery Phase Timeline - Checkpointing Only', 
                 fontsize=14, fontweight='bold')
    ax2.grid(True, axis='x', alpha=0.3)
    
    # Add total recovery time annotation
    ax2.annotate('', xy=(benchmark.recovery_end, -0.5), 
                xytext=(benchmark.failure_start, -0.5),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=3))
    ax2.text((benchmark.failure_start + benchmark.recovery_end) / 2, -0.7, 
             f'Total Recovery: {benchmark.total_recovery_time}s',
             ha='center', va='top', color='blue', fontweight='bold', fontsize=13)
    
    plt.tight_layout()
    
    # Save chart
    chart_path = os.path.join('results', 'focused_cp_recovery_analysis.png')
    os.makedirs('results', exist_ok=True)
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Focused CP recovery chart saved to {chart_path}")
    return chart_path

def print_focused_cp_analysis(results: Dict, benchmark: FocusedCPRecoveryBenchmark):
    """Print detailed analysis of focused CP recovery performance"""
    print("\n" + "="*80)
    print("FOCUSED CHECKPOINTING RECOVERY ANALYSIS")
    print("="*80)
    
    cp_times = results['CP_times']
    cp_phases = results['CP_phases']
    time_points = results['time_points']
    
    print(f"\n📊 DETAILED PHASE-BY-PHASE ANALYSIS:")
    print("-" * 70)
    
    for phase_name, phase in benchmark.recovery_phases.items():
        # Find samples in this phase
        phase_samples = []
        phase_time_points = []
        
        for i, (time_val, response_time, phase_label) in enumerate(zip(time_points, cp_times, cp_phases)):
            if phase_label == phase_name:
                phase_samples.append(response_time)
                phase_time_points.append(time_val)
        
        if phase_samples:
            avg_time = np.mean(phase_samples)
            max_time = np.max(phase_samples)
            min_time = np.min(phase_samples)
            std_time = np.std(phase_samples)
            
            print(f"\n🔹 {phase_name.upper()} PHASE:")
            print(f"   Duration:     {phase.duration}s ({phase.start_time}s - {phase.start_time + phase.duration}s)")
            print(f"   Response:     {avg_time:.0f}ms ± {std_time:.0f}ms")
            print(f"   Range:        {min_time:.0f} - {max_time:.0f}ms")
            print(f"   Activity:     {phase.description}")
            print(f"   Samples:      {len(phase_samples)} measurements")
            
            # Calculate impact relative to normal operation
            normal_baseline = 150  # Normal operation baseline
            impact_factor = avg_time / normal_baseline
            print(f"   Impact:       {impact_factor:.1f}x normal response time")
            
            # Phase-specific insights
            if phase_name == 'detection':
                print(f"   Analysis:     Initial degradation as system detects failure")
                print(f"   Optimization: Faster health checks could reduce this phase")
            elif phase_name == 'reaction':
                print(f"   Analysis:     Checkpoint restoration process initialization")
                print(f"   Optimization: Pre-loaded checkpoint metadata could help")
            elif phase_name == 'repair':
                print(f"   Analysis:     CRITICAL PHASE - Highest resource utilization")
                print(f"   Optimization: Incremental checkpoints, parallel restoration")
                percentage_of_recovery = (phase.duration / benchmark.total_recovery_time) * 100
                print(f"   Duration:     {percentage_of_recovery:.0f}% of total recovery time")
            elif phase_name == 'recovery':
                print(f"   Analysis:     Performance stabilization and state finalization")
                print(f"   Optimization: Warm-up procedures could reduce this phase")
    
    # Overall recovery analysis
    failure_period_start = int(benchmark.failure_start * 4)
    recovery_period_end = int(benchmark.recovery_end * 4)
    
    pre_failure = cp_times[failure_period_start - 80:failure_period_start]
    during_recovery = cp_times[failure_period_start:recovery_period_end]
    post_recovery = cp_times[recovery_period_end:recovery_period_end + 80]
    
    if pre_failure and during_recovery and post_recovery:
        pre_avg = np.mean(pre_failure)
        during_avg = np.mean(during_recovery)
        during_max = np.max(during_recovery)
        post_avg = np.mean(post_recovery)
        
        print(f"\n📈 OVERALL RECOVERY PERFORMANCE:")
        print("-" * 70)
        print(f"  Pre-failure baseline:    {pre_avg:.0f}ms")
        print(f"  Peak recovery impact:    {during_max:.0f}ms ({during_max/pre_avg:.1f}x)")
        print(f"  Average recovery impact: {during_avg:.0f}ms ({during_avg/pre_avg:.1f}x)")
        print(f"  Post-recovery baseline:  {post_avg:.0f}ms")
        print(f"  Recovery efficiency:     {post_avg/pre_avg:.2f}x (closer to 1.0 = better)")
    
    print(f"\n🎯 KEY FINDINGS:")
    print("-" * 70)
    print(f"  • Total recovery time: {benchmark.total_recovery_time}s")
    
    # Find the most expensive phase
    phase_impacts = {}
    for phase_name in benchmark.recovery_phases.keys():
        phase_samples = [rt for rt, pl in zip(cp_times, cp_phases) if pl == phase_name]
        if phase_samples:
            phase_impacts[phase_name] = np.mean(phase_samples)
    
    if phase_impacts:
        most_expensive_phase = max(phase_impacts, key=phase_impacts.get)
        least_expensive_phase = min(phase_impacts, key=phase_impacts.get)
        
        print(f"  • Most expensive phase: {most_expensive_phase.title()} ({phase_impacts[most_expensive_phase]:.0f}ms avg)")
        print(f"  • Least expensive phase: {least_expensive_phase.title()} ({phase_impacts[least_expensive_phase]:.0f}ms avg)")
        
        repair_duration = benchmark.recovery_phases['repair'].duration
        repair_percentage = (repair_duration / benchmark.total_recovery_time) * 100
        print(f"  • Repair phase dominance: {repair_percentage:.0f}% of total recovery time")
    
    print(f"\n🔧 OPTIMIZATION PRIORITIES:")
    print("-" * 70)
    print(f"  1. Repair Phase: Implement incremental checkpointing")
    print(f"  2. Detection: Faster failure detection mechanisms")
    print(f"  3. Reaction: Pre-cache checkpoint metadata")
    print(f"  4. Recovery: Optimize state finalization process")
    print(f"  5. Overall: Consider checkpoint frequency vs recovery time tradeoffs")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print("🔄 FOCUSED CHECKPOINTING RECOVERY BENCHMARK")
    print("="*80)
    print("Detailed analysis of CP recovery phases only")
    print("Enhanced focus on checkpointing behavior and optimization")
    print("="*80)
    
    # Initialize and run benchmark
    benchmark = FocusedCPRecoveryBenchmark()
    results = benchmark.run_focused_cp_benchmark()
    
    # Create focused chart
    print(f"\n📈 Generating focused CP recovery chart...")
    chart_path = create_focused_cp_recovery_chart(results, benchmark)
    
    # Print detailed analysis
    print_focused_cp_analysis(results, benchmark)
    
    # Save raw data
    results_dir = 'results'
    data_path = os.path.join(results_dir, 'focused_cp_recovery_data.json')
    
    # Prepare data for serialization
    serializable_results = {
        'CP_times': results['CP_times'],
        'time_points': results['time_points'],
        # Convert phases to indices for serialization
        'CP_phases_indices': [list(benchmark.recovery_phases.keys()).index(phase) 
                             if phase in benchmark.recovery_phases.keys() else -1 
                             for phase in results['CP_phases']]
    }
    
    combined_data = {
        'recovery_data': serializable_results,
        'recovery_phases': {
            name: {
                'start_time': phase.start_time,
                'duration': phase.duration,
                'description': phase.description,
                'color': phase.color
            } for name, phase in benchmark.recovery_phases.items()
        },
        'configuration': {
            'total_requests': benchmark.total_requests,
            'duration': benchmark.duration_seconds,
            'concurrent_users': benchmark.concurrent_users,
            'input_rate': benchmark.input_rate,
            'failure_start': benchmark.failure_start,
            'total_recovery_time': benchmark.total_recovery_time,
            'base_response_time': benchmark.base_response_time
        },
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'scenario': 'focused_cp_recovery_analysis',
            'chart_type': 'detailed_recovery_phases',
            'focus': 'checkpointing_only'
        }
    }
    
    with open(data_path, 'w') as f:
        json.dump(combined_data, f, indent=2)
    
    print(f"\n✅ Focused CP Recovery Analysis Complete!")
    print(f"📁 Files generated:")
    print(f"   📈 {chart_path}")
    print(f"   📄 {data_path}")
    
    print(f"\n📋 SUMMARY:")
    print(f"   ✓ Focused exclusively on checkpointing recovery behavior")
    print(f"   ✓ Detailed phase-by-phase analysis: Detection → Reaction → Repair → Recovery")
    print(f"   ✓ High-resolution sampling for precise phase timing")
    print(f"   ✓ Recovery optimization recommendations provided")
    print(f"   ✓ Clean visualization without comparison technique distractions")
    print(f"   ✓ Total recovery time: {benchmark.total_recovery_time} seconds")