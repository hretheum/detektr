# Faza 2 / Zadanie 3: Redis Sentinel High Availability Setup

## Cel zadania

Wdrożyć Redis Sentinel dla zapewnienia automatycznego failoveru message brokera, eliminując single point of failure i osiągając 99.9% availability z automatycznym przełączaniem w <60 sekund.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites i backup obecnego systemu

#### Zadania atomowe

1. **[x] Backup obecnej konfiguracji Redis**
   - **Metryka**: Backup plików zawierający všetkie dane Redis
   - **Walidacja**:
     ```bash
     ssh nebula "docker exec detektor-redis-1 redis-cli BGSAVE"
     ssh nebula "docker exec detektor-redis-1 redis-cli LASTSAVE"
     # Verify backup file exists and is recent
     ssh nebula "docker exec detektor-redis-1 ls -la /data/dump.rdb"
     ```
   - **Quality Gate**: Backup file size >1KB, created within last 5 minutes
   - **Guardrails**: Never proceed without confirmed backup
   - **Czas**: 0.5h

2. **[x] Weryfikacja dostępnych zasobów systemowych**
   - **Metryka**: Wystarczające zasoby dla 4 dodatkowych kontenerów
   - **Walidacja**:
     ```bash
     ssh nebula "free -h | grep Mem"  # Min 2GB free
     ssh nebula "df -h / | tail -1"   # Min 5GB disk free
     ssh nebula "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep redis"
     ```
   - **Quality Gate**: RAM >2GB free, Disk >5GB free, Redis healthy
   - **Guardrails**: Terminate if insufficient resources
   - **Czas**: 0.5h

3. **[x] Inwentaryzacja aplikacji używających Redis**
   - **Metryka**: Lista wszystkich serwisów z Redis connections
   - **Walidacja**:
     ```bash
     grep -r "redis.Redis\|REDIS_HOST" services/ --include="*.py"
     grep -r "redis:" docker-compose*.yml
     # Count connections and identify all Redis clients
     ```
   - **Quality Gate**: Pełna lista serwisów wymagających modyfikacji
   - **Guardrails**: No hidden Redis dependencies
   - **Czas**: 1h

#### 📊 **Wyniki Bloku 0:**
- ✅ **Backup created**: 7.6MB dump.rdb file (timestamp: 1753192075)
- ✅ **Resources sufficient**: 57GB RAM free, 154GB disk free
- ✅ **Redis healthy**: detektr-redis-1 running normally
- ✅ **Services inventory**: 3 primary services identified (frame-buffer, telegram-alerts, load-tester)
- ✅ **Compose files**: 6 docker-compose files require updates

**UWAGA**: Redis HA został przygotowany (kod i konfiguracja) ale nie został wdrożony na produkcję. System działa na pojedynczej instancji Redis, która jest wystarczająca dla obecnych potrzeb.

### Blok 1: Konfiguracja Redis Master-Slave z Sentinel

#### Zadania atomowe

1. **[ ] Utworzenie plików konfiguracyjnych Redis HA**
   - **Metryka**: 3 pliki konfiguracyjne: master, slave, sentinel
   - **Walidacja**:
     ```bash
     # Verify config files exist and contain required settings
     ls -la config/redis-master.conf config/redis-slave.conf config/sentinel.conf
     grep "replicaof\|sentinel monitor" config/*
     ```
   - **Quality Gate**: All configs validate with redis-server --test-config
   - **Guardrails**: Configs must include persistence, monitoring, security
   - **Czas**: 1h

2. **[ ] Docker Compose setup dla Redis HA**
   - **Metryka**: docker-compose.redis-ha.yml z 4 serwisami
   - **Walidacja**:
     ```bash
     # Verify compose file structure
     docker-compose -f docker-compose.redis-ha.yml config
     # Check services: redis-master, redis-slave, sentinel-1, sentinel-2, sentinel-3
     ```
   - **Quality Gate**: Compose validation passes, all networks configured
   - **Guardrails**: Health checks for all services, proper dependencies
   - **Czas**: 1.5h

