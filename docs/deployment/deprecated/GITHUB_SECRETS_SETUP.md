# GitHub Secrets Setup - WYMAGANE DLA CI/CD

## 🚨 KRYTYCZNE - BEZ TEGO CI/CD NIE DZIAŁA!

Workflow GitHub Actions wymaga następujących sekretów do poprawnego działania.

## Krok po kroku

1. **Otwórz GitHub Repository Settings**:
   ```
   https://github.com/hretheum/detektr/settings/secrets/actions
   ```

2. **Dodaj następujące sekrety** (New repository secret):

### NEBULA_SSH_KEY
- **Opis**: Klucz prywatny SSH do połączenia z serwerem Nebula
- **Jak pobrać**:
  ```bash
  cat ~/.ssh/id_rsa  # lub inny klucz używany do SSH na Nebula
  ```
- **Format**: Cały klucz włącznie z nagłówkiem BEGIN i stopką END

### NEBULA_HOST
- **Opis**: Adres IP lub hostname serwera Nebula
- **Wartość**: np. `192.168.1.100` lub `nebula.local` lub `nebula`

### NEBULA_USER
- **Opis**: Nazwa użytkownika SSH na serwerze Nebula
- **Wartość**: np. `hretheum`

### SOPS_AGE_KEY
- **Opis**: Klucz prywatny age do deszyfrowania sekretów
- **Jak pobrać**:
  ```bash
  cat keys.txt  # w katalogu projektu
  ```
- **Format**: Cały klucz zaczynający się od `AGE-SECRET-KEY-`

## Weryfikacja

Po dodaniu sekretów:

1. **Wykonaj push do main**:
   ```bash
   git push origin main
   ```

2. **Sprawdź workflow**:
   ```bash
   gh run list --workflow=deploy.yml --limit=1
   ```

3. **Jeśli są błędy**, sprawdź logi:
   ```bash
   gh run view [RUN_ID] --log
   ```

## Troubleshooting

### Problem: SSH key authentication failed
- Upewnij się, że skopiowałeś CAŁY klucz prywatny
- Sprawdź czy klucz działa lokalnie: `ssh nebula`

### Problem: Host key verification failed
- Workflow automatycznie dodaje host do known_hosts
- Jeśli nadal nie działa, sprawdź czy NEBULA_HOST jest poprawny

### Problem: SOPS decryption failed
- Sprawdź czy skopiowałeś właściwy klucz age
- Upewnij się, że to ten sam klucz co w .sops.yaml

## Status sekretów

Możesz sprawdzić czy sekrety są ustawione:
```bash
gh secret list
```

## 🔒 Bezpieczeństwo

- GitHub szyfruje sekrety
- Są dostępne tylko podczas wykonywania workflow
- Nie są widoczne w logach (GitHub je maskuje)
- NIGDY nie loguj ich wartości!
