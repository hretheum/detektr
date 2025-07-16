# Faza 0 / Zadanie 4: Przygotowanie środowiska developerskiego

## Cel zadania

Skonfigurować środowisko developerskie umożliwiające wygodną pracę z Mac OS z wykorzystaniem GPU na serwerze Ubuntu, z pełnym wsparciem dla remote development.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites

#### Zadania atomowe

1. **[ ] Weryfikacja połączenia SSH Mac → Ubuntu**
   - **Metryka**: SSH key-based auth działa
   - **Walidacja**: `ssh ubuntu-server hostname`
   - **Czas**: 0.5h

2. **[ ] Sprawdzenie wymagań sieciowych**
   - **Metryka**: Porty 22, 2375, 6000-6010 dostępne
   - **Walidacja**: `nc -zv ubuntu-server 22 2375`
   - **Czas**: 0.5h

### Blok 1: Remote Docker development

#### Zadania atomowe

1. **[ ] Konfiguracja Docker context**
   - **Metryka**: Docker commands z Mac → Ubuntu
   - **Walidacja**: `docker --context ubuntu ps`
   - **Czas**: 1h

2. **[ ] Setup Docker over SSH**
   - **Metryka**: Secure Docker API access
   - **Walidacja**: `DOCKER_HOST=ssh://ubuntu-server docker info`
   - **Czas**: 2h

3. **[ ] VS Code Remote-SSH setup**
   - **Metryka**: Full IDE features over SSH
   - **Walidacja**: Open project, IntelliSense works
   - **Czas**: 1h

### Blok 2: GPU development support

#### Zadania atomowe

1. **[ ] CUDA toolkit na Mac (opcjonalne)**
   - **Metryka**: CUDA headers dla IntelliSense
   - **Walidacja**: VS Code rozpoznaje CUDA types
   - **Czas**: 1h

2. **[ ] Remote GPU debugging setup**
   - **Metryka**: cuda-gdb over SSH
   - **Walidacja**: Breakpoint w CUDA kernel
   - **Czas**: 2h

3. **[ ] GPU monitoring dashboard**
   - **Metryka**: nvidia-smi w Grafana
   - **Walidacja**: Real-time GPU metrics
   - **Czas**: 2h

### Blok 3: Development workflow

#### Zadania atomowe

1. **[ ] Automated sync Mac ↔ Ubuntu**
   - **Metryka**: Code changes auto-sync
   - **Walidacja**: mutagen/rsync working
   - **Czas**: 2h

2. **[ ] Remote debugging Python**
   - **Metryka**: Debugger attach to container
   - **Walidacja**: Breakpoint hits
   - **Czas**: 2h

3. **[ ] Hot reload configuration**
   - **Metryka**: Code changes = instant reload
   - **Walidacja**: Change → reload <2s
   - **Czas**: 1h

### Blok 4: DevContainer setup

#### Zadania atomowe

1. **[ ] .devcontainer configuration**
   - **Metryka**: Full env in container
   - **Walidacja**: `devcontainer up` works
   - **Czas**: 2h

2. **[ ] Extensions i settings sync**
   - **Metryka**: Consistent dev experience
   - **Walidacja**: Extensions auto-install
   - **Czas**: 1h

3. **[ ] Documentation i onboarding**
   - **Metryka**: New dev setup <30min
   - **Walidacja**: Follow guide test
   - **Czas**: 2h

## Całościowe metryki sukcesu zadania

1. **Productivity**: No difference vs local dev
2. **Performance**: <100ms latency Mac-Ubuntu
3. **Reliability**: Stable 8h+ sessions
4. **GPU access**: Full CUDA debugging

## Deliverables

1. `.devcontainer/` - DevContainer config
2. `scripts/dev-setup/` - Setup automation
3. `docs/dev-environment.md` - Setup guide
4. `.vscode/remote-settings.json` - Remote config
5. `docker/dev-compose.yml` - Dev services

## Narzędzia

- **VS Code Remote-SSH**: Remote development
- **Docker Context**: Remote Docker
- **mutagen**: File sync
- **cuda-gdb**: GPU debugging
- **ngrok**: Optional tunnel

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-szablon-dokumentacji.md](./05-szablon-dokumentacji.md)
