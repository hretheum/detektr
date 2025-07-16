# Faza 1 / Zadanie 8: Podstawowe dashboardy i alerty

## Cel zadania

Utworzenie kompletnego zestawu dashboardów Grafana oraz konfiguracja alertów dla monitorowania infrastruktury, zapewniając proaktywne wykrywanie problemów od samego początku projektu.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja Grafana i Prometheus działają**
   - **Metryka**: Grafana dostępna, Prometheus zbiera metryki
   - **Walidacja**:

     ```bash
     curl -s http://admin:admin@localhost:3000/api/health | jq '.database'
     # "ok"
     curl -s http://localhost:9090/api/v1/query?query=up | jq '.status'
     # "success"
     ```

   - **Czas**: 0.5h

2. **[ ] Weryfikacja metryk systemowych dostępne**
   - **Metryka**: node_exporter, cadvisor eksportują metryki
   - **Walidacja**:

     ```bash
     curl -s http://localhost:9090/api/v1/targets | \
       jq '.data.activeTargets[] | select(.labels.job | contains("node")) | .health'
     # "up"
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: System monitoring dashboards

#### Zadania atomowe

1. **[ ] Dashboard: System Overview**
   - **Metryka**: CPU, RAM, Disk, Network dla serwera
   - **Walidacja**:

     ```bash
     # Import dashboard
     curl -X POST http://admin:admin@localhost:3000/api/dashboards/import \
       -H "Content-Type: application/json" \
       -d @dashboards/system-overview.json
     # Verify panels load data
     ```

   - **Czas**: 1.5h

2. **[ ] Dashboard: Docker Containers**
   - **Metryka**: Container stats, restart counts, resource limits
   - **Walidacja**:

     ```bash
     # Check container metrics exist
     curl -s http://localhost:9090/api/v1/query?query=container_memory_usage_bytes | \
       jq '.data.result | length'
     # > 5 (liczba kontenerów)
     ```

   - **Czas**: 1h

3. **[ ] Dashboard: GPU Monitoring**
   - **Metryka**: GPU utilization, memory, temperature, power
   - **Walidacja**:

     ```bash
     # NVIDIA GPU metrics
     curl -s http://localhost:9090/api/v1/query?query=nvidia_gpu_utilization | \
       jq '.data.result[0].value[1]'
     # Should show percentage
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- All system resources monitored
- Historical data visible (1h, 24h, 7d)
- Drill-down capability do specific containers

### Blok 2: Application monitoring dashboards

#### Zadania atomowe

1. **[ ] Dashboard: Service Health Overview**
   - **Metryka**: Health status wszystkich serwisów, uptime
   - **Walidacja**:

     ```bash
     # Service health panel shows green/red status
     # Based on /health endpoint checks
     ```

   - **Czas**: 1h

2. **[ ] Dashboard: Tracing Overview**
   - **Metryka**: Request rate, error rate, duration (RED metrics)
   - **Walidacja**:

     ```bash
     # Prometheus queries for trace metrics
     curl -s http://localhost:9090/api/v1/query?query=traces_spans_total | \
       jq '.data.result | length'
     # > 0
     ```

   - **Czas**: 1h

