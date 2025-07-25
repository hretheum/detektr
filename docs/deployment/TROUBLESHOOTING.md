# 🚨 Troubleshooting Guide - Napotkane Problemy i Rozwiązania

> **WAŻNE**: Ten dokument zawiera rozwiązania problemów napotkanych podczas deploymentu. Przeczytaj PRZED dodaniem nowej usługi!

## 📋 Spis treści

1. [Najczęstsze Problemy](#najczęstsze-problemy)
2. [Lista Portów - SPRAWDŹ PRZED DODANIEM USŁUGI](#lista-portów)
3. [Problemy z Nazwami Kontenerów](#problemy-z-nazwami-kontenerów)
4. [Problemy z Hasłami i .env](#problemy-z-hasłami-i-env)
5. [Problemy z Bazą Danych](#problemy-z-bazą-danych)
6. [Problemy z Docker Volumes](#problemy-z-docker-volumes)
7. [Checklist dla Nowej Usługi](#checklist-dla-nowej-usługi)

## 🔥 Najczęstsze Problemy

### 1. **"port is already allocated"**
- **Przyczyna**: Konflikt portów między usługami
- **Rozwiązanie**: Sprawdź [PORT_ALLOCATION.md](./PORT_ALLOCATION.md)
- **Komenda**: `docker ps --format 'table {{.Names}}\t{{.Ports}}'`

### 2. **"password authentication failed"**
- **Przyczyna**: Brak załadowania zmiennych z .env
- **Rozwiązanie**: Używaj `docker compose --env-file .env`
- **Sprawdzenie**: `docker inspect [container] | grep DATABASE_URL`

### 3. **"Volume exists but doesn't match configuration"**
- **Przyczyna**: Różne COMPOSE_PROJECT_NAME
- **Rozwiązanie**: Zawsze używaj `COMPOSE_PROJECT_NAME=detektor`
- **Cleanup**: `docker volume ls | grep base_ | xargs docker volume rm`

## 🔌 Lista Portów

### **KRYTYCZNE - Zawsze sprawdź przed dodaniem usługi!**

Zobacz pełną listę w [PORT_ALLOCATION.md](./PORT_ALLOCATION.md)

**Najważniejsze zakresy:**
- **8000-8099**: Serwisy aplikacyjne (TUTAJ DODAWAJ NOWE!)
- **5432**: PostgreSQL (NIE ZMIENIAJ)
- **6379**: Redis (NIE ZMIENIAJ)
- **6432**: PgBouncer (NIE ZMIENIAJ)

**Wolne porty dla nowych usług:**
- 8016-8079 (sprawdź PORT_ALLOCATION.md!)
- 8084-8099

## 🏷️ Problemy z Nazwami Kontenerów

### Problem: "base-postgres-1" vs "detektor-postgres-1"

**Objawy:**
```
Error: Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Przyczyna:**
- Brak ustawienia `COMPOSE_PROJECT_NAME=detektor`
- Różne nazwy projektów tworzą duplikaty kontenerów

**Rozwiązanie:**
1. W `deploy.sh` dodaj na początku:
   ```bash
   export COMPOSE_PROJECT_NAME=detektor
   ```

2. Usuń stare kontenery:
   ```bash
   docker ps -a | grep base- | awk '{print $1}' | xargs docker rm -f
   ```

## 🔐 Problemy z Hasłami i .env

### Problem: "InvalidPasswordError: password authentication failed"

**Objawy:**
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "detektor"
```

**Przyczyna:**
- Docker Compose nie ładuje zmiennych z .env
- Używa domyślnych wartości zamiast faktycznych haseł

**Rozwiązanie:**

1. **ZAWSZE używaj --env-file:**
   ```bash
   docker compose --env-file .env -f docker/base/docker-compose.yml up -d
   ```

2. **Sprawdź czy hasło jest załadowane:**
   ```bash
   docker inspect [container] | grep POSTGRES_PASSWORD
   ```

3. **W production compose sprawdź DATABASE_URL:**
   ```yaml
   environment:
     - DATABASE_URL=postgresql+asyncpg://detektor:${POSTGRES_PASSWORD:-detektor_pass}@postgres:5432/detektor
   ```

## 🗄️ Problemy z Bazą Danych

### Problem: "database 'detektor_db' does not exist"

**Objawy:**
```
asyncpg.exceptions.InvalidCatalogNameError: database "detektor_db" does not exist
```

**Przyczyna:**
- Niezgodność nazw baz danych
- Baza nazywa się `detektor` a nie `detektor_db`

**Rozwiązanie:**
1. Sprawdź nazwę bazy:
   ```bash
   docker exec detektor-postgres-1 psql -U detektor -c "SELECT current_database();"
   ```

2. Popraw w kodzie serwisu:
   ```python
   DATABASE_URL = os.getenv(
       "DATABASE_URL",
       "postgresql+asyncpg://detektor:detektor_pass@postgres:5432/detektor",  # NIE detektor_db!
   )
   ```

## 💾 Problemy z Docker Volumes

### Problem: "Volume exists but doesn't match configuration"

**Przyczyna:**
- Stare volumes z różnymi nazwami projektów
- Mieszanie `base_*` i `detektor_*` volumes

**Rozwiązanie:**
```bash
# Lista volumes
docker volume ls | grep -E 'base_|detektor_'

# Usuń stare base_ volumes
docker volume ls | grep base_ | awk '{print $2}' | xargs docker volume rm

# Usuń niepotrzebne detektor_ volumes
docker volume prune
```

## ✅ Checklist dla Nowej Usługi

### **PRZED ROZPOCZĘCIEM:**

1. **📍 Sprawdź porty:**
   ```bash
   cat docs/deployment/PORT_ALLOCATION.md
   docker ps --format 'table {{.Names}}\t{{.Ports}}'
   ```

2. **🔍 Wybierz wolny port:**
   - Zakres 8016-8099 dla aplikacji
   - Zakres 9200-9999 dla eksporterów

3. **📝 Zaktualizuj PORT_ALLOCATION.md:**
   ```markdown
   | **8016** | twoja-usluga | All | docker-compose.yml | ✅ Active |
   ```

### **KONFIGURACJA SERWISU:**

4. **🗄️ Jeśli używa bazy danych:**
   ```yaml
   environment:
     - DATABASE_URL=postgresql+asyncpg://detektor:${POSTGRES_PASSWORD:-detektor_pass}@postgres:5432/detektor
   ```
   ⚠️ **UWAGA**: Baza nazywa się `detektor` NIE `detektor_db`!

5. **🔧 W production compose:**
   ```yaml
   twoja-usluga:
     <<: *production-defaults
     image: ghcr.io/hretheum/detektr/twoja-usluga:${IMAGE_TAG:-latest}
     ports:
       - "8016:8016"  # Użyj wolnego portu!
     environment:
       - LOG_LEVEL=INFO
       - DATABASE_URL=postgresql+asyncpg://detektor:${POSTGRES_PASSWORD:-detektor_pass}@postgres:5432/detektor
   ```

6. **📦 Dodaj do workflows:**
   - W `.github/workflows/main-pipeline.yml` dodaj do listy serwisów
   - W sekcji `paths-filter` dodaj ścieżki

### **DEPLOYMENT:**

7. **🚀 Testuj lokalnie:**
   ```bash
   cd /opt/detektor-clean
   export COMPOSE_PROJECT_NAME=detektor
   docker compose --env-file .env [...] up -d twoja-usluga
   ```

8. **🔍 Sprawdź logi:**
   ```bash
   docker logs detektor-twoja-usluga-1 --follow
   ```

9. **✅ Sprawdź health:**
   ```bash
   curl http://localhost:8016/health
   ```

## 🛠️ Komendy Diagnostyczne

```bash
# Sprawdź zajęte porty
netstat -tlnp | grep -E '(8080|8005|8010|5432|6432)'

# Sprawdź zmienne środowiskowe kontenera
docker inspect [container] | jq '.[0].Config.Env'

# Sprawdź hasło PostgreSQL
docker exec detektor-postgres-1 psql -U postgres -c "\du"

# Restart z prawidłowym .env
cd /opt/detektor-clean
export COMPOSE_PROJECT_NAME=detektor
docker compose --env-file .env -f [...] down
docker compose --env-file .env -f [...] up -d

# Cleanup duplikatów
docker ps -a | grep -E '^[a-f0-9]+.*base-' | awk '{print $1}' | xargs docker rm -f
docker volume ls | grep base_ | awk '{print $2}' | xargs docker volume rm
```

## 📚 Dokumentacja Powiązana

- [PORT_ALLOCATION.md](./PORT_ALLOCATION.md) - Mapa wszystkich portów
- [README.md](./README.md) - Główny przewodnik deployment
- [services/](./services/) - Dokumentacja poszczególnych serwisów

---

**💡 Złota Zasada**: Gdy coś nie działa, sprawdź:
1. Porty (PORT_ALLOCATION.md)
2. Zmienne środowiskowe (--env-file .env)
3. Nazwę projektu (COMPOSE_PROJECT_NAME=detektor)
4. Logi kontenera (docker logs)
