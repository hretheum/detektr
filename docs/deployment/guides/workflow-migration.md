# 🔄 Workflow Migration Guide

> **Status**: ✅ Migracja zakończona (Faza 2)

## 📋 Przegląd zmian

### Przed migracją (14 workflows)
```
├── rtsp-capture-deploy.yml
├── frame-buffer-deploy.yml
├── frame-tracking-deploy.yml
├── metadata-storage-deploy.yml
├── base-template-deploy.yml
├── echo-service-deploy.yml
├── cleanup-runner.yml
├── test-runner.yml
├── diagnostic.yml
├── backup.yml
├── daily-cleanup.yml
├── weekly-rebuild.yml
├── security-scan.yml
└── ghcr-cleanup.yml
```

### Po migracji (5 workflows)
```
├── main-pipeline.yml      # Główny CI/CD pipeline
├── pr-checks.yml          # Walidacja PR
├── manual-operations.yml  # Operacje manualne
├── scheduled-tasks.yml    # Zadania cykliczne
└── release.yml           # Zarządzanie wersjami
```

## 🚀 Nowe funkcjonalności

### 1. Smart Service Detection
```yaml
# main-pipeline.yml automatycznie wykrywa zmienione serwisy
- name: Detect changed services
  id: changes
  uses: dorny/paths-filter@v2
  with:
    filters: |
      rtsp-capture:
        - 'services/rtsp-capture/**'
      frame-buffer:
        - 'services/frame-buffer/**'
```

### 2. Równoległe budowanie
```yaml
# Wszystkie serwisy budują się równocześnie
strategy:
  matrix:
    service: ${{ fromJson(needs.detect-changes.outputs.services) }}
  max-parallel: 10
```

### 3. Unified dispatch
```yaml
# Jeden workflow, wiele opcji
workflow_dispatch:
  inputs:
    action:
      type: choice
      options:
        - build-and-deploy
        - build-only
        - deploy-only
    services:
      description: 'Comma-separated list of services'
```

## 📝 Mapowanie starych komend

### Deploy serwisu
```bash
# Stare
gh workflow run rtsp-capture-deploy.yml

# Nowe
gh workflow run main-pipeline.yml -f services=rtsp-capture
# lub po prostu
git push origin main
```

### Cleanup
```bash
# Stare
gh workflow run cleanup-runner.yml

# Nowe
gh workflow run manual-operations.yml -f operation=cleanup-docker
```

### Daily tasks
```bash
# Stare
gh workflow run daily-cleanup.yml

# Nowe (automatyczne o 2:00 UTC)
# lub manualnie:
gh workflow run scheduled-tasks.yml -f task=daily-cleanup
```

### GHCR cleanup
```bash
# Stare
gh workflow run ghcr-cleanup.yml

# Nowe (zintegrowane w scheduled-tasks)
gh workflow run scheduled-tasks.yml -f task=ghcr-cleanup
```

## 🔧 Migracja konfiguracji

### 1. Aktualizacja dokumentacji
```bash
# Zmień referencje do workflows
sed -i 's/\.github\/workflows\/.*-deploy\.yml/main-pipeline.yml/g' docs/**/*.md
```

### 2. Aktualizacja skryptów
```bash
# Jeśli masz skrypty wywołujące workflows
# Zmień np.:
gh workflow run frame-buffer-deploy.yml
# Na:
gh workflow run main-pipeline.yml -f services=frame-buffer
```

### 3. Aktualizacja CI/CD badges
```markdown
<!-- Stare -->
![Deploy](https://github.com/hretheum/detektr/workflows/rtsp-capture-deploy/badge.svg)

<!-- Nowe -->
![CI/CD](https://github.com/hretheum/detektr/workflows/main-pipeline/badge.svg)
```

## ⚡ Korzyści z migracji

1. **Szybsze deploye** - równoległe budowanie
2. **Mniej duplikacji** - wspólna logika w jednym miejscu
3. **Łatwiejsze utrzymanie** - 5 plików zamiast 14
4. **Elastyczność** - łatwe dodawanie nowych serwisów
5. **Spójność** - jeden standard dla wszystkich operacji

## 🆘 Troubleshooting

### Problem: Workflow nie widzi mojego serwisu
```yaml
# Dodaj serwis do main-pipeline.yml w sekcji paths-filter
frame-processor:
  - 'services/frame-processor/**'
  - 'docker/base/docker-compose.yml'
```

### Problem: Chcę zbudować wszystkie serwisy
```bash
# Użyj all jako wartości
gh workflow run main-pipeline.yml -f services=all
```

### Problem: Deploy specific version
```bash
# Użyj deploy-only z konkretnym tagiem
gh workflow run main-pipeline.yml \
  -f action=deploy-only \
  -f services=rtsp-capture \
  -f version=v1.2.3
```

## 📚 Dodatkowe zasoby

- [Main Pipeline Documentation](.github/workflows/main-pipeline.yml)
- [PR Checks Documentation](.github/workflows/pr-checks.yml)
- [Manual Operations Guide](./manual-operations.md)
- [Scheduled Tasks Guide](./scheduled-tasks.md)
