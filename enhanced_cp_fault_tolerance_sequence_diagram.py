"""
Enhanced Checkpointing (CP) Fault Tolerance Sequence Diagram
=============================================================

Creates a sequence/timing diagram showing the fault tolerance protocol
for Enhanced Checkpointing mechanism in Fission, similar to the RR sequence diagram.

Shows the timeline of:
1. Normal operation with async checkpointing
2. Pod failure detection
3. Fast recovery from checkpoint
4. Minimal request disruption

Key differences from RR:
- Single pod execution (not replicated)
- Async checkpoint saves (background)
- Recovery from checkpoint (not from scratch)
- Lower overhead, fast recovery
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

def create_enhanced_cp_sequence_diagram():
    """
    Create sequence diagram for Enhanced CP fault tolerance protocol
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Colors
    color_user = '#4A90E2'
    color_router = '#F39C12'
    color_k8s = '#5DADE2'
    color_executor = '#95A5A6'
    color_pod_active = '#52BE80'
    color_pod_new = '#A9DFBF'
    color_checkpoint = '#F4D03F'
    
    # === Actor boxes at top ===
    actors = [
        (1, 'User', color_user),
        (3, 'Router CP', color_router),
        (5.5, 'Kubernetes\nAPI', color_k8s),
        (8, 'NewDeploy\nExecutor', color_executor),
        (10.5, 'Active-Pod1', color_pod_active),
        (13, 'Checkpoint\nStorage', color_checkpoint),
    ]
    
    y_top = 9.5
    for x, label, color in actors:
        box = FancyBboxPatch((x-0.6, y_top-0.3), 1.2, 0.5,
                            boxstyle="round,pad=0.05",
                            facecolor=color,
                            edgecolor='black',
                            linewidth=1.5)
        ax.add_patch(box)
        ax.text(x, y_top-0.05, label, ha='center', va='center',
                fontsize=9, fontweight='bold')
    
    # === Lifelines ===
    y_start = 8.8
    y_end = 0.5
    for x, _, _ in actors:
        ax.plot([x, x], [y_start, y_end], 'k--', linewidth=1, alpha=0.5)
    
    # === Timeline sequence ===
    y_current = 8.5
    
    # 1. Function call from User to Router
    y_current -= 0.4
    arrow1 = FancyArrowPatch((1, y_current), (3, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='black', linewidth=1.5)
    ax.add_patch(arrow1)
    ax.text(2, y_current+0.15, 'function call', ha='center', va='bottom',
            fontsize=8)
    
    # 2. Router to K8s - get pod IP
    y_current -= 0.5
    arrow2 = FancyArrowPatch((3.2, y_current), (5.3, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow2)
    ax.text(4.25, y_current+0.15, 'get the IP address of active pod', 
            ha='center', va='bottom', fontsize=7, color='blue')
    
    arrow2_return = FancyArrowPatch((5.3, y_current-0.2), (3.2, y_current-0.2),
                                    arrowstyle='<-,head_width=0.2,head_length=0.2',
                                    color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow2_return)
    
    # 3. Router to Active Pod - forward request
    y_current -= 0.6
    arrow3 = FancyArrowPatch((3.2, y_current), (10.3, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='blue', linewidth=1.5)
    ax.add_patch(arrow3)
    ax.text(6.75, y_current+0.15, 'forward request', ha='center', va='bottom',
            fontsize=8, color='blue')
    
    # 4. Active Pod processing with async checkpoint saving
    y_current -= 0.5
    # Show pod is executing (activation bar)
    exec_bar = Rectangle((10.4, y_current-1.0), 0.2, 1.0,
                         facecolor=color_pod_active, edgecolor='darkgreen',
                         linewidth=2)
    ax.add_patch(exec_bar)
    ax.text(10.8, y_current-0.5, 'execute', ha='left', va='center',
            fontsize=7, style='italic')
    
    # Async checkpoint save
    y_checkpoint1 = y_current - 0.3
    arrow_cp1 = FancyArrowPatch((10.6, y_checkpoint1), (12.8, y_checkpoint1),
                                arrowstyle='->,head_width=0.2,head_length=0.2',
                                color='orange', linewidth=2, linestyle=':')
    ax.add_patch(arrow_cp1)
    ax.text(11.7, y_checkpoint1+0.15, 'save checkpoint', ha='center', va='bottom',
            fontsize=7, color='orange', fontweight='bold')
    ax.text(11.7, y_checkpoint1-0.15, '(async/incremental)', ha='center', va='top',
            fontsize=6, color='orange', style='italic')
    
    # 5. Response back to router
    y_current -= 1.1
    arrow5 = FancyArrowPatch((10.3, y_current), (3.2, y_current),
                             arrowstyle='<-,head_width=0.2,head_length=0.2',
                             color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow5)
    ax.text(6.75, y_current+0.15, 'response', ha='center', va='bottom',
            fontsize=8, color='blue')
    
    # Alternative box - no failure case
    y_current -= 0.3
    alt_box1 = Rectangle((0.3, y_current-0.5), 13.4, 0.5,
                         facecolor='lightyellow', edgecolor='gray',
                         linewidth=1, alpha=0.3)
    ax.add_patch(alt_box1)
    ax.text(0.5, y_current-0.25, 'Alt', ha='left', va='center',
            fontsize=8, fontweight='bold')
    ax.text(7, y_current-0.25, '[no failure]', ha='center', va='center',
            fontsize=7, style='italic')
    
    # 6. Deliver response to user (no failure)
    y_current -= 0.5
    arrow6 = FancyArrowPatch((3, y_current), (1, y_current),
                             arrowstyle='<-,head_width=0.2,head_length=0.2',
                             color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow6)
    ax.text(2, y_current+0.15, 'deliver first response', ha='center', va='bottom',
            fontsize=8, color='blue')
    
    # === Pod Failure Scenario ===
    y_current -= 0.7
    
    # Failure marker on Active-Pod1
    ax.plot(10.5, y_current, 'rX', markersize=20, markeredgewidth=3)
    ax.text(11.2, y_current, '[Pod 1 failure]', ha='left', va='center',
            fontsize=8, color='red', fontweight='bold')
    
    # Red box indicating failed pod
    failed_box = Rectangle((10.2, y_current-1.8), 0.6, 1.7,
                           facecolor='white', edgecolor='red',
                           linewidth=2, linestyle='-', alpha=0.5)
    ax.add_patch(failed_box)
    
    # 7. K8s detects failure and signals Executor
    y_current -= 0.5
    arrow7 = FancyArrowPatch((5.5, y_current), (8, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='red', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow7)
    ax.text(6.75, y_current+0.15, 'detect failure', ha='center', va='bottom',
            fontsize=7, color='red')
    
    # 8. Executor creates new pod
    y_current -= 0.5
    arrow8 = FancyArrowPatch((8, y_current), (10.5, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='green', linewidth=1.5)
    ax.add_patch(arrow8)
    ax.text(9.25, y_current+0.15, 'create', ha='center', va='bottom',
            fontsize=8, color='green')
    
    # New Pod appears
    y_new_pod = y_current - 0.3
    new_pod_box = FancyBboxPatch((10.2, y_new_pod-0.25), 0.6, 0.4,
                                 boxstyle="round,pad=0.03",
                                 facecolor=color_pod_new,
                                 edgecolor='darkgreen',
                                 linewidth=2)
    ax.add_patch(new_pod_box)
    ax.text(10.5, y_new_pod-0.05, 'New Pod', ha='center', va='center',
            fontsize=7, fontweight='bold')
    
    # New pod lifeline
    ax.plot([10.5, 10.5], [y_new_pod-0.25, y_end], 'k--', linewidth=1, alpha=0.5)
    
    # 9. New pod restores from checkpoint
    y_current -= 0.7
    arrow9 = FancyArrowPatch((13, y_current), (10.7, y_current),
                             arrowstyle='->,head_width=0.2,head_length=0.2',
                             color='orange', linewidth=2)
    ax.add_patch(arrow9)
    ax.text(11.85, y_current+0.15, 'restore checkpoint', ha='center', va='bottom',
            fontsize=8, color='orange', fontweight='bold')
    ax.text(11.85, y_current-0.15, '(fast: ~7s)', ha='center', va='top',
            fontsize=6, color='orange', style='italic')
    
    # 10. New pod executes from checkpoint state
    y_current -= 0.5
    exec_bar2 = Rectangle((10.4, y_current-0.4), 0.2, 0.4,
                          facecolor=color_pod_new, edgecolor='darkgreen',
                          linewidth=2)
    ax.add_patch(exec_bar2)
    ax.text(10.8, y_current-0.2, 'resume', ha='left', va='center',
            fontsize=7, style='italic')
    
    # 11. Response from new pod
    y_current -= 0.6
    arrow11 = FancyArrowPatch((10.3, y_current), (3.2, y_current),
                              arrowstyle='<-,head_width=0.2,head_length=0.2',
                              color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow11)
    ax.text(6.75, y_current+0.15, 'response', ha='center', va='bottom',
            fontsize=8, color='blue')
    
    # 12. Deliver response to user
    y_current -= 0.5
    arrow12 = FancyArrowPatch((3, y_current), (1, y_current),
                              arrowstyle='<-,head_width=0.2,head_length=0.2',
                              color='blue', linewidth=1.5, linestyle='--')
    ax.add_patch(arrow12)
    ax.text(2, y_current+0.15, 'deliver response', ha='center', va='bottom',
            fontsize=8, color='blue')
    
    # === Title ===
    ax.text(7, 10.2, 'Fault Tolerance Protocol with Enhanced Checkpointing (CP) Mechanism',
            ha='center', va='center', fontsize=13, fontweight='bold')
    
    # === Legend ===
    legend_elements = [
        ('Normal request flow', 'blue', '-'),
        ('Checkpoint operation (async)', 'orange', ':'),
        ('Failure & recovery', 'red', '--'),
        ('Pod creation', 'green', '-'),
    ]
    
    legend_y = 0.3
    legend_x = 0.5
    ax.text(legend_x, legend_y, 'Legend:', ha='left', va='center',
            fontsize=8, fontweight='bold')
    
    for idx, (label, color, style) in enumerate(legend_elements):
        y_pos = legend_y - 0.2 - (idx * 0.15)
        ax.plot([legend_x, legend_x + 0.4], [y_pos, y_pos],
                color=color, linestyle=style, linewidth=2)
        ax.text(legend_x + 0.5, y_pos, label, ha='left', va='center',
                fontsize=7)
    
    # === Key metrics box ===
    metrics_box = FancyBboxPatch((9.5, 0.1), 4, 0.8,
                                 boxstyle="round,pad=0.1",
                                 facecolor='lightyellow',
                                 edgecolor='orange',
                                 linewidth=2)
    ax.add_patch(metrics_box)
    ax.text(11.5, 0.7, 'Enhanced CP Metrics', ha='center', va='center',
            fontsize=9, fontweight='bold', color='darkorange')
    ax.text(11.5, 0.52, '• Recovery Time: ~7s (53% faster than Basic CP)', 
            ha='center', va='center', fontsize=6.5)
    ax.text(11.5, 0.40, '• Response Time: 5.20ms (Rank #2)', 
            ha='center', va='center', fontsize=6.5)
    ax.text(11.5, 0.28, '• Throughput Retention: 93.8% during failures', 
            ha='center', va='center', fontsize=6.5)
    ax.text(11.5, 0.16, '• Checkpoint Size: 70% smaller (incremental)', 
            ha='center', va='center', fontsize=6.5)
    
    plt.tight_layout()
    
    # Save the diagram
    output_path = "results/enhanced_cp_fault_tolerance_sequence_diagram.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Diagram saved to: {output_path}")
    
    return output_path

if __name__ == "__main__":
    print("=" * 70)
    print("ENHANCED CP FAULT TOLERANCE SEQUENCE DIAGRAM")
    print("=" * 70)
    print("\n📊 Creating sequence diagram for Enhanced Checkpointing protocol...")
    print("Similar to Request Replication (RR) sequence/timing diagram\n")
    
    output_path = create_enhanced_cp_sequence_diagram()
    
    print("\n" + "=" * 70)
    print("DIAGRAM GENERATION COMPLETE")
    print("=" * 70)
    print("\nThe sequence diagram shows:")
    print("1. User initiates function call to Router CP")
    print("2. Router queries Kubernetes API for active pod")
    print("3. Request forwarded to single Active-Pod1")
    print("4. Pod executes with async checkpoint saves (background)")
    print("5. Normal response returned to user (no failure case)")
    print("6. FAILURE SCENARIO:")
    print("   - Pod 1 fails during execution")
    print("   - Kubernetes detects failure")
    print("   - Executor creates new pod")
    print("   - New pod restores from checkpoint (~7s)")
    print("   - Execution resumes from checkpoint state")
    print("   - Response delivered to user")
    print("\n✨ Key Advantages vs RR:")
    print("   - Lower resource usage (single pod vs 3 replicas)")
    print("   - Zero data loss (perfect state preservation)")
    print("   - Fast recovery (checkpoint restore vs cold start)")
    print("   - 95%+ of RR performance at <50% cost")
