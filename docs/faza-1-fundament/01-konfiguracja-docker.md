# Faza 1 / Zadanie 1: Konfiguracja środowiska Docker na serwerze Ubuntu

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Cel jest jasny i biznesowo uzasadniony
2. Dekompozycja pokrywa 100% zakresu zadania
3. Nie ma luk między blokami zadań
4. Całość można ukończyć w podanym czasie
-->

## Cel zadania

Zainstalować i skonfigurować Docker Engine oraz Docker Compose v2 na serwerze Ubuntu, przygotowując fundament dla całej infrastruktury kontenerowej projektu z security best practices i monitoring od początku.

## Blok 0: Prerequisites check
<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe

1. **[x] Weryfikacja wymagań systemowych**
   - **Metryka**: Ubuntu 22.04+, kernel 5.15+, 50GB+ free space
   - **Walidacja**:

     ```bash
     ./scripts/check-docker-prerequisites.sh
     # Sprawdza: OS version, kernel, disk space, CPU arch
     # Exit 0 = ready to install
     ```

   - **Czas**: 0.5h

2. **[x] Backup istniejącej konfiguracji**
   - **Metryka**: Existing Docker config (if any) backed up
   - **Walidacja**:

     ```bash
     ls -la /backups/docker/$(date +%Y%m%d)/{daemon.json,docker-compose.yml}
     # Files exist or "No existing Docker" logged
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Przygotowanie systemu i instalacja Docker
<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Każde zadanie atomowe musi być wykonalne w MAX 3h
2. Zadania w bloku powinny być logicznie powiązane
3. Kolejność zadań musi mieć sens (dependencies)
4. Blok powinien dostarczać konkretną wartość biznesową
-->

#### Zadania atomowe

1. **[x] Aktualizacja systemu i instalacja prerequisites**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Mieć JEDEN konkretny deliverable
   - Być wykonalne przez jedną osobę bez przerw
   - Mieć jasne kryterium "done"
   - NIE wymagać czekania na zewnętrzne zależności
   -->
   - **Metryka**: System updated, required packages installed
   - **Walidacja**:

     ```bash
     apt list --installed | grep -E "(ca-certificates|curl|gnupg)" | wc -l
     # Should return 3
     dpkg -l | grep -E "^ii.*apt-transport-https" # Should show installed
     ```

   - **Czas**: 1h

2. **[x] Dodanie oficjalnego Docker repository**
   - **Metryka**: Docker GPG key added, repository configured
   - **Walidacja**:

     ```bash
     apt-key list | grep Docker
     # Shows Docker Release key
     cat /etc/apt/sources.list.d/docker.list | grep "download.docker.com"
     # Shows correct repository
     ```

   - **Czas**: 0.5h

3. **[x] Instalacja Docker Engine i CLI**
   - **Metryka**: Docker CE 24.0+ installed and running
   - **Walidacja**:

     ```bash
     docker --version | grep -E "Docker version 2[4-9]"
     systemctl is-active docker # returns "active"
     docker run hello-world 2>&1 | grep "Hello from Docker!"
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku
<!--
LLM PROMPT dla metryk bloku:
Metryki muszą potwierdzać że blok osiągnął swój cel.
Powinny być:
1. Mierzalne automatycznie gdzie możliwe
2. Agregować metryki zadań atomowych
3. Dawać pewność że można przejść do następnego bloku
-->
- Docker Engine działa i odpowiada na komendy
- Systemd service skonfigurowany z auto-start
- Hello-world container wykonuje się poprawnie

### Blok 2: Instalacja i konfiguracja Docker Compose

#### Zadania atomowe

1. **[x] Instalacja Docker Compose v2 jako plugin**
   - **Metryka**: Version 2.20+
   - **Walidacja**: `docker compose version | grep -E "v2\.(2[0-9]|[3-9][0-9])"`
   - **Czas**: 0.5h

2. **[x] Konfiguracja auto-complete dla compose**
   - **Metryka**: Tab completion działa w bash/zsh
   - **Walidacja**: Wpisz `docker compose u[TAB]` → `up`
   - **Czas**: 0.5h

