# 🔧 Common Issues & Solutions

## 🚨 Quick Diagnosis

### 1. Service Won't Start
**Symptoms**: GitHub Actions fails, container exits immediately

**Quick Fix**:
```bash
docker logs [service-name]
# Look for: "Error:", "Failed to", "Cannot connect"
```

### 2. Health Check Fails
**Symptoms**: Service runs but `/health` returns error

**Quick Fix**:
```bash
curl -v http://localhost:[port]/health
docker logs [service-name] --tail 20
```

### 3. Metrics Missing
**Symptoms**: Prometheus shows no data

**Quick Fix**:
```bash
curl http://localhost:[port]/metrics
# Visit: http://nebula:9090/targets
```

## 📋 RTSP Capture Specific Issues

### Issue 1: RTSP Connection Failed
**Symptoms**:
```
ERROR: Could not connect to RTSP stream
```

**Solutions**:
```bash
# 1. Test RTSP URL
ffmpeg -i rtsp://user:pass@camera-ip:554/stream -t 1 -f null -

# 2. Check camera
ping camera-ip

# 3. Verify credentials
curl -u user:pass rtsp://camera-ip:554/stream

# 4. Test locally
docker run -it --rm \
  -e RTSP_URL="rtsp://user:pass@camera-ip:554/stream" \
  ghcr.io/hretheum/detektr/rtsp-capture:latest
```

### Issue 2: High Memory Usage
**Symptoms**:
```
Memory usage > 80%
```

**Solutions**:
```bash
# 1. Check memory
docker stats rtsp-capture

# 2. Reduce quality
# Edit docker-compose.yml:
environment:
  - STREAM_QUALITY=medium
  - RECORDING_ENABLED=false

# 3. Restart with new config
git add docker-compose.yml
git commit -m "fix: reduce memory usage"
git push origin main
```

### Issue 3: Frame Rate Too Low
**Symptoms**:
```
FPS < 15
```

**Solutions**:
```bash
# 1. Check CPU usage
docker stats rtsp-capture

# 2. Check network
ping camera-ip

# 3. Reduce resolution
# Edit docker-compose.yml:
environment:
  - STREAM_QUALITY=medium
  - FRAME_SKIP=2
```

## 📋 GitHub Runner Issues

### Issue 1: Runner Offline
**Symptoms**:
```
GitHub Actions queue builds but don't start
```

**Solutions**:
```bash
# 1. Check runner status
ssh nebula
sudo systemctl status github-runner

# 2. Restart runner
sudo systemctl restart github-runner

# 3. Check logs
sudo journalctl -u github-runner -f
```

### Issue 2: Runner Permissions
**Symptoms**:
```
Permission denied: docker.sock
```

**Solutions**:
```bash
# 1. Check permissions
ls -la /var/run/docker.sock
groups github-runner

# 2. Add to docker group
sudo usermod -aG docker github-runner
sudo systemctl restart github-runner
```

## 📋 Docker Registry Issues

### Issue 1: Image Not Found
**Symptoms**:
```
Error: image not found
```

**Solutions**:
```bash
# 1. Check image exists
docker pull ghcr.io/hretheum/detektr/[service-name]:latest

# 2. Check GitHub packages
# Visit: https://github.com/hretheum/detektr/packages

# 3. Manual build
docker build -t ghcr.io/hretheum/detektr/[service-name]:latest .
docker push ghcr.io/hretheum/detektr/[service-name]:latest
```

### Issue 2: Registry Authentication
**Symptoms**:
```
Error: unauthorized
```

**Solutions**:
```bash
# 1. Check GitHub token
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 2. Renew token
# Go to: GitHub Settings > Developer settings > Personal access tokens
```

## 📋 SOPS/Secrets Issues

### Issue 1: Decryption Failed
**Symptoms**:
```
Error: failed to decrypt file
```

**Solutions**:
```bash
# 1. Check age key
age-keygen -y ~/.age/key.txt

# 2. Verify key in .sops.yaml
cat .sops.yaml

# 3. Re-encrypt
sops -r -i .env.sops
```

### Issue 2: Wrong Environment Variables
**Symptoms**:
```
Service starts but with wrong config
```

**Solutions**:
```bash
# 1. Check decrypted variables
sops -d .env.sops

# 2. Verify in container
docker exec [service-name] env | grep [VARIABLE]
```

## 🆘 Emergency Procedures

### Service Down Emergency
```bash
# 1. Quick restart
docker restart [service-name]

# 2. Rollback
git revert HEAD
git push origin main

# 3. Manual rollback
docker-compose -f docker-compose.[service].yml down
docker-compose -f docker-compose.[service].yml up -d [previous-version]
```

### Complete System Reset
```bash
# 1. Stop all services
docker-compose down

# 2. Clear cache
docker system prune -f

# 3. Redeploy
git push origin main
```

## 🔍 Debug Commands Reference

### Container Debugging
```bash
# Check container
docker ps -a | grep [service-name]

# Check logs
docker logs [service-name] --tail 50 -f

# Check config
docker inspect [service-name]

# Shell into container
docker exec -it [service-name] /bin/bash
```

### Network Debugging
```bash
# Check connectivity
curl http://localhost:[port]/health

# Check ports
netstat -tlnp | grep [port]

# Check DNS
nslookup nebula

# Test from container
docker exec [service-name] curl http://localhost:[port]/health
```

### Performance Debugging
```bash
# Check resources
docker stats

# Check processes
docker top [service-name]

# Check disk usage
df -h
docker system df
```

## 📞 Get Help

### Before Creating Issue
1. **Check logs**: `docker logs [service-name]`
2. **Check health**: `curl http://localhost:[port]/health`
3. **Check GitHub Actions**: https://github.com/hretheum/detektr/actions

### Create Detailed Issue
```markdown
## Problem
[Clear description]

## Environment
- Service: [service-name]
- Version: [docker image tag]
- Error message: [exact error]

## Logs
```bash
[paste relevant logs]
```

## Steps to Reproduce
1. [step 1]
2. [step 2]
3. [step 3]
