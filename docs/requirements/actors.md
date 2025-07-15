# Aktorzy Systemu Detektor

## User (Użytkownik)
**Opis**: Właściciel/administrator systemu, osoba konfigurująca i korzystająca z automatyzacji.

**Główne interakcje**:
- Konfiguruje kamery i strefy detekcji
- Definiuje reguły automatyzacji
- Otrzymuje powiadomienia o zdarzeniach
- Wydaje komendy głosowe
- Wykonuje gesty kontrolne
- Przegląda historię zdarzeń

## System (System Detektor)
**Opis**: Autonomiczny system przetwarzający obraz i podejmujący decyzje.

**Główne funkcje**:
- Przechwytuje strumień wideo z kamer IP
- Analizuje obraz w czasie rzeczywistym
- Wykrywa obiekty, twarze, gesty
- Rozpoznaje komendy głosowe
- Wysyła zdarzenia do kolejki
- Monitoruje własną wydajność

## Home Assistant
**Opis**: System automatyzacji domowej odbierający komendy z Detektora.

**Główne interakcje**:
- Odbiera zdarzenia przez MQTT
- Wykonuje automatyzacje (światła, muzyka, alarmy)
- Raportuje status urządzeń
- Potwierdza wykonanie akcji

## Camera (Kamera IP)
**Opis**: Urządzenie dostarczające strumień wideo.

**Charakterystyka**:
- Dostarcza strumień RTSP
- Obsługuje różne rozdzielczości
- Może mieć własną detekcję ruchu
- Wymaga uwierzytelnienia

## AI Models (Modele AI)
**Opis**: Zewnętrzne i wewnętrzne serwisy AI.

**Typy**:
- Lokalne modele (YOLO, MediaPipe, Whisper)
- Zewnętrzne API (OpenAI, Anthropic)
- Specjalizowane modele (face recognition, gesture detection)