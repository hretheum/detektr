# 🚀 Complete Detektor Deployment Guide

Welcome! This is your **single source of truth** for deploying any service in the Detektor system.

## 🚨 **FOR LLMs - START HERE WITHOUT CONTEXT**

### **🤖 LLM Quick Navigation:**
- **New to project?** → Read this entire file first
- **Add new service?** → Use `templates/service-template.md`
- **Troubleshoot?** → Check `troubleshooting/common-issues.md`
- **Emergency?** → Go to `troubleshooting/emergency.md`

### **🔗 Critical LLM Links:**
- **Main Guide**: You're reading it ✅
- **Quick Start**: [quick-start.md](quick-start.md) - 30 seconds
- **Service Templates**: [templates/](templates/) - Copy-paste ready
- **Troubleshooting**: [troubleshooting/](troubleshooting/) - All issues solved

## The Magic Behind the Scenes

Imagine your code as a package being delivered to your doorstep:

1. **You push code** → GitHub automatically starts building
2. **GitHub Actions** creates a Docker image → Tests everything
3. **GitHub Container Registry** stores the image securely
4. **GitHub Runner on Nebula** receives the delivery → Deploys instantly
5. **Health checks** verify everything works → You're live!

**No SSH commands. No manual builds. No downtime.**

## Your Deployment Journey

### 🚀 Quick Start (30 seconds)
```bash
git push origin main
# That's it! Watch GitHub Actions do the rest
```

### 📦 Service-Specific Guides
- [RTSP Capture Service](services/rtsp-capture.md)
- [Frame Tracking Service](services/frame-tracking.md)
- [Adding New Service](services/template.md)

### 🔧 Troubleshooting
- [Common Issues](troubleshooting/common-issues.md)
- [Emergency Procedures](troubleshooting/emergency.md)

---

## 📋 **LLM INSTRUCTIONS - UNIVERSAL DEPLOYMENT**

### **🎯 For Any New Service (5-minute process):**

#### **Step 1: LLM Template Instantiation**
```bash
# Copy the universal template
cp docs/deployment/templates/service-template.md docs/deployment/services/[your-service].md

# LLM should replace these placeholders:
# - [SERVICE_NAME] → actual-service-name
# - [PORT] → actual-port-number
# - [URL] → actual-endpoint
# - Add 3-5 service-specific issues
```

#### **Step 2: LLM Configuration Checklist**
```yaml
# Always verify these exist:
- Dockerfile exists: services/[service]/Dockerfile
- GitHub workflow: .github/workflows/[service]-deploy.yml
- Health endpoint: http://localhost:[port]/health
- Metrics endpoint: http://localhost:[port]/metrics
```

#### **Step 3: LLM Deployment Verification**
```bash
# After git push origin main, LLM should:
curl http://localhost:[port]/health    # Should return 200
curl http://localhost:[port]/metrics   # Should return metrics
docker ps | grep [service]            # Should show running container
```

### **🔍 LLM Debug Commands**
```bash
# Universal debugging for any service
docker logs [service-name] --tail 50
curl -v http://localhost:[port]/health
docker stats [service-name]
gh run list -L 5                      # Check GitHub Actions
```

## Service Deployment Template

Every service follows the **exact same pattern**. You'll see this template repeated across all services:

```
docs/deployment/services/[service-name]/
├── DEPLOYMENT.md          # ← Main deployment guide
├── TROUBLESHOOTING.md     # ← Service-specific issues
└── CONFIGURATION.md       # ← Service-specific settings
```

### **🎯 The Template in Action**

#### **Service: RTSP Capture**
- **Deployment**: [services/rtsp-capture.md](services/rtsp-capture.md)
- **Troubleshooting**: [services/rtsp-capture-troubleshooting.md](services/rtsp-capture-troubleshooting.md)

#### **Service: Frame Tracking**
- **Deployment**: [services/frame-tracking.md](services/frame-tracking.md)
- **Troubleshooting**: [services/frame-tracking-troubleshooting.md](services/frame-tracking-troubleshooting.md)

