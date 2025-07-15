# Use Cases - System Detektor

## 1. Use Cases dla User

### Zarządzanie Konfiguracją
- **UC01**: Konfiguracja kamer
- **UC02**: Definiowanie stref detekcji
- **UC03**: Ustawianie reguł automatyzacji
- **UC04**: Zarządzanie użytkownikami

### Interakcja z Systemem
- **UC05**: Wydawanie komend głosowych
- **UC06**: Wykonywanie gestów kontrolnych
- **UC07**: Przeglądanie historii zdarzeń
- **UC08**: Otrzymywanie powiadomień

## 2. Use Cases dla System

### Przetwarzanie Wizyjne
- **UC09**: Przechwytywanie strumienia wideo
- **UC10**: Wykrywanie obiektów
- **UC11**: Rozpoznawanie twarzy
- **UC12**: Detekcja gestów
- **UC13**: Detekcja zwierząt

### Przetwarzanie Audio
- **UC14**: Rozpoznawanie mowy (STT)
- **UC15**: Synteza mowy (TTS)

### Integracje
- **UC16**: Wysyłanie zdarzeń do HA
- **UC17**: Przetwarzanie intencji (LLM)
- **UC18**: Monitorowanie wydajności

## 3. Use Cases dla Home Assistant

### Automatyzacje
- **UC19**: Sterowanie oświetleniem
- **UC20**: Zarządzanie alarmami
- **UC21**: Kontrola multimediów

## Relacje między Use Cases

### Include
- UC10 → UC11 (wykrywanie obiektów zawiera rozpoznawanie twarzy)
- UC10 → UC12 (wykrywanie obiektów zawiera detekcję gestów)
- UC10 → UC13 (wykrywanie obiektów zawiera detekcję zwierząt)
- UC05 → UC14 (komendy głosowe wymagają STT)

### Extend
- UC16 może rozszerzyć UC17 (wysyłanie zdarzeń może wymagać przetwarzania intencji)

## Diagram PlantUML
Pełny diagram dostępny w pliku: [use-cases.puml](./use-cases.puml)