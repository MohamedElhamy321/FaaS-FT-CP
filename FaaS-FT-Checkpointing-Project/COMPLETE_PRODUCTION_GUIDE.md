# Complete Production Deployment Guide
**Incremental Checkpoint System v2.0.0**

## Overview
This guide covers the complete production deployment including all optional enhancements:
1. ✅ Grafana Dashboard Integration
2. ✅ Prometheus Alerts Configuration
3. ✅ Load Testing Validation
4. ✅ Automated Backup System
5. ✅ Log Aggregation (Loki)
6. ✅ Fission FaaS Integration

---

## 1. Grafana Dashboard Setup

### Access Grafana
```bash
# Get Grafana URL
minikube service grafana -n monitoring --url

# Default credentials
Username: admin
Password: admin
```

### Import Checkpoint Dashboard
1. Login to Grafana
2. Navigate to **Dashboards → Import**
3. Upload `monitoring-tools/grafana-dashboard.json`
4. Select **Prometheus** as datasource
5. Click **Import**

**Dashboard Features:**
- 13 visualization panels
- Real-time metrics for:
  - Checkpoint creation rate (FULL vs INCR)
  - Latency percentiles (P50/P95/P99)
  - Storage usage and compression ratio
  - Cache hit rate
  - Error tracking
  - System health status

### Add Loki Datasource (for logs)
1. Navigate to **Configuration → Data Sources**
2. Add **Loki** datasource
3. URL: `http://loki.monitoring.svc.cluster.local:3100`
4. Click **Save & Test**

---

## 2. Prometheus Alerts

### Deploy Alert Rules
```bash
kubectl create configmap prometheus-alerts \
  --from-file=monitoring-tools/prometheus-alerts.yaml \
  -n monitoring

# Restart Prometheus to pick up alerts
kubectl rollout restart deployment/prometheus -n monitoring
```

### Alert Categories (20+ rules)
- **Performance**: SlowCheckpointCreation, VerySlowCheckpointCreation
- **Errors**: HighCheckpointErrorRate, CheckpointCreationFailures
- **Storage**: HighStorageUsage, CriticalStorageUsage, TooManyCheckpoints
- **Health**: CheckpointSystemUnhealthy, NoRecentCheckpoints
- **Cache**: LowCacheHitRate, VeryLowCacheHitRate
- **Resources**: HighMemoryUsage, HighCPUUsage, CheckpointPodDown

### View Alerts
```bash
# Access Prometheus UI
minikube service prometheus -n monitoring --url

# Navigate to: Status → Rules
```

---

## 3. Load Testing Results

### Automated Load Tests
```bash
cd tests
python load_test.py
```

### Test Scenarios
1. **Concurrent Load**: 1000 requests, 10 threads
2. **Sustained Load**: 30s @ 20 req/s
3. **Stress Test**: Gradual increase to find limits

### Expected Performance
- **Throughput**: 12-50 req/s (depends on infrastructure)
- **Latency P95**: < 20ms
- **Latency P99**: < 50ms
- **Success Rate**: > 95%

### Results Location
- `tests/load_test_results.json`
- `tests/production_performance_results.json`

---

## 4. Automated Backup System

### Deploy Backup CronJob
```bash
kubectl apply -f deploy-router/kubernetes/backup-cronjob.yaml
```

### Backup Schedule
- **Frequency**: Daily at 2:00 AM
- **Retention**: 7 days
- **Storage**: 10Gi PVC

### What's Backed Up
- ConfigMaps
- Deployments
- Services
- HPA configuration
- Checkpoint data (tar.gz)
- Backup manifest

### Manual Backup
```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/backup-checkpoint-system.ps1

# Location
.\backups\checkpoint-backup-YYYYMMDD-HHMMSS\
```

### Restore from Backup
```powershell
powershell -ExecutionPolicy Bypass -File scripts/restore-checkpoint-system.ps1 `
  -BackupPath ".\backups\latest"
