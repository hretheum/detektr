# Status Konsolidacji Workflows - Faza 2

## ✅ FAZA 2 COMPLETED (2025-07-23)

### Wykonane zmiany

#### 1. Redukcja workflows
- **Przed**: 14 plików workflow
- **Po**: 5 plików workflow
- **Redukcja**: -64%

#### 2. Nowa struktura workflows

##### main-pipeline.yml
- **Zastępuje**: deploy-self-hosted.yml, deploy-only.yml, manual-service-build.yml, db-deploy.yml
- **Funkcje**: Build, deploy, lub oba
- **Użycie**:
  ```bash
  # Domyślnie: build + deploy
  gh workflow run main-pipeline.yml

  # Tylko build
  gh workflow run main-pipeline.yml -f action=build-only

  # Tylko deploy
  gh workflow run main-pipeline.yml -f action=deploy-only

  # Wybrane serwisy
  gh workflow run main-pipeline.yml -f services=rtsp-capture,frame-tracking
  ```

##### pr-checks.yml (rozszerzony)
- **Zastępuje**: ci.yml + stary pr-checks.yml
- **Funkcje**:
  - Walidacja tytułu PR
  - Etykiety rozmiaru
  - Przegląd zależności
  - Testy Python (wszystkie serwisy)
  - Testy budowania Docker
- **Użycie**: Automatyczne na każdym PR

##### manual-operations.yml
- **Zastępuje**: cleanup-runner.yml, test-runner.yml, diagnostic.yml
- **Funkcje**: Cleanup, diagnostyka, backup, migracje DB
- **Użycie**:
  ```bash
  # Cleanup docker
  gh workflow run manual-operations.yml -f operation=cleanup-docker

  # Test runner
  gh workflow run manual-operations.yml -f operation=test-runner

  # Diagnostyka
  gh workflow run manual-operations.yml -f operation=diagnostic
  ```

##### scheduled-tasks.yml
- **Zastępuje**: build-gpu-base.yml (schedule), security.yml
- **Funkcje**:
  - Codzienne: Cleanup (2 AM UTC)
  - Tygodniowe: Rebuild obrazów (niedziela 3 AM UTC)
  - Miesięczne: Skan bezpieczeństwa (1. dzień 4 AM UTC)
- **Użycie**: Automatyczne lub manualne

##### release.yml
- **Status**: Bez zmian (już dobrze zorganizowany)

### Narzędzia migracji

#### scripts/migrate-workflows.sh
- Automatyczny backup starych workflows
- Przeniesienie do .github/workflows/deprecated/
- Aktualizacja referencji w README
- Generowanie przewodnika migracji

### Weryfikacja

```bash
# Sprawdzenie liczby workflows
ls -1 .github/workflows/*.yml | wc -l
# Wynik: 5 (plus stare w deprecated/)

# Test nowego main pipeline
gh workflow run main-pipeline.yml -f action=build-only -f services=example-otel

# Test manual operations
gh workflow run manual-operations.yml -f operation=test-runner
```

### Następne kroki
- ✅ Dokumentacja zsynchronizowana
- ⏳ FAZA 3: Reorganizacja Docker Compose
