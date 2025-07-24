# GitHub Actions Optimization & Recovery Plan

## 📋 Executive Summary

Po kompleksowej analizie systemu CI/CD stwierdzono, że architektura jest poprawnie skonfigurowana jako hybrid approach:
- **BUILD**: GitHub-hosted runners (ubuntu-latest) - budowanie i push obrazów do ghcr.io
- **DEPLOY**: Self-hosted runner (Nebula) - pobieranie obrazów i deployment lokalny

### Główny Problem
Workflow nie uruchamiają się automatycznie po push do main branch, mimo poprawnej konfiguracji.

## 🏗️ Aktualna Architektura

### Hybrid CI/CD Architecture
```mermaid
graph LR
    A[Developer Push] --> B[GitHub]
    B --> C[GitHub-hosted Runner]
    C --> D[Build Images]
    D --> E[Push to ghcr.io]
    E --> F[Self-hosted Runner]
    F --> G[Pull Images]
    G --> H[Deploy on Nebula]
```

### Komponenty
1. **GitHub-hosted runners**: Budowanie obrazów Docker
2. **ghcr.io**: Registry dla obrazów
3. **Self-hosted runner na Nebula**: Deployment produkcyjny
4. **SOPS**: Zarządzanie secretami

## 📊 Analiza Workflow Files

### Przed Optymalizacją (Faza 2)
- **14 workflow files**
- Duplikacja logiki
- Trudne w utrzymaniu

### Po Optymalizacji (Obecnie)
- **5 głównych workflow** + pomocnicze
- Lepsza organizacja
- Ale nadal 16 aktywnych plików .yml

### Lista Aktywnych Workflow (16 plików)
1. `main-pipeline.yml` - Główny pipeline CI/CD
2. `pr-checks.yml` - Walidacja PR
3. `manual-operations.yml` - Operacje manualne
4. `scheduled-tasks.yml` - Zadania cykliczne
5. `release.yml` - Release management
6. `security.yml` - Security scanning
7. `ci.yml` - Service quality checks
8. `ghcr-cleanup.yml` - Czyszczenie registry
9. `build-gpu-base.yml` - GPU base image
10. `cleanup-runner.yml` - Czyszczenie runner
11. `db-deploy.yml` - Database deployment
12. `deploy-production-isolated.yml` - Isolated deployment
13. `diagnostic.yml` - Diagnostyka
14. `manual-service-build.yml` - Manual builds
15. `test-runner.yml` - Runner testing
16. `UNIFIED-deploy.yml` - Unified deployment

### Rekomendacja Konsolidacji
Możliwa dalsza redukcja do **3-4 workflow**:
1. **main.yml** - Build, test, deploy (łączy main-pipeline + ci + security)
2. **maintenance.yml** - Wszystkie manual operations + scheduled tasks + cleanup
3. **release.yml** - Bez zmian
4. **emergency.yml** - Diagnostic + manual overrides

## 🎯 Plan Działań

### 1. Monitoring GitHub Runner

#### Zadania Atomowe:

**1.1 Health Check Endpoint**
- [ ] Utworzyć `/opt/github-runner/health-check.sh`
- [ ] Sprawdzać: runner status, ostatnie zadanie, połączenie z GitHub
- [ ] Wystawiać metryki do Prometheus
- [ ] Czas: 2h

**1.2 Systemd Service Monitoring**
- [ ] Dodać `Restart=always` do service unit
- [ ] Skonfigurować `RestartSec=30`
- [ ] Dodać `OnFailure=notify-admin@.service`
- [ ] Czas: 1h

**1.3 GitHub Webhook Monitor**
- [ ] Stworzyć webhook receiver na Nebula (port 8888)
- [ ] Logować wszystkie GitHub events
- [ ] Alerty gdy brak eventów > 1h po push
- [ ] Czas: 3h

**1.4 Runner Metrics Exporter**
- [ ] Parsować logi z `_diag/Runner_*.log`
- [ ] Eksportować: jobs received, jobs completed, failures
- [ ] Integracja z Prometheus
- [ ] Czas: 2h

**1.5 Grafana Dashboard**
- [ ] Import/stworzenie dashboardu "GitHub Runner Health"
- [ ] Panele: job queue, success rate, runner uptime
- [ ] Alerty: runner offline, job failures > 3
- [ ] Czas: 2h

### 2. Automated Recovery Mechanisms

#### Zadania Atomowe:

**2.1 Runner Auto-Recovery Script**
```bash
#!/bin/bash
# /opt/github-runner/auto-recovery.sh
# Sprawdza stan runner i restartuje w razie problemów
```
- [ ] Sprawdzanie czy runner przyjmuje zadania
- [ ] Auto-restart po 3 failed health checks
- [ ] Rotacja logów przed restartem
- [ ] Czas: 2h

