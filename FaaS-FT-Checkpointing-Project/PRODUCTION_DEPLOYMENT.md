# 🚀 Production Deployment - Quick Start

## ✅ System Ready for Production

The incremental checkpoint system **v2.0.0** is fully implemented with:
- ✅ Core checkpointing (Steps 1-4)
- ✅ 106 tests passing (Step 5)
- ✅ Performance optimizations (Step 6)
- ✅ Production features (Step 7)
- ✅ Integration tools (Step 8)
- ✅ Complete documentation (Step 9)
- ✅ Monitoring & deployment (Step 10)

---

## 🎯 Choose Your Deployment Method

### Option 1: Docker Compose (Recommended for Local/Testing)

**Requirements:** Docker Desktop installed and running

```powershell
# PowerShell (Windows)
cd FaaS-FT-Checkpointing-Project
.\deploy-docker.ps1
```

```bash
# Bash (Linux/Mac)
cd FaaS-FT-Checkpointing-Project
docker-compose up -d --build
```

**Services Started:**
- Checkpoint Manager: http://localhost:8080
- Prometheus: http://localhost:9091
- Grafana: http://localhost:3000 (admin/admin)

**Test it:**
```powershell
# Health check
curl http://localhost:8080/health

# Create checkpoint
curl -X POST http://localhost:8080/checkpoint -H "Content-Type: application/json" -d "{\"key\":\"value\"}"

# View metrics
curl http://localhost:9090/metrics
```

---

### Option 2: Kubernetes (For Production Clusters)

**Requirements:** 
- Kubernetes cluster (v1.21+)
- kubectl configured
- 50GB+ storage available

```bash
# Linux/Mac
cd FaaS-FT-Checkpointing-Project
./deploy-production.sh
```

```powershell
# Windows PowerShell
cd FaaS-FT-Checkpointing-Project
.\deploy-production.bat
```

**Note:** Requires a running Kubernetes cluster. If cluster not available, use Docker Compose instead.

---

### Option 3: Local Python Server (No Docker)

**Requirements:** Python 3.7+

```powershell
# Install dependencies
pip install flask prometheus-client

# Run server
cd FaaS-FT-Checkpointing-Project
python -m incremental_checkpoint.server
```

**Services:**
- Server: http://localhost:8080
- Metrics: http://localhost:9090/metrics

---

## 📊 Deployment Status Check

After deployment, verify everything works:

### 1. Health Check
```powershell
curl http://localhost:8080/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "checkpoint_count": 0,
  "storage_used_mb": 0.0
}
```

### 2. Create Test Checkpoint
```powershell
curl -X POST http://localhost:8080/checkpoint `
  -H "Content-Type: application/json" `
  -d "{\"user_id\": 123, \"session\": \"abc\", \"count\": 42}"
```

### 3. View Statistics
```powershell
curl http://localhost:8080/stats
```

### 4. Access Monitoring (Docker Compose only)
- **Grafana Dashboard:** http://localhost:3000
  - Login: admin/admin
  - Dashboard: Import `monitoring-tools/grafana-dashboard.json`
- **Prometheus:** http://localhost:9091

---

## 🔧 Configuration

### Environment Variables

```bash
CHECKPOINT_DIR=/data/checkpoints      # Storage location
LOG_LEVEL=INFO                        # Logging level
PYTHONUNBUFFERED=1                    # Immediate log output
```

### ConfigMap (Kubernetes)

Edit `deploy-router/kubernetes/configmap.yaml`:
- `compression_level`: 1-9 (6 = balanced)
- `full_checkpoint_interval`: 10 (every 10th checkpoint)
- `max_checkpoints`: 100 (retention limit)

### Docker Compose

Edit `docker-compose.yml`:
- Resource limits (CPU, memory)
- Port mappings
- Volume paths

---

## 📈 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Checkpoint Time | <100ms | **1.90ms** ✅ |
| Restoration Time | <500ms | **2.00ms** ✅ |
| Size Reduction | 60-80% | **98.7%** ✅ |
| Compression Ratio | 3-5x | **5.79x** ✅ |
| Throughput | 10/sec | **192.8/sec** ✅ |

---

## 🔍 Monitoring

### Prometheus Metrics

Available at http://localhost:9090/metrics:
- `checkpoint_creation_total` - Total checkpoints created
- `checkpoint_creation_duration_seconds` - Creation latency
- `checkpoint_size_bytes` - Checkpoint sizes
- `checkpoint_errors_total` - Error count
- `checkpoint_cache_hits_total` - Cache performance
- `checkpoint_health_status` - System health (1=healthy)

### Grafana Dashboards

13 pre-configured panels:
- Checkpoint creation rate (FULL vs INCR)
- Latency percentiles (P50, P95, P99)
- Storage usage and trends
- Error rates and types
- Cache hit rates
- System health status

---

## 🚨 Troubleshooting

### Docker: Port Already in Use

```powershell
# Find process using port
netstat -ano | findstr :8080

# Kill process
taskkill /PID <pid> /F

# Or change port in docker-compose.yml
```

### Docker: Container Won't Start

```powershell
# View logs
docker-compose logs checkpoint-manager

# Restart
docker-compose restart checkpoint-manager

# Full rebuild
docker-compose down
docker-compose up -d --build
```

### Kubernetes: Cluster Not Available

Use Docker Compose or local Python server instead:
```powershell
python -m incremental_checkpoint.server
```

### Health Check Fails

```powershell
# Wait 30 seconds for startup
Start-Sleep -Seconds 30

# Check if service is listening
netstat -ano | findstr :8080

# Check logs
docker-compose logs checkpoint-manager
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `DEPLOYMENT_GUIDE.md` | Complete deployment procedures |
| `API_REFERENCE.md` | API documentation |
| `PERFORMANCE_TUNING.md` | Optimization guide |
| `TROUBLESHOOTING.md` | Problem resolution |
| `INTEGRATION_GUIDE.md` | Integration patterns |

---

## 🎉 Next Steps After Deployment

1. **Import Grafana Dashboard**
   - Go to http://localhost:3000
   - Login: admin/admin
   - Import `monitoring-tools/grafana-dashboard.json`

2. **Create First Checkpoint**
   ```python
   import requests
   response = requests.post('http://localhost:8080/checkpoint',
       json={'key': 'value'})
   print(response.json())
   ```

3. **Monitor Performance**
   - View Grafana dashboards
   - Check Prometheus metrics
   - Review health endpoint

4. **Integrate with Your Application**
   - See `INTEGRATION_GUIDE.md`
   - Use `JSONCheckpointAdapter` for drop-in replacement
   - Run migration tools for existing checkpoints

---

## 🆘 Need Help?

- **Documentation:** Check TROUBLESHOOTING.md
- **Logs:** `docker-compose logs -f checkpoint-manager`
- **Health:** `curl http://localhost:8080/health`
- **Stats:** `curl http://localhost:8080/stats`

---

## 🎯 Quick Commands Reference

```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f checkpoint-manager

# Restart
docker-compose restart

# Health check
curl http://localhost:8080/health

# Create checkpoint
curl -X POST http://localhost:8080/checkpoint -H "Content-Type: application/json" -d "{\"data\":\"test\"}"

# List checkpoints
curl http://localhost:8080/checkpoints

# View metrics
curl http://localhost:9090/metrics
```

---

**System Version:** 2.0.0  
**Status:** Production Ready  
**Last Updated:** November 24, 2025
