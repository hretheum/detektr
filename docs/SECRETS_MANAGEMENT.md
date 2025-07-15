# Zarządzanie Sekretami w Projekcie Detektor

## 🔐 Używamy SOPS z age

Ten projekt używa [SOPS](https://github.com/mozilla/sops) (Secrets OPerationS) z [age](https://github.com/FiloSottile/age) do bezpiecznego zarządzania sekretami.

## Szybki Start

### 1. Instalacja narzędzi

```bash
# macOS
brew install sops age

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install age
# SOPS: pobierz binary z https://github.com/mozilla/sops/releases
```

### 2. Generowanie klucza age

```bash
# Wygeneruj parę kluczy (wykonaj RAZ)
age-keygen -o ~/.config/sops/age/keys.txt

# Wyświetl swój klucz publiczny
age-keygen -y ~/.config/sops/age/keys.txt
```

**WAŻNE**: 
- Klucz prywatny (`keys.txt`) - NIGDY nie commituj!
- Klucz publiczny (zaczyna się od `age1...`) - możesz bezpiecznie udostępniać

### 3. Konfiguracja projektu

1. Skopiuj swój klucz publiczny
2. Edytuj `.sops.yaml` i zamień `AGE-PUBLIC-KEY-HERE` na swój klucz:
   ```yaml
   creation_rules:
     - path_regex: \.env$
       age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
   ```

### 4. Praca z sekretami

#### Pierwsze użycie - stwórz .env z .env.example:
```bash
cp .env.example .env
# Edytuj .env i wypełnij prawdziwymi wartościami
```

#### Szyfrowanie pliku .env:
```bash
# Opcja 1: Edytuj bezpośrednio (SOPS otworzy edytor)
sops .env

# Opcja 2: Zaszyfruj istniejący plik
sops -e .env > .env.encrypted
mv .env.encrypted .env
```

#### Odszyfrowanie do użycia:
```bash
# Wyświetl odszyfrowaną zawartość
sops -d .env

# Zapisz odszyfrowany plik (np. dla docker-compose)
sops -d .env > .env.decrypted
# Pamiętaj usunąć po użyciu!
```

#### Edycja zaszyfrowanego pliku:
```bash
# SOPS automatycznie odszyfruje, otworzy edytor, i zaszyfruje po zapisaniu
sops .env
```

## 📁 Struktura plików

```
.env.example    # Template z przykładowymi wartościami (commituj)
.env            # Zaszyfrowany plik z sekretami (commituj)
.env.decrypted  # Tymczasowy odszyfrowany plik (NIE commituj)
.sops.yaml      # Konfiguracja SOPS (commituj)
~/.config/sops/age/keys.txt  # Twój klucz prywatny (NIE commituj!)
```

## 🤝 Współpraca zespołowa

### Dodawanie nowego członka zespołu:

1. Poproś o klucz publiczny age
2. Dodaj klucz do `.sops.yaml`:
   ```yaml
   age: >-
     age1klucz-osoby-1,
     age1klucz-osoby-2
   ```
3. Re-encrypt wszystkie pliki:
   ```bash
   sops updatekeys .env
   ```

### Dołączanie do projektu:

1. Wygeneruj klucze: `age-keygen -o ~/.config/sops/age/keys.txt`
2. Wyślij klucz publiczny do team lead
3. Po dodaniu do `.sops.yaml` możesz odszyfrować pliki

## 🐳 Integracja z Docker

### Development:
```bash
# Odszyfruj przed uruchomieniem
sops -d .env > .env.decrypted
docker-compose --env-file .env.decrypted up
rm .env.decrypted  # Usuń po użyciu!
```

### Automatyzacja (Makefile):
```makefile
.PHONY: up down

up:
	@sops -d .env > .env.decrypted
	@docker-compose --env-file .env.decrypted up -d
	@rm .env.decrypted

down:
	@docker-compose down
```

## 🚨 Bezpieczeństwo

### Co robić:
- ✅ Commituj zaszyfrowane pliki `.env`
- ✅ Używaj silnych, unikalnych wartości dla każdego sekretu
- ✅ Regularnie rotuj klucze API
- ✅ Używaj różnych sekretów dla dev/staging/prod

### Czego NIE robić:
- ❌ NIE commituj odszyfrowanych plików
- ❌ NIE commituj klucza prywatnego age
- ❌ NIE używaj słabych haseł "na szybko"
- ❌ NIE dziel się kluczem prywatnym

## 🆘 Troubleshooting

### "Failed to get the data key required to decrypt"
- Sprawdź czy masz klucz prywatny: `ls ~/.config/sops/age/keys.txt`
- Sprawdź czy Twój klucz publiczny jest w `.sops.yaml`

### "Could not load age keys"
```bash
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
```

### Zgubiłem klucz prywatny
- Poproś kogoś z zespołu o odszyfrowanie i re-encrypt z nowym kluczem
- Bez klucza prywatnego nie odszyfrujesz plików!

## 📚 Więcej informacji

- [SOPS Documentation](https://github.com/mozilla/sops)
- [age Documentation](https://github.com/FiloSottile/age)
- [SOPS z Docker](https://github.com/mozilla/sops#encrypting-using-docker)