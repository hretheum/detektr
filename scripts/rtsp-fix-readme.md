# RTSP Service Deployment Fix

## Problem
RTSP service failing to start with error: "ModuleNotFoundError: No module named 'opentelemetry.instrumentation.redis'"

## Root Cause Analysis
1. **Package specified correctly** in `services/rtsp-capture/requirements.txt` (line 26: `opentelemetry-instrumentation-redis==0.43b0`)
2. **Dockerfile issue**: The multi-stage build might have caching issues causing the package to not be installed in the runtime image
3. **Registry image**: The pre-built image in ghcr.io might be outdated or cached

## Solution Options

### Option 1: Emergency Fix (Fastest)
Run the emergency fix script directly on nebula:

```bash
# Copy emergency script to nebula
scp scripts/emergency-rtsp-fix.sh nebula:/tmp/
ssh nebula "chmod +x /tmp/emergency-rtsp-fix.sh && /tmp/emergency-rtsp-fix.sh"
```

### Option 2: Rebuild & Deploy (Recommended)
Run the proper fix script on nebula:

```bash
# Copy fix script to nebula
scp scripts/fix-rtsp-deployment.sh nebula:/tmp/
ssh nebula "chmod +x /tmp/fix-rtsp-deployment.sh && /tmp/fix-rtsp-deployment.sh"
```

### Option 3: Manual Fix
Execute commands directly on nebula:

```bash
# SSH to nebula
ssh nebula

# Navigate to deployment directory
cd /opt/detektor

# Pull latest image
docker pull ghcr.io/hretheum/detektr/rtsp-capture:latest

# Force rebuild from source
docker compose build --no-cache rtsp-capture
docker compose up -d rtsp-capture

# Check service
docker logs detektor-rtsp-capture-1
curl -f http://localhost:8001/health
```

## Verification Steps
1. Check package installation: `docker exec detektor-rtsp-capture-1 python -c "import opentelemetry.instrumentation.redis; print('OK')"`
2. Verify service health: `curl -f http://localhost:8001/health`
3. Check logs: `docker logs detektor-rtsp-capture-1`

## Docker Improvements
The Dockerfile has been updated to:
- Add package verification step during build
- Ensure proper installation of opentelemetry-instrumentation-redis
- Include runtime validation

## Long-term Fix
Update CI/CD pipeline to:
- Force rebuild when requirements.txt changes
- Add package verification in build process
- Tag images with requirements hash for better caching
