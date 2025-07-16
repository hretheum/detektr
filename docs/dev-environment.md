# Środowisko Developerskie - Detektor

## Quick Start (< 30 min)

### 1. Wymagania
- macOS z Docker Desktop
- VS Code z extensions:
  - Remote-SSH
  - Remote-Containers
  - Docker
- SSH key skonfigurowany dla serwera

### 2. Szybka konfiguracja

```bash
# 1. Sklonuj repo
git clone <repo-url> detektor
cd detektor

# 2. Uruchom setup
./scripts/dev-setup/vscode-remote-setup.sh

# 3. Ustaw Docker context
docker context use nebula

# 4. Otwórz w VS Code
code --remote ssh-remote+nebula /home/hretheum/detektor
```

### 3. Weryfikacja

```bash
# Test Docker
docker --context nebula ps

# Test SSH
ssh nebula hostname

# Test GPU (gdy sterowniki zainstalowane)
ssh nebula nvidia-smi
```

## Dostępne tryby pracy

### A. Remote SSH Development
- Edycja bezpośrednio na serwerze
- Pełny dostęp do GPU
- Najlepsza wydajność

```bash
code --remote ssh-remote+nebula /home/hretheum/detektor
```

### B. DevContainer
- Spójne środowisko
- Automatyczne dependencies
- Isolation

```bash
# W VS Code: Reopen in Container
```

### C. Local + Remote Docker
- Edycja lokalna
- Docker na serwerze
- Sync plików

```bash
docker --context nebula compose up
```

## Porty i serwisy

| Serwis | Port | URL |
|--------|------|-----|
| RTSP Capture | 8001 | http://192.168.1.193:8001 |
| Face Recognition | 8002 | http://192.168.1.193:8002 |
| Object Detection | 8003 | http://192.168.1.193:8003 |
| HA Bridge | 8004 | http://192.168.1.193:8004 |
| LLM Intent | 8005 | http://192.168.1.193:8005 |
| Prometheus | 9090 | http://192.168.1.193:9090 |
| Jaeger | 16686 | http://192.168.1.193:16686 |
| Grafana | 3000 | http://192.168.1.193:3000 |

## Debugging

### Python Remote Debugging
1. W kodzie: `import debugpy; debugpy.listen(5678)`
2. W VS Code: Run → "Python: Remote Attach"

### Docker Debugging
```bash
docker --context nebula logs -f <service>
docker --context nebula exec -it <container> bash
```

## Synchronizacja plików

### Automatyczna (zalecana)
VS Code Remote-SSH automatycznie synchronizuje

### Ręczna
```bash
# Jednorazowa
rsync -avz ./ nebula:~/detektor/

# Ciągła
./scripts/dev-setup/watch-sync.sh
```

## Troubleshooting

### Problem: Permission denied (Docker)
```bash
ssh nebula "sudo usermod -aG docker $USER"
# Wyloguj się i zaloguj ponownie
```

### Problem: VS Code nie łączy się
1. Sprawdź SSH: `ssh nebula`
2. Sprawdź klucz w ~/.ssh/config
3. Restart VS Code

### Problem: GPU nie widoczne
Sterowniki NVIDIA będą instalowane w Fazie 1

## Best Practices

1. **Zawsze używaj Docker context**
   ```bash
   docker context use nebula
   ```

2. **Commituj tylko z lokalnej maszyny**
   ```bash
   git add .
   git commit -m "message"
   ```

3. **Testuj na serwerze**
   ```bash
   docker --context nebula compose run tests
   ```

4. **Monitoruj zasoby**
   ```bash
   ssh nebula "htop"
   ssh nebula "docker stats"
   ```