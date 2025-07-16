# Docker Setup - Notatki z instalacji

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

## Następne kroki
- Blok 2: Instalacja i konfiguracja Docker Compose (już zainstalowane jako plugin)
- Blok 3: Security hardening i monitoring
- Blok 4: Integracja z projektem