3. **[ ] Lokalne testy konfiguracji HA**
   - **Metryka**: Redis HA działa lokalnie z automatycznym failoverem
   - **Walidacja**:
     ```bash
     # Local test of HA setup
     docker-compose -f docker-compose.redis-ha.yml up -d
     docker exec redis-master redis-cli INFO replication
     docker exec sentinel-1 redis-cli -p 26379 SENTINEL masters
     # Test failover: stop master, verify slave promotion
     ```
   - **Quality Gate**: Replication working, Sentinel detects topology
   - **Guardrails**: Failover completes in <60 seconds
   - **Czas**: 2h

### Blok 2: Modyfikacja aplikacji dla Sentinel support

#### Zadania atomowe

1. **[x] Aktualizacja frame-buffer service**
   - **Metryka**: Frame-buffer używa Sentinel connection
   - **Walidacja**:
     ```bash
     # Verify code changes
     grep "sentinel\|Sentinel" services/frame-buffer/src/main.py
     # Test connection
     curl http://localhost:8002/health
     ```
   - **Quality Gate**: Service connects to Redis through Sentinel
   - **Guardrails**: Fallback mechanism if Sentinel unavailable
   - **Czas**: 1h

2. **[x] Aktualizacja telegram-alerts service**
   - **Metryka**: Telegram alerts używa Sentinel connection
   - **Walidacja**:
     ```bash
     grep "sentinel" services/telegram-alerts/telegram-monitor.py
     # Test alert functionality
     ```
   - **Quality Gate**: Monitoring functions work with Sentinel
   - **Guardrails**: Alerts work regardless of which Redis instance is master
   - **Czas**: 0.5h

3. **[x] Aktualizacja load-tester**
   - **Metryka**: Load tester kompatybilny z Sentinel
   - **Walidacja**:
     ```bash
     docker run --rm --network detektor-network load-tester --rate 100 --duration 30
     # Should connect through Sentinel and work normally
     ```
   - **Quality Gate**: Load tests pass with Sentinel configuration
   - **Guardrails**: Performance metrics unchanged
   - **Czas**: 0.5h

4. **[x] Lokalne testy integracyjne**
   - **Metryka**: Wszystkie serwisy działają z Redis HA lokalnie
   - **Walidacja**:
     ```bash
     docker-compose up -d
     curl http://localhost:8002/health  # frame-buffer
     curl http://localhost:8002/metrics # check redis metrics
     # Test all services can read/write through Sentinel
     ```
   - **Quality Gate**: All services healthy, metrics show Sentinel usage
   - **Guardrails**: No performance degradation vs direct Redis connection
   - **Czas**: 1h

### Blok 3: Deployment na Nebula z minimalizacją downtime

#### Zadania atomowe

1. **[ ] Przygotowanie środowiska Nebula**
   - **Metryka**: Pliki konfiguracyjne skopiowane na Nebulę
   - **Walidacja**:
     ```bash
     ssh nebula "ls -la /opt/detektor/config/redis-master.conf"
     ssh nebula "ls -la /opt/detektor/docker-compose.redis-ha.yml"
     ```
   - **Quality Gate**: All required files present and readable
   - **Guardrails**: Verify file permissions and syntax
   - **Czas**: 0.5h

2. **[ ] Graceful shutdown obecnego Redis**
   - **Metryka**: Kontrolowany shutdown z zapisem danych
   - **Walidacja**:
     ```bash
     # Graceful shutdown sequence
     ssh nebula "docker exec detektr-redis-1 redis-cli BGSAVE"
     ssh nebula "docker-compose stop frame-buffer telegram-alerts"
     ssh nebula "docker-compose stop redis"
     ```
   - **Quality Gate**: Clean shutdown, no data corruption
   - **Guardrails**: Services stopped in correct order
   - **Czas**: 0.5h

3. **[ ] Deployment Redis HA cluster**
   - **Metryka**: Redis HA cluster operational na Nebuli
   - **Walidacja**:
     ```bash
     ssh nebula "cd /opt/detektor && docker-compose -f docker-compose.redis-ha.yml up -d"
     ssh nebula "docker ps | grep -E 'redis-master|redis-slave|sentinel'"
     # Verify replication
     ssh nebula "docker exec redis-master redis-cli INFO replication"
     ```
   - **Quality Gate**: Master-slave replication established, Sentinels running
   - **Guardrails**: All containers healthy, no port conflicts
   - **Czas**: 1h

