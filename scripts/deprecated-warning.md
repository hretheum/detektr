# ⚠️ DEPRECATED - DO NOT USE

The manual deployment scripts in this directory are **deprecated** and **should not be used**.

## Use GitHub Actions CI/CD instead:

1. **Push to main branch** with RTSP changes to trigger automatic deployment
2. **Manual deployment** should use:
   ```bash
   ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.yml -f docker-compose.rtsp.yml up -d rtsp-capture"
   ```

## Current Status:
- ✅ GitHub Actions workflow: `.github/workflows/rtsp-capture-deploy.yml`
- ✅ Registry images: `ghcr.io/hretheum/bezrobocie-detektor/rtsp-capture:latest`
- ✅ Automated testing and security scanning
- ✅ Zero-downtime deployment
