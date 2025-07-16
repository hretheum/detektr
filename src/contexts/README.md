# Bounded Contexts

System Detektor podzielony jest na następujące bounded contexts:

## Detection Context

Odpowiedzialny za wykrywanie obiektów, twarzy i gestów w strumieniu wideo.

## Automation Context

Zarządza regułami automatyzacji i wykonywaniem akcji w odpowiedzi na zdarzenia.

## Monitoring Context

Obsługuje metryki, logi, distributed tracing i alerty systemowe.

## Integration Context

Zapewnia integrację z zewnętrznymi systemami (Home Assistant, LLM APIs).

## Management Context

Zarządza konfiguracją systemu, użytkownikami i kamerami.

Każdy context ma własną strukturę:

- `domain/` - logika biznesowa, encje, wydarzenia
- `application/` - use cases, serwisy aplikacyjne
- `infrastructure/` - implementacje repozytoriów, adaptery
