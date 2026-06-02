# Production Deployment Guide

Complete checklist and runbook for deploying the incremental checkpoint system to production.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Validation](#post-deployment-validation)
5. [Monitoring Setup](#monitoring-setup)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

### 1. Requirements Verification

- [ ] **Kubernetes Cluster**: v1.21+ available
- [ ] **Storage**: 50GB+ persistent volume available
- [ ] **Resources**: Sufficient CPU/memory (3 pods × 2GB RAM, 2 CPU each)
- [ ] **Python**: 3.7+ available in container images
- [ ] **Monitoring**: Prometheus and Grafana installed
- [ ] **Network**: Service mesh (optional, for canary deployments)

### 2. Access & Permissions

- [ ] kubectl configured and authenticated
- [ ] Access to container registry
- [ ] Permissions to create namespace, deployments, services
- [ ] Access to Prometheus and Grafana
- [ ] SSH access to cluster nodes (for debugging)

### 3. Configuration Review

- [ ] Review `configmap.yaml` settings
- [ ] Adjust resource limits based on workload
- [ ] Configure persistent volume path
- [ ] Set up backup strategy for checkpoints
- [ ] Review logging configuration

### 4. Testing Validation

- [ ] All 106 unit tests passing locally
- [ ] Integration tests successful
- [ ] Performance benchmarks meet targets (1.90ms checkpoint, 2.00ms restore)
- [ ] Load testing completed
- [ ] Chaos testing performed (pod failures, network issues)

### 5. Documentation

- [ ] Architecture diagram available
- [ ] API documentation accessible
- [ ] Runbook prepared
- [ ] On-call team briefed
- [ ] Rollback plan documented

### 6. Monitoring & Alerting

- [ ] Prometheus scraping configured
- [ ] Alert rules deployed
- [ ] Grafana dashboard imported
- [ ] PagerDuty/Opsgenie integration configured
- [ ] Alert routing configured

### 7. Backup & Recovery

- [ ] Backup strategy defined
- [ ] Recovery procedures documented
- [ ] Backup retention policy set
- [ ] Restore testing completed

---

## Infrastructure Setup

### Step 1: Create Namespace

```bash
# Create namespace
kubectl apply -f deploy-router/kubernetes/namespace.yaml

# Verify
kubectl get namespace checkpoint-system
```

**Expected Output:**
```
NAME                 STATUS   AGE
checkpoint-system    Active   5s
```

### Step 2: Set Up Storage

```bash
# Create persistent volume and claim
kubectl apply -f deploy-router/kubernetes/persistent-volume.yaml

# Verify
kubectl get pv,pvc -n checkpoint-system
```

**Expected Output:**
```
NAME                              CAPACITY   ACCESS MODES   STATUS   CLAIM
persistentvolume/checkpoint-pv    50Gi       RWX            Bound    checkpoint-system/checkpoint-pvc

NAME                                   STATUS   VOLUME          CAPACITY   ACCESS MODES
persistentvolumeclaim/checkpoint-pvc   Bound    checkpoint-pv   50Gi       RWX
```

**Validation:**
- [ ] PV created and bound
- [ ] PVC bound to PV
- [ ] Storage accessible from nodes

### Step 3: Deploy Configuration

```bash
# Apply ConfigMap
kubectl apply -f deploy-router/kubernetes/configmap.yaml

# Verify
kubectl get configmap -n checkpoint-system
kubectl describe configmap checkpoint-config -n checkpoint-system
```

**Validation:**
- [ ] ConfigMap created
- [ ] Configuration values correct
- [ ] Logging configuration present

### Step 4: Build and Push Container Image

```bash
# Build image
docker build -t checkpoint-system:v1.3.0 .

# Tag for registry
docker tag checkpoint-system:v1.3.0 your-registry/checkpoint-system:v1.3.0

# Push to registry
docker push your-registry/checkpoint-system:v1.3.0
```

**Validation:**
- [ ] Image built successfully
- [ ] Image pushed to registry
- [ ] Image pullable from cluster

---

## Deployment Steps

### Option A: Full Deployment (For New Installations)

```bash
# Deploy all resources
kubectl apply -f deploy-router/kubernetes/deployment.yaml
kubectl apply -f deploy-router/kubernetes/service.yaml
kubectl apply -f deploy-router/kubernetes/hpa.yaml
kubectl apply -f deploy-router/kubernetes/servicemonitor.yaml

# Wait for rollout
kubectl rollout status deployment/checkpoint-manager -n checkpoint-system

# Verify pods
kubectl get pods -n checkpoint-system -l app=incremental-checkpoint
```

**Expected Output:**
```
NAME                                  READY   STATUS    RESTARTS   AGE
checkpoint-manager-7d9c8f5b6d-abc12   1/1     Running   0          2m
checkpoint-manager-7d9c8f5b6d-def34   1/1     Running   0          2m
checkpoint-manager-7d9c8f5b6d-ghi56   1/1     Running   0          2m
```

### Option B: Canary Deployment (For Updates)

```bash
# Run canary deployment script
python deploy-router/canary-deploy.py \
  --namespace checkpoint-system \
  --deployment checkpoint-manager \
  --new-version v1.3.0 \
  --old-version v1.2.0

# Script will automatically:
# 1. Validate current system
# 2. Deploy 5% canary
# 3. Expand to 25%, 50%, 100%
# 4. Rollback on failure
```

**Deployment Timeline:**
- Validation: 5 minutes
- Canary 5%: 10 minutes
- Canary 25%: 10 minutes
- Canary 50%: 10 minutes
- Full rollout: 10 minutes
- **Total: ~45 minutes**

---

## Post-Deployment Validation

### 1. Pod Health Checks

```bash
# Check pod status
kubectl get pods -n checkpoint-system

# Check pod logs
kubectl logs -f deployment/checkpoint-manager -n checkpoint-system

# Check for errors
kubectl logs deployment/checkpoint-manager -n checkpoint-system | grep ERROR
```

**Success Criteria:**
- [ ] All pods in `Running` state
- [ ] No crash loops
- [ ] No error logs
- [ ] Health checks passing

### 2. Service Verification

```bash
# Check services
kubectl get svc -n checkpoint-system

# Test HTTP endpoint
kubectl port-forward svc/checkpoint-manager 8080:8080 -n checkpoint-system
curl http://localhost:8080/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.3.0",
  "checkpoint_count": 0,
  "storage_used_mb": 0.0
}
```

**Success Criteria:**
- [ ] Services created
- [ ] Endpoints available
- [ ] Health endpoint returns 200
- [ ] Metrics endpoint returns data

### 3. Metrics Validation

```bash
# Check metrics endpoint
kubectl port-forward svc/checkpoint-manager-metrics 9090:9090 -n checkpoint-system
curl http://localhost:9090/metrics
```

**Expected Metrics:**
```
# HELP checkpoint_creation_total Total number of checkpoints created
# TYPE checkpoint_creation_total counter
checkpoint_creation_total{checkpoint_type="FULL",status="success"} 0

# HELP checkpoint_health_status Health status
# TYPE checkpoint_health_status gauge
checkpoint_health_status 1
```

**Success Criteria:**
- [ ] Metrics endpoint accessible
- [ ] All expected metrics present
- [ ] Health status = 1 (healthy)

### 4. Functional Testing

```bash
# Run functional tests
python tests/run_integration_tests.py --env=production

# Test checkpoint creation
python -c "
from incremental_checkpoint import ProductionCheckpointManager
manager = ProductionCheckpointManager('/data/checkpoints')
state = {'test': 'data'}
checkpoint = manager.create_checkpoint(state)
restored = manager.restore_state(checkpoint.checkpoint_id)
assert restored == state
print('✅ Functional test passed')
"
```

**Success Criteria:**
- [ ] Integration tests pass
- [ ] Can create checkpoints
- [ ] Can restore from checkpoints
- [ ] Performance within SLA (< 10ms)

### 5. Performance Validation

Check Grafana dashboard or query Prometheus:

```bash
# Average checkpoint creation time
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(checkpoint_creation_duration_seconds_sum[5m])/rate(checkpoint_creation_duration_seconds_count[5m])'

# Error rate
curl -G 'http://prometheus:9090/api/v1/query' \
  --data-urlencode 'query=rate(checkpoint_errors_total[5m])'
```

**Success Criteria:**
- [ ] Average checkpoint time < 5ms
- [ ] P95 latency < 10ms
- [ ] P99 latency < 50ms
- [ ] Error rate < 1%
- [ ] Throughput > 10/sec
- [ ] Cache hit rate > 90%

---

## Monitoring Setup

### 1. Grafana Dashboard

```bash
# Import dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring-tools/grafana-dashboard.json
```

**Dashboard URL:** `http://grafana:3000/d/checkpoint-system`

**Panels to Monitor:**
- Checkpoint creation rate
- Checkpoint creation duration (p50, p95, p99)
- Storage usage
- Error rate
- Cache hit rate
- Health status

### 2. Alert Rules

```bash
# Deploy Prometheus alerts
kubectl apply -f monitoring-tools/prometheus-alerts.yaml

# Verify alerts loaded
curl http://prometheus:9090/api/v1/rules | jq '.data.groups[] | select(.name=="checkpoint_alerts")'
```

**Critical Alerts:**
- [ ] CheckpointSystemUnhealthy
- [ ] HighCheckpointErrorRate
- [ ] CriticalStorageUsage
- [ ] CheckpointPodDown

**Warning Alerts:**
- [ ] SlowCheckpointCreation
- [ ] HighStorageUsage
- [ ] LowCacheHitRate
- [ ] InsufficientCheckpointReplicas

### 3. Alert Testing

```bash
# Test alert firing (temporarily break health)
kubectl exec -it deployment/checkpoint-manager -n checkpoint-system -- \
  touch /tmp/force-unhealthy

# Wait 2 minutes, verify alert fires in Prometheus
# Remove test condition
kubectl exec -it deployment/checkpoint-manager -n checkpoint-system -- \
  rm /tmp/force-unhealthy
```

**Success Criteria:**
- [ ] Alert fires within 2 minutes
- [ ] Alert resolves when condition cleared
- [ ] Notification sent (email/Slack/PagerDuty)

---

## Rollback Procedures

### Automatic Rollback (via Canary Script)

The canary deployment script automatically rolls back on failure. No manual intervention needed.

### Manual Rollback

If manual rollback is needed:

```bash
# Rollback to previous version
kubectl rollout undo deployment/checkpoint-manager -n checkpoint-system

# Check rollback status
kubectl rollout status deployment/checkpoint-manager -n checkpoint-system

# Verify pods running old version
kubectl get pods -n checkpoint-system -o jsonpath='{.items[*].spec.containers[*].image}'
```

**Rollback Timeline:** ~5 minutes

### Emergency Rollback (Critical Issue)

```bash
# Scale down deployment immediately
kubectl scale deployment checkpoint-manager --replicas=0 -n checkpoint-system

# Fix issue (update config, image, etc.)
# ...

# Scale back up
kubectl scale deployment checkpoint-manager --replicas=3 -n checkpoint-system
```

### Rollback Validation

After rollback, verify:

- [ ] All pods running
- [ ] Health checks passing
- [ ] Metrics being collected
- [ ] No errors in logs
- [ ] Performance restored

---

## Troubleshooting

### Issue: Pods Not Starting

**Symptoms:**
- Pods stuck in `Pending` or `CrashLoopBackOff`

**Diagnosis:**
```bash
kubectl describe pod <pod-name> -n checkpoint-system
kubectl logs <pod-name> -n checkpoint-system --previous
```

**Common Causes:**
1. **Insufficient resources:** Check node resources
2. **Image pull error:** Verify image exists in registry
3. **Volume mount failure:** Check PVC status
4. **Configuration error:** Review ConfigMap

**Solutions:**
```bash
# Check node resources
kubectl top nodes

# Check PVC
kubectl get pvc -n checkpoint-system

# Fix image pull
kubectl create secret docker-registry regcred \
  --docker-server=<your-registry> \
  --docker-username=<username> \
  --docker-password=<password> \
  -n checkpoint-system
```

### Issue: High Error Rate

**Symptoms:**
- Error rate > 5%
- Alert: `HighCheckpointErrorRate`

**Diagnosis:**
```bash
# Check error logs
kubectl logs deployment/checkpoint-manager -n checkpoint-system | grep ERROR

# Check metrics
curl http://prometheus:9090/api/v1/query?query=checkpoint_errors_total
```

**Solutions:**
1. Check storage health
2. Verify configuration
3. Review resource limits
4. Check for network issues

### Issue: Slow Performance

**Symptoms:**
- P95 latency > 10ms
- Alert: `SlowCheckpointCreation`

**Diagnosis:**
```bash
# Check resource usage
kubectl top pods -n checkpoint-system

# Check bottlenecks via logs
kubectl logs deployment/checkpoint-manager -n checkpoint-system | grep "bottleneck"
```

**Solutions:**
1. Increase CPU/memory limits
2. Reduce compression level
3. Enable parallel compression
4. Check storage I/O performance

### Issue: Storage Full

**Symptoms:**
- Alert: `CriticalStorageUsage`
- Cannot create new checkpoints

**Diagnosis:**
```bash
# Check storage usage
kubectl exec -it deployment/checkpoint-manager -n checkpoint-system -- \
  du -sh /data/checkpoints
```

**Solutions:**
```bash
# Manual cleanup
kubectl exec -it deployment/checkpoint-manager -n checkpoint-system -- \
  python -c "
from incremental_checkpoint import ProductionCheckpointManager
manager = ProductionCheckpointManager('/data/checkpoints')
history = manager.get_checkpoint_history()
# Keep only last 50
for cp_id in history[:-50]:
    manager.delete_checkpoint(cp_id)
"

# Or increase PV size
kubectl patch pvc checkpoint-pvc -n checkpoint-system \
  -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'
```

---

## Deployment Sign-Off

Before considering deployment complete, ensure all items checked:

### ✅ Pre-Deployment
- [ ] All tests passing
- [ ] Configuration reviewed
- [ ] Team briefed
- [ ] Monitoring configured

### ✅ Deployment
- [ ] Pods running healthy
- [ ] Services accessible
- [ ] Metrics collecting
- [ ] No errors in logs

### ✅ Validation
- [ ] Functional tests pass
- [ ] Performance within SLA
- [ ] Alerts configured
- [ ] Dashboard accessible

### ✅ Documentation
- [ ] Deployment documented
- [ ] Runbook available
- [ ] Team trained
- [ ] Rollback tested

---

## Quick Reference

### Useful Commands

```bash
# Check deployment status
kubectl get all -n checkpoint-system

# View logs
kubectl logs -f deployment/checkpoint-manager -n checkpoint-system

# Port forward for debugging
kubectl port-forward svc/checkpoint-manager 8080:8080 -n checkpoint-system

# Execute command in pod
kubectl exec -it deployment/checkpoint-manager -n checkpoint-system -- bash

# Check metrics
curl http://localhost:9090/metrics

# Health check
curl http://localhost:8080/health

# Scale deployment
kubectl scale deployment checkpoint-manager --replicas=5 -n checkpoint-system

# Restart deployment
kubectl rollout restart deployment/checkpoint-manager -n checkpoint-system
```

### Contact Information

- **On-Call Engineer:** [Contact Info]
- **Team Slack:** #checkpoint-system
- **Documentation:** https://docs.example.com/checkpoint-system
- **Dashboard:** http://grafana:3000/d/checkpoint-system
- **Prometheus:** http://prometheus:9090

---

**Deployment Version:** 2.0.0  
**Last Updated:** November 24, 2025  
**Next Review:** December 2025
