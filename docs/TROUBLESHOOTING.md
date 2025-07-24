# 🔧 Troubleshooting Guide

## Spis treści

1. [Najczęstsze problemy](#najczęstsze-problemy)
2. [Docker & Containers](#docker--containers)
3. [Networking](#networking)
4. [Services Issues](#services-issues)
5. [Performance](#performance)
6. [GPU & CUDA](#gpu--cuda)
7. [Secrets & Authentication](#secrets--authentication)
8. [CI/CD & Deployment](#cicd--deployment)
9. [Monitoring & Observability](#monitoring--observability)
10. [Emergency Procedures](#emergency-procedures)

## Najczęstsze problemy

### Problem: Services nie startują

**Objawy**: Services nie startują lub restartują się w pętli

**Rozwiązanie**:
```bash
# 1. Sprawdź logi (użyj Make)
make logs SERVICE=[service-name]

# 2. Sprawdź zależności
make ps

# 3. Restart z clean state
make down
make clean-docker
make up

# 4. Sprawdź porty
netstat -tulpn | grep -E "(8001|8005|8006|9090|3000)"
```

### Problem: "Cannot connect to Redis"

**Objawy**: Services pokazują błąd połączenia z Redis

**Rozwiązanie**:
```bash
# 1. Sprawdź czy Redis działa
make ps | grep redis
make logs SERVICE=redis

# 2. Test połączenia
docker exec -it detektor-redis-1 redis-cli ping
# Powinno zwrócić: PONG

# 3. Sprawdź konfigurację
docker exec -it [service-name] env | grep REDIS

# 4. Restart Redis
./scripts/deploy.sh local restart redis
```

### Problem: Health check failing

**Objawy**: Service status pokazuje "unhealthy"

**Rozwiązanie**:
```bash
# 1. Sprawdź endpoint bezpośrednio
curl -v http://localhost:8001/health

# 2. Sprawdź w kontenerze
docker exec -it detektor-rtsp-capture-1 curl localhost:8001/health

# 3. Debug health check
docker inspect detektor-rtsp-capture-1 | jq '.[0].State.Health'
```

## Docker & Containers

### Problem: "No space left on device"

**Rozwiązanie**:
```bash
# 1. Cleanup Docker
docker system prune -af --volumes
docker volume prune -f

# 2. Sprawdź przestrzeń
df -h
docker system df

# 3. Zmień Docker root directory (jeśli potrzeba)
# Edit /etc/docker/daemon.json:
{
  "data-root": "/new/docker/root"
}
sudo systemctl restart docker
```

### Problem: Container keeps restarting

**Debugowanie**:
```bash
# 1. Sprawdź exit code
docker ps -a | grep [container-name]

# 2. Inspect container
docker inspect [container-id] | jq '.[0].State'

# 3. Check resource limits
docker stats [container-name]

# 4. Disable restart temporarily
docker update --restart=no [container-name]
```

### Problem: Cannot build images

**Rozwiązanie**:
```bash
# 1. Clean build cache
docker builder prune -af

# 2. Build with no cache
docker build --no-cache -t service-name .

# 3. Check Dockerfile syntax
docker build --check .

# 4. Verbose build
docker build --progress=plain .
```

## Networking

### Problem: Services cannot communicate

**Debugowanie**:
```bash
# 1. List networks
docker network ls

# 2. Inspect network
docker network inspect detektor-network

# 3. Test connectivity
docker exec -it [service1] ping [service2]
docker exec -it [service1] nc -zv [service2] [port]

# 4. Check DNS
docker exec -it [service] nslookup redis
```

### Problem: Port already in use

**Rozwiązanie**:
```bash
# 1. Find process using port
sudo lsof -i :8001
sudo netstat -tulpn | grep 8001

# 2. Kill process
sudo kill -9 [PID]

# 3. Change port in docker-compose
# Edit docker-compose.yml:
ports:
  - "8002:8001"  # Map to different external port
```

### Problem: Cannot access service from host

**Sprawdzenie**:
```bash
# 1. Check iptables
sudo iptables -L -n | grep -E "(8001|DOCKER)"

# 2. Check Docker proxy
docker ps --format "table {{.Names}}\t{{.Ports}}"

# 3. Test localhost vs 0.0.0.0
curl http://localhost:8001/health
curl http://0.0.0.0:8001/health
curl http://127.0.0.1:8001/health
```

## Services Issues

### RTSP Capture Service

**Problem**: Cannot connect to camera

```bash
# 1. Test RTSP URL directly
ffprobe rtsp://user:pass@192.168.1.195:554/Preview_01_main

# 2. Check network connectivity
docker exec -it detektor-rtsp-capture-1 ping 192.168.1.195

# 3. Verify credentials in env
docker exec -it detektor-rtsp-capture-1 env | grep CAMERA

# 4. Enable debug logging
docker exec -it detektor-rtsp-capture-1 \
  python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
```

### Frame Buffer Service

**Problem**: High memory usage

```bash
# 1. Check Redis memory
docker exec -it detektor-redis-1 redis-cli INFO memory

# 2. Set memory limit
docker exec -it detektor-redis-1 redis-cli CONFIG SET maxmemory 2gb

# 3. Check stream length
docker exec -it detektor-redis-1 redis-cli XLEN frames:stream

# 4. Trim old messages
docker exec -it detektor-redis-1 redis-cli XTRIM frames:stream MAXLEN ~ 10000
```

### Face Recognition Service

**Problem**: Model not loading

```bash
# 1. Check model files
docker exec -it detektor-face-recognition-1 ls -la /app/models/

# 2. Download models manually
docker exec -it detektor-face-recognition-1 python -m insightface.app

# 3. Check GPU availability
docker exec -it detektor-face-recognition-1 python -c "import torch; print(torch.cuda.is_available())"
```

## Performance

### Problem: High CPU usage

**Diagnostyka**:
```bash
# 1. Top processes
docker stats --no-stream
docker top [container-name]

# 2. CPU profiling
docker exec -it [container] py-spy top --pid 1

# 3. Check thread count
docker exec -it [container] ps -eLf | wc -l

# 4. Limit CPU
docker update --cpus="2.0" [container]
```

### Problem: Memory leaks

**Debugowanie**:
```bash
# 1. Memory usage over time
docker stats [container] --format "table {{.Container}}\t{{.MemUsage}}"

# 2. Memory profiling
docker exec -it [container] python -m tracemalloc

# 3. Heap dump
docker exec -it [container] python -m pyheapdump

# 4. Set memory limit
docker update -m 2g [container]
```

### Problem: Slow response times

**Analiza**:
```bash
# 1. Check Jaeger traces
open http://localhost:16686

# 2. API latency test
ab -n 1000 -c 10 http://localhost:8001/health

# 3. Database query times
docker exec -it detektor-postgres-1 psql -U postgres -c "SELECT * FROM pg_stat_statements;"

# 4. Redis latency
docker exec -it detektor-redis-1 redis-cli --latency
```

## GPU & CUDA

### Problem: GPU not detected

**Sprawdzenie**:
```bash
# 1. Host GPU status
nvidia-smi

# 2. Docker GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 3. In container
docker exec -it [container] nvidia-smi

# 4. Python check
docker exec -it [container] python -c "import torch; print(torch.cuda.device_count())"
```

### Problem: CUDA out of memory

**Rozwiązanie**:
```bash
# 1. Check memory usage
nvidia-smi --query-gpu=memory.used,memory.free --format=csv

# 2. Clear cache in Python
docker exec -it [container] python -c "import torch; torch.cuda.empty_cache()"

# 3. Limit GPU memory
export CUDA_VISIBLE_DEVICES=0
export TF_FORCE_GPU_ALLOW_GROWTH=true

# 4. Restart service
docker compose restart [gpu-service]
```

## Secrets & Authentication

### Problem: SOPS decryption fails

**Rozwiązanie**:
```bash
# 1. Check age key
age --version
ls -la ~/.config/sops/age/keys.txt

# 2. Test decryption
sops -d .env.sops > /tmp/test.env

# 3. Re-encrypt
sops -e .env > .env.sops

# 4. Verify in container
docker exec -it [container] env | grep -E "(API_KEY|SECRET)"
```

### Problem: Permission denied

**Fix**:
```bash
# 1. Check file ownership
ls -la /opt/detektor/

# 2. Fix permissions
sudo chown -R $USER:docker /opt/detektor/
chmod -R 755 /opt/detektor/

# 3. Docker socket permissions
sudo usermod -aG docker $USER
newgrp docker
```

## CI/CD & Deployment

### Problem: GitHub Actions failing

**Debugowanie**:
```bash
# 1. Check runner status
gh run list -L 5
gh run view [run-id]

# 2. Download logs
gh run download [run-id]

# 3. Re-run with debug
gh workflow run main-pipeline.yml -f debug_enabled=true

# 4. Check runner logs locally
journalctl -u github-runner -f
```

### Problem: Deployment stuck

**Rozwiązanie**:
```bash
# 1. Check deployment script
./scripts/deploy.sh production status

# 2. SSH to server
ssh nebula "docker ps -a"

# 3. Check deployment logs
ssh nebula "tail -f /var/log/detektor-deploy.log"

# 4. Manual rollback
ssh nebula "cd /opt/detektor && git checkout HEAD~1 && docker compose up -d"
```

## Monitoring & Observability

### Problem: Prometheus not scraping

**Sprawdzenie**:
```bash
# 1. Check targets
curl http://localhost:9090/api/v1/targets

# 2. Verify metrics endpoint
curl http://localhost:8001/metrics

# 3. Check Prometheus config
docker exec -it detektor-prometheus-1 cat /etc/prometheus/prometheus.yml

# 4. Reload config
docker exec -it detektor-prometheus-1 kill -HUP 1
```

### Problem: No data in Grafana

**Fix**:
```bash
# 1. Check datasource
curl -u admin:admin http://localhost:3000/api/datasources

# 2. Test query
curl -G http://localhost:9090/api/v1/query --data-urlencode 'query=up'

# 3. Import dashboards
cd dashboards/
for f in *.json; do
  curl -X POST -H "Content-Type: application/json" \
    -d @$f http://admin:admin@localhost:3000/api/dashboards/db
done
```

### Problem: Jaeger traces missing

**Debugowanie**:
```bash
# 1. Check OTEL config
docker exec -it [service] env | grep OTEL

# 2. Test trace export
docker exec -it [service] python -c "
from opentelemetry import trace
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span('test'):
    print('Trace sent')
"

# 3. Check Jaeger
curl http://localhost:16686/api/traces?service=[service-name]
```

## Emergency Procedures

### System nie odpowiada

```bash
#!/bin/bash
# emergency-restart.sh

# 1. Stop wszystko
make down

# 2. Clean up
make clean-all

# 3. Restart Docker
sudo systemctl restart docker

# 4. Start core services only
./docker/dev.sh up -d redis postgres

# 5. Wait for ready
sleep 10

# 6. Start pozostałe
make up
```

### Rollback deployment

```bash
#!/bin/bash
# rollback.sh

# 1. Use deployment script rollback
./scripts/deploy.sh production rollback

# Or manually:
# 1. Stop current
make down

# 2. Checkout previous version
git checkout HEAD~1

# 3. Deploy
make deploy

# 4. Verify
make prod-verify
```

### Data recovery

```bash
#!/bin/bash
# recover-data.sh

# 1. PostgreSQL backup
docker exec detektor-postgres-1 pg_dump -U postgres detektor > backup.sql

# 2. Redis backup
docker exec detektor-redis-1 redis-cli BGSAVE
docker cp detektor-redis-1:/data/dump.rdb ./redis-backup.rdb

# 3. Restore PostgreSQL
docker exec -i detektor-postgres-1 psql -U postgres detektor < backup.sql

# 4. Restore Redis
docker cp redis-backup.rdb detektor-redis-1:/data/dump.rdb
docker restart detektor-redis-1
```

## Useful Debug Commands

```bash
# Container internals
docker exec -it [container] bash
docker exec -it [container] sh
docker exec -it [container] /bin/ash

# Network debug
docker run --rm -it --network detektor-network nicolaka/netshoot

# Process monitoring
docker exec -it [container] htop
docker exec -it [container] iotop

# File watching
docker exec -it [container] inotifywait -m /app

# Strace
docker run --rm -it --pid container:[container] --cap-add SYS_PTRACE alpine strace -p 1
```

## Getting Help

Jeśli problem persystuje:

1. **Check logs**: Zawsze najpierw sprawdź logi
2. **Search issues**: [GitHub Issues](https://github.com/hretheum/detektr/issues)
3. **Ask on Discord**: [Project Discord](#)
4. **Create issue**: Z dokładnym opisem i logami

---

Zobacz także:
- [Development Guide](DEVELOPMENT.md)
- [Deployment Guide](deployment/unified-deployment.md)
- [Architecture](ARCHITECTURE.md)
