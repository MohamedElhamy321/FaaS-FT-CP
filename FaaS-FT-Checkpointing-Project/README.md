# FaaS Fault Tolerance with Checkpointing

This project demonstrates the implementation of checkpointing in a Function-as-a-Service (FaaS) environment using Fission on Kubernetes. The checkpointing mechanism allows long-running functions to resume from their last saved state after failures, significantly reducing recovery time.

## Project Structure

```
FaaS-FT-Checkpointing-Project/
├── fibo-app/
│   └── fibonacci.py              # Modified Fibonacci function with checkpointing
├── deploy-router/
│   ├── deploy-routerAS.yaml      # Active-Standby router deployment
│   └── deploy-routerRR.yaml      # Request Replication router deployment
├── monitoring-tools/
│   └── heapster.sh               # Monitoring setup script
├── test_checkpoint_recovery.sh   # Test script to demonstrate checkpointing
├── pod_failure.yaml              # Chaos Mesh pod failure configuration
├── node_failure.yaml             # Chaos Mesh node failure configuration
├── network_delay.yaml            # Chaos Mesh network delay configuration
├── tsung_workload.xml            # Tsung workload configuration
├── fission-deploy.sh             # Fission deployment script
├── helm-install.sh               # Helm installation script
├── install-pkg.sh                # Package installation script
├── k8s-install.sh                # Kubernetes installation script
├── kubelet.sh                    # Kubelet configuration script
├── master-config.sh              # Master node configuration script
├── reset-config.sh               # Reset configuration script
└── README.md                     # This file
```

## Key Features

### Checkpointing Implementation
- **File-based checkpointing**: Saves intermediate Fibonacci sequence to `/tmp/fibonacci_checkpoint.json`
- **Automatic recovery**: Function resumes from last checkpoint after failures
- **Periodic saves**: Checkpoints are saved every 10 iterations
- **Error handling**: Handles corrupted checkpoint files gracefully

### Test Scenarios
- **Pod failure simulation**: Uses Chaos Mesh to kill function pods
- **Recovery demonstration**: Shows function resuming from checkpoint
- **Performance comparison**: Measures recovery time with and without checkpointing

## Quick Start

1. **Prerequisites**: Ensure you have a Kubernetes cluster with Fission and Chaos Mesh installed
2. **Deploy the function**: Follow the deployment steps in `TESTING_GUIDE.md`
3. **Run the test**: Execute `./test_checkpoint_recovery.sh`
4. **Observe results**: Check function logs for checkpoint loading messages

## Files Description

- `fibonacci.py`: Enhanced Fibonacci function with checkpointing capabilities
- `test_checkpoint_recovery.sh`: Automated test script for demonstrating checkpointing benefits
- `pod_failure.yaml`: Chaos Mesh configuration for pod failure injection
- `tsung_workload.xml`: Load testing configuration for performance evaluation

For detailed setup and testing instructions, see `TESTING_GUIDE.md`.

