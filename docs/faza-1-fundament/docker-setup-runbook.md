# Docker Setup Runbook - Detektor Project

## Quick Reference

### Server Access

```bash
ssh nebula  # 192.168.1.193
```

### Docker Status

```bash
docker --version  # 28.3.2
docker compose version  # v2.38.2
systemctl status docker
```

### Project Location

- Server: `/opt/detektor/`
- Local: `/Users/hretheum/dev/bezrobocie/detektor/`

## Infrastructure Setup

### Networks

```bash
# Already created
detektor_frontend  # External-facing services
detektor_backend   # Internal services (isolated)
```

### Directory Structure (on server)

```
/opt/detektor/
├── config/     # Service configurations
├── data/       # Persistent data (group: docker)
├── logs/       # Application logs (group: docker)
├── scripts/    # Utility scripts
└── services/   # Service-specific files
```

### Docker Configuration

Location: `/etc/docker/daemon.json`

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}
```

## Common Operations

### Deploy Services

```bash
# From local machine
docker --context nebula compose up -d

# Or SSH to server
ssh nebula
cd /opt/detektor
docker compose up -d
```

### Monitor Services

```bash
# Container status
docker --context nebula ps

# Resource usage
docker --context nebula stats

# Metrics endpoint
curl http://192.168.1.193:9323/metrics
```

### View Logs

```bash
# All services
docker --context nebula compose logs -f

# Specific service
docker --context nebula compose logs -f [service-name]
```

## Troubleshooting

### Docker Issues

```bash
# Check daemon
ssh nebula "sudo journalctl -xeu docker.service -n 50"

# Restart Docker
ssh nebula "sudo systemctl restart docker"

# Check disk space
ssh nebula "df -h /"
```

### Network Issues

```bash
# List networks
docker --context nebula network ls

# Inspect network
docker --context nebula network inspect detektor_backend
```

### Cleanup

```bash
# Remove stopped containers
docker --context nebula container prune -f

# Remove unused images
docker --context nebula image prune -f

# Full cleanup (careful!)
docker --context nebula system prune -a
```

## Security Features

- ✅ Seccomp: enabled
- ✅ AppArmor: enabled
- ✅ Log rotation: 100MB/file, max 3
- ✅ Metrics: Prometheus-ready

## Next Steps

- Phase 1, Task 2: NVIDIA Container Toolkit
- Phase 1, Task 4: Observability Stack (Jaeger, Prometheus, Grafana)
