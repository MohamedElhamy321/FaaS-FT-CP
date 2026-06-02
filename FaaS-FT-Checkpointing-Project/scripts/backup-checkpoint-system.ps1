#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Backup script for checkpoint system data
.DESCRIPTION
    Creates backups of all checkpoints and stores them with timestamp
.PARAMETER BackupPath
    Path where backups will be stored (default: ./backups)
.PARAMETER Namespace
    Kubernetes namespace (default: checkpoint-system)
#>

param(
    [string]$BackupPath = ".\backups",
    [string]$Namespace = "checkpoint-system"
)

$ErrorActionPreference = "Stop"

# Create backup directory with timestamp
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $BackupPath "checkpoint-backup-$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Write-Host "=" * 70
Write-Host "CHECKPOINT SYSTEM BACKUP"
Write-Host "=" * 70
Write-Host "Backup directory: $backupDir"
Write-Host "Namespace: $Namespace"
Write-Host ""

# 1. Backup ConfigMap
Write-Host "[1/5] Backing up ConfigMap..."
kubectl get configmap checkpoint-config -n $Namespace -o yaml > "$backupDir\configmap.yaml"
Write-Host "  ✓ ConfigMap backed up"

# 2. Backup PVC data
Write-Host "[2/5] Backing up PVC data..."
$pod = kubectl get pods -n $Namespace -l app=incremental-checkpoint -o jsonpath='{.items[0].metadata.name}'
if ($pod) {
    Write-Host "  Using pod: $pod"
    
    # Create tar of checkpoint data
    kubectl exec -n $Namespace $pod -- tar czf /tmp/checkpoints-backup.tar.gz -C /data checkpoints 2>$null
    
    # Copy from pod
    kubectl cp "${Namespace}/${pod}:/tmp/checkpoints-backup.tar.gz" "$backupDir\checkpoints-data.tar.gz"
    
    # Cleanup temp file
    kubectl exec -n $Namespace $pod -- rm /tmp/checkpoints-backup.tar.gz 2>$null
    
    Write-Host "  ✓ Checkpoint data backed up"
} else {
    Write-Host "  ⚠️  No pods found, skipping data backup"
}

# 3. Backup deployment configuration
Write-Host "[3/5] Backing up deployment configuration..."
kubectl get deployment checkpoint-manager -n $Namespace -o yaml > "$backupDir\deployment.yaml"
kubectl get service -n $Namespace -o yaml > "$backupDir\services.yaml"
kubectl get hpa -n $Namespace -o yaml > "$backupDir\hpa.yaml"
Write-Host "  ✓ Deployment configuration backed up"

# 4. Export current metrics snapshot
Write-Host "[4/5] Exporting metrics snapshot..."
try {
    $metricsData = Invoke-RestMethod -Uri "http://localhost:8080/health" -ErrorAction SilentlyContinue
    $metricsData | ConvertTo-Json -Depth 5 > "$backupDir\health-snapshot.json"
    Write-Host "  ✓ Health snapshot exported"
} catch {
    Write-Host "  ⚠️  Could not export metrics (service may not be port-forwarded)"
}

# 5. Create backup manifest
Write-Host "[5/5] Creating backup manifest..."
$manifest = @{
    timestamp = $timestamp
    namespace = $Namespace
    backup_path = $backupDir
    files = @(
        "configmap.yaml",
        "deployment.yaml",
        "services.yaml",
        "hpa.yaml",
        "checkpoints-data.tar.gz",
        "health-snapshot.json"
    )
    kubernetes_version = (kubectl version --short 2>$null)
}
$manifest | ConvertTo-Json -Depth 5 > "$backupDir\manifest.json"
Write-Host "  ✓ Manifest created"

Write-Host ""
Write-Host "=" * 70
Write-Host "✅ BACKUP COMPLETE!"
Write-Host "=" * 70
Write-Host "Backup location: $backupDir"
Write-Host ""

# Create latest symlink/copy
$latestPath = Join-Path $BackupPath "latest"
if (Test-Path $latestPath) {
    Remove-Item $latestPath -Recurse -Force
}
Copy-Item $backupDir $latestPath -Recurse
Write-Host "Latest backup: $latestPath"
