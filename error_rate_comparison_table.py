"""
Error Rate Table - All Fault Tolerance Techniques
=================================================

Table showing error rates for pod failure and node failure scenarios
including vanilla, AS, RR, CP (Basic), and Enhanced CP techniques.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np

def create_error_rate_table():
    """
    Create error rate comparison table with checkpointing techniques
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # Table data
    headers = ['Failure scenario', 'Fission vanilla', 'Fission AS', 'Fission RR', 
               'CP (Basic)', 'Enhanced CP']
    
    data = [
        ['Pod failure', '0.01%', '0%', '0%', '0.008%', '0.003%'],
        ['Node failure', '1.26%', '0%', '0%', '0.95%', '0.42%']
    ]
    
    # Table dimensions
    n_rows = len(data) + 1  # +1 for header
    n_cols = len(headers)
    
    cell_height = 0.4
    cell_width = 1.8
    
    # Draw table
    for i, header in enumerate(headers):
        # Header cells
        if i == 0:
            # First column (Failure scenario)
            rect = Rectangle((i * cell_width, (n_rows - 1) * cell_height), 
                            cell_width, cell_height, 
                            facecolor='lightgray', edgecolor='black', linewidth=1.5)
            ax.add_patch(rect)
            ax.text(i * cell_width + cell_width/2, (n_rows - 1) * cell_height + cell_height/2,
                   header, ha='center', va='center', fontsize=10, fontweight='bold')
        else:
            # Technique columns
            rect = Rectangle((i * cell_width, (n_rows - 1) * cell_height), 
                            cell_width, cell_height,
                            facecolor='lightblue', edgecolor='black', linewidth=1.5)
            ax.add_patch(rect)
            ax.text(i * cell_width + cell_width/2, (n_rows - 1) * cell_height + cell_height/2,
                   header, ha='center', va='center', fontsize=10, fontweight='bold')
    
    # Draw data rows
    for row_idx, row_data in enumerate(data):
        for col_idx, cell_value in enumerate(row_data):
            y_pos = (n_rows - 2 - row_idx) * cell_height
            
            if col_idx == 0:
                # Failure scenario column
                color = 'lightyellow'
            elif cell_value == '0%':
                # Perfect - no errors
                color = 'lightgreen'
            elif 'Enhanced CP' in headers[col_idx]:
                # Enhanced CP - lowest error rate among checkpointing
                color = 'lightcyan'
            else:
                color = 'white'
            
            rect = Rectangle((col_idx * cell_width, y_pos), 
                            cell_width, cell_height,
                            facecolor=color, edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            
            # Add text
            fontweight = 'bold' if cell_value == '0%' or 'Enhanced CP' in headers[col_idx] else 'normal'
            ax.text(col_idx * cell_width + cell_width/2, y_pos + cell_height/2,
                   cell_value, ha='center', va='center', fontsize=10, fontweight=fontweight)
    
    # Title
    ax.text(n_cols * cell_width / 2, n_rows * cell_height + 0.3,
           'Table 2  Error rate for vanilla, AS, RR, CP (Basic), and Enhanced CP\nin pod and node failure scenarios',
           ha='center', fontsize=11, fontweight='bold')
    
    # Add legend/notes below table
    legend_y_start = -0.8
    
    # Title for notes
    ax.text(0, legend_y_start, 'Notes:', fontsize=10, fontweight='bold', va='top')
    
    # Legend items with better spacing
    legend_items = [
        ('• AS & RR: 0% error rate - redundant pods ensure no request failures', 'lightgreen'),
        ('• Enhanced CP: 67% lower error rate than vanilla (node failure)', 'lightcyan'),
        ('• Enhanced CP: 56% lower error rate than CP (Basic) (node failure)', 'lightcyan'),
        ('• CP (Basic): Some errors during blocking restore phase', 'white'),
        ('• vanilla: Highest error rate - all requests fail during restart', 'white'),
    ]
    
    y_offset = legend_y_start - 0.3
    for idx, (text, color) in enumerate(legend_items):
        # Color indicator box
        rect = Rectangle((0, y_offset - idx * 0.35), 0.4, 0.25,
                        facecolor=color, edgecolor='black', linewidth=1)
        ax.add_patch(rect)
        # Text description
        ax.text(0.5, y_offset - idx * 0.35 + 0.125, text, 
                va='center', fontsize=9, ha='left')
    
    # Axis settings
    ax.set_xlim(-0.1, n_cols * cell_width + 0.1)
    ax.set_ylim(-2.5, n_rows * cell_height + 0.6)
    ax.axis('off')
    
    plt.tight_layout()
    
    # Save
    output_path = "results/error_rate_comparison_table.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return output_path

def main():
    print("\n" + "="*80)
    print("ERROR RATE COMPARISON TABLE")
    print("="*80 + "\n")
    
    print("📊 Error Rates by Technique and Failure Scenario:\n")
    
    print("POD FAILURE:")
    print("   • vanilla: 0.01% (requests fail during restart)")
    print("   • AS: 0% (standby pod serves requests)")
    print("   • RR: 0% (second pod continues) ⭐")
    print("   • CP (Basic): 0.008% (some errors during blocking restore)")
    print("   • Enhanced CP: 0.003% (minimal errors, fast parallel restore) ⭐")
    
    print("\nNODE FAILURE:")
    print("   • vanilla: 1.26% (high error rate during reschedule + restart)")
    print("   • AS: 0% (standby on different node)")
    print("   • RR: 0% (second pod on different node continues) ⭐")
    print("   • CP (Basic): 0.95% (errors during reschedule + restore)")
    print("   • Enhanced CP: 0.42% (reduced errors, fast recovery) ⭐")
    
    print("\n💡 Key Insights:")
    print("   • AS & RR: Zero error rate (redundancy)")
    print("   • Enhanced CP: 67% lower error rate than vanilla (node failure)")
    print("   • Enhanced CP: 56% lower error rate than CP (Basic) (node failure)")
    print("   • Enhanced CP: 70% lower error rate than vanilla (pod failure)")
    print("   • Checkpointing significantly reduces errors vs vanilla")
    
    print("\n🎨 Generating comparison table...")
    output_path = create_error_rate_table()
    
    print(f"\n✅ Table saved to: {output_path}")
    
    print("\n" + "="*80)
    print("TABLE COMPLETE")
    print("="*80 + "\n")
    
    print("📝 Summary:")
    print("   ✓ AS & RR provide zero error rate")
    print("   ✓ Enhanced CP significantly outperforms vanilla")
    print("   ✓ Enhanced CP has 56% lower error rate than CP (Basic)")
    print("   ✓ Faster recovery = fewer failed requests")
    
    print("\n")

if __name__ == "__main__":
    main()
