# Wymagania Funkcjonalne - System Detektor

## 1. Akwizycja i Przetwarzanie Obrazu

- **RF001**: [MUST] System musi przechwytywać strumień wideo z kamer IP przez protokół RTSP
- **RF002**: [MUST] System musi obsługiwać minimum 4 kamery jednocześnie przy 10 FPS
- **RF003**: [MUST] System musi buforować klatki wideo w kolejce do przetwarzania
- **RF004**: [MUST] System musi przypisywać unikalny tracking ID każdej klatce: `{timestamp}_{camera_id}_{sequence_number}`
- **RF005**: [SHOULD] System musi przechowywać metadane klatek w bazie danych czasowych

## 2. Detekcja i Rozpoznawanie Obiektów

- **RF006**: [MUST] System musi wykrywać obecność osób w obrazie z dokładnością >90%
- **RF007**: [MUST] System musi rozpoznawać twarze zarejestrowanych użytkowników
- **RF008**: [SHOULD] System musi wykrywać zwierzęta domowe (psy, koty) z dokładnością >85%
- **RF009**: [SHOULD] System musi identyfikować predefiniowane gesty (min. 5 gestów)
- **RF010**: [MUST] System musi działać w czasie rzeczywistym z opóźnieniem <2s

## 3. Przetwarzanie Audio

- **RF011**: [SHOULD] System musi rozpoznawać komendy głosowe w języku polskim
- **RF012**: [COULD] System musi odpowiadać głosowo używając syntezy mowy
- **RF013**: [COULD] System musi obsługiwać wake word "Detektor"
- **RF014**: [WONT] System musi rozróżniać głosy różnych użytkowników

## 4. Automatyzacje i Integracje

- **RF015**: [MUST] System musi wysyłać zdarzenia do Home Assistant przez MQTT
- **RF016**: [MUST] System musi wykonywać predefiniowane scenariusze automatyzacji
- **RF017**: [SHOULD] System musi integrować się z LLM dla zaawansowanej analizy intencji
- **RF018**: [MUST] System musi logować wszystkie zdarzenia z możliwością filtrowania

## 5. Zarządzanie i Konfiguracja

- **RF019**: [MUST] System musi umożliwiać definiowanie stref detekcji dla każdej kamery
- **RF020**: [SHOULD] System musi pozwalać na tworzenie reguł if-then-else dla automatyzacji
- **RF021**: [MUST] System musi umożliwiać zarządzanie bazą twarzy użytkowników
- **RF022**: [COULD] System musi eksportować historię zdarzeń w formacie CSV/JSON

## 6. Monitoring i Diagnostyka

- **RF023**: [MUST] System musi dostarczać metryki wydajności (CPU, GPU, RAM, latency)
- **RF024**: [SHOULD] System musi generować alerty przy przekroczeniu progów wydajności
- **RF025**: [MUST] System musi umożliwiać distributed tracing wszystkich operacji