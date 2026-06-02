import argparse
import json
import matplotlib.pyplot as plt
from main import run_paper_experiment
import os

def plot_results(results, save_path=None):
    """Plot training results"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    epochs = range(1, len(results['train_losses']) + 1)
    
    # Plot losses
    ax1.plot(epochs, results['train_losses'], label='Train Loss', marker='o')
    ax1.plot(epochs, results['test_losses'], label='Test Loss', marker='s')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Test Loss')
    ax1.legend()
    ax1.grid(True)
    
    # Plot accuracy
    ax2.plot(epochs, results['test_accuracies'], label='Test Accuracy', marker='o', color='green')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.set_title('Test Accuracy')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Run Paper Code Experiments')
    parser.add_argument('--epochs', type=int, default=20, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size')
    parser.add_argument('--save_results', action='store_true', help='Save results to file')
    parser.add_argument('--plot', action='store_true', help='Generate plots')
    
    args = parser.parse_args()
    
    print("Paper Code Experiment Runner")
    print(f"Configuration: epochs={args.epochs}, batch_size={args.batch_size}")
    print("-" * 50)
    
    # Run experiment
    results = run_paper_experiment(num_epochs=args.epochs, batch_size=args.batch_size)
    
    # Save results if requested
    if args.save_results:
        os.makedirs('results', exist_ok=True)
        results_file = 'results/experiment_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {results_file}")
    
    # Generate plots if requested
    if args.plot:
        os.makedirs('results', exist_ok=True)
        plot_path = 'results/training_plots.png'
        plot_results(results, plot_path)
    
    print("\nExperiment completed successfully!")

if __name__ == "__main__":
    main()
