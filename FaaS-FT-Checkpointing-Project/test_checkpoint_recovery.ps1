# This script demonstrates checkpointing recovery for the Fibonacci function.
# It assumes a Kubernetes cluster with Fission and Chaos Mesh installed.
# The fibonacci function should be deployed to Fission with checkpointing enabled.

$FISSION_ROUTER_URL = "http://localhost:8888/fibonacci"
$FUNCTION_NAME = "fibonacci-func"
$NAMESPACE = "default"
$N_VALUE = 100  # Calculate Fibonacci up to N_VALUE (make it long-running)

Write-Host "--- Starting Checkpointing Demonstration ---"

# 1. Initial invocation of the long-running Fibonacci function
Write-Host "`n--- Phase 1: Initial Fibonacci calculation (will be interrupted) ---"
Write-Host "Invoking $FUNCTION_NAME with N=$N_VALUE. This will run in the background."

# Send request in background to simulate long-running task
$job = Start-Job -ScriptBlock { 
    param($url, $n)
    Invoke-WebRequest -Uri $url -Method POST -Body $n -ContentType 'application/x-www-form-urlencoded'
} -ArgumentList $FISSION_ROUTER_URL, $N_VALUE

Write-Host "Waiting for 30 seconds before injecting chaos..."
Start-Sleep -Seconds 30

# 2. Inject Pod Kill Chaos
Write-Host "`n--- Phase 2: Injecting Pod Kill Chaos ---"
Write-Host "Applying pod_failure.yaml to kill the $FUNCTION_NAME pod."
kubectl apply -f pod_failure.yaml

Write-Host "Waiting for 10 seconds for chaos to take effect and pod to restart..."
Start-Sleep -Seconds 10

# 3. Re-invoke the function and observe recovery
Write-Host "`n--- Phase 3: Re-invoking Fibonacci function to observe recovery ---"
$startTime = Get-Date
Write-Host "Re-invoking $FUNCTION_NAME with N=$N_VALUE."

$response = Invoke-WebRequest -Uri $FISSION_ROUTER_URL -Method POST -Body $N_VALUE -ContentType 'application/x-www-form-urlencoded'
$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "`n--- Phase 4: Analysis ---"
Write-Host "Function Response: $($response.Content)"
Write-Host "Time taken for re-invocation (after chaos): $duration seconds"

# 4. Clean up Chaos experiment
Write-Host "`n--- Phase 5: Cleaning up Chaos Mesh experiment ---"
kubectl delete -f pod_failure.yaml

Write-Host "`n--- Demonstration Complete ---"
Write-Host "To verify checkpointing, you would compare the logs of the fibonacci function pod."
Write-Host "Look for 'Loaded checkpoint' messages in the logs of the new pod after the kill."
Write-Host "kubectl logs -f <fibonacci-pod-name> -n fission"

# Example of how to run this script:
# 1. Ensure Minikube, Fission, and Chaos Mesh are installed and running.
# 2. Deploy the modified fibonacci.py to Fission.
# 3. Place pod_failure.yaml in the same directory as this script.
# 4. Run: .\test_checkpoint_recovery.ps1