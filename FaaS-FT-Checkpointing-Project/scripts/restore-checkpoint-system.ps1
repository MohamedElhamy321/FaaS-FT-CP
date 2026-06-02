#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Restore script for checkpoint system data
.DESCRIPTION
    Restores checkpoints and configuration from backup
.PARAMETER BackupPath
    Path to backup directory to restore from
.PARAMETER Namespace
    Kubernetes namespace (default: checkpoint-system)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupPath,
    [string]$Namespace = "checkpoint-system"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupPath)) {
    Write-Host "❌ Backup path not found: $BackupPath"
    exit 1
}

Write-Host "=" * 70
Write-Host "CHECKPOINT SYSTEM RESTORE"
Write-Host "=" * 70
Write-Host "Backup source: $BackupPath"
Write-Host "Namespace: $Namespace"
Write-Host ""

# Read manifest
$manifestPath = Join-Path $BackupPath "manifest.json"
if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath | ConvertFrom-Json
    Write-Host "Backup timestamp: $($manifest.timestamp)"
    Write-Host ""
}

# Confirm restore
$confirmation = Read-Host "This will restore data to namespace '$Namespace'. Continue? (yes/no)"
if ($confirmation -ne "yes") {
    Write-Host "Restore cancelled"
    exit 0
}

# 1. Restore ConfigMap
Write-Host "[1/4] Restoring ConfigMap..."
$configmapPath = Join-Path $BackupPath "configmap.yaml"
if (Test-Path $configmapPath) {
    kubectl apply -f $configmapPath
    Write-Host "  ✓ ConfigMap restored"
} else {
    Write-Host "  ⚠️  ConfigMap backup not found"
}

# 2. Restore PVC data
Write-Host "[2/4] Restoring checkpoint data..."
$dataPath = Join-Path $BackupPath "checkpoints-data.tar.gz"
if (Test-Path $dataPath) {
    # Get a running pod
    $pod = kubectl get pods -n $Namespace -l app=incremental-checkpoint -o jsonpath='{.items[0].metadata.name}'
    
    if ($pod) {
        Write-Host "  Using pod: $pod"
        
        # Copy backup to pod
        kubectl cp $dataPath "${Namespace}/${pod}:/tmp/checkpoints-backup.tar.gz"
        
        # Extract in pod
        kubectl exec -n $Namespace $pod -- tar xzf /tmp/checkpoints-backup.tar.gz -C /data
        
        # Cleanup
        kubectl exec -n $Namespace $pod -- rm /tmp/checkpoints-backup.tar.gz
        
        Write-Host "  ✓ Checkpoint data restored"
    } else {
        Write-Host "  ⚠️  No pods found. Deploy the application first, then retry restore."
    }
} else {
    Write-Host "  ⚠️  Checkpoint data backup not found"
}

# 3. Restart pods to pick up changes
Write-Host "[3/4] Restarting pods..."
kubectl rollout restart deployment/checkpoint-manager -n $Namespace
kubectl rollout status deployment/checkpoint-manager -n $Namespace --timeout=120s
Write-Host "  ✓ Pods restarted"

# 4. Verify restore
Write-Host "[4/4] Verifying restore..."
Start-Sleep -Seconds 10

try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -ErrorAction SilentlyContinue
    Write-Host "  ✓ Service is healthy"
    Write-Host "  ✓ Checkpoint count: $($health.checkpoint_count)"
} catch {
    Write-Host "  ⚠️  Could not verify (service may not be port-forwarded)"
}

Write-Host ""
Write-Host "=" * 70
Write-Host "✅ RESTORE COMPLETE!"
Write-Host "=" * 70
