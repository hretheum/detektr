# Runbook: Rollback Procedure

## Cel
Bezpieczny rollback do poprzedniej wersji w przypadku problemów z deploymentem.

## Typy rollbacków

1. **Quick Rollback** - powrót do poprzednich obrazów Docker
2. **Git Rollback** - powrót do poprzedniego commitu
3. **Database Rollback** - przywrócenie danych
4. **Full System Rollback** - kompletny reset

## Quick Rollback (< 5 minut)

### 1. Identyfikacja problemu

```bash
# Check status
./scripts/deploy.sh production status

# Check logs
./scripts/deploy.sh production logs --tail 100

# Health checks
for port in 8001 8005 8006 8007 8010; do
  echo "Checking port $port:"
  curl -s http://nebula:$port/health | jq .
done
```

### 2. Rollback konkretnego serwisu

```bash
# Stop problematic service
ssh nebula "docker stop detektor-[service-name]-1"

# List available tags
ssh nebula "docker images ghcr.io/hretheum/detektr/[service-name]"

# Run previous version
ssh nebula "docker run -d \
  --name detektor-[service-name]-1 \
  --network detektor-network \
  -p [port]:[port] \
  ghcr.io/hretheum/detektr/[service-name]:previous-tag"
```

### 3. Weryfikacja

```bash
# Check if running
ssh nebula "docker ps | grep [service-name]"

# Test endpoint
curl http://nebula:[port]/health
```

## Git Rollback (10-15 minut)

### 1. Znajdź dobry commit

```bash
# Show recent deployments
git log --oneline -n 20 --grep="deploy"

# Find last working commit
LAST_GOOD_COMMIT=$(git log --format="%H" -n 1 --before="2 hours ago")
echo "Last good commit: $LAST_GOOD_COMMIT"
```

### 2. Revert changes

```bash
# Create revert commit
git revert HEAD --no-edit
git push origin main

# Or hard reset (careful!)
git reset --hard $LAST_GOOD_COMMIT
git push --force-with-lease origin main
```

### 3. Wait for CI/CD

```bash
# Monitor deployment
gh run list -L 5
gh run watch

# Or manual deploy
./scripts/deploy.sh production deploy
```

## Database Rollback

### 1. Stop services

```bash
# Prevent data corruption
ssh nebula "docker compose stop rtsp-capture frame-tracking"
```

### 2. Restore backup

```bash
# List backups
ssh nebula "ls -la /backups/postgres/"

# Restore specific backup
ssh nebula "docker exec -i detektor-postgres-1 \
  psql -U postgres detektor < /backups/postgres/backup-20240120-1000.sql"

# For Redis
ssh nebula "docker cp /backups/redis/dump-20240120.rdb detektor-redis-1:/data/dump.rdb"
ssh nebula "docker restart detektor-redis-1"
```

### 3. Restart services

```bash
ssh nebula "docker compose start rtsp-capture frame-tracking"
```

## Full System Rollback

### 1. Backup current state

```bash
#!/bin/bash
# backup-before-rollback.sh

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/backups/rollback-$TIMESTAMP"

ssh nebula "mkdir -p $BACKUP_DIR"

# Backup configs
ssh nebula "cp -r /opt/detektor/.env* $BACKUP_DIR/"
ssh nebula "docker compose config > $BACKUP_DIR/docker-compose.resolved.yml"

# Backup data
ssh nebula "docker exec detektor-postgres-1 pg_dumpall -U postgres > $BACKUP_DIR/postgres.sql"
ssh nebula "docker exec detektor-redis-1 redis-cli BGSAVE"
ssh nebula "cp /var/lib/docker/volumes/detektor_redis_data/_data/dump.rdb $BACKUP_DIR/"
```

### 2. Stop everything

```bash
ssh nebula "cd /opt/detektor && docker compose down"
```

### 3. Restore from backup

```bash
# Use specific backup point
RESTORE_POINT="20240120-0800"

# Restore code
ssh nebula "cd /opt/detektor && git fetch && git checkout backup-$RESTORE_POINT"

# Restore volumes
ssh nebula "docker volume rm detektor_postgres_data detektor_redis_data"
ssh nebula "docker volume create detektor_postgres_data"
ssh nebula "docker volume create detektor_redis_data"

# Restore data
ssh nebula "docker run --rm -v detektor_postgres_data:/data \
  -v /backups/$RESTORE_POINT:/backup \
  alpine cp -r /backup/postgres/* /data/"
```

### 4. Start services

```bash
ssh nebula "cd /opt/detektor && docker compose up -d"
```

## Emergency Contacts

W przypadku krytycznych problemów:

1. **DevOps Lead**: @username (Slack)
2. **On-call**: Sprawdź PagerDuty
3. **Escalation**: CTO (email)

## Post-Rollback

### 1. Incident report

```markdown
## Incident Report - [Date]

### Summary
- **Time**: Start - End
- **Impact**: Services affected
- **Root Cause**: Brief description

### Timeline
- HH:MM - Issue detected
- HH:MM - Rollback initiated
- HH:MM - Service restored

### Lessons Learned
- What went wrong
- How to prevent

### Action Items
- [ ] Fix root cause
- [ ] Update monitoring
- [ ] Update runbooks
```

### 2. Cleanup

```bash
# Remove failed images
docker image prune -f

# Clean old containers
docker container prune -f

# Archive logs
tar -czf incident-logs-$(date +%Y%m%d).tar.gz /var/log/detektor/
```

### 3. Prevention

- Add tests for the failure scenario
- Update health checks
- Improve monitoring alerts
- Document in troubleshooting guide

## Verification Checklist

After rollback:

- [ ] All services are running
- [ ] Health checks passing
- [ ] No error logs in last 5 minutes
- [ ] Monitoring dashboards normal
- [ ] Test critical user flows
- [ ] Database consistency check
- [ ] Notify team of resolution

## Common Rollback Scenarios

### Scenario: Bad AI model

```bash
# Rollback just the model file
ssh nebula "cd /opt/detektor/models && git checkout HEAD~1 -- yolov8.pt"
ssh nebula "docker restart detektor-object-detection-1"
```

### Scenario: Config error

```bash
# Fix config without full rollback
ssh nebula "cd /opt/detektor && cp .env.backup .env"
ssh nebula "docker compose up -d"
```

### Scenario: Memory leak

```bash
# Quick fix - restart with memory limit
ssh nebula "docker update --memory=2g detektor-[service]-1"
ssh nebula "docker restart detektor-[service]-1"
```