4. **[ ] Restart application services**
   - **Metryka**: Wszystkie serwisy działają z nową konfiguracją Sentinel
   - **Walidacja**:
     ```bash
     ssh nebula "docker-compose -f docker-compose.yml -f docker-compose.redis-ha.yml up -d"
     curl http://192.168.1.193:8002/health
     curl http://192.168.1.193:8002/metrics | grep redis
     ```
   - **Quality Gate**: All services connect through Sentinel
   - **Guardrails**: Health checks pass, metrics show correct Redis connection
   - **Czas**: 1h

### Blok 4: Testy funkcjonalności i failover

#### Zadania atomowe

1. **[ ] Weryfikacja replikacji Master-Slave**
   - **Metryka**: Dane synchronizują się między Master a Slave w <1s
   - **Walidacja**:
     ```bash
     # Test replication lag
     ssh nebula "docker exec redis-master redis-cli SET test_key 'test_value_$(date +%s)'"
     ssh nebula "docker exec redis-slave redis-cli GET test_key"
     # Verify values match
     ssh nebula "docker exec redis-master redis-cli INFO replication"
     ```
   - **Quality Gate**: Replication lag <100ms, no sync errors
   - **Guardrails**: Data integrity maintained across instances
   - **Czas**: 0.5h

2. **[ ] Test automatycznego failoveru**
   - **Metryka**: Automatic failover completes w <60 sekund
   - **Walidacja**:
     ```bash
     # Simulate master failure
     ssh nebula "docker stop redis-master"
     # Monitor failover process
     ssh nebula "docker logs sentinel-1 -f" &
     # Verify new master elected
     sleep 60
     ssh nebula "docker exec sentinel-1 redis-cli -p 26379 SENTINEL masters"
     ```
   - **Quality Gate**: New master elected, applications reconnect automatically
   - **Guardrails**: Zero data loss during failover
   - **Czas**: 1h

3. **[ ] Test recovery i rejoin**
   - **Metryka**: Dawny master dołącza jako slave po restarcie
   - **Walidacja**:
     ```bash
     # Restart failed master
     ssh nebula "docker start redis-master"
     # Verify it joins as slave
     sleep 30
     ssh nebula "docker exec redis-master redis-cli INFO replication | grep role:slave"
     ```
   - **Quality Gate**: Ex-master becomes slave of new master
   - **Guardrails**: No split-brain scenarios, consistent data
   - **Czas**: 0.5h

4. **[ ] Load test pod HA setup**
   - **Metryka**: Performance nie gorsza niż przed HA setup
   - **Walidacja**:
     ```bash
     ssh nebula "docker run --rm --network detektor-network load-tester --rate 500 --duration 120"
     # Compare with previous results: >400 msg/s, <1ms latency
     ```
   - **Quality Gate**: Throughput >400 msg/s, latency <1ms, success rate 100%
   - **Guardrails**: Performance regression <10%
   - **Czas**: 1h

### Blok 5: Monitoring i alerting dla HA setup

#### Zadania atomowe

1. **[ ] Aktualizacja Prometheus configuration**
   - **Metryka**: Prometheus scrapes wszystkie Redis instances i Sentinels
   - **Walidacja**:
     ```bash
     curl 'http://192.168.1.193:9090/api/v1/targets' | grep -E 'redis-master|redis-slave|sentinel'
     # All targets should be 'up'
     ```
   - **Quality Gate**: All Redis HA components monitored
   - **Guardrails**: No monitoring blind spots
   - **Czas**: 1h

2. **[ ] Aktualizacja Grafana dashboard**
   - **Metryka**: Dashboard pokazuje HA topology i failover events
   - **Walidacja**:
     ```bash
     # Verify new panels in dashboard
     curl -s 'http://admin:admin@192.168.1.193:3000/api/dashboards/uid/broker-metrics' | jq '.dashboard.panels[] | select(.title | contains("Sentinel"))'
     ```
   - **Quality Gate**: Dashboard shows master/slave roles, Sentinel status
   - **Guardrails**: Historical data preserved, new metrics added
   - **Czas**: 1.5h

