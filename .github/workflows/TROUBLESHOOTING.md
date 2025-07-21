# GitHub Actions Workflow Troubleshooting Guide

## Problem: Workflow Jobs Showing "Skipped" Status

This guide explains why your GitHub Actions workflows might be showing "skipped" status and provides solutions.

## Common Causes and Solutions

### 1. **Path Filter Issues** (Most Common)
**Problem**: Workflows only run when specific files are changed.

**Solution**:
- **Original workflows** only trigger on:
  - `services/rtsp-capture/**`
  - `.github/workflows/[workflow-name].yml`
- **Fixed workflows** include additional paths and manual triggers

**How to test**: Use `workflow_dispatch` to manually trigger workflows.

### 2. **Branch Restrictions**
**Problem**: Workflows only run on specific branches.

**Original restrictions**:
- Only `main` and `develop` branches
- PRs must target `main` or `develop`

**Testing approach**: Push to `main`/`develop` or create PRs to these branches.

### 3. **Missing Required Secrets**
**Required secrets**:
- `KUBECONFIG`: For Kubernetes health checks
- `SLACK_WEBHOOK_URL`: For failure notifications
- `GITHUB_TOKEN`: Usually available by default

**Check secrets availability**:
```bash
# Run diagnostic workflow to check secrets
```

### 4. **Conditional Job Execution**
**Problem**: Jobs have strict `if` conditions.

| Job | Original Condition | Fixed Condition |
|-----|-------------------|-----------------|
| `performance-test` | Only `workflow_dispatch` | Now includes `main`/`develop` pushes |
| `integration-test` | Only PR or `main` branch | Now includes `develop` and `workflow_dispatch` |
| `deploy-staging` | Only `develop` branch | Now includes `workflow_dispatch` |
| `deploy-production` | Only `main` branch | Unchanged (security) |

### 5. **Job Dependencies**
**Problem**: Jobs depend on previous jobs succeeding.

**Original chain**:
```
test → security-scan → build-and-push → integration-test → deploy
```

**Fixed approach**: Added `continue-on-error: true` and `if: always()` conditions.

## Using the Fixed Workflows

### Option 1: Replace Original Workflows

```bash
# Backup original workflows
cp .github/workflows/monitoring.yml .github/workflows/monitoring.yml.backup
cp .github/workflows/rtsp-capture-ci.yml .github/workflows/rtsp-capture-ci.yml.backup

# Use fixed versions
cp .github/workflows/monitoring-fixed.yml .github/workflows/monitoring.yml
cp .github/workflows/rtsp-capture-ci-fixed.yml .github/workflows/rtsp-capture-ci.yml
```

### Option 2: Use Diagnostic Workflow

Run the diagnostic workflow to identify specific issues:

1. Go to Actions tab in GitHub
2. Select "Diagnostic - Check Skip Conditions"
3. Click "Run workflow"
4. Review the output for specific skip reasons

### Option 3: Manual Testing

**For development/testing**:
1. Push changes to `develop` branch
2. Use `workflow_dispatch` to manually trigger
3. Ensure changes include `services/rtsp-capture/**` or workflow files

## Quick Fix Commands

```bash
# Add missing secrets (if needed)
gh secret set KUBECONFIG < kubeconfig.yaml
gh secret set SLACK_WEBHOOK_URL https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Test workflow manually
gh workflow run diagnostic.yml
```

## Environment-Specific Notes

### Development Environment
- KUBECONFIG likely missing (expected)
- Use `workflow_dispatch` for testing
- Fixed workflows handle missing secrets gracefully

### Staging/Production
- Ensure KUBECONFIG is configured
- Verify all required secrets are present
- Check cluster connectivity

## Monitoring Workflow Status

After applying fixes:

1. **Check Actions tab** for workflow runs
2. **Review job logs** for specific error messages
3. **Use diagnostic workflow** for detailed analysis
4. **Monitor artifacts** for reports and logs

## Rollback Plan

If fixes cause issues:

```bash
# Restore original workflows
cp .github/workflows/monitoring.yml.backup .github/workflows/monitoring.yml
cp .github/workflows/rtsp-capture-ci.yml.backup .github/workflows/rtsp-capture-ci.yml
```

## Support

If issues persist:
1. Run the diagnostic workflow
2. Check the Actions tab for detailed logs
3. Verify secrets configuration
4. Ensure branch permissions are correct
