# Redis HA Migration Plan

## Obecna sytuacja

1. **Pojedynczy Redis** działa na porcie 6379 w `docker-compose.yml`
2. **Redis HA** jest przygotowany w `docker-compose.redis-ha.yml` ale nie jest wdrożony
3. **Konflikt portów** - oba setupy używają portu 6379
4. **Brak konfiguracji** - pliki config dla Redis HA nie są deployowane

## Strategia migracji

### Opcja 1: Zastąpienie Redis (RECOMMENDED)
Całkowite zastąpienie pojedynczego Redis przez Redis HA.

**Zalety:**
- Prawdziwe HA od początku
- Brak konfliktów portów
- Czysta architektura

**Wady:**
- Wymaga restartu wszystkich serwisów
- Krótka przerwa w działaniu

### Opcja 2: Równoległe działanie
Uruchomienie Redis HA na innych portach obok istniejącego Redis.

**Zalety:**
- Brak przestoju
- Możliwość stopniowej migracji

**Wady:**
- Skomplikowana konfiguracja
- Podwójne zużycie zasobów
- Trudne zarządzanie

## Kroki implementacji (Opcja 1)

### 1. Przygotowanie plików konfiguracyjnych

```bash
# Na lokalnym środowisku
cd /Users/hretheum/dev/bezrobocie/detektor

# Utworzenie override file dla Redis HA
cat > docker-compose.redis-ha-override.yml << 'EOF'
# Override dla zastąpienia pojedynczego Redis przez Redis HA
services:
  # Wyłączenie pojedynczego Redis
  redis:
    deploy:
      replicas: 0
    command: echo "Single Redis disabled - using Redis HA"
    entrypoint: /bin/true
EOF
```

### 2. Modyfikacja deployment script

Dodanie do `scripts/deploy-to-nebula.sh`:
- Kopiowanie plików konfiguracji Redis
- Opcjonalne włączenie Redis HA
- Prawidłowa kolejność uruchamiania

### 3. Aktualizacja serwisów

Wszystkie serwisy muszą używać Redis Sentinel dla połączeń:
- Zmiana z `redis:6379` na sentinel-aware connection
- Dodanie redis-sentinel client library

### 4. Deployment proces

```bash
# 1. Zatrzymanie aplikacji (zachowanie danych)
ssh nebula "cd /opt/detektor && docker compose stop"

# 2. Backup danych Redis
ssh nebula "docker exec detektr-redis-1 redis-cli BGSAVE"
ssh nebula "docker cp detektr-redis-1:/data/dump.rdb /opt/detektor/redis-backup.rdb"

# 3. Deploy Redis HA
ssh nebula "cd /opt/detektor && docker compose -f docker-compose.yml -f docker-compose.redis-ha.yml -f docker-compose.redis-ha-override.yml up -d"

# 4. Restore danych do Redis Master
ssh nebula "docker cp /opt/detektor/redis-backup.rdb redis-master:/data/"
ssh nebula "docker exec redis-master redis-cli SHUTDOWN NOSAVE"
ssh nebula "docker start redis-master"

# 5. Restart aplikacji
ssh nebula "cd /opt/detektor && docker compose up -d"
```

## Alternatywa: Proste rozwiązanie tymczasowe

Jeśli Redis HA nie jest krytyczny teraz:

1. **Usuń Redis HA z deployment**
   - Nie deployuj `docker-compose.redis-ha.yml`
   - Używaj tylko pojedynczego Redis

2. **Popraw health check**
   - Usuń sprawdzanie sentinel containers
   - Sprawdzaj tylko działające serwisy

3. **Zaplanuj migrację na później**
   - Po ustabilizowaniu podstawowych serwisów
   - Z właściwym testem i rollback plan

## Rekomendacja

**Na ten moment**: Zostań przy pojedynczym Redis i napraw health check.

**Dlaczego?**
- Redis HA wymaga zmian w kodzie wszystkich serwisów
- Sentinel-aware clients nie są jeszcze zaimplementowane
- Pojedynczy Redis jest wystarczający dla POC/MVP
- Skupienie na działających serwisach jest ważniejsze

**Plan działania:**
1. Napraw health-check script
2. Udokumentuj Redis HA jako "Future Enhancement"
3. Wróć do tego po zakończeniu Fazy 2
