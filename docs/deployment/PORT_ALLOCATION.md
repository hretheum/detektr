# 🔌 Port Allocation Registry

> **WAŻNE**: Ten dokument jest źródłem prawdy dla wszystkich alokacji portów w projekcie Detektor

## 📊 Port Allocation Table

| Port | Service | Environment | Compose File | Status |
|------|---------|-------------|--------------|--------|
| **3000** | Grafana | All | docker-compose.observability.yml | ✅ Active |
| **4317** | Jaeger (OTLP gRPC) | All | docker-compose.observability.yml | ✅ Active |
| **4318** | Jaeger (OTLP HTTP) | All | docker-compose.observability.yml | ✅ Active |
| **5432** | PostgreSQL | All | docker-compose.storage.yml | ✅ Active |
| **5775/udp** | Jaeger (Zipkin/thrift) | All | docker-compose.observability.yml | ✅ Active |
| **5778** | Jaeger (Config) | All | docker-compose.observability.yml | ✅ Active |
| **6378** | Redis HAProxy | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **6379** | Redis | All | docker-compose.storage.yml | ✅ Active |
| **6380** | Redis Slave 1 | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **6381** | Redis Slave 2 | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **6432** | PgBouncer | All | docker-compose.storage.yml | ✅ Active |
| **6831/udp** | Jaeger (Thrift compact) | All | docker-compose.observability.yml | ✅ Active |
| **6832/udp** | Jaeger (Thrift binary) | All | docker-compose.observability.yml | ✅ Active |
| **8000** | Base Template | All | base/docker-compose.yml | ✅ Active |
| **8001** | Frame Tracking (library) | - | - | ❌ Deprecated |
| **8002** | Frame Buffer | All | base/docker-compose.yml | ✅ Active |
| **8003** | Face Recognition | GPU | features/gpu/docker-compose.gpu.yml | 🔄 Optional |
| **8004** | Object Detection | GPU | features/gpu/docker-compose.gpu.yml | 🔄 Optional |
| **8005** | Metadata Storage | All | base/docker-compose.yml | ✅ Active |
| **8006** | Reserved | - | - | 🔮 Future |
| **8007** | Echo Service | Dev | base/docker-compose.yml | 🔄 Optional |
| **8008** | GPU Demo | GPU | features/gpu/docker-compose.gpu.yml | 🔄 Optional |
| **8009** | Example OTEL | All | base/docker-compose.yml | ✅ Active |
| **8080** | RTSP Capture | All | base/docker-compose.yml | ✅ Active |
| **8081** | Frame Events | All | base/docker-compose.yml | ✅ Active |
| **8082** | cAdvisor | Monitoring | base/docker-compose.observability.yml | 🔄 Optional |
| **8083** | Adminer | Dev | environments/development/docker-compose.yml | 🔧 Dev |
| **8010** | LLM Intent | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8011** | Gesture Detection | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8012** | Audio Analysis | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8013** | Scene Understanding | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8014** | HA Bridge | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8015** | Telegram Alerts | AI | ai-services/docker-compose.ai.yml | 🔄 Optional |
| **8099** | Example Processor | Dev | base/docker-compose.yml | 🔧 Dev |
| **8404** | Redis HAProxy Stats | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **9090** | Prometheus | All | docker-compose.observability.yml | ✅ Active |
| **9093** | Alertmanager | Monitoring | docker-compose.observability.yml | 🔄 Optional |
| **9100** | Node Exporter | Monitoring | docker-compose.observability.yml | 🔄 Optional |
| **9121** | Redis Exporter | Monitoring | docker-compose.storage.yml | 🔄 Optional |
| **9122** | Redis Exporter HA | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **9187** | PostgreSQL Exporter | Monitoring | docker-compose.storage.yml | 🔄 Optional |
| **9411** | Jaeger (Zipkin HTTP) | All | docker-compose.observability.yml | ✅ Active |
| **9445** | NVIDIA GPU Exporter | GPU | gpu/docker-compose.gpu.yml | 🔄 Optional |
| **14250** | Jaeger (gRPC collector) | All | docker-compose.observability.yml | ✅ Active |
| **14268** | Jaeger (HTTP collector) | All | docker-compose.observability.yml | ✅ Active |
| **16686** | Jaeger UI | All | docker-compose.observability.yml | ✅ Active |
| **26379** | Redis Sentinel 1 | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **26380** | Redis Sentinel 2 | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |
| **26381** | Redis Sentinel 3 | HA | redis-ha/docker-compose.redis-ha.yml | 🔄 Optional |

## ✅ Historia zmian portów

### Aktualizacja 2025-07-26
- **Frame Buffer**: Port 8002 - naprawiony hardkodowany port w Dockerfile
- **Frame Events**: Port 8081 (wcześniej frame-tracking service)
- **Frame Tracking**: Teraz biblioteka, nie serwis
- **cAdvisor**: Przeniesiony na port 8082

### Aktualizacja 2025-07-25
- **RTSP Capture**: Przeniesiony z 8001 → **8080**
- **Frame Tracking**: Przeniesiony z 8006 → **8001**
- **cAdvisor**: Pozostaje na **8081**
- **Adminer**: Pozostaje na **8083**
- **Base Template**: Używa **8000**

### Rozwiązane konflikty
1. **Port 8080** - RTSP Capture (wcześniej cAdvisor)
2. **Port 8001** - Frame Tracking (wcześniej RTSP Capture)

## 🔒 Produkcja - Zabezpieczenia

W środowisku produkcyjnym (`production/docker-compose.yml`):
- Porty są bindowane tylko do localhost (127.0.0.1:)
- Zewnętrzny dostęp przez reverse proxy (nginx/traefik)

## 📝 Zasady alokacji

1. **8000-8099**: Serwisy aplikacyjne
2. **9000-9999**: Eksportery metryk (Prometheus)
3. **3000-3999**: UI (Grafana, etc.)
4. **5000-5999**: Bazy danych i cache
5. **6000-6999**: Bazy danych (repliki, proxy)
6. **14000-16999**: Jaeger (distributed tracing)
7. **26000-26999**: Redis Sentinels

## 🚨 Przed dodaniem nowego portu

1. Sprawdź tę tabelę
2. Uruchom: `docker ps --format 'table {{.Names}}\t{{.Ports}}'`
3. Dodaj nowy port do tej tabeli
4. Użyj odpowiedniego zakresu dla typu serwisu

## 🔧 Narzędzia diagnostyczne

```bash
# Sprawdź zajęte porty na Nebula
ssh nebula "docker ps --format 'table {{.Names}}\t{{.Ports}}' | sort"

# Sprawdź konflikty portów
ssh nebula "netstat -tlnp | grep -E '(8080|8005|8010|5432|6432)'"

# Znajdź proces blokujący port
ssh nebula "sudo lsof -i :5432"
```
