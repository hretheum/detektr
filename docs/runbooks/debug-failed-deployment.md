# Runbook: Debug Failed Deployment

## Cel
Systematyczne podejście do debugowania nieudanego deploymentu.

## Initial Assessment

### 1. Sprawdź CI/CD Pipeline

```bash
# GitHub Actions status
gh run list -L 5
gh run view --log-failed

# Download artifacts
gh run download [run-id]

# Check specific job
gh run view [run-id] --log --job [job-id]
```

### 2. SSH to Server

```bash
# Connect
ssh nebula

# Basic checks
docker ps -a
docker compose ps
systemctl status docker
df -h
free -m
```

## Debugging Steps

### Step 1: Identify Failed Services

```bash
#!/bin/bash
# check-services.sh

echo "=== Service Status ==="
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n=== Failed Services ==="
docker compose ps --format "table {{.Service}}\t{{.Status}}" | grep -v "Up"

echo -e "\n=== Recent Events ==="
docker events --since 10m --until now
```

### Step 2: Analyze Logs

```bash
# All logs from last deployment
docker compose logs --since 30m > deployment-logs.txt

# Failed service logs
FAILED_SERVICE=$(docker compose ps --format "{{.Service}}" | \
  xargs -I {} sh -c 'docker compose ps {} | grep -v "Up" && echo {}' | \
  grep -v "NAME" | head -1)

echo "Checking logs for: $FAILED_SERVICE"
docker compose logs $FAILED_SERVICE --tail 100
```

### Step 3: Check Resources

```bash
# Disk space
df -h | grep -E "(/$|/var|/opt)"

# Memory
free -m
docker stats --no-stream

# CPU
top -bn1 | head -20

# Network
netstat -tulpn | grep LISTEN
```

### Step 4: Validate Configuration

```bash
# Environment variables
docker compose config > /tmp/resolved-config.yml
grep -E "(ERROR|WARNING)" /tmp/resolved-config.yml

# Secrets
if [ -f .env ]; then
  echo "Checking .env file..."
  grep -E "^[A-Z_]+=" .env | wc -l
  echo "Environment variables found"
fi

# Image availability
docker compose config | grep "image:" | sort -u | while read -r line; do
  IMAGE=$(echo $line | cut -d'"' -f2)
  echo -n "Checking $IMAGE... "
  docker pull $IMAGE --quiet && echo "OK" || echo "FAILED"
done
```

## Common Issues & Solutions

### Issue: Image Pull Failed

```bash
# Check registry auth
docker login ghcr.io

# Manual pull
docker pull ghcr.io/hretheum/detektr/[service]:latest

# Check rate limits
curl -s -I -H "Authorization: Bearer $(echo -n $GITHUB_TOKEN | base64)" \
  https://ghcr.io/v2/hretheum/detektr/[service]/manifests/latest
```

### Issue: Port Already in Use

```bash
# Find process
sudo lsof -i :[port]
sudo netstat -tulpn | grep :[port]

# Kill or change port
sudo kill -9 [PID]
# Or edit docker-compose.yml ports section
```

### Issue: Container Exits Immediately

```bash
# Check exit code
docker ps -a --filter "name=[service]" --format "table {{.Names}}\t{{.Status}}"

# Debug interactively
docker run -it --rm \
  --network detektor-network \
  --env-file .env \
  ghcr.io/hretheum/detektr/[service]:latest \
  /bin/bash

# Check entrypoint
docker inspect ghcr.io/hretheum/detektr/[service]:latest | jq '.[0].Config.Entrypoint'
```

### Issue: Database Connection Failed

```bash
# Test connectivity
docker exec -it detektor-[service]-1 /bin/bash
apt-get update && apt-get install -y postgresql-client
psql -h postgres -U postgres -d detektor -c "SELECT 1"

# Check DNS
nslookup postgres
nslookup redis

# Check network
docker network inspect detektor-network
```

### Issue: Health Check Timeout

```bash
# Increase timeout
docker exec -it detektor-[service]-1 /bin/bash
curl -v http://localhost:[port]/health

# Check from host
curl -v http://localhost:[port]/health

# Modify health check
docker compose up -d --no-deps \
  --health-interval=60s \
  --health-timeout=30s \
  [service]
```

## Advanced Debugging

### Enable Debug Logging

```bash
# Set debug mode
export LOG_LEVEL=DEBUG
docker compose up -d [service]

# Python debugging
docker exec -it detektor-[service]-1 \
  python -m pdb -m uvicorn main:app --host 0.0.0.0
```

### Network Packet Capture

```bash
# Capture traffic
docker run --rm -it \
  --net container:detektor-[service]-1 \
  nicolaka/netshoot \
  tcpdump -i any -w capture.pcap

# Analyze
docker run --rm -it \
  -v $(pwd):/data \
  nicolaka/netshoot \
  tshark -r /data/capture.pcap
```

### Strace Container

```bash
# Trace system calls
docker run --rm -it \
  --pid container:detektor-[service]-1 \
  --cap-add SYS_PTRACE \
  alpine sh -c "apk add strace && strace -p 1"
```

### Memory Profiling

```bash
# Python memory profiler
docker exec -it detektor-[service]-1 pip install memory_profiler
docker exec -it detektor-[service]-1 \
  python -m memory_profiler main.py
```

## Recovery Actions

### Quick Fix Attempts

```bash
# 1. Restart single service
docker compose restart [service]

# 2. Recreate container
docker compose up -d --force-recreate [service]

# 3. Pull latest and retry
docker compose pull [service]
docker compose up -d [service]

# 4. Clear and retry
docker compose rm -f [service]
docker compose up -d [service]
```

### Full Reset

```bash
#!/bin/bash
# full-reset.sh

# Stop everything
docker compose down

# Clean volumes (careful!)
docker volume ls -q | grep detektor | xargs docker volume rm

# Clean images
docker images | grep detektr | awk '{print $3}' | xargs docker rmi -f

# Fresh start
docker compose pull
docker compose up -d
```

## Gathering Debug Info

```bash
#!/bin/bash
# collect-debug-info.sh

DEBUG_DIR="debug-$(date +%Y%m%d-%H%M%S)"
mkdir -p $DEBUG_DIR

# System info
uname -a > $DEBUG_DIR/system.txt
docker version >> $DEBUG_DIR/system.txt
docker compose version >> $DEBUG_DIR/system.txt

# Docker info
docker ps -a > $DEBUG_DIR/containers.txt
docker images > $DEBUG_DIR/images.txt
docker network ls > $DEBUG_DIR/networks.txt

# Logs
docker compose logs > $DEBUG_DIR/compose-logs.txt
journalctl -u docker --since "1 hour ago" > $DEBUG_DIR/docker-daemon.txt

# Config
docker compose config > $DEBUG_DIR/resolved-config.yml
cp .env $DEBUG_DIR/env-vars.txt 2>/dev/null || echo "No .env file" > $DEBUG_DIR/env-vars.txt

# Create archive
tar -czf $DEBUG_DIR.tar.gz $DEBUG_DIR/
echo "Debug info collected in $DEBUG_DIR.tar.gz"
```

## Escalation Path

If unable to resolve within 30 minutes:

1. **Create GitHub Issue** with debug info
2. **Post in #dev-alerts** Slack channel
3. **Tag @oncall** in Slack
4. **Share debug archive**

## Prevention Checklist

After resolution:

- [ ] Add health check for failure mode
- [ ] Create unit test for bug
- [ ] Update deployment validation
- [ ] Add monitoring alert
- [ ] Document in troubleshooting
- [ ] Update this runbook
