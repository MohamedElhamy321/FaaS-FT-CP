# Docker Compose Deployment Script for Production
# Incremental Checkpoint System v2.0.0

Write-Host "==================================" -ForegroundColor Green
Write-Host "Docker Compose Deployment" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
        Write-Host ""
        Write-Host "Alternative: Run locally without Docker:" -ForegroundColor Yellow
        Write-Host "  1. Install dependencies: pip install -r requirements.txt" -ForegroundColor Cyan
        Write-Host "  2. Run server: python -m incremental_checkpoint.server" -ForegroundColor Cyan
        exit 1
    }
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Install Docker Desktop from https://docker.com" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building and starting services..." -ForegroundColor Yellow
docker-compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Waiting for services to be healthy (30s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    Write-Host ""
    Write-Host "==================================" -ForegroundColor Green
    Write-Host "✅ Deployment Complete!" -ForegroundColor Green
    Write-Host "==================================" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "🌐 Services:" -ForegroundColor Cyan
    Write-Host "  Checkpoint Manager: http://localhost:8080" -ForegroundColor White
    Write-Host "  Prometheus:         http://localhost:9091" -ForegroundColor White
    Write-Host "  Grafana:           http://localhost:3000 (admin/admin)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "🔍 Endpoints:" -ForegroundColor Cyan
    Write-Host "  Health:    curl http://localhost:8080/health" -ForegroundColor White
    Write-Host "  Metrics:   curl http://localhost:9090/metrics" -ForegroundColor White
    Write-Host "  Stats:     curl http://localhost:8080/stats" -ForegroundColor White
    Write-Host ""
    
    Write-Host "📊 Test Health:" -ForegroundColor Cyan
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -ErrorAction SilentlyContinue
        Write-Host "  Status: $($health.status)" -ForegroundColor Green
        Write-Host "  Version: $($health.version)" -ForegroundColor Green
    } catch {
        Write-Host "  ⏳ Service still starting up..." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "📝 Commands:" -ForegroundColor Cyan
    Write-Host "  View logs:    docker-compose logs -f checkpoint-manager" -ForegroundColor White
    Write-Host "  Stop:         docker-compose down" -ForegroundColor White
    Write-Host "  Restart:      docker-compose restart" -ForegroundColor White
    Write-Host ""
    
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed. Check the error above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Make sure Docker Desktop is running" -ForegroundColor Cyan
    Write-Host "  2. Make sure ports 8080, 9090, 9091, 3000 are available" -ForegroundColor Cyan
    Write-Host "  3. Try: docker-compose down && docker-compose up -d --build" -ForegroundColor Cyan
}
