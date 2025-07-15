# Faza 1 / Zadanie 4: Deploy stack observability

## Cel zadania
Uruchomienie kompletnego stosu observability (Jaeger, Prometheus, Grafana, Loki) z podstawową konfiguracją, zapewniając widoczność systemu od samego początku rozwoju projektu.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja Docker Compose i dostępnych portów**
   - **Metryka**: Docker Compose v2.20+, porty 3000,9090,16686,3100 wolne
   - **Walidacja**: 
     ```bash
     docker compose version | grep -E "2\.(2[0-9]|[3-9][0-9])"
     for port in 3000 9090 16686 3100; do 
       lsof -i :$port || echo "Port $port available"
     done
     ```
   - **Czas**: 0.5h

2. **[ ] Weryfikacja zasobów systemowych**
   - **Metryka**: Min 8GB RAM wolne, 20GB dysku
   - **Walidacja**: 
     ```bash
     free -h | grep Mem | awk '{print $7}'
     df -h / | tail -1 | awk '{print $4}'
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Prometheus i Grafana setup

#### Zadania atomowe:
1. **[ ] Konfiguracja Prometheus z podstawowymi targets**
   - **Metryka**: Prometheus scraping node_exporter i cadvisor
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'
     # Powinno zwrócić >= 3 (prometheus, node_exporter, cadvisor)
     ```
   - **Czas**: 1.5h

2. **[ ] Deploy Grafana z provisioning**
   - **Metryka**: Grafana UI dostępne, datasource skonfigurowany
   - **Walidacja**: 
     ```bash
     curl -s http://admin:admin@localhost:3000/api/datasources | jq '.[0].name'
     # Powinno zwrócić "Prometheus"
     ```
   - **Czas**: 1h

3. **[ ] Import podstawowych dashboards**
   - **Metryka**: 3 dashboardy (Node Exporter, Docker, System Overview)
   - **Walidacja**: 
     ```bash
     curl -s http://admin:admin@localhost:3000/api/dashboards/db | jq '. | length'
     # Powinno zwrócić >= 3
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Prometheus zbiera metryki co 15s
- Grafana pokazuje system metrics w real-time
- Dashboardy automatycznie provisioned przy starcie

### Blok 2: Jaeger distributed tracing

#### Zadania atomowe:
1. **[ ] Deploy Jaeger all-in-one**
   - **Metryka**: Jaeger UI dostępne na :16686
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:16686/api/services | jq '. | has("data")'
     # Powinno zwrócić true
     ```
   - **Czas**: 1h

2. **[ ] Konfiguracja Jaeger storage (Elasticsearch)**
   - **Metryka**: Elasticsearch jako backend dla Jaeger
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:9200/_cat/indices | grep jaeger
     # Powinny być widoczne jaeger indices
     ```
   - **Czas**: 1.5h

3. **[ ] Test trace z przykładowym serwisem**
   - **Metryka**: Hot R.O.D demo pokazuje traces
   - **Walidacja**: 
     ```bash
     # Po uruchomieniu Hot R.O.D
     curl -s "http://localhost:16686/api/traces?service=frontend" | jq '.data | length'
     # Powinno zwrócić > 0
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Jaeger przyjmuje traces przez HTTP i gRPC
- Traces persisted w Elasticsearch
- UI pokazuje service dependencies

### Blok 3: Loki log aggregation

#### Zadania atomowe:
1. **[ ] Deploy Loki z podstawową konfiguracją**
   - **Metryka**: Loki API dostępne na :3100
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:3100/ready | grep ready
     ```
   - **Czas**: 1h

2. **[ ] Konfiguracja Promtail dla Docker logs**
   - **Metryka**: Promtail zbiera logi ze wszystkich kontenerów
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:3100/loki/api/v1/labels | jq '.data | length'
     # Powinno pokazać labels jak container_name, compose_service
     ```
   - **Czas**: 1h

3. **[ ] Integracja Loki z Grafana**
   - **Metryka**: Loki jako datasource w Grafana
   - **Walidacja**: 
     ```bash
     # Test query w Grafana
     curl -s -X POST http://admin:admin@localhost:3000/api/ds/query \
       -H "Content-Type: application/json" \
       -d '{"queries":[{"datasource":{"type":"loki"},"expr":"{job=\"detektor\"}"}]}'
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Logi ze wszystkich kontenerów w Loki
- Query logs przez Grafana Explore
- Retention policy ustawiony na 7 dni

### Blok 4: Monitoring sam observability stack

#### Zadania atomowe:
1. **[ ] Metryki dla Prometheus, Grafana, Jaeger**
   - **Metryka**: Self-monitoring wszystkich komponentów
   - **Walidacja**: 
     ```bash
     # Prometheus monitoruje sam siebie
     curl -s http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_samples | \
       jq '.data.result | length'
     # > 0
     ```
   - **Czas**: 1h

2. **[ ] Alerty dla observability stack**
   - **Metryka**: 5 podstawowych alertów (down, high memory, disk space)
   - **Walidacja**: 
     ```bash
     curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules | length'
     # Powinno zwrócić >= 5
     ```
   - **Czas**: 1h

3. **[ ] Backup configuration dla Grafana**
   - **Metryka**: Automated backup dashboards i datasources
   - **Walidacja**: 
     ```bash
     ls -la ./backups/grafana/dashboards/*.json | wc -l
     # Powinno pokazać liczbe dashboardów
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Observability stack self-monitored
- Alerty skonfigurowane dla critical components
- Backup działa automatycznie

## Całościowe metryki sukcesu zadania

1. **Dostępność**: Wszystkie 4 UI (Grafana, Prometheus, Jaeger, Loki) dostępne
2. **Integracja**: Grafana pokazuje metrics, traces i logs
3. **Monitoring**: System i Docker metrics collected
4. **Persistence**: Dane zachowane po restart

## Deliverables

1. `/docker-compose.observability.yml` - Stack configuration
2. `/config/prometheus/prometheus.yml` - Prometheus config
3. `/config/grafana/provisioning/` - Dashboards i datasources
4. `/config/loki/loki-config.yml` - Loki configuration
5. `/config/promtail/promtail-config.yml` - Log collection
6. `/config/prometheus/alerts.yml` - Alert rules
7. `/scripts/backup-observability.sh` - Backup script

## Narzędzia

- **Prometheus**: Metrics collection i storage
- **Grafana**: Visualization platform
- **Jaeger**: Distributed tracing
- **Loki + Promtail**: Log aggregation
- **Elasticsearch**: Trace storage backend

## Zależności

- **Wymaga**: Docker environment (zadanie 1) i Git repo (zadanie 3)
- **Blokuje**: OpenTelemetry config (zadanie 5)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| High memory usage przez Elasticsearch | Wysokie | Średni | Limit memory w Docker, use alternative storage | Memory >8GB |
| Port conflicts z innymi serwisami | Średnie | Niski | Use different ports, dokumentacja | Bind errors |
| Data loss przy restart | Średnie | Wysoki | Persistent volumes dla wszystkich serwisów | No data after restart |

## Rollback Plan

1. **Detekcja problemu**: Services crashują, high resource usage
2. **Kroki rollback**:
   - [ ] `docker compose -f docker-compose.observability.yml down`
   - [ ] Restore poprzednia konfiguracja
   - [ ] Start tylko critical services (Prometheus + Grafana)
3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-opentelemetry-config.md](./05-opentelemetry-config.md)