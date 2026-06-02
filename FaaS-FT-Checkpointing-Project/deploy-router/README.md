# Deploy Incremental Checkpoint System to Kubernetes

## Quick Deploy

```bash
# 1. Create namespace and resources
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/persistent-volume.yaml
kubectl apply -f kubernetes/configmap.yaml

# 2. Deploy application
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/servicemonitor.yaml

# 3. Verify deployment
kubectl get all -n checkpoint-system
kubectl rollout status deployment/checkpoint-manager -n checkpoint-system

# 4. Test health
kubectl port-forward svc/checkpoint-manager 8080:8080 -n checkpoint-system &
curl http://localhost:8080/health
```

## Canary Deployment

```bash
# Automated canary rollout with health checks
python canary-deploy.py \
  --namespace checkpoint-system \
  --deployment checkpoint-manager \
  --new-version v2.0.0 \
  --old-version v1.3.0
```

## Monitoring

```bash
# Import Grafana dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @../monitoring-tools/grafana-dashboard.json

# Deploy Prometheus alerts
kubectl apply -f ../monitoring-tools/prometheus-alerts.yaml

# Access metrics
kubectl port-forward svc/checkpoint-manager-metrics 9090:9090 -n checkpoint-system &
curl http://localhost:9090/metrics
```

## Complete Guide

See `DEPLOYMENT_GUIDE.md` for full deployment procedures, validation, and troubleshooting.
