# CI/CD Setup - Instrukcje konfiguracji

## 🎯 Cel

Ten dokument opisuje jak skonfigurować automatyczne budowanie i deployment dla projektu Detektor.

## 📋 Prerequisites

### 1. GitHub Repository Secrets

Skonfiguruj następujące secrets w GitHub repo (Settings → Secrets → Actions):

```bash
NEBULA_SSH_KEY      # Klucz prywatny SSH do połączenia z serwerem Nebula
NEBULA_HOST         # Adres IP lub hostname serwera Nebula
NEBULA_USER         # Username na serwerze (np. hretheum)
SOPS_AGE_KEY        # Klucz age do odszyfrowywania sekretów SOPS
```

### 2. GitHub Container Registry

Upewnij się że repo ma uprawnienia do GHCR:
- Settings → Actions → General → Workflow permissions
- Wybierz "Read and write permissions"

### 3. Serwer Nebula setup

```bash
# Na serwerze Nebula
sudo mkdir -p /opt/detektor
sudo chown $USER:$USER /opt/detektor

# Docker network
docker network create detektor-network

# SSH key setup (add public key do ~/.ssh/authorized_keys)
```

## 🚀 Jak to działa

### Automatyczny deployment

1. **Push do main branch**:
   ```bash
   git add .
   git commit -m "feat: nowy serwis xyz"
   git push origin main
   ```

2. **GitHub Actions automatycznie**:
   - Buduje wszystkie service images
   - Publikuje do `ghcr.io/hretheum/detektr/`
   - Deployuje na serwer Nebula (jeśli enabled)

### Manual deployment

```bash
# Deploy z lokalnego środowiska
./scripts/deploy-to-nebula.sh

# Deploy konkretnego serwisu
ssh nebula "cd /opt/detektor && docker-compose up -d example-otel"
```

## 🔧 Workflow Files

### `.github/workflows/deploy.yml`
- **Trigger**: push na main, manual dispatch
- **Buduje**: wszystkie serwisy równolegle
- **Publikuje**: do GitHub Container Registry
- **Deploy**: automatyczny na Nebula (configurable)

### `scripts/deploy-to-nebula.sh`
- Pull images z registry
- Decrypt secrets (.env)
- Update docker-compose files
- Rolling restart services
- Health checks

### `scripts/health-check-all.sh`
- Weryfikuje wszystkie endpoints
- Sprawdza status kontenerów
- GPU monitoring

## 📊 Monitoring

Po deployment sprawdź:

```bash
# Health check wszystkich serwisów
ssh nebula "/opt/detektor/scripts/health-check-all.sh"

# Logi konkretnego serwisu
ssh nebula "cd /opt/detektor && docker-compose logs example-otel"

# Status wszystkich kontenerów
ssh nebula "docker ps | grep detektor"
```

## 🐛 Troubleshooting

### Build fails w GitHub Actions

1. Sprawdź czy Dockerfile istnieje w `services/[service-name]/`
2. Sprawdź permissions do GHCR
3. Zobacz logs w Actions tab

### Deploy fails na Nebula

1. Sprawdź SSH connectivity:
   ```bash
   ssh nebula "echo 'SSH OK'"
   ```

2. Sprawdź czy images są dostępne:
   ```bash
   ssh nebula "docker pull ghcr.io/hretheum/detektr/example-otel:latest"
   ```

3. Sprawdź secrets:
   ```bash
   ssh nebula "cd /opt/detektor && ls -la .env"
   ```

### Service nie startuje

1. Sprawdź logi:
   ```bash
   ssh nebula "cd /opt/detektor && docker-compose logs [service-name]"
   ```

2. Sprawdź health endpoint:
   ```bash
   ssh nebula "curl -f http://localhost:800X/health"
   ```

3. Sprawdź czy network istnieje:
   ```bash
   ssh nebula "docker network ls | grep detektor"
   ```

## 💡 Best Practices

### Dla nowych serwisów

1. **Copy template**:
   ```bash
   cp -r services/base-template services/new-service
   ```

2. **Update Dockerfile** - sprawdź czy base image jest OK

3. **Dodaj do deploy.yml** - matrix strategy

4. **Test lokalnie**:
   ```bash
   docker build -f services/new-service/Dockerfile .
   ```

5. **Commit i push** - automatyczny deployment

### Secrets management

- **NIGDY** nie commituj `.env.decrypted`
- Używaj `sops .env` do edycji
- Wszystkie nowe sekrety dodawaj do SOPS
- Test decryption przed deployment

### Image optimization

- Używaj multi-stage builds
- Pin versions w requirements.txt
- Use official base images (python:3.11-slim)
- Minimize layers

## 🔄 Rollback procedure

```bash
# 1. Zatrzymaj problematyczny serwis
ssh nebula "cd /opt/detektor && docker-compose down [service-name]"

# 2. Pull poprzednią wersję
ssh nebula "docker pull ghcr.io/hretheum/detektr/[service]:previous-tag"

# 3. Update tag w docker-compose.yml (manual edit)

# 4. Restart
ssh nebula "cd /opt/detektor && docker-compose up -d [service-name]"
```

## 📞 Support

- GitHub Issues: problemy z CI/CD
- Logi w GitHub Actions
- SSH na Nebula dla runtime issues
