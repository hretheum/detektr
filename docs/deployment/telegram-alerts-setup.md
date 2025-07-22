# Konfiguracja alertów Telegram dla Detektor

## Przygotowanie

### 1. Utworzenie bota Telegram

1. Otwórz Telegram i znajdź **@BotFather**
2. Wyślij komendę `/newbot`
3. Podaj nazwę bota (np. "Detektor Alert Bot")
4. Podaj username bota (musi kończyć się na `bot`, np. `detektor_alert_bot`)
5. Zapisz otrzymany **token** (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Uzyskanie Chat ID

1. Dodaj swojego bota do grupy lub napisz do niego prywatnie
2. Wyślij dowolną wiadomość
3. Otwórz w przeglądarce:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Znajdź `"chat":{"id":` - to jest twój Chat ID (może być ujemny dla grup)

## Konfiguracja na serwerze

### 1. Dodaj zmienne do .env

```bash
# Na serwerze Nebula
cd /opt/detektor

# Edytuj plik .env (zaszyfrowany SOPS)
sops .env

# Dodaj:
TELEGRAM_BOT_TOKEN=your_actual_bot_token
TELEGRAM_CHAT_ID=your_actual_chat_id
```

### 2. Deploy Telegram Alerts

```bash
# Build image lokalnie (opcjonalnie)
docker build -t telegram-alerts services/telegram-alerts/

# Lub użyj docker-compose
docker compose -f services/telegram-alerts/docker-compose.telegram.yml up -d
```

## Monitorowane metryki

### 1. Przestrzeń dyskowa
- Alert gdy użycie > 80%
- Monitorowane partycje:
  - `/` - system
  - `/data/redis` - Redis persistence
  - `/data/postgres` - PostgreSQL data
  - `/data/frames` - Frame storage

### 2. Pamięć Redis
- Alert gdy użycie > 3.5GB (z 4GB limitu)
- Pokazuje peak usage

### 3. Kontenery Docker
- Alert gdy kontener nie działa
- Alert gdy restart count > 5
- Automatyczne powiadomienie o recovery

## Przykładowe alerty

```
🚨 Detektor Alert

📁 Disk Alert: /data/postgres
Usage: 82.5% (82GB / 100GB)
Free: 18GB
```

```
🚨 Detektor Alert

🔴 Redis Memory Alert
Used: 3.75GB / 3.5GB limit
Peak: 3.9GB
```

```
🚨 Detektor Alert

🐳 Container Down: detektor-rtsp-capture-1
Status: exited
```

## Dostosowanie alertów

### Zmiana progów w docker-compose:

```yaml
environment:
  DISK_ALERT_THRESHOLD: 90  # Alert przy 90% zamiast 80%
  REDIS_MEMORY_THRESHOLD_GB: 3.8  # Alert przy 3.8GB
  POSTGRES_DISK_THRESHOLD_GB: 90  # Alert przy 90GB
```

### Zmiana częstotliwości sprawdzania

W `telegram-monitor.py`, linia ~195:
```python
await asyncio.sleep(300)  # Zmień na inną wartość (sekundy)
```

## Testowanie

### Test ręczny:
```bash
# Wyślij testową wiadomość
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"${TELEGRAM_CHAT_ID}\", \"text\": \"Test alert from Detektor\"}"
```

### Sprawdzenie logów:
```bash
docker logs detektor-telegram-alerts
```

## Troubleshooting

### Bot nie wysyła wiadomości
1. Sprawdź token i chat ID
2. Upewnij się, że bot jest członkiem grupy
3. Sprawdź logi: `docker logs detektor-telegram-alerts`

### Zbyt dużo alertów
1. Zwiększ progi alertów
2. Zwiększ histerezę (różnica między alertem a normalizacją)
3. Wydłuż interwał sprawdzania

### Monitor nie widzi kontenerów
1. Sprawdź montowanie `/var/run/docker.sock`
2. Upewnij się, że kontener ma odpowiednie uprawnienia
