# Analiza GitHub Workflows - Projekt Detektor

## 1. Przegląd Istniejących Workflows

### Główne Workflows (Aktywne)

#### 🚀 deploy-self-hosted.yml
**Cel**: Główny workflow CI/CD - budowanie i deployment
**Triggery**:
- Push na main
- workflow_dispatch z opcjami:
  - force_all: buduj wszystkie serwisy
  - services: wybór konkretnych serwisów
  - skip_deploy: tylko build
  - skip_build: tylko deploy
**Funkcjonalność**:
- Inteligentna detekcja zmian (tylko zmienione serwisy)
- Budowanie obrazów Docker
- Push do GitHub Container Registry
- Deploy na Nebula (self-hosted runner)

#### 🔧 deploy-only.yml
**Cel**: Szybki deployment bez budowania
**Triggery**: workflow_dispatch
**Funkcjonalność**:
- Pull istniejących obrazów
- Restart serwisów
- Health check

#### 🏗️ manual-service-build.yml
**Cel**: Ręczne budowanie pojedynczego serwisu
**Triggery**: workflow_dispatch z wyborem serwisu
**Funkcjonalność**:
- Wybór serwisu z dropdown
- Custom tagi
- Opcjonalny deploy

#### ✅ pr-checks.yml
**Cel**: Walidacja Pull Requests
**Triggery**: pull_request
**Funkcjonalność**:
- Walidacja tytułu PR (semantic)
- Dodawanie etykiet rozmiaru
- Review zależności

