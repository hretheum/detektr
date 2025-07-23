# 🚨 Emergency Procedures

## 🆘 Critical Situations

### 1. Complete Service Outage
**Symptoms**: All services down, nothing responding

**Immediate Actions**:
```bash
# 1. Check system status
ssh nebula
sudo systemctl status docker
docker ps -a

# 2. Quick restart
sudo systemctl restart docker
docker-compose up -d

# 3. Check GitHub Actions
# Visit: https://github.com/hretheum/detektr/actions
```

### 2. Database Corruption
**Symptoms**: Services crash on start, disk errors

**Immediate Actions**:
```bash
# 1. Stop all services
docker-compose down

# 2. Check disk
sudo fsck -f /dev/sda1

# 3. Restore from backup
# (Contact system administrator)
```

### 3. Security Breach
**Symptoms**: Unauthorized access, suspicious activity

**Immediate Actions**:
```bash
# 1. Isolate system
sudo ufw --force reset
sudo ufw default deny incoming

# 2. Change all secrets
sops -d .env.sops > .env.tmp
# Edit sensitive values
sops -e .env.tmp > .env.sops

# 3. Force redeploy
git commit --allow-empty -m "security: rotate secrets"
git push origin main
```

## 🔥 Service-Specific Emergencies

### RTSP Capture Down
```bash
# 1. Check camera
ping camera-ip
telnet camera-ip 554

# 2. Quick restart
docker restart rtsp-capture

# 3. Check stream
curl http://localhost:8080/stream/status

# 4. Emergency fallback
# Switch to secondary camera
sed -i 's/camera-ip/backup-camera-ip/g' docker-compose.yml
git add docker-compose.yml
git commit -m "emergency: switch to backup camera"
git push origin main
```

### Registry Down
```bash
# 1. Check GitHub status
curl https://www.githubstatus.com/api/v2/status.json

# 2. Use local images
docker images | grep rtsp-capture
docker tag local-image:latest ghcr.io/hretheum/detektr/rtsp-capture:latest

# 3. Manual deployment
docker-compose -f docker-compose.rtsp.yml up -d
```

### Runner Offline
```bash
# 1. Check runner
ssh nebula
sudo systemctl status github-runner

# 2. Restart runner
sudo systemctl restart github-runner

# 3. Check logs
sudo journalctl -u github-runner -f

# 4. Manual deployment
cd /opt/detektor
git pull origin main
docker-compose up -d
```

## 📞 Emergency Contacts

### System Administrator
- **Primary**: +48 XXX XXX XXX
- **Backup**: +48 XXX XXX XXX
- **Email**: admin@bezrobocie.pl

### GitHub Support
- **Status**: https://www.githubstatus.com/
- **Support**: https://support.github.com/

### Cloud Provider
- **DigitalOcean**: https://status.digitalocean.com/

## 🔄 Rollback Procedures

### Immediate Rollback
```bash
# 1. Stop current deployment
docker-compose down

# 2. Rollback to last known good
git log --oneline -10
git revert [commit-hash]
git push origin main

# 3. Manual rollback
docker pull ghcr.io/hretheum/detektr/[service]:[previous-tag]
docker-compose up -d
```

### Partial Rollback
```bash
# Rollback specific service
docker-compose -f docker-compose.[service].yml down
docker-compose -f docker-compose.[service].yml up -d [previous-tag]
```

## 📊 Monitoring During Emergency

### Real-time Status
```bash
# System resources
htop

# Docker status
docker stats

# Network connections
netstat -tlnp

# Disk usage
df -h
```

### Service Health
```bash
# RTSP capture
curl -f http://localhost:8080/health || echo "RTSP DOWN"

# Prometheus
curl -f http://localhost:9090/-/healthy || echo "PROMETHEUS DOWN"

# Jaeger
curl -f http://localhost:16686/ || echo "JAEGER DOWN"
```

## 🛡️ Prevention Checklist

### Daily
- [ ] Check GitHub Actions status
- [ ] Review metrics in Grafana
- [ ] Verify backups

### Weekly
- [ ] Update system packages
- [ ] Check disk space
- [ ] Review security logs

### Monthly
- [ ] Rotate secrets
- [ ] Update dependencies
- [ ] Test disaster recovery

## 📋 Emergency Kit

### Essential Commands
```bash
# Save these commands for quick access

# Status check
docker ps -a && docker stats && df -h

# Quick restart
docker-compose down && docker-compose up -d

# Logs tail
docker-compose logs -f

# GitHub Actions
gh run list -L 5
```

### Emergency Files
- `.env.sops` - encrypted secrets
- `docker-compose.yml` - service configuration
- `backup/` - configuration backups

### Emergency Numbers
```
System Admin: +48 XXX XXX XXX
GitHub Support: https://support.github.com
Cloud Provider: https://status.digitalocean.com
```

## 🚨 Emergency Communication

### Internal Team
1. **Slack**: #deployment-emergency
2. **Email**: team@bezrobocie.pl
3. **Phone**: +48 XXX XXX XXX

### External Stakeholders
1. **Status Page**: https://status.bezrobocie.pl
2. **Email**: customers@bezrobocie.pl
3. **Phone**: +48 XXX XXX XXX

## 🎯 Recovery Steps

### Phase 1: Stabilize (0-15 minutes)
1. Identify root cause
2. Implement quick fix
3. Verify services are running

### Phase 2: Investigate (15-60 minutes)
1. Analyze logs
2. Determine impact
3. Document findings

### Phase 3: Prevent (1-24 hours)
1. Implement permanent fix
2. Update monitoring
3. Improve procedures

### Phase 4: Communicate (ongoing)
1. Update status page
2. Notify stakeholders
3. Post-mortem review
