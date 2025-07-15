# Faza 0 / Zadanie 2: Utworzenie struktury projektu i repozytorium

## Cel zadania
Utworzenie kompletnej struktury katalogów zgodnej z Clean Architecture, konfiguracja narzędzi developerskich, oraz setup CI/CD pipeline.

## Dekompozycja na bloki zadań

### Blok 0: Prerequisites
#### Zadania atomowe:
1. **[x] Weryfikacja narzędzi developerskich**
   - **Metryka**: Docker, docker-compose, git, python3.11+ zainstalowane
   - **Walidacja**: `docker --version && docker-compose --version && git --version && python3 --version`
   - **Czas**: 0.5h

2. **[x] Przegląd i instalacja dodatkowych narzędzi**
   - **Metryka**: pre-commit, hadolint, black, ruff zainstalowane
   - **Walidacja**: `pre-commit --version && hadolint --version`
   - **Czas**: 0.5h

### Blok 1: Struktura katalogów Clean Architecture

#### Zadania atomowe:
1. **[x] Utworzenie struktury głównych katalogów**
   - **Metryka**: Struktura zgodna z hexagonal architecture
   - **Walidacja**: `tree -d -L 3 . | grep -E "(domain|application|infrastructure|interfaces)"`
   - **Czas**: 1h

2. **[x] Utworzenie struktury dla każdego bounded context**
   - **Metryka**: Min. 5 contexts (detection, automation, monitoring, etc.)
   - **Walidacja**: Każdy context ma layers: domain, application, infra
   - **Czas**: 2h

3. **[x] Setup shared kernel i common libraries**
   - **Metryka**: Wspólne typy, interfejsy, utilities
   - **Walidacja**: `ls -la src/shared/`
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Struktura czytelna i skalowalna
- Separacja concerns zachowana
- Brak circular dependencies

### Blok 2: Konfiguracja Docker i docker-compose

#### Zadania atomowe:
1. **[x] Utworzenie bazowego docker-compose.yml**
   - **Metryka**: Serwisy: postgres, redis, jaeger, prometheus, grafana
   - **Walidacja**: `docker-compose config | grep -c "services:" # ≥5`
   - **Czas**: 2h

2. **[x] Konfiguracja sieci i volumes**
   - **Metryka**: Named volumes, custom bridge network
   - **Walidacja**: `docker-compose config | grep -E "(networks|volumes)"`
   - **Czas**: 1h

3. **[x] Environment files i SOPS integration**
   - **Metryka**: .env.example, .env.encrypted, docker-compose override
   - **Walidacja**: `make secrets-decrypt && docker-compose config`
   - **Czas**: 1h

4. **[x] Health checks i restart policies**
   - **Metryka**: Każdy serwis ma healthcheck i restart policy
   - **Walidacja**: `docker-compose config | grep -c "healthcheck" # ≥5`
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- `docker-compose up -d` uruchamia wszystkie serwisy
- Serwisy restartują się automatycznie
- Sekrety nie są commitowane

### Blok 3: Setup narzędzi developerskich

#### Zadania atomowe:
1. **[x] Konfiguracja pre-commit hooks**
   - **Metryka**: Hooks dla Python, YAML, Docker, secrets
   - **Walidacja**: `pre-commit run --all-files`
   - **Czas**: 2h

2. **[x] Setup linters i formatters**
   - **Metryka**: Black, isort, ruff, mypy skonfigurowane
   - **Walidacja**: `make lint`
   - **Czas**: 1h

3. **[x] Konfiguracja VS Code / IDE**
   - **Metryka**: .vscode/settings.json z recommended extensions
   - **Walidacja**: Extensions list w README
   - **Czas**: 0.5h

4. **[x] Makefile z common tasks**
   - **Metryka**: Targets: up, down, test, lint, format, clean
   - **Walidacja**: `make help`
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- Pre-commit blokuje złe commity
- Jednolity code style
- Developer experience smooth

### Blok 4: CI/CD Pipeline

#### Zadania atomowe:
1. **[x] GitHub Actions workflow dla CI**
   - **Metryka**: Lint, test, build na każdy PR
   - **Walidacja**: `.github/workflows/ci.yml` exists
   - **Czas**: 2h

2. **[x] Security scanning workflow**
   - **Metryka**: Trivy, git-secrets, SAST
   - **Walidacja**: `.github/workflows/security.yml`
   - **Czas**: 1.5h

3. **[x] Release workflow**
   - **Metryka**: Semantic versioning, changelog generation
   - **Walidacja**: `.github/workflows/release.yml`
   - **Czas**: 1h

4. **[x] Branch protection rules**
   - **Metryka**: Main branch protected, PR required
   - **Walidacja**: GitHub settings screenshot
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Green CI badge na README
- Automatyczne security scans
- Controlled release process

## Całościowe metryki sukcesu zadania

1. **Developer Experience**: Nowy developer może zacząć w <30 min
2. **Automation**: 100% powtarzalnych tasków zautomatyzowane
3. **Security**: 0 sekretów w repozytorium, scanning aktywny
4. **Quality**: Pre-commit łapie 90% problemów przed commitem

## Deliverables

1. Struktura katalogów zgodna z Clean Architecture
2. `docker-compose.yml` z podstawowymi serwisami
3. `.pre-commit-config.yaml` skonfigurowany
4. `Makefile` z common commands
5. `.github/workflows/` z CI/CD pipelines
6. `CONTRIBUTING.md` z instrukcjami dla developerów

## Narzędzia

- **Docker & docker-compose**: Containerization
- **Pre-commit**: Git hooks framework  
- **GitHub Actions**: CI/CD
- **Make**: Task automation
- **Trivy**: Security scanning

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-design-dokumenty.md](./03-design-dokumenty.md)