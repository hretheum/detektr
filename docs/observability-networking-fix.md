# Observability Stack - Rozwiązanie problemów z networking

## Problem z Bridge Network

**Problem**: Kontenery w bridge network nie mapowały portów na localhost.

**Symptomy**:
- `curl localhost:9090` → Connection refused
- `curl localhost:3000` → Connection refused  
- Tylko kontenery z `network_mode: host` działały

**Root Cause**: Docker bridge network z port mappingiem nie działał poprawnie na serwerze Ubuntu.

## Rozwiązanie: Host Networking

**Implementacja**: Wszystkie kontenery observability używają `network_mode: host`

### Korzyści Host Network:
✅ Bezpośredni dostęp do localhost  
✅ Brak problemów z port mappingiem  
✅ Lepsza performance (brak NAT)  
✅ Prostsze debugging  

### Wady Host Network:
⚠️ Mniej izolacji sieciowej  
⚠️ Potencjalne konflikty portów  
⚠️ Kontenery widzą wszystkie porty hosta  

## Finalna konfiguracja

**Compose file**: `docker-compose.observability-complete.yml`

### Porty na localhost:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090  
- Jaeger: http://localhost:16686
- Loki: http://localhost:3100

### Prometheus targets (wszystkie UP):
1. prometheus (localhost:9090)
2. grafana (localhost:3000) 
3. node-exporter (localhost:9100)
4. cadvisor (localhost:8080)
5. docker (localhost:9323)
6. dcgm-exporter (localhost:9400)

## Konfiguracje zaktualizowane

**prometheus.yml**: targets używają localhost zamiast nazw kontenerów  
**datasources**: Grafana łączy się z localhost:9090  
**promtail**: localhost:3100 dla Loki  

## Deployment

```bash
cd /opt/detektor
docker compose -f docker-compose.observability-complete.yml up -d
```

**Status**: ✅ Wszystkie 6/6 targets UP, 4/4 UI endpoints działają
EOF < /dev/null