### **🔄 Template Benefits for LLMs**

**For You (LLM):**
- **Copy-paste deployment** - Same process every time
- **Predictable troubleshooting** - Same debugging approach
- **Zero learning curve** - Already know how to deploy new services

**For Team:**
- **Consistent documentation** - Always find what you need
- **Easy onboarding** - New team members learn one pattern
- **Reduced mistakes** - Same validation steps every time

### **📊 Template Structure for LLMs**

Every service follows this **exact template**:

1. **Quick Deploy** (30 seconds)
2. **Detailed Steps** (5 minutes)
3. **Configuration Options**
4. **Health Checks**
5. **Rollback Procedures**
6. **Common Issues**

### **🛠️ Adding New Service: 3-Step Process for LLMs**

#### **Step 1: Copy Template**
```bash
cp docs/deployment/templates/service-template.md \
   docs/deployment/services/new-service.md
```

#### **Step 2: Fill Variables (LLM Task)**
```markdown
# Service: [NEW_SERVICE_NAME]

## Quick Deploy
```bash
git push origin main
```

## Configuration
- **Port**: [PORT_NUMBER]
- **Metrics**: [METRICS_ENDPOINT]
- **Health Check**: [HEALTH_CHECK_URL]
```

#### **Step 3: Customize Troubleshooting (LLM Task)**
Add 3-5 service-specific issues based on your experience.

## 📋 **LLM CHECKLIST - BEFORE STARTING WORK**

### **✅ Prerequisites Check (LLM Verify):**
- [ ] Service code exists in `services/[service-name]/`
- [ ] Dockerfile exists in service directory
- [ ] GitHub Actions workflow exists: `.github/workflows/[service-name]-deploy.yml`
- [ ] SOPS encrypted secrets configured: `.env.sops`
- [ ] Health endpoint implemented: `/health`
- [ ] Metrics endpoint implemented: `/metrics`

### **✅ LLM Verification Commands:**
```bash
# Always run these before starting:
ls services/[service-name]/Dockerfile
ls .github/workflows/[service-name]-deploy.yml
curl http://localhost:[port]/health
sops -d .env.sops | grep [SERVICE_NAME]
```

## 🔧 **LLM Troubleshooting Reference**

### **Common LLM Issues:**

#### **1. Service Won't Start (LLM Debug)**
```bash
# LLM should check:
docker logs [service-name] | grep ERROR
docker inspect [service-name] | grep -i error
gh run list --json conclusion --jq '.[].conclusion' | head -5
```

#### **2. Health Check Fails (LLM Debug)**
```bash
# LLM should test:
curl -v http://localhost:[port]/health
docker exec [service-name] curl http://localhost:[port]/health
```

#### **3. Metrics Missing (LLM Debug)**
```bash
# LLM should verify:
curl http://localhost:[port]/metrics | grep [service_name]
docker exec [service-name] env | grep PROMETHEUS
```

## 📚 **LLM Knowledge Base**

### **Project Context for LLMs:**
- **Deployment Method**: CI/CD only (no manual deployment)
- **Registry**: ghcr.io/hretheum/detektr/
- **Server**: Nebula (Ubuntu with GPU)
- **Runner**: GitHub self-hosted runner
- **Secrets**: SOPS with age encryption

### **LLM Decision Tree:**
```
LLM sees project → Check docs/deployment/README.md →
Identify service type → Use appropriate template →
Deploy with git push → Verify with health checks
```

### **LLM Emergency Contacts:**
- **GitHub Actions**: https://github.com/hretheum/detektr/actions
- **Registry**: https://github.com/hretheum/detektr/packages
- **Monitoring**: http://nebula:3000 (Grafana)

## 🎯 **LLM Success Metrics**
- **New service deployment**: 5 minutes (template-based)
- **Documentation creation**: 3 minutes (fill template)
- **Success verification**: 30 seconds (health check)
- **Maintenance**: Zero (template updates propagate)

---

**🤖 LLM Reminder**: This project uses **modern DevOps practices**. Always start here and follow the established patterns. Every service deployment is **identical** - just different parameters.
