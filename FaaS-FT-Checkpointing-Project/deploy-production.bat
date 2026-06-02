@echo off
REM Production Deployment Script for Incremental Checkpoint System (Windows)
REM Run this script to deploy to production

echo ==================================
echo Production Deployment Starting
echo ==================================
echo.

REM Configuration
set NAMESPACE=checkpoint-system
set DEPLOYMENT_NAME=checkpoint-manager
set VERSION=v2.0.0

echo Deployment Configuration:
echo   Namespace: %NAMESPACE%
echo   Deployment: %DEPLOYMENT_NAME%
echo   Version: %VERSION%
echo.

REM Step 1: Create namespace
echo Step 1/7: Creating namespace...
kubectl apply -f deploy-router\kubernetes\namespace.yaml
timeout /t 2 >nul

REM Step 2: Set up storage
echo Step 2/7: Setting up persistent storage...
kubectl apply -f deploy-router\kubernetes\persistent-volume.yaml
timeout /t 3 >nul

REM Wait for PVC to bind
echo Waiting for PVC to bind...
kubectl wait --for=condition=Bound pvc/checkpoint-pvc -n %NAMESPACE% --timeout=60s

REM Step 3: Deploy configuration
echo Step 3/7: Deploying configuration...
kubectl apply -f deploy-router\kubernetes\configmap.yaml
timeout /t 2 >nul

REM Step 4: Deploy application
echo Step 4/7: Deploying application...
kubectl apply -f deploy-router\kubernetes\deployment.yaml
kubectl apply -f deploy-router\kubernetes\service.yaml

REM Wait for rollout
echo Waiting for deployment rollout...
kubectl rollout status deployment/%DEPLOYMENT_NAME% -n %NAMESPACE% --timeout=300s

REM Step 5: Deploy autoscaling
echo Step 5/7: Configuring autoscaling...
kubectl apply -f deploy-router\kubernetes\hpa.yaml
timeout /t 2 >nul

REM Step 6: Set up monitoring
echo Step 6/7: Setting up monitoring...
kubectl apply -f deploy-router\kubernetes\servicemonitor.yaml
timeout /t 2 >nul

REM Step 7: Validation
echo Step 7/7: Validating deployment...
echo.

REM Check pod status
echo Pod Status:
kubectl get pods -n %NAMESPACE% -l app=incremental-checkpoint

REM Check service endpoints
echo.
echo Service Endpoints:
kubectl get svc -n %NAMESPACE%

REM Check PVC
echo.
echo Storage:
kubectl get pvc -n %NAMESPACE%

echo.
echo ==================================
echo Deployment Complete!
echo ==================================
echo.
echo Next Steps:
echo   1. Monitor metrics: kubectl port-forward -n %NAMESPACE% svc/checkpoint-manager-metrics 9090:9090
echo   2. View logs: kubectl logs -f -n %NAMESPACE% deployment/%DEPLOYMENT_NAME%
echo   3. Access service: kubectl port-forward -n %NAMESPACE% svc/checkpoint-manager 8080:8080
echo   4. Import Grafana dashboard: monitoring-tools\grafana-dashboard.json
echo.
echo Documentation:
echo   - Deployment Guide: DEPLOYMENT_GUIDE.md
echo   - Troubleshooting: TROUBLESHOOTING.md
echo   - API Reference: API_REFERENCE.md
echo.

pause
