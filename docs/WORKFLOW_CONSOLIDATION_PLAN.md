# Workflow Consolidation Plan

## 📊 Current State Analysis

### Active Workflows (16 files)
```
1. main-pipeline.yml         - Main CI/CD pipeline ✅
2. pr-checks.yml            - PR validation ✅
3. manual-operations.yml    - Manual ops ✅
4. scheduled-tasks.yml      - Scheduled tasks ✅
5. release.yml              - Release management ✅
6. security.yml             - Security scanning
7. ci.yml                   - Service quality checks
8. ghcr-cleanup.yml         - Registry cleanup
9. build-gpu-base.yml       - GPU base image
10. cleanup-runner.yml      - Runner cleanup
11. db-deploy.yml           - Database deployment
12. deploy-production-isolated.yml - Isolated deploy
13. diagnostic.yml          - Diagnostics
14. manual-service-build.yml - Manual builds
15. test-runner.yml         - Runner testing
16. UNIFIED-deploy.yml      - Unified deployment
```

### Dependency Analysis

#### Core Workflows (Keep)
- `main-pipeline.yml` - Primary build/deploy
- `pr-checks.yml` - PR validation
- `release.yml` - Semantic versioning

#### Can Be Merged
- `security.yml` + `ci.yml` → into `main-pipeline.yml`
- `manual-operations.yml` + `diagnostic.yml` + `manual-service-build.yml` → `maintenance.yml`
- `scheduled-tasks.yml` + `ghcr-cleanup.yml` + `cleanup-runner.yml` → `scheduled.yml`
- `db-deploy.yml` + `deploy-production-isolated.yml` + `UNIFIED-deploy.yml` → into `main-pipeline.yml`

## 🎯 Target Architecture (3-4 workflows)

### 1. `main.yml` - Unified Pipeline
Combines:
- Current `main-pipeline.yml`
- `ci.yml` (quality checks)
- `security.yml` (security scanning)
- Database deployment logic

```yaml
name: Main Pipeline
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  # From pr-checks.yml
  validate:
    if: github.event_name == 'pull_request'
    # ... validation logic

  # From ci.yml
  quality:
    # ... linting, type checking

  # From security.yml
  security:
    # ... vulnerability scanning

  # From main-pipeline.yml
  build:
    needs: [quality, security]
    # ... build logic

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    # ... deploy logic
```

### 2. `maintenance.yml` - Manual Operations
Combines:
- Current `manual-operations.yml`
- `diagnostic.yml`
- `manual-service-build.yml`
- `test-runner.yml`

```yaml
name: Maintenance
on:
  workflow_dispatch:
    inputs:
      operation:
        type: choice
        options:
          - cleanup
          - diagnostic
          - build-service
          - test-runner
          - backup
          - restore
```

### 3. `scheduled.yml` - Automated Tasks
Combines:
- Current `scheduled-tasks.yml`
- `ghcr-cleanup.yml`
- `cleanup-runner.yml`

```yaml
name: Scheduled Tasks
on:
  schedule:
    - cron: '0 4 * * 0'  # Weekly
    - cron: '0 2 * * *'  # Daily
  workflow_dispatch:
```

### 4. `release.yml` - Keep As Is
No changes needed - clean and focused

## 📋 Migration Strategy

### Phase 1: Create New Workflows (Day 1)
1. Create new workflow files alongside existing ones
2. Copy logic from source workflows
3. Test in parallel without disabling old workflows

### Phase 2: Parallel Testing (Days 2-3)
1. Run both old and new workflows
2. Compare results
3. Fix any discrepancies

### Phase 3: Gradual Migration (Days 4-5)
1. Update triggers to prevent duplication
2. Add `.disabled` suffix to old workflows
3. Monitor for issues

### Phase 4: Cleanup (Day 7)
1. Remove `.disabled` workflows
2. Update documentation
3. Celebrate 🎉

## 🔧 Implementation Tasks

### Task 1: Create `main.yml`
- [ ] Merge build, test, security logic
- [ ] Preserve matrix strategies
- [ ] Maintain conditional execution
- [ ] Test PR vs push behavior

### Task 2: Create `maintenance.yml`
- [ ] Consolidate manual operations
- [ ] Use workflow_dispatch with choices
- [ ] Preserve all functionality
- [ ] Add clear documentation

### Task 3: Create `scheduled.yml`
- [ ] Merge all scheduled tasks
- [ ] Use multiple cron triggers
- [ ] Add manual trigger option
- [ ] Preserve task isolation

### Task 4: Update Documentation
- [ ] Update README.md
- [ ] Update contribution guide
- [ ] Create migration notes
- [ ] Update CI/CD docs

## 📊 Success Metrics

1. **Reduction**: 16 → 4 workflows (75% reduction)
2. **Performance**: No increase in CI time
3. **Reliability**: No new failures
4. **Usability**: Easier to find/trigger workflows

## ⚠️ Risks & Mitigations

### Risk 1: Breaking Changes
- **Mitigation**: Parallel testing period
- **Rollback**: Keep old workflows disabled

### Risk 2: Lost Functionality
- **Mitigation**: Comprehensive testing matrix
- **Validation**: Compare workflow runs

### Risk 3: Increased Complexity
- **Mitigation**: Clear job names and documentation
- **Solution**: Modular job design

## 📅 Timeline

- **Day 1**: Create new workflows
- **Days 2-3**: Parallel testing
- **Days 4-5**: Migration
- **Day 6**: Validation
- **Day 7**: Cleanup

## 🎯 Expected Benefits

1. **Simplified Management**: 75% fewer files
2. **Better Organization**: Logical grouping
3. **Reduced Duplication**: Shared job logic
4. **Easier Discovery**: Clear workflow purposes
5. **Lower Maintenance**: Fewer files to update
