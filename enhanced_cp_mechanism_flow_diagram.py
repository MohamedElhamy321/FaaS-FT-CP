"""
Enhanced Checkpointing (CP) Mechanism Flow Diagram
===================================================

Creates a visual diagram showing the Enhanced CP mechanism flow in Fission,
matching the visual style of the Request Replication (RR) diagram (Fig. 5).

Enhanced CP Flow:
1. User sends request to Router CP
2. Router gets pod info from Kubernetes API
3. Request forwarded to function pod
4. State saved asynchronously to checkpoint storage (incremental)
5. Response sent to router
6. Response delivered to user
* On failure: Pod recovers from latest checkpoint

Key Features:
- Asynchronous checkpointing (no blocking)
- Incremental state saving (delta encoding)
- Fast recovery from checkpoint
- Minimal overhead on normal execution
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle, Polygon
import numpy as np

def create_enhanced_cp_flow_diagram():
    """
    Create Enhanced CP mechanism flow diagram matching RR diagram style
    """
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')
    
    # Colors matching RR diagram
    color_router = '#F4A460'  # Sandy brown/orange (like RR router)
    color_executor = '#E8E8E8'  # Light gray
    color_k8s = '#326CE5'  # Kubernetes blue
    color_pod = '#90EE90'  # Light green
    color_checkpoint = '#FFE4B5'  # Moccasin/light orange for storage
    color_user_body = '#4169E1'  # Royal blue
    color_user_head = '#FFE4C4'  # Bisque (skin tone)
    
    # === User Icon (matching RR style - person figure) ===
    # Head
    user_head = Circle((6.5, 8.6), 0.22, facecolor=color_user_head, 
                       edgecolor='black', linewidth=1.5, zorder=10)
    ax.add_patch(user_head)
    # Body (trapezoid shape)
    body_x = [6.2, 6.8, 6.9, 6.1]
    body_y = [8.35, 8.35, 7.9, 7.9]
    body = Polygon(list(zip(body_x, body_y)), facecolor=color_user_body,
                   edgecolor='black', linewidth=1.5, zorder=10)
    ax.add_patch(body)
    
    # === Router CP (matching RR Router style) ===
    router = FancyBboxPatch((5, 6.8), 2.5, 0.85,
                            boxstyle="round,pad=0.05",
                            facecolor=color_router,
                            edgecolor='black',
                            linewidth=1.5)
    ax.add_patch(router)
    ax.text(6.25, 7.22, 'Router CP', ha='center', va='center',
            fontsize=11, fontweight='bold')
    
    # === Executor (matching RR style) ===
    executor = FancyBboxPatch((1.5, 6.8), 1.8, 0.85,
                              boxstyle="round,pad=0.05",
                              facecolor=color_executor,
                              edgecolor='black',
                              linewidth=1.5)
    ax.add_patch(executor)
    ax.text(2.4, 7.3, 'Executor', ha='center', va='center',
            fontsize=10, fontweight='bold')
    # NewDeploy box inside
    newdeploy = FancyBboxPatch((1.7, 6.9), 1.4, 0.35,
                                boxstyle="round,pad=0.02",
                                facecolor='white',
                                edgecolor='gray',
                                linewidth=1)
    ax.add_patch(newdeploy)
    ax.text(2.4, 7.07, 'NewDeploy', ha='center', va='center',
            fontsize=8, style='italic')
    
    # === Arrow from Executor to Kubernetes API ===
    ax.annotate('', xy=(2.5, 5.9), xytext=(2.4, 6.8),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.2,
                               linestyle='dashed'))
    
    # === Kubernetes API (matching RR style with logo) ===
    k8s = FancyBboxPatch((2.5, 5.0), 5.5, 0.9,
                         boxstyle="round,pad=0.05",
                         facecolor=color_k8s,
                         edgecolor='black',
                         linewidth=1.5)
    ax.add_patch(k8s)
    ax.text(4.8, 5.45, 'Kubernetes API', ha='center', va='center',
            fontsize=12, fontweight='bold', color='white')
    # K8s helm/wheel icon
    k8s_icon = Circle((7.2, 5.45), 0.28, facecolor='white', 
                      edgecolor=color_k8s, linewidth=2, zorder=5)
    ax.add_patch(k8s_icon)
    # Simple helm spokes
    for angle in range(0, 360, 45):
        rad = np.radians(angle)
        ax.plot([7.2, 7.2 + 0.18*np.cos(rad)], 
                [5.45, 5.45 + 0.18*np.sin(rad)],
                color=color_k8s, linewidth=1.5, zorder=6)
    
    # === Node 1 with Function Pod (matching RR Node style) ===
    node1 = FancyBboxPatch((1.3, 2.0), 3.2, 2.0,
                           boxstyle="round,pad=0.1",
                           facecolor='white',
                           edgecolor='gray',
                           linewidth=1.5,
                           linestyle='--')
    ax.add_patch(node1)
    ax.text(1.6, 3.85, 'Node 1', ha='left', va='top',
            fontsize=9, fontweight='bold', color='gray')
    
    # Function Pod (Active-Pod style from RR)
    pod1 = FancyBboxPatch((1.8, 2.3), 2.2, 1.0,
                          boxstyle="round,pad=0.05",
                          facecolor=color_pod,
                          edgecolor='darkgreen',
                          linewidth=1.5)
    ax.add_patch(pod1)
    ax.text(2.9, 2.8, 'Function-Pod', ha='center', va='center',
            fontsize=9, fontweight='bold')
    
    # === Checkpoint Storage (clean box style) ===
    checkpoint_storage = FancyBboxPatch((5.8, 2.0), 3.5, 2.0,
                                        boxstyle="round,pad=0.1",
                                        facecolor=color_checkpoint,
                                        edgecolor='#CD853F',
                                        linewidth=1.5)
    ax.add_patch(checkpoint_storage)
    ax.text(7.55, 3.85, 'Checkpoint Storage', ha='center', va='top',
            fontsize=9, fontweight='bold', color='#8B4513')
    
    # Incremental checkpoint representation
    checkpoint_box = FancyBboxPatch((6.3, 2.4), 2.5, 1.1,
                                    boxstyle="round,pad=0.05",
                                    facecolor='white',
                                    edgecolor='#CD853F',
                                    linewidth=1.5)
    ax.add_patch(checkpoint_box)
    ax.text(7.55, 3.15, 'Incremental', ha='center', va='center',
            fontsize=9, fontweight='bold')
    ax.text(7.55, 2.85, 'Checkpoint', ha='center', va='center',
            fontsize=9, fontweight='bold')
    ax.text(7.55, 2.55, '(Delta)', ha='center', va='center',
            fontsize=7, style='italic', color='#8B4513')
    
    # === Arrows matching RR diagram style ===
    
    # (1) Request from User to Router
    ax.annotate('', xy=(6.25, 7.65), xytext=(6.4, 7.85),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    ax.text(5.4, 7.85, 'Request (1)', ha='center', va='center',
            fontsize=9, color='black')
    
    # (6) Deliver response to user
    ax.annotate('', xy=(6.6, 7.85), xytext=(6.8, 7.65),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
    ax.text(7.8, 7.9, '(6)', ha='left', va='center',
            fontsize=9, color='green', fontweight='bold')
    ax.text(8.1, 7.9, 'Deliver response', ha='left', va='center',
            fontsize=9, color='green')
    ax.text(8.1, 7.65, 'to the user', ha='left', va='center',
            fontsize=9, color='green')
    
    # (2) Router to Kubernetes - Get pod info (dashed)
    ax.annotate('', xy=(4.5, 5.9), xytext=(5.2, 6.8),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.2, 
                               linestyle='dashed'))
    ax.text(3.5, 6.5, 'Get the IP address of the', ha='center', va='center',
            fontsize=8, color='black')
    ax.text(3.5, 6.25, 'function pod', ha='center', va='center',
            fontsize=8, color='black')
    ax.text(4.7, 6.1, '(2)', ha='center', va='center',
            fontsize=8, color='black')
    
    # (3) Kubernetes to Pod - Forward request
    ax.annotate('', xy=(2.9, 3.3), xytext=(4.0, 5.0),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5,
                               linestyle='dashed'))
    ax.text(2.5, 4.5, 'Forward request to', ha='center', va='center',
            fontsize=8, color='black')
    ax.text(2.5, 4.25, 'function pod (3)', ha='center', va='center',
            fontsize=8, color='black')
    
    # (4) Pod to Checkpoint Storage - Save state (async)
    ax.annotate('', xy=(6.3, 2.9), xytext=(4.0, 2.8),
                arrowprops=dict(arrowstyle='->', color='#CD853F', lw=2,
                               linestyle='dotted'))
    ax.text(5.15, 3.2, '(4) save state', ha='center', va='center',
            fontsize=8, color='#8B4513')
    ax.text(5.15, 2.5, '(async/incremental)', ha='center', va='center',
            fontsize=7, color='#8B4513', style='italic')
    
    # (5) Response from Pod to Router
    ax.annotate('', xy=(6.5, 6.8), xytext=(3.5, 3.3),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
    ax.text(8.5, 5.6, '(5) send the response', ha='left', va='center',
            fontsize=8, color='green')
    ax.text(8.7, 5.35, 'to the router', ha='left', va='center',
            fontsize=8, color='green')
    
    # Recovery arrow (dashed red) - from Checkpoint to Pod
    ax.annotate('', xy=(4.0, 2.5), xytext=(6.3, 2.6),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5,
                               linestyle='dashed'))
    ax.text(5.15, 2.1, 'Restore on failure', ha='center', va='center',
            fontsize=8, color='red', style='italic')
    
    # === Title ===
    ax.text(5.5, 9.3, 'Enhanced Checkpointing (CP) Mechanism in Fission', 
            ha='center', va='center',
            fontsize=13, fontweight='bold')
    
    # === Figure Caption (matching RR Fig. 5 style) ===
    ax.text(5.5, 0.4, 'Fig. 6  Overview of Enhanced Checkpointing mechanism in Fission', 
            ha='center', va='center',
            fontsize=10, style='italic')
    
    # === Key Features (small, bottom right) ===
    ax.text(9.5, 1.5, 'Key Features:', ha='left', va='top',
            fontsize=7, fontweight='bold', color='gray')
    ax.text(9.5, 1.25, '• Async checkpointing', ha='left', va='top',
            fontsize=6, color='gray')
    ax.text(9.5, 1.05, '• Incremental (60-80%)', ha='left', va='top',
            fontsize=6, color='gray')
    ax.text(9.5, 0.85, '• Fast recovery (~7s)', ha='left', va='top',
            fontsize=6, color='gray')
    
    plt.tight_layout()
    
    # Save the diagram
    output_path = "results/enhanced_cp_mechanism_flow_diagram.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
    print(f"✅ Diagram saved to: {output_path}")
    
    plt.close()
    return output_path

if __name__ == "__main__":
    print("=" * 60)
    print("ENHANCED CP MECHANISM FLOW DIAGRAM")
    print("=" * 60)
    print("\n📊 Creating Enhanced Checkpointing mechanism flow diagram...")
    print("Similar to Request Replication (RR) architecture diagram\n")
    
    output_path = create_enhanced_cp_flow_diagram()
    
    print("\n" + "=" * 60)
    print("DIAGRAM GENERATION COMPLETE")
    print("=" * 60)
    print("\nThe diagram shows:")
    print("1. Request flow from user to Router CP")
    print("2. Pod information retrieval from Kubernetes API")
    print("3. Request forwarding to function pod")
    print("4. Asynchronous incremental checkpoint saving")
    print("5. Response delivery back to user")
    print("6. Recovery mechanism from checkpoint storage")
    print("\n✨ Enhanced CP provides:")
    print("   - 12.3% faster response time vs Basic CP")
    print("   - 14.7% better throughput during failures")
    print("   - 70% smaller checkpoint size")
    print("   - ~7s recovery time (53% faster)")