**2.2 Deployment Circuit Breaker**
- [ ] Dodać do `deploy.sh`: licznik failed deployments
- [ ] Po 3 failures: stop auto-deploy, send alert
- [ ] Manual reset przez `make reset-circuit-breaker`
- [ ] Czas: 3h

**2.3 Fallback Deployment Strategy**
- [ ] Backup deployment method przez SSH + docker-compose
- [ ] Gdy GitHub Actions nie działa > 30min
- [ ] Triggered przez monitoring alert
- [ ] Czas: 4h

**2.4 Self-Healing Containers**
- [ ] Health check dla każdego serwisu
- [ ] Auto-restart unhealthy containers
- [ ] Zachowanie logów przed restartem
- [ ] Czas: 3h

### 3. Workflow Consolidation

#### Zadania Atomowe:

**3.1 Analiza Zależności**
- [ ] Mapowanie które workflow używają których akcji
- [ ] Identyfikacja duplikacji
- [ ] Plan migracji bez breaking changes
- [ ] Czas: 2h

**3.2 Utworzenie Nowych Workflow**
- [ ] `main.yml`: Połączenie main-pipeline + ci + security
- [ ] `maintenance.yml`: Manual ops + scheduled + cleanup
- [ ] `emergency.yml`: Diagnostic + recovery
- [ ] Czas: 4h

**3.3 Migration Strategy**
- [ ] Faza 1: Nowe workflow jako kopie
- [ ] Faza 2: Testy równoległe
- [ ] Faza 3: Wyłączenie starych workflow
- [ ] Faza 4: Usunięcie po 7 dniach
- [ ] Czas: 2 dni

### 4. Debugging & Diagnostics

#### Zadania Atomowe:

**4.1 Enhanced Logging**
- [ ] Structured logs (JSON) dla wszystkich serwisów
- [ ] Correlation IDs dla workflow runs
- [ ] Centralizacja w Loki
- [ ] Czas: 3h

**4.2 Trace Pipeline**
- [ ] OpenTelemetry dla całego pipeline
- [ ] Trace od push do deploy complete
- [ ] Wizualizacja w Jaeger
- [ ] Czas: 4h

**4.3 Debug Mode**
- [ ] Flag `DEBUG_PIPELINE=true` w workflow
- [ ] Verbose logging wszystkich kroków
- [ ] Zachowanie artifacts z każdego kroku
- [ ] Czas: 2h

### 5. Performance & Resilience

#### Zadania Atomowe:

**5.1 Parallel Builds**
- [ ] Matrix strategy dla wszystkich serwisów
- [ ] Max 4 równoległe buildy
- [ ] Intelligent batching
- [ ] Czas: 2h

**5.2 Cache Optimization**
- [ ] Docker layer caching
- [ ] Dependency caching (pip, npm)
- [ ] Build artifact caching
- [ ] Czas: 3h

**5.3 Retry Logic**
- [ ] Retry failed steps (max 3)
- [ ] Exponential backoff
- [ ] Different retry strategy per step type
- [ ] Czas: 2h

## 📈 Metryki Sukcesu

1. **Availability**: 99.9% uptime dla CI/CD pipeline
2. **Performance**: Build time < 5 min, Deploy time < 2 min
3. **Reliability**: Success rate > 95%
4. **Recovery**: MTTR < 15 min

## 🚀 Harmonogram Implementacji

### Faza 1: Emergency (Dzień 1)
- Runner health check
- Basic monitoring
- Auto-recovery script

### Faza 2: Stabilization (Dni 2-3)
- Enhanced monitoring
- Circuit breaker
- Workflow consolidation planning

### Faza 3: Optimization (Dni 4-7)
- Workflow migration
- Performance improvements
- Full observability

## 🔧 Narzędzia i Technologie

- **Monitoring**: Prometheus + Grafana + Loki
- **Tracing**: OpenTelemetry + Jaeger
- **Alerting**: AlertManager + Telegram
- **Automation**: Bash + Python + Make
- **Recovery**: systemd + cron + webhooks

## 📝 Następne Kroki

1. Zatwierdzenie planu
2. Utworzenie backlog w GitHub Issues
3. Przypisanie priorytetów
4. Start implementacji z Fazy 1

## 🎯 Długoterminowe Cele

1. **Self-Service CI/CD**: Developers mogą debugować własne problemy
2. **Zero-Downtime Deployments**: Blue-green deployment strategy
3. **Predictive Maintenance**: ML-based failure prediction
4. **Cost Optimization**: Automatyczne skalowanie runners

---

*Dokument utworzony: 2025-07-24*
*Wersja: 1.0*
*Autor: Team DevOps*