#### 🧪 ci.yml
**Cel**: Testy jednostkowe i integracyjne
**Triggery**: push/PR na paths: services/**
**Funkcjonalność**:
- Testy Python dla rtsp-capture
- Test build Docker

### Workflows Pomocnicze

#### 📊 db-deploy.yml
**Cel**: Deploy bazy danych (TimescaleDB, PgBouncer)
**Triggery**: push na main (paths: services/timescaledb/**, services/pgbouncer/**)
**Status**: Specjalistyczny - osobny workflow dla DB

#### 🏷️ release.yml
**Cel**: Tworzenie releases
**Triggery**: push tagów v*
**Funkcjonalność**:
- Generowanie changelog
- Tworzenie GitHub Release
- Build wszystkich serwisów z tagiem wersji
- Deploy dokumentacji

#### 🧹 cleanup-runner.yml
**Cel**: Czyszczenie przestrzeni dyskowej
**Triggery**: workflow_call, workflow_dispatch
**Status**: Pomocniczy

#### 🔍 diagnostic.yml
**Cel**: Diagnostyka problemów z workflows
**Triggery**: workflow_dispatch (disabled auto triggers)
**Status**: Narzędzie debugowania

#### 🧪 test-runner.yml
**Cel**: Test self-hosted runner
**Triggery**: workflow_dispatch
**Status**: Narzędzie testowe

#### 🛡️ security.yml
**Cel**: Skanowanie bezpieczeństwa
**Status**: **WYŁĄCZONY** (zakomentowany z powodu uprawnień SARIF)

#### 🚧 UNIFIED-deploy.yml
**Cel**: Template przyszłego zunifikowanego workflow
**Status**: **TEMPLATE** (nieaktywny, przygotowany na konsolidację)

#### 🔄 build-gpu-base.yml
**Cel**: Budowanie bazowego obrazu GPU
**Triggery**: schedule (weekly), workflow_dispatch
**Status**: Specjalistyczny - może pozostać osobno

## 2. Duplikacje Funkcjonalności

### Budowanie i Deployment
- **deploy-self-hosted.yml** - główny workflow (build + deploy)
- **manual-service-build.yml** - duplikuje budowanie pojedynczych serwisów
- **deploy-only.yml** - duplikuje część deployment
- **UNIFIED-deploy.yml** - próba konsolidacji (nieaktywna)

### Deployment
- **deploy-self-hosted.yml** - deploy wszystkich/wybranych serwisów
- **deploy-only.yml** - tylko deploy
- **db-deploy.yml** - deploy baz danych

### Testowanie
- **ci.yml** - testy jednostkowe
- **test-runner.yml** - test infrastruktury
- **diagnostic.yml** - diagnostyka workflows

## 3. Propozycja Konsolidacji

### ✅ main-pipeline.yml (Zastąpi: deploy-self-hosted.yml, manual-service-build.yml, części deploy-only.yml)
```yaml
name: Main CI/CD Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      action:
        type: choice
        options:
          - build-and-deploy
          - build-only
          - deploy-only
      services:
        description: 'Services (empty = all changed/all)'
        type: string
      force_all:
        type: boolean
      custom_tag:
        type: string

jobs:
  detect-changes:
    # Logika detekcji zmian

  build:
    if: inputs.action != 'deploy-only'
    # Budowanie obrazów

  deploy:
    if: inputs.action != 'build-only'
    # Deployment na Nebula
```

### ✅ pr-checks.yml (Pozostaje + rozszerzenie o testy z ci.yml)
```yaml
name: PR Validation & Tests

on:
  pull_request:

jobs:
  validate-pr:
    # Istniejąca walidacja

  unit-tests:
    # Przeniesione z ci.yml

  integration-tests:
    # Opcjonalne testy integracyjne
```

### ✅ manual-operations.yml (Nowy - konsoliduje pomocnicze)
```yaml
name: Manual Operations

on:
  workflow_dispatch:
    inputs:
      operation:
        type: choice
        options:
          - cleanup-runner
          - test-runner
          - diagnostic
          - deploy-database
          - build-gpu-base

jobs:
  execute:
    # Switch po wybranej operacji
```

### ✅ scheduled-tasks.yml (Nowy - wszystkie cykliczne zadania)
```yaml
name: Scheduled Tasks

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
    - cron: '0 2 * * *'  # Daily

jobs:
  weekly-gpu-base:
    if: github.event.schedule == '0 0 * * 0'
    # Build GPU base image

  daily-cleanup:
    if: github.event.schedule == '0 2 * * *'
    # Cleanup old images/cache
```

### ✅ release.yml (Pozostaje bez zmian)
- Specyficzna logika release
- Dobrze zorganizowany
- Nie wymaga konsolidacji

## 4. Workflows do Usunięcia

1. **UNIFIED-deploy.yml** - zastąpiony przez main-pipeline.yml
2. **deploy-self-hosted.yml** - funkcjonalność w main-pipeline.yml
3. **manual-service-build.yml** - funkcjonalność w main-pipeline.yml
4. **deploy-only.yml** - funkcjonalność w main-pipeline.yml
5. **ci.yml** - przeniesiony do pr-checks.yml
6. **cleanup-runner.yml** - przeniesiony do manual-operations.yml
7. **diagnostic.yml** - przeniesiony do manual-operations.yml
8. **test-runner.yml** - przeniesiony do manual-operations.yml
9. **db-deploy.yml** - przeniesiony do manual-operations.yml
10. **build-gpu-base.yml** - przeniesiony do scheduled-tasks.yml
11. **security.yml** - już wyłączony, można usunąć

## 5. Plan Migracji

### Faza 1: Przygotowanie
1. Utworzenie nowych workflows (main-pipeline.yml, manual-operations.yml, scheduled-tasks.yml)
2. Testowanie na feature branch
3. Walidacja wszystkich ścieżek wykonania

### Faza 2: Migracja
1. Merge nowych workflows do main
2. Monitorowanie przez 1-2 dni
3. Wyłączenie starych workflows (rename na .yml.backup)

### Faza 3: Cleanup
1. Po tygodniu - usunięcie starych workflows
2. Aktualizacja dokumentacji
3. Aktualizacja README w .github/workflows/

## 6. Korzyści z Konsolidacji

### Redukcja Duplikacji
- Z 14 workflows do 5
- Jednolita logika budowania i deploymentu
- Łatwiejsze utrzymanie

### Lepsze UX
- Intuicyjne nazwy i organizacja
- Mniej workflows do wyboru w Actions
- Jasna separacja: CI/CD, PR, Manual, Scheduled, Release

### Łatwiejszy Development
- Jedna lokalizacja dla głównej logiki CI/CD
- Reużywalne komponenty
- Prostsza diagnostyka problemów

## 7. Uwagi Specjalne

### deploy-self-hosted.yml
- Najważniejszy workflow - wymaga ostrożnej migracji
- Zawiera zaawansowaną logikę detekcji zmian
- Dobrze przetestowany na produkcji

### Self-hosted Runner
- Wszystkie workflows muszą wspierać [self-hosted, nebula]
- Cleanup workspace konieczny przed checkout
- Specjalne uprawnienia sudo

### Secrets Management
- SOPS dla dekrypcji .env
- Age keys na runner
- Cleanup po deployment
