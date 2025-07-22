# GitHub Actions Workflows - Projekt Detektor

## Przegląd Workflow

### 🚀 Główny Workflow Deploy
**`deploy-self-hosted.yml`** - Zoptymalizowany workflow CI/CD
- Automatycznie buduje tylko zmienione serwisy
- Wspiera ręczny wybór serwisów do budowania
- Deploy na Nebula z self-hosted runner

### 🔧 Workflow Pomocnicze

1. **`manual-service-build.yml`** - Ręczne budowanie pojedynczego serwisu
   - Wybór konkretnego serwisu z listy
   - Opcjonalny deploy po zbudowaniu
   - Custom tagi dla obrazów

2. **`monitoring.yml`** - Monitoring infrastruktury (archiwum)
3. **`rtsp-capture-ci.yml`** - CI dla RTSP capture (archiwum)

## Użycie

### Automatyczny Deploy (push do main)
```bash
git add . && git commit -m "feat: nowa funkcja" && git push origin main
```

### Ręczne Uruchomienie z Wyborem Serwisów
1. Idź do Actions → "Build and Deploy (Self-hosted) - Optimized"
2. Kliknij "Run workflow"
3. Opcje:
   - `force_all`: Buduj wszystkie serwisy
   - `services`: Lista serwisów (np. "frame-buffer,telegram-alerts")
   - `skip_deploy`: Tylko build bez deploy

### Budowanie Pojedynczego Serwisu
1. Idź do Actions → "Manual Service Build"
2. Wybierz serwis z dropdown
3. Opcjonalnie włącz deploy
4. Opcjonalnie ustaw custom tag

## Struktura Serwisów

```
services/
├── base-template/      # Bazowy template dla nowych serwisów
├── echo-service/       # Prosty echo service (test)
├── example-otel/       # Przykład z OpenTelemetry
├── frame-buffer/       # Buforowanie klatek z Redis HA
├── frame-tracking/     # Śledzenie klatek wideo
├── gpu-demo/          # Demo wykorzystania GPU
├── rtsp-capture/      # Przechwytywanie strumieni RTSP
└── telegram-alerts/   # Alerty przez Telegram
```

## Optymalizacje

### Inteligentna Detekcja Zmian
- Workflow buduje tylko serwisy które się zmieniły
- Zmiany w `base-template` triggerują rebuild serwisów zależnych
- Oszczędność czasu: ~40min → ~10min dla typowych zmian

### Cache Docker Layers
- Wykorzystanie GitHub Actions cache
- Szybsze rebuildy dzięki cache layers
- Automatyczne czyszczenie starych cache

### Równoległe Budowanie
- Matrix strategy dla równoległego budowania
- Każdy serwis budowany niezależnie
- Fail fast wyłączone - jeden błąd nie zatrzymuje pozostałych

## Rozwiązywanie Problemów

### Błąd: "Matrix vector does not contain any values"
**Przyczyna**: Brak zmian w serwisach przy push
**Rozwiązanie**: Użyj manual trigger lub zmień pliki serwisu

### Błąd: "Brakujący plik: docker-compose.yml"
**Przyczyna**: Sparse checkout nie zawiera wymaganych plików
**Rozwiązanie**: Sprawdź sekcję `sparse-checkout` w workflow

### Serwis nie buduje się automatycznie
**Przyczyna**: Paths filter nie obejmuje zmienionych plików
**Rozwiązanie**: Sprawdź filtry w `detect-changes` job

## Best Practices

1. **Commituj często, małe zmiany** - łatwiejsze śledzenie i debug
2. **Używaj manual trigger** dla testowania bez zmian kodu
3. **Monitoruj Actions tab** po push - szybkie wykrycie problemów
4. **Taguj ważne release** - łatwy rollback w razie problemów

## Sekrety i Konfiguracja

Wymagane sekrety (już skonfigurowane):
- `GITHUB_TOKEN` - automatycznie dostępny
- `SOPS_AGE_KEY` - dla dekrypcji sekretów (na Nebula runner)
