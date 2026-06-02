@echo off
REM Docker Compose Deployment Script for Windows

echo ==================================
echo Docker Compose Deployment
echo ==================================
echo.

echo Building and starting services...
docker-compose up -d --build

echo.
echo Waiting for services to be healthy...
timeout /t 10 >nul

echo.
echo ==================================
echo Deployment Complete!
echo ==================================
echo.

echo Services:
echo   Checkpoint Manager: http://localhost:8080
echo   Prometheus:         http://localhost:9091
echo   Grafana:           http://localhost:3000 (admin/admin)
echo.

echo Endpoints:
echo   Health:    curl http://localhost:8080/health
echo   Metrics:   curl http://localhost:9090/metrics
echo   Stats:     curl http://localhost:8080/stats
echo.

echo To view logs:
echo   docker-compose logs -f checkpoint-manager
echo.

echo To stop:
echo   docker-compose down
echo.

pause