3. **[ ] Konfiguracja alertów dla HA events**
   - **Metryka**: Alerts na: failover events, split-brain, replication lag
   - **Walidacja**:
     ```bash
     # Test alert rules
     curl 'http://192.168.1.193:9090/api/v1/rules' | grep -E 'RedisMaster|RedisSlave|Sentinel'
     # Simulate alert condition and verify notifications
     ```
   - **Quality Gate**: Alerts fire within 30s of issues
   - **Guardrails**: Alert fatigue avoided, actionable alerts only
   - **Czas**: 1h

4. **[ ] Dokumentacja deployment procedure**
   - **Metryka**: Kompletny runbook dla Redis HA operations
   - **Walidacja**:
     ```bash
     ls -la docs/deployment/services/redis-sentinel.md
     # Document should include: deployment, failover procedures, troubleshooting
     ```
   - **Quality Gate**: Documentation covers all operational scenarios
   - **Guardrails**: Procedures tested and verified
   - **Czas**: 1h

## Status implementacji

### ✅ Zrealizowane:
1. **Kod aplikacji** - Wszystkie serwisy mają wsparcie dla Redis Sentinel (RedisSentinelClient)
2. **Konfiguracja** - Pliki konfiguracyjne i docker-compose.redis-ha.yml przygotowane
3. **Testy lokalne** - Redis HA przetestowany lokalnie

### ❌ NIE zrealizowane:
1. **Deployment produkcyjny** - Redis HA nie jest uruchomiony na Nebuli
2. **Testy failover** - Nie przeprowadzono testów automatycznego przełączania
3. **Monitoring HA** - Prometheus/Grafana nie monitorują topologii HA
4. **Dokumentacja operacyjna** - Brak runbook dla operacji HA

### 📋 Decyzja:
Redis HA został **odłożony** jako future enhancement. Pojedyncza instancja Redis jest wystarczająca dla:
- POC/MVP projektu
- Obecnego obciążenia
- Testów funkcjonalności

Redis HA będzie wdrożony po zakończeniu Fazy 2, gdy wszystkie serwisy będą stabilne.

## Całościowe metryki sukcesu zadania (planowane)

1. **High Availability**: Automatic failover w <60s, 99.9% uptime
2. **Performance**: Brak degradacji wydajności (>400 msg/s maintained)
3. **Reliability**: Zero data loss podczas failoveru
4. **Observability**: Pełny monitoring HA topology w Prometheus/Grafana
5. **Operability**: Dokumentowane procedury dla wszystkich scenariuszy

## Deliverables

1. `config/redis-master.conf` - Master Redis configuration
2. `config/redis-slave.conf` - Slave Redis configuration
3. `config/sentinel.conf` - Sentinel configuration
4. `docker-compose.redis-ha.yml` - HA deployment configuration
5. `docs/deployment/services/redis-sentinel.md` - Operational runbook
6. Updated application code - Sentinel client integration
7. Enhanced Grafana dashboard - HA topology monitoring
8. Alert rules - Failover and health notifications

## Narzędzia

- **Redis 7+**: Master-slave replication
- **Redis Sentinel**: Automatic failover management
- **Docker Compose**: Container orchestration
- **Python redis-py**: Sentinel client library

## Zależności

- **Wymaga**: Działający Redis (obecny setup)
- **Blokuje**: Możliwe 5-10 min downtime podczas migracji
- **Następne**: Enhanced monitoring, multi-region setup (future)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Failover nie działa | Niskie | Wysoki | Extensive testing, rollback plan | Monitoring alerts |
| Performance degradation | Średnie | Średni | Load testing, benchmarking | Performance metrics |
| Split-brain scenario | Niskie | Wysoki | Quorum configuration, monitoring | Sentinel logs |
| Configuration errors | Średnie | Wysoki | Validation, testing pipeline | Config syntax checks |

## Rollback Plan

1. **Detekcja problemu**:
   - Failover nie działa prawidłowo
   - Performance degradation >20%
   - Data inconsistency detected

2. **Kroki rollback**:
   - [ ] Stop all HA components: `docker-compose -f docker-compose.redis-ha.yml down`
   - [ ] Restore single Redis: `docker-compose up -d redis`
   - [ ] Revert application code to direct Redis connections
   - [ ] Verify service functionality

3. **Czas rollback**: <5 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-postgresql-timescale.md](./04-postgresql-timescale.md)
