# Build Errors Analysis

## Błędy budowania obrazów (2025-07-25)

### Lista usług z błędami budowania:

1. **gpu-demo**
   - Błąd: `/services/gpu-demo`: not found
   - Dockerfile szuka: `COPY services/gpu-demo/requirements.txt`

2. **frame-tracking**
   - Błąd: `/services/frame-tracking`: not found
   - Dockerfile szuka: `COPY services/frame-tracking/requirements.txt`

3. **frame-buffer**
   - Błąd: `/services/frame-buffer/requirements.txt`: not found
   - Błąd: `/services/frame-buffer/src`: not found

4. **base-template**
   - Błąd: `/services/base-template/requirements.txt`: not found
   - Błąd: `/services/base-template`: not found

5. **echo-service**
   - Błąd: `/services/echo-service`: not found

6. **example-otel**
   - Błąd: `/services/example-otel`: not found

### Przyczyna problemu:
Wszystkie błędy wskazują na to, że Docker build jest uruchamiany z niewłaściwym kontekstem. Dockerfile'e oczekują że build context to root projektu, ale prawdopodobnie workflow uruchamia build z innego miejsca.

### Usługi w docker-compose:

#### Production (docker/environments/production/docker-compose.yml):
- rtsp-capture ✓
- frame-tracking ❌ (błąd build)
- echo-service ❌ (błąd build)
- example-otel ❌ (błąd build)
- base-template ❌ (błąd build)
- metadata-storage ✓
- gpu-demo ❌ (błąd build)

#### Base (docker/base/docker-compose.yml):
- rtsp-capture
- frame-tracking
- frame-buffer ❌ (błąd build)
- telegram-alerts
- metadata-storage
- echo-service
- example-otel

### Analiza potrzebnych usług:

#### KRYTYCZNE (muszą działać):
1. **rtsp-capture** - ✓ działa
2. **frame-tracking** - ❌ błąd build, ale działa ze starym obrazem
3. **metadata-storage** - ✓ działa
4. **postgres** - ✓ działa
5. **redis** - ✓ działa

#### WAŻNE (powinny działać):
1. **frame-buffer** - ❌ błąd build
2. **base-template** - ❌ błąd build, restartuje się

#### OPCJONALNE (demo/przykłady):
1. **gpu-demo** - ❌ błąd build (można wyłączyć)
2. **example-otel** - ❌ błąd build (można wyłączyć)
3. **echo-service** - ❌ błąd build (można wyłączyć)

#### MONITORING (nice to have):
1. **prometheus** - ✓ działa
2. **grafana** - ✓ działa
3. **jaeger** - ✓ działa
4. **pgbouncer** - ⚠️ unhealthy

### Rekomendacje:

1. **PILNE**: Naprawić workflow build - prawdopodobnie problem z working directory
2. **KRÓTKOTERMINOWE**: Wyłączyć niepotrzebne demo services (gpu-demo, example-otel, echo-service)
3. **DŁUGOTERMINOWE**: Sprawdzić dlaczego pgbouncer jest unhealthy

### Następne kroki:
1. Sprawdzić jak workflow uruchamia docker build
2. Poprawić build context w workflow
3. Tymczasowo wyłączyć demo services
