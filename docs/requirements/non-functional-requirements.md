# Wymagania Niefunkcjonalne - System Detektor

## 1. Wymagania Wydajnościowe (Performance)

- **RNF001**: [MUST] System musi przetwarzać minimum 4 strumienie wideo @ 10 FPS jednocześnie
  - **Metryka**: 40 FPS łącznie, wykorzystanie GPU <80%
  - **Walidacja**: Load test z 4 kamerami

- **RNF002**: [MUST] Opóźnienie end-to-end (kamera → detekcja → akcja) < 2 sekundy
  - **Metryka**: P95 latency < 2000ms
  - **Walidacja**: Distributed tracing z Jaeger

- **RNF003**: [MUST] Dokładność detekcji twarzy > 90% przy dobrym oświetleniu
  - **Metryka**: Precision > 0.9, Recall > 0.9
  - **Walidacja**: Test set z 1000 oznaczonych obrazów

- **RNF004**: [SHOULD] System musi obsługiwać burst do 100 zdarzeń/sekundę
  - **Metryka**: Queue throughput > 100 msg/s
  - **Walidacja**: Stress test z generatorem zdarzeń

- **RNF005**: [SHOULD] Wykorzystanie RAM < 16GB przy standardowym obciążeniu
  - **Metryka**: RSS < 16384 MB
  - **Walidacja**: Monitoring Prometheus przez 24h

## 2. Wymagania Bezpieczeństwa (Security)

- **RNF006**: [MUST] Wszystkie sekrety zaszyfrowane (SOPS + age)
  - **Metryka**: 0 hardcoded secrets w kodzie
  - **Walidacja**: `git secrets --scan` oraz SAST

- **RNF007**: [MUST] Komunikacja z kamerami przez szyfrowane połączenie
  - **Metryka**: TLS 1.2+ dla wszystkich połączeń
  - **Walidacja**: SSL Labs test lub `testssl.sh`

- **RNF008**: [MUST] Autoryzacja dostępu do API systemu
  - **Metryka**: 100% endpointów chronione JWT/OAuth2
  - **Walidacja**: Penetration test podstawowy

- **RNF009**: [SHOULD] Izolacja kontenerów i least privilege
  - **Metryka**: Każdy kontener non-root user
  - **Walidacja**: Docker security scan

- **RNF010**: [SHOULD] Audit log wszystkich operacji administracyjnych
  - **Metryka**: 100% operacji logowane z user ID
  - **Walidacja**: Przegląd logów po test run

## 3. Wymagania Niezawodnościowe (Reliability)

- **RNF011**: [MUST] Dostępność systemu > 99.0% (8.76h downtime/rok)
  - **Metryka**: Uptime 99.0%
  - **Walidacja**: Monitoring z alertami

- **RNF012**: [MUST] MTBF (Mean Time Between Failures) > 720h (30 dni)
  - **Metryka**: Średni czas między awariami
  - **Walidacja**: Analiza logów incydentów

- **RNF013**: [SHOULD] MTTR (Mean Time To Recovery) < 30 minut
  - **Metryka**: Czas od alertu do przywrócenia
  - **Walidacja**: Chaos engineering test

- **RNF014**: [SHOULD] Automatyczny restart failed containers
  - **Metryka**: 100% kontenerów z restart policy
  - **Walidacja**: `docker-compose ps` po kill -9

- **RNF015**: [COULD] Backup konfiguracji i bazy twarzy co 24h
  - **Metryka**: Daily backup completion rate 100%
  - **Walidacja**: Restore test co tydzień

## 4. Wymagania Skalowalności i Utrzymania

- **RNF016**: [MUST] Wsparcie dla 1-8 kamer bez zmiany architektury
  - **Metryka**: Linear scaling do 8 kamer
  - **Walidacja**: Performance test z 1,2,4,8 kamerami

- **RNF017**: [MUST] Storage dla 7 dni historii zdarzeń (bez video)
  - **Metryka**: <100GB dla 7 dni @ 8 kamer
  - **Walidacja**: Projekcja na podstawie 24h testu

- **RNF018**: [SHOULD] Rolling updates bez downtime
  - **Metryka**: 0 dropped frames podczas update
  - **Walidacja**: Blue-green deployment test

- **RNF019**: [SHOULD] Horizontal scaling dla AI services
  - **Metryka**: Możliwość dodania replicas
  - **Walidacja**: Scale out/in test z load

- **RNF020**: [COULD] Multi-node deployment ready
  - **Metryka**: Działa na Docker Swarm/K8s
  - **Walidacja**: Deploy na 2-node cluster
