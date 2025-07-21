# GitHub Runner Deployment Process for RTSP Capture Service

## Overview
The RTSP capture service uses **GitHub self-hosted runner** on Nebula server for continuous deployment.

## GitHub Runner Setup
- **Runner Location**: Nebula server (`runs-on: self-hosted`)
- **Runner Name**: `nebula-forge` (self-hosted runner)
- **Working Directory**: `/opt/detektor`
- **Trigger**: Push to main branch with RTSP changes

## Deployment Flow

### 1. **GitHub Actions Pipeline**
```mermaid
GitHub Actions → Build → Test → Security Scan → Deploy → Health Check
```

### 2. **Registry Images**
- **Latest**: `ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest`
- **Tagged**: `ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:main-SHA`
- **Versioned**: `ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:v1.0.0`

### 3. **Automated Deployment Process**

#### **Step 1: GitHub Actions Triggers**
```bash
# Automatic trigger on push to main
git push origin main
```

#### **Step 2: GitHub Runner Executes**
```bash
# This runs on Nebula via self-hosted runner
cd /opt/detektor
./scripts/deploy-to-nebula.sh --service rtsp-capture --no-prompt
```

#### **Step 3: Health Verification**
```bash
# Automatic health checks
curl -f http://localhost:8001/health
docker ps | grep rtsp-capture
```

## Manual Deployment (if needed)

### **Using GitHub Runner**
```bash
# Check runner status
ssh nebula "cd /opt/detektor && systemctl status github-runner"

# Manual trigger via GitHub API
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/hretheum/bezrobocie-detektor/dispatches \
  -d '{"event_type": "deploy-rtsp"}'
```

### **Direct Deployment (fallback)**
```bash
# Deploy using registry images
ssh nebula "cd /opt/detektor && \
  docker-compose -f docker-compose.yml -f docker-compose.rtsp.yml up -d rtsp-capture"
```

## Environment Configuration

### **Required on Nebula:**
1. **GitHub Runner Service**
   - Service: `github-runner`
   - Config: `/opt/detektor/.github-runner`
   - Logs: `/var/log/github-runner/`

2. **Registry Access**
   - GitHub Container Registry: `ghcr.io`
   - Authentication: GitHub token

3. **Environment Variables**
   - RTSP_URL (encrypted via SOPS)
   - REDIS_URL
   - Database connections

## Monitoring

### **GitHub Actions Monitoring:**
- **URL**: https://github.com/hretheum/bezrobocie-detektor/actions
- **Workflow**: RTSP Capture Service CI/CD

### **Runner Status:**
```bash
# Check runner health
ssh nebula "cd /opt/detektor && ./scripts/check-runner-status.sh"
```

## Troubleshooting

### **Common Issues:**

1. **Runner Not Responding**
   ```bash
   # Restart GitHub runner
   ssh nebula "sudo systemctl restart github-runner"
   ```

2. **Image Pull Issues**
   ```bash
   # Check registry access
   ssh nebula "docker pull ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest"
   ```

3. **Environment Issues**
   ```bash
   # Check .env configuration
   ssh nebula "cd /opt/detektor && sops -d .env | grep RTSP_URL"
   ```

## Verification Commands

### **After Deployment:**
```bash
# Check service health
ssh nebula "curl -f http://localhost:8001/health"

# Check metrics
ssh nebula "curl -s http://localhost:8001/metrics | grep rtsp_"

# Check traces
ssh nebula "curl -s http://localhost:16686/api/traces?service=rtsp-capture"
