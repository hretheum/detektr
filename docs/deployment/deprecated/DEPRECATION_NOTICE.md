# 🚨 DEPRECATED DOCUMENTATION

## ⚠️ Notice
**All files in this directory are deprecated** and have been replaced by the unified deployment documentation structure.

## 📁 New Structure

### ✅ Current Location
All up-to-date documentation is now located in:
```
docs/deployment/
├── README.md                    # Main unified guide
├── quick-start.md              # 30-second deployment
├── services/
│   ├── rtsp-capture.md         # RTSP service deployment
│   └── template.md             # Template for new services
├── troubleshooting/
│   ├── common-issues.md        # Common problems & solutions
│   └── emergency.md            # Emergency procedures
└── templates/
    └── service-template.md     # Copy-paste template
```

### 🗑️ Deprecated Files
The following files have been moved here:
- `CI_CD_IMPLEMENTATION.md` → See `README.md`
- `CI_CD_SETUP.md` → See `README.md`
- `MANUAL_DEPLOYMENT.md` → See `quick-start.md`
- `GITHUB_SECRETS_SETUP.md` → See `README.md`
- `SELF_HOSTED_RUNNER_SETUP.md` → See `README.md`
- `DEPLOYMENT_CHECKLIST.md` → See `services/rtsp-capture.md`
- `DEPLOYMENT_PHASE_1.md` → See `README.md`
- `SECRETS_MANAGEMENT.md` → See `README.md`

## 🚀 Migration Guide

### For RTSP Capture Deployment
**Old way**: Read 8 different files
**New way**: Read `docs/deployment/services/rtsp-capture.md`

### For New Service Deployment
**Old way**: Create from scratch
**New way**: Copy `docs/deployment/templates/service-template.md`

### For Troubleshooting
**Old way**: Search through multiple files
**New way**: Check `docs/deployment/troubleshooting/common-issues.md`

## 📅 Timeline
- **2025-07-21**: Deprecated files moved here
- **2025-08-01**: These files will be removed
- **2025-08-15**: Complete cleanup

## 🆘 Need Help?
- **Quick start**: `docs/deployment/quick-start.md`
- **Full guide**: `docs/deployment/README.md`
- **Issues**: `docs/deployment/troubleshooting/common-issues.md`
