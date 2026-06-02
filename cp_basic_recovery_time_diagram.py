"""
Recovery Time Diagram - CP (Basic) Checkpointing
================================================

Replicates the recovery time diagram showing the phases and states
for CP (Basic) Checkpointing technique during pod failure recovery.

CP (Basic) features:
- Standard checkpointing (synchronous)
- Sequential restoration (blocking)
- Full state checkpoints
- Standard state management

Recovery Phases:
1. Pod Failure: Container crashes
2. Detection: K8s detects pod is unhealthy (~3s)
3. Reaction: K8s decides to restart pod (~3s)
4. Repair: Pod recreates and restores from checkpoint (~18s - blocking restore)
5. Recovery: Service becomes available again (~2s)

Total Recovery Time: ~26s (vs ~30s for vanilla, ~15s for Enhanced CP)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_cp_basic_recovery_diagram():
    """
    Create recovery time diagram for CP (Basic) Checkpointing
    """
    fig, ax = plt.subplots(figsize=(14, 5))
    
    # Time points (in seconds)
    t_start = 0
    t_failure = 5
    t_detection = 8        # 3s detection
    t_reaction = 11        # 3s reaction
    t_repair = 29          # 18s repair (blocking restore from checkpoint)
    t_recovery = 31        # 2s recovery
    t_end = 36
    
    # Timeline
    ax.plot([t_start, t_end], [3, 3], 'k-', linewidth=2, zorder=1)
    
    # Phase markers (vertical dashed lines)
    phases = [
        (t_failure, 'pod-failure', 'red'),
        (t_detection, 'detection', 'red'),
        (t_reaction, 'reaction', 'red'),
        (t_repair, 'repair', 'red'),
        (t_recovery, 'recovery', 'green'),
    ]
    
    for t, label, color in phases:
        ax.axvline(x=t, ymin=0.35, ymax=0.65, color=color, 
                   linestyle='--', linewidth=1.5, zorder=2)
        ax.text(t, 4.5, label, ha='center', fontsize=9, 
                color=color, fontweight='bold')
    
    # Recovery Time bracket
    ax.annotate('', xy=(t_failure, 5), xytext=(t_recovery, 5),
                arrowprops=dict(arrowstyle='<->', color='black', lw=2))
    ax.text((t_failure + t_recovery)/2, 5.3, 'Recovery Time (~26s)', 
            ha='center', fontsize=11, fontweight='bold')
    
    # Pod failure marker (X)
    ax.plot(t_failure, 3, 'rX', markersize=20, markeredgewidth=3, zorder=10)
    
    # Request arrows (before and after)
    # Before failure
    for t in [1, 2, 3, 4]:
        ax.annotate('', xy=(t, 2.7), xytext=(t, 3.5),
                    arrowprops=dict(arrowstyle='->', color='black', lw=1))
    ax.text(2.5, 3.8, 'Requests', ha='center', fontsize=9)
    
    # After recovery
    for t in [32, 33, 34, 35]:
        ax.annotate('', xy=(t, 2.7), xytext=(t, 3.5),
                    arrowprops=dict(arrowstyle='->', color='black', lw=1))
    ax.text(33.5, 3.8, 'Requests', ha='center', fontsize=9)
    
    # Retries during reaction phase
    retry_times = [11.5, 12.5, 13.5]
    for t in retry_times:
        ax.annotate('', xy=(t, 2.7), xytext=(t, 3.3),
                    arrowprops=dict(arrowstyle='->', color='red', lw=0.8))
    ax.text(12.5, 3.5, 'Retries', ha='center', fontsize=8, color='red')
    
    # States below timeline
    y_router = 1.8
    y_pod = 1.3
    y_service = 0.8
    
    # Labels
    ax.text(-1, y_router, 'Router Cache', ha='right', fontsize=9, fontweight='bold')
    ax.text(-1, y_pod, 'Pod state', ha='right', fontsize=9, fontweight='bold')
    ax.text(-1, y_service, 'Service state', ha='right', fontsize=9, fontweight='bold')
    
    # Router Cache states
    router_states = [
        (t_start, t_failure, '{Service URL}', 'lightblue'),
        (t_failure, t_detection, '{Service URL}', 'lightblue'),
        (t_detection, t_reaction, '{Service URL}', 'lightblue'),
        (t_reaction, t_repair, '{Service URL}', 'lightblue'),
        (t_repair, t_recovery, '{ }', 'lightgray'),
        (t_recovery, t_end, '{Service URL}', 'lightblue'),
    ]
    
    for t1, t2, text, color in router_states:
        rect = FancyBboxPatch((t1, y_router-0.15), t2-t1, 0.3,
                              boxstyle="round,pad=0.05", 
                              facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text((t1+t2)/2, y_router, text, ha='center', va='center', 
                fontsize=8)
    
    # Pod states
    pod_states = [
        (t_start, t_failure, 'Running', 'lightgreen'),
        (t_failure, t_detection, 'Running', 'lightgreen'),
        (t_detection, t_reaction, 'Unhealthy', 'lightcoral'),
        (t_reaction, t_repair, 'Unhealthy', 'lightcoral'),
        (t_repair, t_recovery, 'Restoring\n(Blocking)', 'khaki'),
        (t_recovery, t_end, 'Running', 'lightgreen'),
    ]
    
    for t1, t2, text, color in pod_states:
        rect = FancyBboxPatch((t1, y_pod-0.15), t2-t1, 0.3,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text((t1+t2)/2, y_pod, text, ha='center', va='center',
                fontsize=8, fontweight='bold' if 'Restoring' in text else 'normal')
    
    # Service states
    service_states = [
        (t_start, t_failure, 'Available', 'lightgreen'),
        (t_failure, t_detection, 'Available', 'lightgreen'),
        (t_detection, t_reaction, 'Unavailable', 'lightcoral'),
        (t_reaction, t_repair, 'Unavailable', 'lightcoral'),
        (t_repair, t_recovery, 'Unavailable', 'lightcoral'),
        (t_recovery, t_end, 'Available', 'lightgreen'),
    ]
    
    for t1, t2, text, color in service_states:
        rect = FancyBboxPatch((t1, y_service-0.15), t2-t1, 0.3,
                              boxstyle="round,pad=0.05",
                              facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        ax.text((t1+t2)/2, y_service, text, ha='center', va='center',
                fontsize=8)
    
    # Axis settings
    ax.set_xlim(-2, t_end + 1)
    ax.set_ylim(0.3, 6)
    ax.axis('off')
    
    # Title
    ax.text(18, 6.5, 'Recovery Time - CP (Basic) Checkpointing', 
            ha='center', fontsize=14, fontweight='bold')
    
    # Add annotations
    ax.text(18, 6, 
            'Moderate Recovery: ~26s (Blocking Checkpoint Restoration)', 
            ha='center', fontsize=10, style='italic', color='darkorange')
    
    # Add phase durations as text boxes
    phase_durations = [
        ((t_failure + t_detection)/2, 0.3, '~3s\nDetection'),
        ((t_detection + t_reaction)/2, 0.3, '~3s\nReaction'),
        ((t_reaction + t_repair)/2, 0.3, '~18s\nBlocking\nRestore'),
        ((t_repair + t_recovery)/2, 0.3, '~2s\nRecovery'),
    ]
    
    for x, y, text in phase_durations:
        ax.text(x, y, text, ha='center', fontsize=7, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Save
    output_path = "results/cp_basic_recovery_time_diagram.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return output_path

def main():
    print("\n" + "="*80)
    print("RECOVERY TIME DIAGRAM - CP (BASIC) CHECKPOINTING")
    print("="*80 + "\n")
    
    print("📋 Recovery Phases for CP (Basic):")
    print("   1. Pod Failure: Container crashes")
    print("   2. Detection: ~3s (K8s health check)")
    print("   3. Reaction: ~3s (standard retry logic)")
    print("   4. Repair: ~18s (blocking restoration from checkpoint)")
    print("   5. Recovery: ~2s (service becomes available)")
    print("\n   Total Recovery Time: ~26s")
    
    print("\n🔧 CP (Basic) Features:")
    print("   • Standard synchronous checkpointing")
    print("   • Blocking restoration (single-threaded)")
    print("   • Full state checkpoints")
    print("   • Traditional I/O operations")
    
    print("\n📊 Comparison:")
    print("   • Vanilla Recovery Time: ~30s")
    print("   • CP (Basic) Recovery Time: ~26s")
    print("   • Enhanced CP Recovery Time: ~15s")
    print("   • CP (Basic) vs Vanilla: 13% faster")
    print("   • Enhanced CP vs CP (Basic): 42% faster ⭐")
    
    print("\n🎨 Generating recovery time diagram...")
    output_path = create_cp_basic_recovery_diagram()
    
    print(f"\n✅ Diagram saved to: {output_path}")
    
    print("\n" + "="*80)
    print("DIAGRAM COMPLETE")
    print("="*80 + "\n")
    
    print("📝 Characteristics:")
    print("   ✓ Checkpoint available reduces recovery time")
    print("   ✓ Blocking restore slower than parallel (Enhanced CP)")
    print("   ✓ Better than vanilla, but not optimized")
    print("   ✓ Standard checkpointing approach")
    
    print("\n")

if __name__ == "__main__":
    main()