```

### Verify Backup
```bash
kubectl get cronjob checkpoint-backup -n checkpoint-system
kubectl get jobs -n checkpoint-system
kubectl logs job/checkpoint-backup-XXXXXXXX -n checkpoint-system
```

---

## 5. Log Aggregation with Loki

### Deploy Loki Stack
```bash
kubectl apply -f monitoring-tools/loki-deployment.yaml
```

### Components
- **Loki**: Log aggregation system
- **Promtail**: Log collector (DaemonSet on all nodes)

### Query Logs in Grafana
1. Add Loki datasource (see section 1)
2. Navigate to **Explore**
3. Select **Loki** datasource
4. Example queries:
```logql
# All checkpoint-system logs
{namespace="checkpoint-system"}

# Only error logs
{namespace="checkpoint-system"} |= "ERROR"

# Checkpoint creation logs
{namespace="checkpoint-system"} |= "Checkpoint created"

# Filter by pod
{namespace="checkpoint-system",pod=~"checkpoint-manager.*"}
```

### Log Retention
- **Default**: In-memory (pod lifetime)
- **Production**: Configure persistent storage for Loki

---

## 6. Fission FaaS Integration

### Integration Module
Location: `fission_integration.py`

### Features
- **Automatic Checkpointing**: Decorators for functions
- **State Management**: Persistent state across invocations
- **Automatic Recovery**: Restore from last checkpoint on failure
- **Manual Checkpoints**: API endpoints for control

### Usage Example

#### 1. Create Fission Environment
```bash
fission environment create --name python-checkpoint \
  --image fission/python-env:latest \
  --builder fission/python-builder:latest
```

#### 2. Deploy Checkpoint-Enabled Function
```python
# fibonacci_function.py
from fission_integration import checkpoint_decorator

@checkpoint_decorator(checkpoint_interval=5)
def main(state, context):
    # Initialize state
    if 'cache' not in state:
        state['cache'] = {0: 0, 1: 1}
    
    n = int(context.request.get_json().get('n', 10))
    
    # Compute Fibonacci
    def fib(num):
        if num not in state['cache']:
            state['cache'][num] = fib(num-1) + fib(num-2)
        return state['cache'][num]
    
    return {
        "n": n,
        "fibonacci": fib(n),
        "cache_size": len(state['cache'])
    }
```

#### 3. Create Fission Function
```bash
fission function create --name fibonacci-cp \
  --env python-checkpoint \
  --code fibonacci_function.py \
  --entrypoint main
```

#### 4. Create HTTP Trigger
```bash
fission httptrigger create --name fibonacci-trigger \
  --url /fibonacci \
  --function fibonacci-cp
```

#### 5. Test Function
```bash
curl -X POST http://$FISSION_ROUTER/fibonacci \
  -H "Content-Type: application/json" \
  -d '{"n": 10}'
```

### Available Functions in Integration Module
1. **fibonacci_with_checkpoint**: Fibonacci calculator with state
2. **stateful_counter**: Simple counter with history
3. **checkpoint_create_endpoint**: Manual checkpoint creation
4. **checkpoint_restore_endpoint**: Manual checkpoint restoration
5. **checkpoint_list_endpoint**: List all checkpoints
6. **health_check**: Function health status

### Checkpoint Behavior
- **Automatic**: Checkpoint every N invocations (configurable)
- **On Error**: Automatic recovery from last checkpoint
- **Persistence**: Checkpoints stored in configured directory
- **Performance**: Minimal overhead (~1-5ms per checkpoint)

---

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  checkpoint-system namespace                          │  │
│  │  - checkpoint-manager (3 replicas)                    │  │
│  │  - HPA (3-10 replicas)                                │  │
│  │  - PVC (50Gi)                                         │  │
│  │  - Network Policy                                     │  │
│  │  - Resource Quotas                                    │  │
│  │  - Backup CronJob (daily 2 AM)                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  monitoring namespace                                 │  │
│  │  - Prometheus (metrics)                               │  │
│  │  - Grafana (dashboards)                               │  │
│  │  - Loki (log aggregation)                             │  │
│  │  - Promtail (log collection)                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  fission namespace (optional)                         │  │
│  │  - Fission functions with checkpointing              │  │
│  │  - Router/Controller                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Access URLs

### Services
```bash
# Checkpoint System API
kubectl port-forward svc/checkpoint-manager -n checkpoint-system 8080:8080
http://localhost:8080/health
http://localhost:8080/metrics
http://localhost:8080/checkpoint  # POST to create
http://localhost:8080/checkpoints  # GET to list

# Prometheus
minikube service prometheus -n monitoring --url

