# 🚀 New Service Guide

> **⚠️ PRZED ROZPOCZĘCIEM**: Przeczytaj [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) i [PORT_ALLOCATION.md](../PORT_ALLOCATION.md)!

## 📋 Quick Checklist

```bash
# 1. Sprawdź wolne porty
cat docs/deployment/PORT_ALLOCATION.md

# 2. Sprawdź zajęte porty na Nebula
ssh nebula "docker ps --format 'table {{.Names}}\t{{.Ports}}'"

# 3. Wybierz port z zakresu 8016-8099
```

## 🏗️ Struktura Serwisu

### 1. Katalog serwisu
```
services/your-service/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── models.py
├── repositories.py
├── telemetry.py
└── tests/
```

### 2. Dockerfile Template
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8016/health || exit 1

# Run
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8016"]
```

### 3. Database Configuration
```python
# ⚠️ WAŻNE: Baza nazywa się 'detektor' NIE 'detektor_db'!
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://detektor:detektor_pass@postgres:5432/detektor",
)
```

## 📝 Konfiguracja Docker Compose

### 1. W `docker/base/docker-compose.yml`:
```yaml
  your-service:
    image: ghcr.io/hretheum/detektr/your-service:${IMAGE_TAG:-latest}
    ports:
      - "8016:8016"  # Użyj wolnego portu!
    environment:
      - SERVICE_NAME=your-service
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
    depends_on:
      - postgres
      - redis
    networks:
      - detektor-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8016/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    profiles:
      - full  # lub pozostaw puste dla zawsze aktywnego
```

### 2. W `docker/environments/production/docker-compose.yml`:
```yaml
  your-service:
    <<: *production-defaults
    image: ghcr.io/hretheum/detektr/your-service:${IMAGE_TAG:-latest}
    environment:
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
      - DATABASE_URL=postgresql+asyncpg://detektor:${POSTGRES_PASSWORD:-detektor_pass}@postgres:5432/detektor
```

## 🔧 Integracja z CI/CD

### 1. W `.github/workflows/main-pipeline.yml`:

#### Dodaj do paths-filter:
```yaml
your-service:
  - 'services/your-service/**'
```

#### Dodaj do listy serwisów:
```yaml
services=(
  "rtsp-capture"
  "frame-tracking"
  # ...
  "your-service"  # Dodaj tutaj
)
```

### 2. Zaktualizuj dokumentację:

#### W `docs/deployment/PORT_ALLOCATION.md`:
```markdown
| **8016** | Your Service | All | docker-compose.yml | ✅ Active |
```

## 🧪 Testowanie Lokalnie

```bash
# 1. Zbuduj obraz
docker build -t ghcr.io/hretheum/detektr/your-service:latest services/your-service/

# 2. Uruchom z .env
cd /opt/detektor-clean
export COMPOSE_PROJECT_NAME=detektor
docker compose --env-file .env -f docker/base/docker-compose.yml up -d your-service

# 3. Sprawdź logi
docker logs detektor-your-service-1 --follow

# 4. Test health endpoint
curl http://localhost:8016/health
```

## ⚠️ Najczęstsze Błędy

### 1. **Port już zajęty**
```
Error: Bind for 0.0.0.0:8016 failed: port is already allocated
```
**Rozwiązanie**: Sprawdź PORT_ALLOCATION.md i wybierz inny port

### 2. **Błąd autentykacji bazy**
```
InvalidPasswordError: password authentication failed
```
**Rozwiązanie**: Upewnij się że używasz `${POSTGRES_PASSWORD}` w DATABASE_URL

### 3. **Baza nie istnieje**
```
InvalidCatalogNameError: database "detektor_db" does not exist
```
**Rozwiązanie**: Użyj `detektor` nie `detektor_db`

## 📚 Przykłady

### Health Check Endpoint
```python
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Test database
        await db.execute(text("SELECT 1"))

        # Test redis
        await redis_client.ping()

        return {
            "status": "healthy",
            "service": "your-service",
            "database": "connected",
            "redis": "connected"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

### Observability Setup
```python
from telemetry import init_telemetry, traced

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_telemetry("your-service")
    yield
    # Shutdown
    await shutdown_telemetry()

app = FastAPI(lifespan=lifespan)
```

## 🚀 Deployment

```bash
# 1. Push do repozytorium
git add .
git commit -m "feat: add your-service

- Port 8016
- Database integration
- Health checks
- Observability"
git push origin main

# 2. CI/CD automatycznie zbuduje i wdroży

# 3. Sprawdź na Nebula
ssh nebula "docker ps | grep your-service"
```

## 📋 Final Checklist

- [ ] Port dodany do PORT_ALLOCATION.md
- [ ] Używa prawidłowej nazwy bazy (`detektor`)
- [ ] DATABASE_URL używa `${POSTGRES_PASSWORD}`
- [ ] Health check endpoint działa
- [ ] Dodany do main-pipeline.yml
- [ ] Testy lokalne przeszły
- [ ] Dokumentacja serwisu utworzona

---

**💡 Pamiętaj**: W razie problemów sprawdź [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)!
