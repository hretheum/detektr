# 📦 GitHub Container Registry Structure

> **Status**: ✅ Ujednolicona struktura po Fazie 4

## 🏗️ Struktura Registry

### Obecna struktura (po migracji)
```
ghcr.io/hretheum/detektr/
├── base-processor           # Bazowy framework dla procesorów
├── base-template           # Template dla nowych serwisów
├── echo-service            # Serwis echo do testów
├── example-otel            # Przykład z OpenTelemetry
├── frame-buffer            # Bufor ramek
├── frame-tracking          # Śledzenie obiektów
├── metadata-storage        # Przechowywanie metadanych
├── rtsp-capture            # Przechwytywanie RTSP
└── [future-services]       # Przyszłe serwisy
```

### Poprzednia struktura (deprecated)
```
ghcr.io/hretheum/consensus/  # Stare obrazy - do usunięcia
```

## 📋 Naming Convention

### Format nazw
```
ghcr.io/hretheum/detektr/[service-name]:[tag]
```

### Przykłady
```bash
# Latest version
ghcr.io/hretheum/detektr/rtsp-capture:latest

# Specific version
ghcr.io/hretheum/detektr/rtsp-capture:v1.2.3

# Git SHA
ghcr.io/hretheum/detektr/rtsp-capture:sha-abc123

# Branch build
ghcr.io/hretheum/detektr/rtsp-capture:feature-xyz
```

## 🏷️ Tagging Strategy

### Automatic tags
1. **latest** - Zawsze wskazuje na najnowszy build z main
2. **sha-[7-chars]** - Automatyczny tag z Git SHA
3. **pr-[number]** - Dla Pull Requests (nie pushowane do registry)

### Manual tags
1. **v[major].[minor].[patch]** - Semantic versioning
2. **stable** - Ostatnia stabilna wersja
3. **dev** - Development build

## 🔄 Lifecycle Management

### Retention Policy (z scheduled-tasks.yml)
```yaml
retention_days: 30
keep_last_versions: 5
protected_tags:
  - latest
  - stable
  - v*.*.*
```

### Cleanup Schedule
- **Kiedy**: Każda niedziela 4:00 UTC
- **Co**: Usuwa obrazy starsze niż 30 dni
- **Wyjątki**: Zachowuje ostatnie 5 wersji i chronione tagi

## 📡 Registry Operations

### List all images
```bash
# Via GitHub CLI
gh api "/users/hretheum/packages?package_type=container" \
  | jq -r '.[] | select(.name | startswith("detektr/")) | .name'

# Via Docker
docker search ghcr.io/hretheum/detektr/ --limit 100
```

### Get image details
```bash
# Specific service versions
gh api "/users/hretheum/packages/container/detektr%2Frtsp-capture/versions" \
  | jq '.[0:5] | .[] | {tags: .metadata.container.tags, created: .created_at}'

# Image size
docker manifest inspect ghcr.io/hretheum/detektr/rtsp-capture:latest \
  | jq '.config.size'
```

### Pull specific version
```bash
# Latest
docker pull ghcr.io/hretheum/detektr/rtsp-capture:latest

# Specific version
docker pull ghcr.io/hretheum/detektr/rtsp-capture:v1.2.3

# By SHA
docker pull ghcr.io/hretheum/detektr/rtsp-capture:sha-abc123d
```

## 🔐 Access Control

### Public packages
Wszystkie obrazy w `ghcr.io/hretheum/detektr/*` są publiczne (read-only)

### Authentication for push
```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push image
docker push ghcr.io/hretheum/detektr/my-service:latest
```

### Repository permissions
- **Read**: Public
- **Write**: Repository contributors
- **Delete**: Repository admins + automated cleanup

## 🛠️ Manual Operations

### Force cleanup
```bash
# Dry run
gh workflow run scheduled-tasks.yml \
  -f task=ghcr-cleanup \
  -f dry_run=true

# Actual cleanup
gh workflow run scheduled-tasks.yml \
  -f task=ghcr-cleanup \
  -f dry_run=false
```

### Delete specific version
```bash
# Get version ID
VERSION_ID=$(gh api \
  "/users/hretheum/packages/container/detektr%2Frtsp-capture/versions" \
  | jq -r '.[] | select(.metadata.container.tags[] == "old-tag") | .id')

# Delete version
gh api -X DELETE \
  "/users/hretheum/packages/container/detektr%2Frtsp-capture/versions/$VERSION_ID"
```

### Migrate old images
```bash
# Pull from old registry
docker pull ghcr.io/hretheum/consensus/service:tag

# Tag for new registry
docker tag ghcr.io/hretheum/consensus/service:tag \
  ghcr.io/hretheum/detektr/service:tag

# Push to new registry
docker push ghcr.io/hretheum/detektr/service:tag
```

## 📊 Registry Monitoring

### Check space usage
```bash
# Total packages
gh api "/users/hretheum/packages?package_type=container" \
  | jq '. | length'

# Total versions across all packages
gh api "/users/hretheum/packages?package_type=container" \
  | jq -r '.[].name' \
  | xargs -I {} gh api "/users/hretheum/packages/container/{}/versions" \
  | jq '. | length' \
  | awk '{sum+=$1} END {print sum}'
```

### Health check
```bash
# Verify all services have latest tag
for service in rtsp-capture frame-tracking frame-buffer; do
  echo -n "$service: "
  docker manifest inspect ghcr.io/hretheum/detektr/$service:latest \
    >/dev/null 2>&1 && echo "✅" || echo "❌"
done
```

## 🔗 Integration with CI/CD

### Build and push (main-pipeline.yml)
```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    push: true
    tags: |
      ghcr.io/hretheum/detektr/${{ matrix.service }}:latest
      ghcr.io/hretheum/detektr/${{ matrix.service }}:sha-${{ steps.sha.outputs.sha_short }}
```

### Use in docker-compose
```yaml
services:
  rtsp-capture:
    image: ghcr.io/hretheum/detektr/rtsp-capture:latest
    # or specific version
    # image: ghcr.io/hretheum/detektr/rtsp-capture:v1.2.3
```

## 🚨 Troubleshooting

### Cannot pull image
```bash
# Check if image exists
docker manifest inspect ghcr.io/hretheum/detektr/service:tag

# Check network
curl -I https://ghcr.io/v2/

# Try with explicit platform
docker pull --platform linux/amd64 ghcr.io/hretheum/detektr/service:tag
```

### Push rejected
```bash
# Verify authentication
docker login ghcr.io

# Check permissions
gh api /user/packages/container/detektr%2Fservice

# Verify image name format
echo "ghcr.io/hretheum/detektr/service:tag" | \
  grep -E '^ghcr\.io/hretheum/detektr/[a-z0-9-]+:[a-z0-9.-]+$'
```
