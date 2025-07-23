# 🤖 Claude - AI Assistant Project Guide

## 🎯 **For Future LLMs - Project Context**

### 📍 **You Are Here**
This is a **production RTSP capture system** deployed on **Nebula server** using **GitHub Actions CI/CD** with **registry-based deployment**.

**Project Name**: Detektor
**Repository**: github.com/hretheum/detektr
**Registry**: ghcr.io/hretheum/detektr/

### 🏗️ **Architecture Overview**
```
Developer → GitHub (detektr) → GitHub Actions → ghcr.io/hretheum/detektr → Nebula Server
```

### 🔗 **Critical Links for LLMs**
- **Main Deployment Guide**: `docs/deployment/README.md`
- **Quick Start**: `docs/deployment/quick-start.md`
- **Service Templates**: `docs/deployment/templates/`
- **Troubleshooting**: `docs/deployment/troubleshooting/`

## 🚀 **LLM Quick Start Checklist**

### **When Starting Work on This Project**

1. **Check Current Status**
   ```bash
   # Always start here
   cat docs/deployment/README.md
   ```

2. **Identify Service Type**
   - **RTSP Capture**: `docs/deployment/services/rtsp-capture.md`
   - **Frame Tracking**: `docs/deployment/services/frame-tracking.md`
   - **New Service**: Use template from `docs/deployment/templates/service-template.md`

3. **Deployment Method**
   - **Always use**: `git push origin main` (CI/CD)
   - **Never use**: Manual deployment (deprecated)

### **For New Service Development**
```bash
# 1. Copy template
cp docs/deployment/templates/service-template.md docs/deployment/services/[new-service].md

# 2. Follow template
# 3. Deploy with: git push origin main
```

## 📊 **Project Structure for LLMs**

```
detektor/
├── docs/deployment/          # ← START HERE
│   ├── README.md            # Unified deployment guide
│   ├── services/            # Service-specific docs
│   ├── templates/           # Copy-paste templates
│   └── troubleshooting/     # Common issues
├── services/                # Service code
├── scripts/                 # Deployment scripts
└── .github/workflows/       # CI/CD definitions
```

## 🔍 **LLM Investigation Commands**

### **Check Service Status**
```bash
# Quick health check
curl http://nebula:8080/health  # RTSP
curl http://nebula:8081/health  # Frame Tracking

# Check GitHub Actions
gh run list -L 5
```

### **Debug Deployment Issues**
```bash
# Check current deployment
docker ps | grep detektor
docker logs [service-name] --tail 20

# Check configuration
sops -d .env.sops
```

## 🎯 **Common LLM Tasks**

### **Add New Service**
1. **Use template**: `docs/deployment/templates/service-template.md`
2. **Follow pattern**: 80% generic + 20% specific
3. **Deploy**: `git push origin main`

### **Troubleshoot Issues**
1. **Check**: `docs/deployment/troubleshooting/common-issues.md`
2. **Emergency**: `docs/deployment/troubleshooting/emergency.md`
3. **Debug**: Use provided commands in troubleshooting

### **Update Configuration**
1. **Edit**: `.env.sops` (encrypted)
2. **Deploy**: `git push origin main`
3. **Verify**: Health checks

## 🚨 **LLM Red Flags**

### **Never Do These**
- ❌ Manual deployment via SSH
- ❌ Edit files directly on server
- ❌ Use deprecated documentation in `deprecated/`
- ❌ Skip health checks after deployment

### **Always Do These**
- ✅ Use CI/CD deployment (`git push origin main`)
- ✅ Follow template structure
- ✅ Check health endpoints
- ✅ Use encrypted secrets with SOPS

## 📝 **LLM Note-Taking Template**

When working on this project, create entries like:

```markdown
## [Date] - [Service Name] - [Task]
- **Status**: [working/completed/failed]
- **Deployment**: [git commit hash]
- **Health Check**: [URL + status]
- **Issues**: [list or "none"]
- **Next Steps**: [actions]
```

## 🔗 **External Resources for LLMs**

### **GitHub Integration**
- **Repository**: https://github.com/hretheum/detektr
- **Actions**: https://github.com/hretheum/detektr/actions
- **Registry**: https://github.com/hretheum/detektr/packages

### **Monitoring**
- **Prometheus**: http://nebula:9090
- **Grafana**: http://nebula:3000
- **Jaeger**: http://nebula:16686

## 🎯 **LLM Decision Tree**

```
┌─────────────────────────────────────┐
│ Starting work on Detektor project  │
└─────────────────┬───────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼───┐              ┌───────▼───────┐
│New    │              │Existing       │
│Service│              │Service        │
└───┬───┘              └───────┬───────┘
    │                         │
┌───▼───┐              ┌───────▼───────┐
│Use    │              │Check specific │
│template│              │service doc    │
└───┬───┘              └───────┬───────┘
    │                         │
┌───▼─────────────────────────▼─────┐
│   Deploy with: git push origin main │
│   Verify with: health endpoints    │
│   Document with: template pattern  │
└─────────────────────────────────────┘
```

## 🎉 **LLM Success Metrics**
- **Deployment time**: 30 seconds (CI/CD)
- **Documentation time**: 5 minutes (template-based)
- **Success rate**: 100% (health check verification)
- **Maintenance**: Minimal (template updates)

## 📝 **Recent Changes (2025-07-23)**

### ✅ Faza 1: Naming Unification
- **Change**: bezrobocie-detektor → detektr
- **Registry**: ghcr.io/hretheum/detektr/
- **Updated**: 42 files

### ✅ Faza 2: Workflow Consolidation
- **Reduced**: 14 → 5 workflows (-64%)
- **New Structure**:
  - `main-pipeline.yml`: Build, deploy, or both
  - `pr-checks.yml`: PR validation + tests
  - `manual-operations.yml`: Cleanup, diagnostic, backup
  - `scheduled-tasks.yml`: Daily/weekly/monthly jobs
  - `release.yml`: Unchanged
- **Usage**:
  ```bash
  # Main pipeline
  gh workflow run main-pipeline.yml -f action=build-and-deploy

  # Manual operations
  gh workflow run manual-operations.yml -f operation=cleanup-docker

  # Check PR (automatic on PR)
  # Scheduled tasks (automatic or manual)
  gh workflow run scheduled-tasks.yml -f task=daily-cleanup
  ```

### ✅ Faza 3: Docker Compose Reorganization
- **Reduced**: 16+ → 8 files in hierarchy
- **New Structure**:
  ```
  docker/
  ├── base/                  # Core definitions
  ├── environments/          # Dev/prod overrides
  └── features/              # GPU, HA, AI services
  ```
- **Convenience Scripts**:
  ```bash
  ./docker/dev.sh up -d      # Development
  ./docker/prod.sh up -d     # Production
  ./scripts/migrate-docker-compose.sh  # Migration
  ```
- **Makefile Targets**:
  ```bash
  make dev-up               # Start development
  make prod-up              # Start production
  make migrate-compose      # Migrate structure
  ```

### ⏳ Faza 4: GHCR Cleanup (IN PROGRESS)

**Remember**: This project is **production-ready** and uses **modern DevOps practices**. Always start with the documentation in `docs/deployment/` and follow the established patterns.
