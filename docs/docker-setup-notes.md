# Docker Setup - Notatki z instalacji

## Status: ✅ ZADANIE UKOŃCZONE

**Faza 1, Zadanie 1** - Konfiguracja środowiska Docker na serwerze Ubuntu

### Całościowe metryki sukcesu - ZWALIDOWANE

1. **Funkcjonalność**: Docker 28.3.2 (>24.0) i Compose v2.38.2 (>2.20) ✅
2. **Performance**: Container start 0.421s (<2s), network latency 0.105ms (<1ms) ✅
3. **Security**: Seccomp, AppArmor, log rotation, monitoring - wszystko aktywne ✅
4. **Maintainability**: Setup odtwarzalny w 30min z dokumentacją ✅

## Wykonane kroki (Blok 1)

### 1. Usunięcie snap Docker

- Usunięto poprzednią instalację snap: `sudo snap remove docker --purge`
- Wyczyszczono pozostałości: `/var/snap/docker`, `/snap/docker`

### 2. Instalacja Docker CE

- Źródło: Oficjalne repozytorium Docker
- Wersja: 28.3.2 (nowsza niż wymagane 24.0+)
- Komponenty:
  - docker-ce
  - docker-ce-cli
  - containerd.io
  - docker-buildx-plugin
  - docker-compose-plugin v2.38.2

### 3. Konfiguracja

- Systemd service: aktywny i enabled
- Użytkownik hretheum dodany do grupy docker
- Storage driver: overlay2
- Docker root: /var/lib/docker

## Walidacja

✅ Docker daemon działa jako systemd service
✅ Docker Compose v2.38.2 (wymagane 2.20+)
✅ Hello-world container wykonuje się poprawnie
✅ Użytkownik może uruchamiać kontenery bez sudo

## Wykonane kroki (Blok 2)

### 1. Docker Compose v2 jako plugin

- Już zainstalowany z Docker CE (v2.38.2)
- Działa jako `docker compose` (nie docker-compose)

### 2. Auto-completion

- Skonfigurowane dla zsh
- Dodane do ~/.zsh/completions/
- Włączone w ~/.zshrc

### 3. Test multi-container

- Flask-Redis stack uruchomiony pomyślnie
- Services komunikują się poprawnie
- docker compose up/down/ps/logs działają

## Wykonane kroki (Blok 3)

### 1. Security hardening

- Log rotation: 100MB per file, max 3 files
- Seccomp: enabled (builtin profile)
- AppArmor: enabled
- User namespace remapping: przygotowane (dockremap user)

### 2. Monitoring

- Metrics endpoint: <http://localhost:9323/metrics>
- Prometheus-ready metrics (668+ metrics)
- Docker daemon metrics exposed

### 3. Konfiguracja daemon.json

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}
```

## Następne kroki

- Blok 4: Integracja z projektem
