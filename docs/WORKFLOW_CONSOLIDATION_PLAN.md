# Plan Konsolidacji Workflows - Faza 2

## Status: W TRAKCIE REALIZACJI

### Cel
Redukcja z 14 workflows do 5 skonsolidowanych workflows dla lepszego zarządzania i mniejszej duplikacji.

## Nowa Struktura Workflows

### 1. ✅ main-pipeline.yml
**Zastępuje**: deploy-self-hosted.yml, deploy-only.yml, manual-service-build.yml, db-deploy.yml
**Funkcje**:
- Główny CI/CD pipeline
- Inteligentna detekcja zmian
- Build, push i deploy serwisów
- Opcje: build-and-deploy, build-only, deploy-only
- Wsparcie dla wszystkich serwisów

### 2. ✅ pr-checks.yml (rozszerzony)
**Zastępuje**: ci.yml + istniejący pr-checks.yml
**Funkcje**:
- Walidacja tytułu PR
- Etykiety rozmiaru
- Przegląd zależności
- Testy Python (wszystkie serwisy)
- Testy budowania Docker

### 3. ✅ manual-operations.yml
**Zastępuje**: cleanup-runner.yml, test-runner.yml, diagnostic.yml
**Funkcje**:
- Czyszczenie runner/docker
- Testy runnera
- Diagnostyka
- Migracje bazy danych
- Backup/restore wolumenów
- Rebuild obrazów bazowych

### 4. ✅ scheduled-tasks.yml
**Zastępuje**: build-gpu-base.yml (schedule), security.yml, części cleanup
**Funkcje**:
- Codzienne czyszczenie (2 AM UTC)
- Tygodniowe rebuildy obrazów (niedziela 3 AM UTC)
- Miesięczne skany bezpieczeństwa (1. dzień miesiąca 4 AM UTC)
- Rotacja logów
- Sprawdzanie backupów

### 5. ✅ release.yml (bez zmian)
**Status**: Pozostaje jak jest - dobrze zorganizowany
**Funkcje**:
- Tworzenie release
- Generowanie changelog
- Tagowanie obrazów Docker
- Publikacja dokumentacji

## Mapowanie Starych Workflows

| Stary Workflow | Nowy Workflow | Jak używać |
|----------------|---------------|------------|
| ci.yml | pr-checks.yml | Automatycznie na PR |
| deploy-self-hosted.yml | main-pipeline.yml | `gh workflow run main-pipeline.yml` |
| deploy-only.yml | main-pipeline.yml | `-f action=deploy-only` |
| manual-service-build.yml | main-pipeline.yml | `-f services=service-name` |
| cleanup-runner.yml | manual-operations.yml | `-f operation=cleanup-runner` |
| test-runner.yml | manual-operations.yml | `-f operation=test-runner` |
| diagnostic.yml | manual-operations.yml | `-f operation=diagnostic` |
| db-deploy.yml | main-pipeline.yml | Automatycznie przy zmianach |
| build-gpu-base.yml | scheduled-tasks.yml | Tygodniowo lub `-f task=weekly-rebuild` |
| security.yml | scheduled-tasks.yml | Miesięcznie lub `-f task=monthly-security` |
| UNIFIED-deploy.yml | - | Usunięty (template) |

## Korzyści

1. **Redukcja złożoności**: 14 → 5 plików (-64%)
2. **Eliminacja duplikacji**: Jedna logika build/deploy
3. **Lepsze UX**: Intuicyjne nazwy i jasna organizacja
4. **Łatwiejsze utrzymanie**: Mniej miejsc do aktualizacji
5. **Zachowana funkcjonalność**: Wszystkie operacje nadal dostępne

## Implementacja

### Kroki wykonane:
1. ✅ Utworzono main-pipeline.yml
2. ✅ Rozszerzono pr-checks.yml
3. ✅ Utworzono manual-operations.yml
4. ✅ Utworzono scheduled-tasks.yml
5. ✅ Zweryfikowano release.yml
6. ✅ Utworzono skrypt migracji

### Następne kroki:
1. ⏳ Uruchomienie skryptu migracji
2. ⏳ Testowanie nowych workflows
3. ⏳ Aktualizacja dokumentacji
4. ⏳ Usunięcie starych workflows

## Użycie Skryptu Migracji

```bash
# Z katalogu głównego projektu
./scripts/migrate-workflows.sh

# Skrypt automatycznie:
# - Utworzy backup istniejących workflows
# - Przeniesie stare workflows do deprecated/
# - Zaktualizuje referencje w README
# - Utworzy przewodnik migracji
```

## Testowanie

Przed pełną migracją:
1. Utwórz branch testowy
2. Uruchom skrypt migracji
3. Przetestuj każdy nowy workflow
4. Zweryfikuj że wszystkie funkcje działają
5. Merge do main po weryfikacji
