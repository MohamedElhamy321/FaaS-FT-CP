#!/bin/bash

# This script demonstrates checkpointing recovery for the Fibonacci function.
# It assumes a Kubernetes cluster with Fission and Chaos Mesh installed.
# The fibonacci function should be deployed to Fission with checkpointing enabled.

FISSION_ROUTER_URL="http://localhost:8888/fibonacci" # Updated for port-forwarded router
FUNCTION_NAME="fibonacci-func"
NAMESPACE="default"

N_VALUE=100 # Calculate Fibonacci up to N_VALUE (make it long-running)

echo "--- Starting Checkpointing Demonstration ---"

# 1. Initial invocation of the long-running Fibonacci function
echo "\n--- Phase 1: Initial Fibonacci calculation (will be interrupted) ---"
echo "Invoking {FUNCTION_NAME} with N={N_VALUE}. This will run in the background."

# Send request in background to simulate long-running task
curl -s -X POST ${FISSION_ROUTER_URL} -d "${N_VALUE}" > /dev/null 2>&1 &
CURL_PID=$!

echo "Waiting for 30 seconds before injecting chaos..."
sleep 30

# 2. Inject Pod Kill Chaos
echo "\n--- Phase 2: Injecting Pod Kill Chaos ---"
echo "Applying pod_failure.yaml to kill the {FUNCTION_NAME} pod."
kubectl apply -f pod_failure.yaml

echo "Waiting for 10 seconds for chaos to take effect and pod to restart..."
sleep 10

# 3. Re-invoke the function and observe recovery
echo "\n--- Phase 3: Re-invoking Fibonacci function to observe recovery ---"
START_TIME=$(date +%s)
echo "Re-invoking {FUNCTION_NAME} with N={N_VALUE}."

RESPONSE=$(curl -s -X POST ${FISSION_ROUTER_URL} -d "${N_VALUE}")
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "\n--- Phase 4: Analysis ---"
echo "Function Response: ${RESPONSE}"
echo "Time taken for re-invocation (after chaos): ${DURATION} seconds"

# 4. Clean up Chaos experiment
echo "\n--- Phase 5: Cleaning up Chaos Mesh experiment ---"
kubectl delete -f pod_failure.yaml

echo "\n--- Demonstration Complete ---"
echo "To verify checkpointing, you would compare the logs of the fibonacci function pod."
echo "Look for 'Loaded checkpoint' messages in the logs of the new pod after the kill."
echo "kubectl logs -f <fibonacci-pod-name> -n fission"

# Example of how to run this script:
# 1. Ensure Minikube, Fission, and Chaos Mesh are installed and running.
# 2. Deploy the modified fibonacci.py to Fission.
# 3. Place pod_failure.yaml in /home/ubuntu/ (or adjust path in script).
# 4. Run: bash test_checkpoint_recovery.sh


