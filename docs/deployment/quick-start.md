# 🚀 Quick Start Guide - 30 Seconds to Deploy

## TL;DR
```bash
git push origin main
# That's it! Watch GitHub Actions deploy everything automatically
```

## 📋 What Happens Next

### 1. GitHub Actions Trigger (10 seconds)
- [ ] Builds Docker image
- [ ] Runs tests
- [ ] Pushes to GitHub Container Registry
- [ ] Deploys to Nebula server

### 2. Verification (20 seconds)
- [ ] Service health check
- [ ] Metrics collection starts
- [ ] Tracing enabled
- [ ] You're live!

## 🎯 Service-Specific Quick Deploys

### RTSP Capture Service
```bash
# Deploy RTSP capture
git push origin main
# Check: http://nebula:8080/health
```

### Frame Tracking Service
```bash
# Deploy frame tracking
git push origin main
# Check: http://nebula:8081/health
```

### Any New Service
```bash
# Deploy any service
git push origin main
# Check: http://nebula:[port]/health
```

## 🔍 Verify Deployment

### 1. Check GitHub Actions
Go to: `https://github.com/hretheum/detektr/actions`

### 2. Check Service Health
```bash
# Test RTSP capture
curl http://nebula:8080/health

# Test any service
curl http://nebula:[port]/health
```

### 3. Check Metrics
```bash
# Prometheus metrics
curl http://nebula:8080/metrics

# Grafana dashboard
open http://nebula:3000
```

## ⚡ Need Something Custom?

### Custom RTSP URL
```bash
# Edit .env file
nano .env.sops
# Then deploy
git add .env.sops
git commit -m "update: custom RTSP URL"
git push origin main
```

### Custom Port
```bash
# Edit docker-compose.yml
# Change port mapping
# Then deploy
git add docker-compose.yml
git commit -m "update: custom port"
git push origin main
```

## 🆘 Quick Troubleshooting

### Deployment Failed?
```bash
# Check logs
gh run list
gh run view [run-id] --log
```

### Service Won't Start?
```bash
# Check status
docker ps
docker logs [service-name]
```

### Need Help?
- [Full troubleshooting guide](troubleshooting/common-issues.md)
- [Emergency procedures](troubleshooting/emergency.md)
- [Service-specific guides](services/)