3. **[x] Test compose z przykładowym stackiem**
   - **Metryka**: Multi-container app działa
   - **Walidacja**:

     ```bash
     cd /tmp && git clone https://github.com/docker/awesome-compose
     cd awesome-compose/nginx-golang-mysql
     docker compose up -d && docker compose ps
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Compose commands działają globally
- Multi-container orchestration works
- Logs aggregation działa

### Blok 3: Security hardening i monitoring
<!--
LLM PROMPT: Security nie może być afterthought.
Każdy element musi być testowany i mierzalny.
Rozbij duże zadania na mniejsze kroki.
-->

#### Zadania atomowe

1. **[x] Konfiguracja user namespace remapping**
   - **Metryka**: Docker daemon runs as non-root inside containers
   - **Walidacja**:

     ```bash
     docker info | grep "userns"
     # Shows: User Namespace Enabled: true
     cat /etc/subuid | grep dockremap
     # Shows dockremap:100000:65536
     ```

   - **Czas**: 1h

2. **[x] Setup seccomp i AppArmor profiles**
   - **Metryka**: Default security profiles active
   - **Walidacja**:

     ```bash
     docker info | grep -A 5 "Security Options"
     # Shows: seccomp, apparmor
     docker run --rm alpine cat /proc/1/status | grep Seccomp
     # Mode should be 2 (filtered)
     ```

   - **Czas**: 1.5h

3. **[x] Konfiguracja Docker daemon metrics**
   - **Metryka**: Prometheus metrics endpoint active
   - **Walidacja**:

     ```bash
     curl -s localhost:9323/metrics | grep -E "engine_daemon_network_actions_seconds_count"
     # Returns metrics data
     netstat -tlnp | grep 9323
     # Shows docker listening
     ```

   - **Czas**: 1h

4. **[x] Setup log rotation i disk limits**
   - **Metryka**: Logs rotated at 100MB, max 3 files
   - **Walidacja**:

     ```bash
     cat /etc/docker/daemon.json | jq '."log-driver"'  # "json-file"
     cat /etc/docker/daemon.json | jq '."log-opts"."max-size"'  # "100m"
     cat /etc/docker/daemon.json | jq '."log-opts"."max-file"'  # "3"
     ```

   - **Czas**: 0.5h

#### Metryki sukcesu bloku

- Security scan pokazuje 0 critical issues
- Metrics endpoint dostępny dla Prometheus
- Disk usage pod kontrolą (auto-cleanup działa)

### Blok 4: Integracja z projektem i dokumentacja

#### Zadania atomowe

1. **[x] Utworzenie struktury katalogów projektu**
   - **Metryka**: /opt/detektor directories with correct permissions
   - **Walidacja**:

     ```bash
     find /opt/detektor -type d -name "data" -o -name "config" -o -name "logs" | wc -l
     # Should return 3
     stat -c "%U:%G %a" /opt/detektor  # user:docker 750
     ```

   - **Czas**: 0.5h

2. **[x] Utworzenie Docker networks dla projektu**
   - **Metryka**: Isolated networks for frontend/backend
   - **Walidacja**:

     ```bash
     docker network ls | grep -E "detektor_(frontend|backend)" | wc -l
     # Should return 2
     docker network inspect detektor_backend | jq '.[0].EnableIPv6'  # false
     ```

   - **Czas**: 0.5h

3. **[x] Base docker-compose.yml z common services**
   - **Metryka**: Valid compose file with x-templates
   - **Walidacja**:

     ```bash
     docker compose -f /opt/detektor/docker-compose.yml config --quiet
     # No output = valid
     docker compose -f /opt/detektor/docker-compose.yml config | grep -c "x-"
     # Should show templates defined
     ```

   - **Czas**: 1h

4. **[x] Dokumentacja i runbook**
   - **Metryka**: Complete setup guide, troubleshooting section
   - **Walidacja**:

     ```bash
     vale /opt/detektor/docs/docker-setup.md
     # No errors
     grep -c "^##" /opt/detektor/docs/docker-setup.md
     # At least 5 sections
     ```

   - **Czas**: 1h

#### Metryki sukcesu bloku

- Struktura projektu gotowa do deploymentu
- Docker Compose scaffold validates i jest reusable
- Dokumentacja kompletna i przetestowana

## Całościowe metryki sukcesu zadania
<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera (self w tym przypadku)
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Funkcjonalność**: Docker 24.0+ i Compose v2.20+ działają stabilnie
2. **Performance**: Container start <2s, network latency <1ms między containers
3. **Security**: Basic CIS Docker Benchmark items passed (userns, seccomp, AppArmor)
4. **Maintainability**: Setup odtwarzalny w <30min używając dokumentacji

## Deliverables
<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi:
1. Mieć konkretną ścieżkę w filesystem
2. Być wymieniony w jakimś zadaniu atomowym
3. Mieć jasny format i przeznaczenie
-->

1. `/etc/docker/daemon.json` - Docker daemon configuration with security settings
2. `/opt/detektor/docker-compose.yml` - Base compose file with x-templates
3. `/opt/detektor/docs/docker-setup.md` - Complete setup documentation
4. `/opt/detektor/scripts/check-docker-prerequisites.sh` - Prerequisites checker
5. `/opt/detektor/scripts/docker-health-check.sh` - Health monitoring script
6. `/etc/subuid` & `/etc/subgid` - User namespace mappings

## Narzędzia
<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
Dla każdego podaj:
1. Dokładną nazwę i wersję (jeśli istotna)
2. Konkretne zastosowanie w tym zadaniu
3. Alternatywy jeśli główne narzędzie zawiedzie
-->

- **Docker CE 24.0+**: Container runtime (no alternative)
- **Docker Compose v2.20+**: Multi-container orchestration (alternative: docker stack)
- **jq**: JSON processing dla daemon.json (alternative: python -m json.tool)
- **vale**: Documentation linting (alternative: markdownlint)
- **systemctl**: Service management (Ubuntu specific)

## Zależności

- **Wymaga**:
  - SSH dostęp do Ubuntu 22.04+ server
  - Minimum 50GB free disk space
  - Internet dla package downloads
- **Blokuje**:
  - Wszystkie następne zadania (fundament)
  - Szczególnie: NVIDIA toolkit, observability stack

## Ryzyka i mitigacje
<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
Dla każdego ryzyka:
1. Opisz konkretny scenariusz
2. Oceń realistycznie prawdopodobieństwo
3. Zaproponuj WYKONALNĄ mitigację
4. Dodaj trigger/early warning sign
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Konflikt z istniejącym Docker | Średnie | Wysoki | Backup config, test remove/install | `docker --version` shows old version |
| Brak miejsca podczas pull images | Średnie | Wysoki | Check df -h przed, configure limits | df -h shows <20GB free |
| Network conflicts z existing services | Niskie | Średni | Use custom subnets 172.20.x.x | Port 9323 already in use |
| User namespace breaks existing containers | Średnie | Wysoki | Test on single container first | Existing containers running |

## Rollback Plan
<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
Opisz:
1. Jak wykryć że coś poszło źle
2. Kroki do przywrócenia poprzedniego stanu
3. Maksymalny czas rollbacku
-->

1. **Detekcja problemu**:
   - Docker daemon nie startuje
   - Containers fail to run
   - Security features break functionality
   - Network isolation issues

2. **Kroki rollback**:
   - [ ] Stop Docker: `systemctl stop docker`
   - [ ] Restore daemon.json: `cp /backups/docker/$(date +%Y%m%d)/daemon.json /etc/docker/`
   - [ ] Remove user namespace: `userdel dockremap`
   - [ ] Restart Docker: `systemctl start docker`
   - [ ] Verify: `docker run hello-world`

3. **Czas rollback**: <10 minut

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-nvidia-toolkit.md](./02-nvidia-toolkit.md)
