# Faza 1 / Zadanie 3: Setup repozytorium Git z podstawową strukturą

## Cel zadania
Utworzenie kompletnej struktury repozytorium zgodnej z Clean Architecture, konfiguracja CI/CD oraz pre-commit hooks dla zachowania jakości kodu od samego początku projektu.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[x] Weryfikacja dostępu do Git i GitHub**
   - **Metryka**: Git zainstalowany, SSH keys skonfigurowane
   - **Walidacja**: 
     ```bash
     git --version && ssh -T git@github.com
     # Powinno zwrócić wersję git i "Hi username! You've successfully authenticated"
     ```
   - **Czas**: 0.5h

2. **[x] Weryfikacja narzędzi developerskich**
   - **Metryka**: Python 3.11+, pre-commit, poetry/pip-tools zainstalowane
   - **Walidacja**: 
     ```bash
     python --version | grep -E "3\.(11|12)" && pre-commit --version
     ```
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Struktura katalogów Clean Architecture

#### Zadania atomowe:
1. **[ ] Utworzenie głównej struktury katalogów**
   - **Metryka**: Struktura zgodna z DDD i Clean Architecture utworzona
   - **Walidacja**: 
     ```bash
     tree -d -L 3 | grep -E "(domain|infrastructure|application|interfaces)" | wc -l
     # Powinno zwrócić >= 20 katalogów
     ```
   - **Czas**: 1h

2. **[ ] Utworzenie struktury dla bounded contexts**
   - **Metryka**: 5 contexts (monitoring, detection, management, automation, integration)
   - **Walidacja**: 
     ```bash
     ls -1 src/contexts/ | wc -l
     # Powinno zwrócić 5
     ```
   - **Czas**: 1.5h

3. **[ ] Konfiguracja Python packages z __init__.py**
   - **Metryka**: Wszystkie katalogi są prawidłowymi Python packages
   - **Walidacja**: 
     ```bash
     find src -type d -not -path '*/\.*' -exec test -f {}/__init__.py \; -print | wc -l
     # Liczba powinna odpowiadać liczbie katalogów w src/
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Struktura katalogów zgodna z wzorcem z architektura_systemu.md
- Każdy bounded context ma layers: domain, application, infrastructure
- Python imports działają poprawnie między modułami

### Blok 2: Konfiguracja CI/CD z GitHub Actions

#### Zadania atomowe:
1. **[ ] Utworzenie workflow dla CI**
   - **Metryka**: .github/workflows/ci.yml z test, lint, type-check jobs
   - **Walidacja**: 
     ```bash
     gh workflow list | grep "CI"
     # Powinno pokazać workflow CI
     ```
   - **Czas**: 1.5h

2. **[ ] Konfiguracja Docker build w CI**
   - **Metryka**: Build wszystkich serwisów w CI pipeline
   - **Walidacja**: 
     ```bash
     # Po pushu do GitHub
     gh run list --limit 1 | grep "CI.*completed.*success"
     ```
   - **Czas**: 1h

3. **[ ] Setup code coverage i quality gates**
   - **Metryka**: Coverage >80% required, codecov integration
   - **Walidacja**: 
     ```bash
     # W .github/workflows/ci.yml
     grep -E "(codecov|coverage)" .github/workflows/ci.yml
     ```
   - **Czas**: 1h

#### Metryki sukcesu bloku:
- CI pipeline przechodzi dla initial commit
- Coverage report generowany automatycznie
- Build time <5 minut

### Blok 3: Pre-commit hooks i code quality

#### Zadania atomowe:
1. **[ ] Konfiguracja pre-commit z Python linters**
   - **Metryka**: black, isort, flake8, mypy skonfigurowane
   - **Walidacja**: 
     ```bash
     pre-commit run --all-files
     # Wszystkie hooki powinny przejść
     ```
   - **Czas**: 1h

2. **[ ] Dodanie security scanning (bandit, safety)**
   - **Metryka**: Skanowanie security w pre-commit
   - **Walidacja**: 
     ```bash
     pre-commit run bandit --all-files && pre-commit run safety --all-files
     ```
   - **Czas**: 0.5h

3. **[ ] Konfiguracja commit message validation**
   - **Metryka**: Conventional commits enforced
   - **Walidacja**: 
     ```bash
     echo "test: bad message" | commitlint
     # Powinno zwrócić błąd
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Pre-commit automatycznie instaluje się przy pierwszym commicie
- Wszystkie pliki Python przechodzą linting
- Commit messages follow conventional format

### Blok 4: Dokumentacja i tooling setup

#### Zadania atomowe:
1. **[ ] Utworzenie głównych plików dokumentacji**
   - **Metryka**: README.md, CONTRIBUTING.md, ARCHITECTURE.md utworzone
   - **Walidacja**: 
     ```bash
     ls -1 *.md | grep -E "(README|CONTRIBUTING|ARCHITECTURE)" | wc -l
     # Powinno zwrócić 3
     ```
   - **Czas**: 1h

2. **[ ] Setup MkDocs dla dokumentacji**
   - **Metryka**: MkDocs skonfigurowany z material theme
   - **Walidacja**: 
     ```bash
     mkdocs build && ls -la site/index.html
     ```
   - **Czas**: 1h

3. **[ ] Utworzenie Makefile z common tasks**
   - **Metryka**: Make targets dla: test, lint, run, build
   - **Walidacja**: 
     ```bash
     make help | grep -E "(test|lint|run|build)" | wc -l
     # Powinno zwrócić >= 4
     ```
   - **Czas**: 0.5h

#### Metryki sukcesu bloku:
- Dokumentacja builduje się bez błędów
- Makefile upraszcza common operations
- README zawiera quick start guide

## Całościowe metryki sukcesu zadania

1. **Struktura**: Clean Architecture z 5 bounded contexts
2. **CI/CD**: Automated pipeline z <5min build time
3. **Quality**: Pre-commit hooks enforce standards
4. **Documentation**: Auto-generated docs site

## Deliverables

1. `/.github/workflows/ci.yml` - CI pipeline configuration
2. `/.pre-commit-config.yaml` - Pre-commit hooks setup
3. `/src/contexts/*/` - 5 bounded contexts struktura
4. `/Makefile` - Developer convenience commands
5. `/mkdocs.yml` - Documentation configuration
6. `/README.md` - Project overview and quick start
7. `/CONTRIBUTING.md` - Development guidelines
8. `/ARCHITECTURE.md` - System architecture overview

## Narzędzia

- **Git**: Version control
- **GitHub Actions**: CI/CD platform
- **pre-commit**: Git hooks framework
- **MkDocs + Material**: Documentation site generator
- **Make**: Task automation

## Zależności

- **Wymaga**: Zadanie 1 (Docker) i 2 (NVIDIA Toolkit) ukończone
- **Blokuje**: Wszystkie kolejne zadania development

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| CI pipeline timeout z powodu wolnych testów | Średnie | Średni | Parallel test execution, test optimization | Build time >3 min |
| Pre-commit hooks spowalniają development | Niskie | Niski | Możliwość skip z --no-verify | Skargi developerów |
| Konflikty w strukturze katalogów | Niskie | Wysoki | Review struktura przed implementacją | Import errors |

## Rollback Plan

1. **Detekcja problemu**: CI builds failing, pre-commit blocking work
2. **Kroki rollback**:
   - [ ] Disable failing GitHub Actions workflow
   - [ ] Remove pre-commit hooks tymczasowo
   - [ ] Revert do prostszej struktury jeśli needed
3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-observability-stack.md](./04-observability-stack.md)