# Runbook: [PROCEDURE_NAME]

## Overview

**Purpose**: Brief description of when to use this runbook
**Audience**: Who should execute this procedure
**Frequency**: How often this procedure is typically run

## Prerequisites

- [ ] Access to production systems
- [ ] Required tools installed
- [ ] Backup taken (if applicable)
- [ ] Stakeholders notified

## Procedure Steps

### Step 1: [Action Name]

**What**: Description of what this step does
**Why**: Why this step is necessary
**Commands**:

```bash
# Step 1 commands here
command --option value
```

**Expected output**:

```
Expected command output
```

**Verification**:

```bash
# How to verify step completed successfully
verify-command
```

### Step 2: [Action Name]

[Same structure]

## Rollback Procedure

Steps to undo changes if something goes wrong:

1. Stop service: `systemctl stop service-name`
2. Restore backup: `restore-command`
3. Verify rollback: `health-check`

## Troubleshooting

### Issue: Common Problem A

**Symptoms**: How to recognize this issue
**Solution**:

```bash
fix-command
```

### Issue: Common Problem B

**Symptoms**: How to recognize this issue
**Solution**:

```bash
fix-command
```

## Monitoring & Alerts

- Dashboard: Link to relevant Grafana dashboard
- Alerts: Which alerts to watch
- Logs: Where to find relevant logs

## Success Criteria

How to know the procedure completed successfully:

- [ ] All services healthy
- [ ] Metrics within normal range
- [ ] No error alerts triggered

## Emergency Contacts

- **On-call engineer**: [contact info]
- **Service owner**: [contact info]
- **Escalation**: [contact info]

## Related Documentation

- Architecture: [link]
- API docs: [link]
- Other runbooks: [links]

---
**Last updated**: YYYY-MM-DD
**Last tested**: YYYY-MM-DD
**Owner**: [Team/Person]
