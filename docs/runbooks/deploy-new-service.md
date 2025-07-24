# Runbook: Deploy New Service

## Cel
Krok po kroku deployment nowego serwisu do produkcji.

## Prerequisites
- [ ] Dostęp do GitHub repo
- [ ] Klucze SSH do serwera Nebula
- [ ] Dostęp do SOPS/age keys
- [ ] Docker & Docker Compose

## Procedura

### 1. Przygotowanie serwisu

```bash
# Clone i setup
cd services/
cp -r base-template my-service
cd my-service

# Update configuration
find . -type f -exec sed -i 's/base-template/my-service/g' {} \;

# Set port (znajdź wolny)
echo "PORT=8011" >> .env.example
```

### 2. Implementacja

```bash
# Edit głównych plików
vim src/main.py
vim src/config.py
vim Dockerfile

# Dodaj testy
mkdir -p tests/unit
vim tests/unit/test_service.py
```

### 3. Lokalne testowanie

```bash
# Build
docker build -t my-service .

# Run locally
docker run -p 8011:8011 my-service

# Test endpoint
curl http://localhost:8011/health
```

### 4. Dodanie do docker-compose

```bash
# Edit base compose
vim docker/base/docker-compose.yml

# Dodaj serwis:
services:
  my-service:
    build: ./services/my-service
    image: ghcr.io/hretheum/detektr/my-service:${IMAGE_TAG:-latest}
    ports:
      - "8011:8011"
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8011/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 5. CI/CD Configuration

```bash
# Add to workflows
vim .github/workflows/main-pipeline.yml

# Dodaj w sekcji detect-changes:
my-service:
  - 'services/my-service/**'
```

### 6. Commit i Push

```bash
git add .
git commit -m "feat: add my-service with health endpoint"
git push origin feature/my-service
```

### 7. Create PR

```bash
gh pr create --title "feat: Add my-service" \
  --body "## Summary
- New service for X functionality
- Health endpoint at /health
- Port 8011

## Test plan
- [x] Local tests pass
- [x] Docker build successful
- [ ] Integration tests
"
```

### 8. Deployment

Po merge do main:
```bash
# Automatyczny deployment przez CI/CD
# Lub manual:
./scripts/deploy.sh production deploy

# Verify
./scripts/deploy.sh production verify
curl http://nebula:8011/health
```

### 9. Monitoring

```bash
# Check logs
./scripts/deploy.sh production logs my-service

# Grafana dashboard
open http://nebula:3000/d/service-overview

# Jaeger traces
open http://nebula:16686/search?service=my-service
```

## Rollback

Jeśli coś pójdzie źle:

```bash
# Quick rollback
docker compose stop my-service
docker compose rm -f my-service

# Full rollback
git revert HEAD
git push origin main
# CI/CD automatically redeploys
```

## Checklist

- [ ] Service builds locally
- [ ] Health endpoint works
- [ ] Tests pass
- [ ] Added to docker-compose
- [ ] CI/CD configured
- [ ] PR approved
- [ ] Deployed to production
- [ ] Monitoring configured
- [ ] Documentation updated

## Troubleshooting

### Service nie startuje
```bash
docker logs detektor-my-service-1
docker exec -it detektor-my-service-1 bash
```

### Port conflict
```bash
netstat -tulpn | grep 8011
# Zmień port w docker-compose
```

### Health check failing
```bash
docker exec detektor-my-service-1 curl localhost:8011/health
# Check network
docker network inspect detektor-network
```