3. **[ ] Dashboard: Frame Pipeline**
   - **Metryka**: Frames/second, processing stages, queue depths
   - **Walidacja**:

     ```bash
     # Custom metrics from frame tracking
     curl -s http://localhost:9090/api/v1/query?query=frame_processing_stage | \
       jq '.data.result[0].metric.stage'
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Application-specific metrics visible
- Service dependencies mapped
- Performance trends clear

### Blok 3: Alerting rules configuration

#### Zadania atomowe

1. **[ ] Infrastructure alerts (CPU, memory, disk)**
   - **Metryka**: 10+ infrastructure alert rules
   - **Walidacja**:

     ```bash
     curl -s http://localhost:9090/api/v1/rules | \
       jq '.data.groups[] | select(.name=="infrastructure") | .rules | length'
     # >= 10
     ```

   - **Czas**: 1h

2. **[ ] Service alerts (down, high error rate)**
   - **Metryka**: Alert gdy service down >1min, error rate >5%
   - **Walidacja**:

     ```bash
     # Test alert by stopping service
     docker stop example-service
     sleep 70
     curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | .labels.alertname'
     # Should show "ServiceDown"
     ```

   - **Czas**: 1h

3. **[ ] Custom alerts dla frame pipeline**
   - **Metryka**: Frame drop rate, processing latency alerts
   - **Walidacja**:

     ```yaml
     # Alert rule example
     - alert: HighFrameDropRate
       expr: rate(frames_dropped_total[5m]) > 0.01
       for: 2m
     ```

   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- All critical conditions have alerts
- Alert fatigue minimized (no noisy alerts)
- Clear severity levels (critical, warning, info)

### Blok 4: Alert notification setup

#### Zadania atomowe

1. **[ ] Konfiguracja Alertmanager**
   - **Metryka**: Alertmanager running, routers configured
   - **Walidacja**:

     ```bash
     curl -s http://localhost:9093/api/v1/status | jq '.data.uptime'
     # Shows uptime
     ```

   - **Czas**: 1h

2. **[ ] Notification channels (email/Slack/webhook)**
   - **Metryka**: Test notification delivered do każdego kanału
   - **Walidacja**:

     ```bash
     # Send test alert
     curl -X POST http://localhost:9093/api/v1/alerts \
       -H "Content-Type: application/json" \
       -d '[{"labels":{"alertname":"TestAlert","severity":"warning"}}]'
     # Check notification received
     ```

   - **Czas**: 1h

3. **[ ] Alert dashboard w Grafana**
   - **Metryka**: Unified view wszystkich alertów
   - **Walidacja**:

     ```bash
     # Grafana alert list panel
     curl -s http://localhost:3000/api/alerts | jq '. | length'
     # Shows configured alerts
     ```

   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- Notifications delivered <1min from trigger
- Proper routing based on severity
- Alert history preserved

## Całościowe metryki sukcesu zadania

1. **Coverage**: All system components monitored
2. **Visibility**: 15+ dashboards covering infra i app
3. **Alerting**: 20+ alert rules z proper routing
4. **Response**: Alert to notification <60s

## Deliverables

1. `/config/grafana/dashboards/system-overview.json`
2. `/config/grafana/dashboards/docker-containers.json`
3. `/config/grafana/dashboards/gpu-monitoring.json`
4. `/config/grafana/dashboards/service-health.json`
5. `/config/grafana/dashboards/frame-pipeline.json`
6. `/config/prometheus/alerts/infrastructure.yml`
7. `/config/prometheus/alerts/services.yml`
8. `/config/alertmanager/alertmanager.yml`
9. `/docs/monitoring/runbook.md` - Alert response procedures

## Narzędzia

- **Grafana**: Dashboard platform
- **Prometheus**: Metrics i alerting
- **Alertmanager**: Alert routing i notifications
- **node_exporter**: System metrics
- **cadvisor**: Container metrics
- **nvidia_gpu_exporter**: GPU metrics

## Zależności

- **Wymaga**: Observability stack (zadanie 4)
- **Blokuje**: Production readiness

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Alert fatigue from too many alerts | Wysokie | Średni | Careful threshold tuning, grouping | >10 alerts/hour |
| Dashboard performance z many panels | Średnie | Niski | Query optimization, caching | Load time >5s |
| Missing critical metrics | Średnie | Wysoki | Regular review, RED/USE method | Incidents without alerts |

## Rollback Plan

1. **Detekcja problemu**: Grafana slow, alerts noisy, notifications failing
2. **Kroki rollback**:
   - [ ] Disable noisy alerts temporarily
   - [ ] Reduce dashboard refresh rate
   - [ ] Fallback to basic email notifications
3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [Faza 2: Akwizycja - 01-rtsp-capture-service.md](../faza-2-akwizycja/01-rtsp-capture-service.md)
