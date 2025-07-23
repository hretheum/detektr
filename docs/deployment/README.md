# 🚀 Detektor Deployment Documentation

> **For LLMs**: This is your entry point. Start here for any deployment task.

## 📋 Quick Navigation

| Task | Guide | Time |
|------|-------|------|
| **Deploy existing service** | [Quick Deploy](#quick-deploy) | 30s |
| **Add new service** | [New Service Guide](#adding-new-service) | 5min |
| **Fix deployment issues** | [Troubleshooting](./troubleshooting/) | 2min |
| **Emergency procedures** | [Emergency Guide](./troubleshooting/emergency.md) | 1min |

## 🏗️ Architecture Overview

```
GitHub Push → GitHub Actions → Build Image → Push to Registry → Deploy on Nebula
     ↓              ↓                ↓              ↓                    ↓
  main branch    Automated      Docker Build    ghcr.io         Self-hosted runner
```

### Key Components
- **Registry**: `ghcr.io/hretheum/bezrobocie-detektor/*`
- **Deployment Server**: Nebula (Ubuntu with GPU)
- **CI/CD**: GitHub Actions with self-hosted runner
- **Secrets**: SOPS encrypted `.env` files

## 🚀 Quick Deploy

Deploy any existing service:

```bash
# 1. Make your changes
# 2. Commit and push
git add .
git commit -m "fix: your changes"
git push origin main

# That's it! GitHub Actions handles everything
```

Monitor deployment:
- **GitHub Actions**: https://github.com/hretheum/detektr/actions
- **Service Health**: `curl http://nebula:800X/health`

## 📦 Adding New Service

### Step 1: Create Service Structure

```bash
# Create service directory
mkdir -p services/my-service/src

# Create required files
touch services/my-service/Dockerfile
touch services/my-service/requirements.txt
touch services/my-service/src/main.py
```

### Step 2: Add to Deployment Pipeline

Edit `.github/workflows/deploy-self-hosted.yml`:

1. Add to change detection filters (around line 55):
```yaml
my-service:
  - 'services/my-service/**'
  - 'services/base-template/**'
```

2. Add to build matrix (around line 200):
```yaml
service:
  - example-otel
  - frame-tracking
  # ... other services
  - my-service  # ← Add here
```

3. Add to manual build workflow `.github/workflows/manual-service-build.yml` (around line 10):
```yaml
options:
  - example-otel
  # ... other services
  - my-service  # ← Add here
```

### Step 3: Configure Docker Compose

Add to `docker-compose.yml`:

```yaml
my-service:
  image: ghcr.io/hretheum/bezrobocie-detektor/my-service:latest
  container_name: my-service
  restart: unless-stopped
  ports:
    - "800X:800X"  # Use next available port
  environment:
    SERVICE_NAME: my-service
    PORT: 800X
  networks:
    - detektor-network
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:800X/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  depends_on:
    - redis  # If needed
```

### Step 4: Implement Required Endpoints

Every service MUST have:

```python
# src/main.py
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "my-service"}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Step 5: Deploy

```bash
git add .
git commit -m "feat: add my-service"
git push origin main
```

## 🔧 Unified Workflows

We use three main workflows:

### 1. `deploy-self-hosted.yml` (Main)
- **Triggers**: Push to main, manual
- **Purpose**: Build changed services and deploy
- **Smart**: Only builds what changed

### 2. `deploy-only.yml`
- **Triggers**: Manual only
- **Purpose**: Deploy without building
- **Use case**: Redeploy existing images

### 3. `manual-service-build.yml`
- **Triggers**: Manual only
- **Purpose**: Build single service with custom tag
- **Use case**: Testing, hotfixes

## 📊 Port Allocation

| Port | Service | Status |
|------|---------|--------|
| 8001 | rtsp-capture | ✅ Active |
| 8002 | face-recognition | 🔜 Planned |
| 8003 | object-detection | 🔜 Planned |
| 8004 | ha-bridge | 🔜 Planned |
| 8005 | metadata-storage | ✅ Active |
| 8006 | frame-tracking | ✅ Active |
| 8007 | echo-service | ✅ Active |
| 8008 | gpu-demo | ✅ Active |
| 8009 | example-otel | ✅ Active |
| 8010+ | Available | - |

## 🛠️ Common Tasks

### View Logs
```bash
ssh nebula "docker logs my-service --tail 50"
```

### Restart Service
```bash
ssh nebula "cd /opt/detektor && docker compose restart my-service"
```

### Check Health
```bash
curl http://nebula:800X/health
```

### Manual Deployment
```bash
# Trigger specific service build
gh workflow run manual-service-build.yml \
  -f service=my-service \
  -f deploy=true \
  -f tag=latest
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
ssh nebula "docker logs my-service"

# Check if port is already used
ssh nebula "sudo lsof -i :800X"

# Check image exists
ssh nebula "docker images | grep my-service"
```

### Build Fails
```bash
# Check GitHub Actions
gh run list --workflow=deploy-self-hosted.yml --limit=5

# View failed logs
gh run view --log-failed
```

### Deployment Stuck
```bash
# Clean up and retry
ssh nebula "cd /opt/detektor && docker compose down my-service"
ssh nebula "cd /opt/detektor && docker compose up -d my-service"
```

## 📁 Documentation Structure

```
docs/deployment/
├── README.md                    # This file - start here
├── guides/
│   ├── new-service.md          # Detailed new service guide
│   ├── secrets-management.md   # SOPS and secrets guide
│   └── monitoring.md           # Prometheus/Grafana setup
├── services/                   # Service-specific docs
│   ├── rtsp-capture.md
│   ├── frame-tracking.md
│   └── metadata-storage.md
├── troubleshooting/
│   ├── common-issues.md       # Common problems and solutions
│   └── emergency.md           # When things go wrong
└── templates/
    └── service-dockerfile.md   # Dockerfile template
```

## 🔐 Secrets Management

All secrets use SOPS encryption:

```bash
# Edit secrets
make secrets-edit

# Deploy with secrets
# Secrets are automatically decrypted during deployment
```

## 📈 Monitoring

- **Prometheus**: http://nebula:9090
- **Grafana**: http://nebula:3000
- **Jaeger**: http://nebula:16686

## 🤖 For LLMs - Key Rules

1. **NEVER** build on production - always use CI/CD
2. **NEVER** hardcode secrets - use SOPS encrypted `.env`
3. **ALWAYS** implement `/health` and `/metrics` endpoints
4. **ALWAYS** add new services to all 3 places in workflows
5. **ALWAYS** use `ghcr.io/hretheum/bezrobocie-detektor/` prefix

## 📚 Additional Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker Compose Docs](https://docs.docker.com/compose/)
- [SOPS Documentation](https://github.com/getsops/sops)
- [Project Context](../../PROJECT_CONTEXT.md)