# Grafana
minikube service grafana -n monitoring --url
# Credentials: admin/admin

# Loki (internal only)
# Access through Grafana Explore
```

---

## Validation Checklist

### Deployment Validation
- [ ] All pods running in checkpoint-system namespace
- [ ] All pods running in monitoring namespace
- [ ] Services accessible (checkpoint-manager, prometheus, grafana)
- [ ] PVCs bound (checkpoint-pvc, backup-pvc)
- [ ] HPA configured and active

### Monitoring Validation
- [ ] Prometheus scraping checkpoint-manager metrics
- [ ] Grafana dashboard imported and displaying data
- [ ] Prometheus alerts loaded
- [ ] Loki receiving logs
- [ ] Promtail collecting from all pods

### Functionality Validation
- [ ] Health endpoint returns healthy
- [ ] Checkpoint creation working (FULL & INCR)
- [ ] Checkpoint restoration working
- [ ] Metrics endpoint accessible
- [ ] Performance within targets

### Security Validation
- [ ] Network policies applied
- [ ] Resource quotas enforced
- [ ] Limit ranges applied
- [ ] Service accounts configured
- [ ] RBAC roles created

### Backup Validation
- [ ] CronJob scheduled
- [ ] Backup PVC created
- [ ] Manual backup script works
- [ ] Restore script works
- [ ] Backup retention working

---

## Troubleshooting

### Pods Not Starting
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

### Metrics Not Appearing
```bash
# Check Prometheus targets
kubectl port-forward svc/prometheus -n monitoring 9090:9090
# Navigate to: Status → Targets

# Check ServiceMonitor
kubectl get servicemonitor -n checkpoint-system
```

### Backup Failures
```bash
# Check CronJob status
kubectl get cronjobs -n checkpoint-system
kubectl get jobs -n checkpoint-system
kubectl logs job/<job-name> -n checkpoint-system
```

### Loki Not Receiving Logs
```bash
# Check Promtail pods
kubectl get pods -n monitoring -l app=promtail
kubectl logs <promtail-pod> -n monitoring

# Test Loki
kubectl port-forward svc/loki -n monitoring 3100:3100
curl http://localhost:3100/ready
```

---

## Performance Tuning

### Scale Checkpoint Manager
```bash
kubectl scale deployment checkpoint-manager -n checkpoint-system --replicas=5
```

### Adjust HPA Thresholds
```bash
kubectl edit hpa checkpoint-manager-hpa -n checkpoint-system
```

### Increase Storage
```bash
kubectl edit pvc checkpoint-pvc -n checkpoint-system
# Update storage request
```

---

## Maintenance

### Weekly Tasks
- Review Grafana dashboards for anomalies
- Check Prometheus alerts
- Verify backup completion
- Review log patterns in Loki

### Monthly Tasks
- Review resource usage and adjust quotas
- Test restore procedure
- Update dashboard/alert thresholds
- Performance benchmarking

### As Needed
- Scale replicas based on load
- Cleanup old checkpoints
- Update checkpoint system version
- Rotate backup storage

---

## Support & Documentation

### Files Reference
- `DEPLOYMENT_GUIDE.md` - Core deployment
- `PRODUCTION_DEPLOYMENT.md` - Quick start
- `TROUBLESHOOTING.md` - Common issues
- `API_REFERENCE.md` - API documentation
- `TESTING_GUIDE.md` - Testing procedures

### Test Scripts
- `tests/production_performance_test.py` - Performance validation
- `tests/test_integration.py` - Integration tests
- `tests/load_test.py` - Load testing

### Scripts
- `scripts/backup-checkpoint-system.ps1` - Backup script
- `scripts/restore-checkpoint-system.ps1` - Restore script
- `deploy-production.sh/bat` - Automated deployment

---

## Summary

All 6 optional enhancements have been implemented:
1. ✅ **Grafana Dashboard**: 13-panel monitoring dashboard
2. ✅ **Prometheus Alerts**: 20+ alert rules across 6 categories
3. ✅ **Load Testing**: Comprehensive performance validation
4. ✅ **Automated Backups**: Daily CronJob with 7-day retention
5. ✅ **Log Aggregation**: Loki + Promtail stack deployed
6. ✅ **Fission Integration**: Complete FaaS checkpointing module

**System Status: Production Ready with Full Observability** 🎉
