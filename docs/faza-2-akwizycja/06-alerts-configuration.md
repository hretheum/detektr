# Faza 2 / Zadanie 6: Alerty - frame drop, latency, queue size

## Cel zadania

Skonfigurować system alertów dla krytycznych metryk pipeline'u z automatyczną eskalacją i integracją z systemami powiadomień.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja Alertmanager**
   - **Metryka**: Alertmanager running, API dostępne
   - **Walidacja**:

     ```bash
     curl http://localhost:9093/-/healthy
     curl http://localhost:9093/api/v2/status | jq .cluster.status
     # "ready"
     ```

   - **Czas**: 0.5h

2. **[ ] Test notification channels**
   - **Metryka**: Email/Slack webhook working
   - **Walidacja**:

     ```bash
     amtool alert add test_alert --annotation=test=true
     # Check if notification received
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Alert rules definition

#### Zadania atomowe

1. **[ ] Frame drop rate alerts**
   - **Metryka**: Alert gdy frame loss >1% przez 2 min
   - **Walidacja**:

     ```yaml
     # prometheus/rules/frame_pipeline.yml
     - alert: HighFrameDropRate
       expr: rate(frames_dropped_total[2m]) / rate(frames_captured_total[2m]) > 0.01
       for: 2m
     ```

   - **Czas**: 1.5h

2. **[ ] Processing latency alerts**
   - **Metryka**: p95 latency >200ms triggers warning
   - **Walidacja**:

     ```promql
     histogram_quantile(0.95, rate(frame_processing_duration_bucket[5m])) > 0.2
     # Test with synthetic slow processing
     ```

   - **Czas**: 1.5h

3. **[ ] Queue saturation alerts**
   - **Metryka**: Queue >5000 items = critical
   - **Walidacja**:

     ```bash
     # Fill queue artificially
     redis-cli LPUSH frame_queue $(seq 1 5001)
     # Alert should fire within 1 min
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- All alert rules active
- Thresholds properly tuned
- No false positives

### Blok 2: Alert routing i grouping

#### Zadania atomowe

1. **[ ] Alertmanager routing config**
   - **Metryka**: Alerts routed by severity
   - **Walidacja**:

     ```yaml
     # alertmanager/config.yml
     route:
       group_by: ['alertname', 'cluster']
       group_wait: 10s
       routes:
         - match: {severity: critical}
           receiver: pagerduty
     ```

   - **Czas**: 2h

2. **[ ] Alert suppression rules**
   - **Metryka**: Maintenance mode stops alerts
   - **Walidacja**:

     ```bash
     amtool silence add alertname=".*" --comment="Maintenance"
     # No alerts fire during silence
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Smart routing working
- Alert fatigue minimized
- Escalation paths clear

### Blok 3: Integration i dokumentacja

#### Zadania atomowe

1. **[ ] Grafana alert integration**
   - **Metryka**: Alerts visible in dashboards
   - **Walidacja**:

     ```bash
     curl http://localhost:3000/api/alerts | jq '.[].state'
     # Shows current alert states
     ```

   - **Czas**: 1.5h

2. **[ ] Runbook links i docs**
   - **Metryka**: Each alert has runbook URL
   - **Walidacja**:

     ```yaml
     annotations:
       runbook_url: "https://docs/alerts/{{ .GroupLabels.alertname }}"
     # All URLs resolve correctly
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Full integration achieved
- Documentation complete
- Operators confident

## Całościowe metryki sukcesu zadania

1. **Coverage**: 100% critical paths have alerts
2. **Accuracy**: <5% false positive rate
3. **Response**: Alert to notification <30s

## Deliverables

1. `/prometheus/rules/frame_pipeline.yml` - Alert rules
2. `/alertmanager/config.yml` - Routing configuration
3. `/docs/runbooks/` - Alert response procedures
4. `/grafana/provisioning/notifiers/` - Notification channels
5. `/scripts/test_alerts.sh` - Alert testing script

## Narzędzia

- **Prometheus**: Alert rule evaluation
- **Alertmanager**: Alert routing and grouping
- **amtool**: CLI for alert management
- **webhook**: Test notification endpoint

## Zależności

- **Wymaga**:
  - Metrics collection working
  - Notification channels configured
- **Blokuje**: Production readiness

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Alert storm | Średnie | Wysoki | Rate limiting, grouping | >10 alerts/min |
| Alert fatigue | Wysokie | Średni | Proper thresholds, suppression | Team ignoring alerts |

## Rollback Plan

1. **Detekcja problemu**:
   - Too many false alerts
   - Alerts not firing
   - Notification failures

2. **Kroki rollback**:
   - [ ] Silence all alerts: `amtool silence add alertname=".*"`
   - [ ] Restore previous rules from git
   - [ ] Reload Prometheus config
   - [ ] Verify with test alerts

3. **Czas rollback**: <5 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/alerts-configuration.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/alerts-configuration.md#deploy](docs/deployment/services/alerts-configuration.md#deploy)

2. **[ ] Konfiguracja Alertmanager na Nebuli**
   - **Metryka**: Alertmanager running with routing rules
   - **Walidacja**: `curl http://nebula:9093/api/v2/status`
   - **Procedura**: [docs/deployment/services/alerts-configuration.md#configuration](docs/deployment/services/alerts-configuration.md#configuration)

3. **[ ] Upload alert rules do Prometheus**
   - **Metryka**: All alert rules loaded and active
   - **Walidacja**: `curl http://nebula:9090/api/v1/rules`
   - **Procedura**: [docs/deployment/services/alerts-configuration.md#rules](docs/deployment/services/alerts-configuration.md#rules)

4. **[ ] Test alerting pipeline**
   - **Metryka**: Test alert fires and is received
   - **Walidacja**: Trigger test alert and verify notification
   - **Procedura**: [docs/deployment/services/alerts-configuration.md#testing](docs/deployment/services/alerts-configuration.md#testing)

5. **[ ] Grafana alert dashboard**
   - **Metryka**: Alert status visible in Grafana
   - **Walidacja**: Dashboard shows firing/pending alerts
   - **Procedura**: [docs/deployment/services/alerts-configuration.md#dashboard](docs/deployment/services/alerts-configuration.md#dashboard)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź status Alertmanager:
curl http://nebula:9093/api/v2/status | jq

# Sprawdź załadowane reguły:
curl http://nebula:9090/api/v1/rules | jq '.data.groups[].rules[] | {alert: .name, state: .state}'

# Test alert:
amtool --alertmanager.url=http://nebula:9093 alert add test
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/alerts-configuration.md](docs/deployment/services/alerts-configuration.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Alertmanager operational na Nebuli
- ✅ All frame pipeline alerts configured
- ✅ Notification channels working
- ✅ Alert dashboard in Grafana
- ✅ <1min alert response time
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tej fazy, przejdź do:
→ [Faza 3 - AI Services](../faza-3-ai-services/02-object-detection.md)
