# Faza 4 / Zadanie 1: MQTT integration with Home Assistant

## Cel zadania

Zbudować dwukierunkową integrację MQTT między systemem Detektor a Home Assistant z automatycznym odkrywaniem urządzeń i pełną obsługą stanów.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja infrastruktury MQTT**
   - **Metryka**: MQTT broker dostępny, HA MQTT integration włączona
   - **Walidacja**:

     ```bash
     # Check MQTT broker
     docker ps | grep mosquitto
     mosquitto_sub -h localhost -p 1883 -t '$SYS/#' -C 5
     # Check HA MQTT
     curl -H "Authorization: Bearer $HA_TOKEN" \
          http://homeassistant:8123/api/config | jq '.components | contains(["mqtt"])'
     ```

   - **Czas**: 0.5h

2. **[ ] Test połączenia Detektor-HA**
   - **Metryka**: Bidirectional communication verified
   - **Walidacja**:

     ```bash
     # Send test from Detektor
     mosquitto_pub -h localhost -t "detektor/test/ping" -m "$(date +%s)"
     # Listen in HA
     docker exec homeassistant mosquitto_sub -t "detektor/test/ping" -C 1
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Home Assistant Discovery Protocol

#### Zadania atomowe

1. **[ ] Implementacja discovery publisher**
   - **Metryka**: Auto-discovery messages dla wszystkich komponentów
   - **Walidacja**:

     ```python
     # Test discovery messages
     from src.integration.mqtt import DiscoveryPublisher
     publisher = DiscoveryPublisher()
     configs = publisher.generate_configs()
     assert len(configs) >= 10  # sensors, switches, cameras
     for config in configs:
         assert "unique_id" in config
         assert "device" in config
         assert config["device"]["identifiers"][0].startswith("detektor_")
     ```

   - **Czas**: 2.5h

2. **[ ] Device registry integration**
   - **Metryka**: Wszystkie urządzenia widoczne w HA jako jeden system
   - **Walidacja**:

     ```bash
     # Check HA device registry
     curl -H "Authorization: Bearer $HA_TOKEN" \
          http://homeassistant:8123/api/states | \
          jq '.[] | select(.attributes.device_class != null) |
              select(.entity_id | startswith("sensor.detektor_"))'
     # Should show all Detektor sensors
     ```

   - **Czas**: 2h

3. **[ ] Entity availability tracking**
   - **Metryka**: Online/offline status dla każdego komponentu
   - **Walidacja**:

     ```python
     # Kill detection service
     docker stop detektor-detection
     sleep 10
     # Check availability in HA
     state=$(curl -s -H "Authorization: Bearer $HA_TOKEN" \
             http://homeassistant:8123/api/states/binary_sensor.detektor_detection_available | \
             jq -r '.state')
     assert [ "$state" = "off" ]
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Wszystkie komponenty auto-discovered
- Device grouping działa poprawnie
- Availability tracking w czasie rzeczywistym

### Blok 2: State synchronization

#### Zadania atomowe

1. **[ ] Event to entity mapper**
   - **Metryka**: Każdy event type ma odpowiedni entity w HA
   - **Walidacja**:

     ```python
     from src.integration.mqtt import EventEntityMapper
     mapper = EventEntityMapper()

     # Test all event types
     events = [
         PersonDetectedEvent(camera_id="front", confidence=0.95),
         MotionDetectedEvent(camera_id="back", zones=["entrance"]),
         ObjectDetectedEvent(object_type="car", camera_id="garage")
     ]

     for event in events:
         entity = mapper.to_entity(event)
         assert entity.unique_id.startswith(f"detektor_{event.camera_id}")
         assert entity.state in ["on", "off", "detected", "clear"]
         assert entity.attributes["confidence"] if hasattr(event, "confidence") else True
     ```

   - **Czas**: 2.5h

2. **[ ] Retain strategy for states**
   - **Metryka**: Critical states retained, temporary states expire
   - **Walidacja**:

     ```bash
     # Publish retained state
     mosquitto_pub -h localhost -t "detektor/camera/front/motion" \
                   -m '{"state": "detected"}' -r
     # Restart HA
     docker restart homeassistant
     sleep 30
     # Check state persisted
     mosquitto_sub -h localhost -t "detektor/camera/front/motion" -C 1
     ```

   - **Czas**: 1.5h

3. **[ ] Command handling from HA**
   - **Metryka**: HA może kontrolować Detektor (start/stop detection, change settings)
   - **Walidacja**:

     ```python
     # Test command reception
     import asyncio
     from src.integration.mqtt import CommandHandler

     handler = CommandHandler()
     received = []
     handler.on_command = lambda cmd: received.append(cmd)

     # Send command from HA
     await handler.start()
     # mosquitto_pub -t "detektor/camera/front/command" -m '{"action": "start_recording"}'
     await asyncio.sleep(2)

     assert len(received) == 1
     assert received[0].action == "start_recording"
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Pełna synchronizacja stanów
- Dwukierunkowa komunikacja
- Persistence dla critical states

### Blok 3: Performance and reliability

#### Zadania atomowe

1. **[ ] Message batching and throttling**
   - **Metryka**: Max 100 msgs/s per topic, batch similar events
   - **Walidacja**:

     ```python
     # Flood with events
     for i in range(1000):
         bridge.send_event(MotionDetectedEvent(camera_id="front"))

     # Check actual messages sent
     stats = bridge.get_stats()
     assert stats.messages_sent < 200  # Should batch
     assert stats.max_rate_per_second <= 100
     ```

   - **Czas**: 2h

2. **[ ] Connection resilience**
   - **Metryka**: Auto-reconnect <5s, zero message loss during disconnects
   - **Walidacja**:

     ```bash
     # Start message counter
     ./scripts/mqtt-message-counter.sh start

     # Send messages while cycling broker
     for i in {1..100}; do
         mosquitto_pub -t "test/counter" -m "$i"
         if [ $i -eq 50 ]; then
             docker restart mosquitto
         fi
         sleep 0.1
     done

     # Verify all received
     ./scripts/mqtt-message-counter.sh verify 100
     ```

   - **Czas**: 1.5h

3. **[ ] Integration tests z HA**
   - **Metryka**: E2E flow: detection → MQTT → HA → automation
   - **Walidacja**:

     ```python
     # Full integration test
     from tests.integration import DetektorHAIntegration

     test = DetektorHAIntegration()
     test.setup_automation("person_detected", "turn_on_lights")

     # Trigger detection
     test.simulate_person_detection("front_door")

     # Verify automation fired
     await asyncio.sleep(2)
     assert test.get_entity_state("light.entrance") == "on"
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Stabilna komunikacja pod obciążeniem
- Zero message loss
- Automatyzacje działają niezawodnie

## Całościowe metryki sukcesu zadania

1. **Integracja**: 100% komponentów Detektor widocznych w HA
2. **Niezawodność**: 99.9% message delivery rate, <5s reconnect time
3. **Wydajność**: <100ms latency detection→HA, obsługa 1000+ events/s
4. **Użyteczność**: Możliwość tworzenia automatyzacji w HA UI

## Deliverables

1. `/src/contexts/integration/infrastructure/mqtt/ha_discovery.py` - Discovery publisher
2. `/src/contexts/integration/infrastructure/mqtt/entity_mapper.py` - Event to entity mapping
3. `/src/contexts/integration/infrastructure/mqtt/command_handler.py` - Command processor
4. `/config/homeassistant/detektor_package.yaml` - HA configuration package
5. `/tests/integration/test_ha_mqtt_integration.py` - Integration tests
6. `/docs/api/mqtt-topics.md` - MQTT topic documentation

## Narzędzia

- **Eclipse Mosquitto**: MQTT broker (already configured)
- **paho-mqtt**: Python MQTT client library
- **Home Assistant MQTT Integration**: Built-in HA component
- **MQTT Explorer**: GUI debugging tool
- **mosquitto-clients**: CLI testing tools

## Zależności

- **Wymaga**:
  - Running MQTT broker
  - Home Assistant z MQTT integration
  - Detection services publishing events
- **Blokuje**:
  - HA automations
  - Dashboard integration
  - Voice control

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| HA API changes | Niskie | Wysoki | Version pinning, API abstraction layer | Integration test failures |
| MQTT broker overload | Średnie | Wysoki | Rate limiting, message prioritization | Broker CPU >80% |
| Discovery spam | Średnie | Średni | Discovery cache, controlled intervals | HA log warnings |
| Network partitions | Niskie | Średni | Local queue, automatic retry | Connection drops |

## Rollback Plan

1. **Detekcja problemu**:
   - HA entities unavailable
   - Message delivery <99%
   - Automation failures

2. **Kroki rollback**:
   - [ ] Disable discovery publisher
   - [ ] Clear retained messages: `mosquitto_sub -h localhost -t '#' -r -C 1 | xargs -I {} mosquitto_pub -t '{}' -r -n`
   - [ ] Restart HA to clear entities
   - [ ] Revert to manual MQTT configuration

3. **Czas rollback**: <15 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **UNIFIED CI/CD DEPLOYMENT**

> **📚 Deployment dla tego serwisu jest zautomatyzowany przez zunifikowany workflow CI/CD.**

### Kroki deployment

1. **[ ] Przygotowanie serwisu do deployment**
   - **Metryka**: MQTT bridge dodany do workflow matrix
   - **Walidacja**:
     ```bash
     # Sprawdź czy serwis jest w .github/workflows/deploy-self-hosted.yml
     grep "mqtt-bridge" .github/workflows/deploy-self-hosted.yml
     ```
   - **Dokumentacja**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)

2. **[ ] Konfiguracja MQTT i Home Assistant**
   - **Metryka**: MQTT broker i HA credentials w SOPS
   - **Konfiguracja**:
     ```bash
     # Edytuj sekrety
     make secrets-edit
     # Dodaj: MQTT_HOST, MQTT_PORT, HA_TOKEN, HA_URL
     ```

3. **[ ] Deploy przez GitHub Actions**
   - **Metryka**: Automated deployment via git push
   - **Komenda**:
     ```bash
     git add .
     git commit -m "feat: deploy mqtt-bridge for Home Assistant integration"
     git push origin main
     ```
   - **Monitorowanie**: https://github.com/hretheum/bezrobocie/actions

### **📋 Walidacja po deployment:**

```bash
# 1. Sprawdź health serwisu
curl http://nebula:8016/health

# 2. Test MQTT broker
mosquitto_sub -h nebula -t '$SYS/#' -C 1
mosquitto_sub -h nebula -t 'detektor/#' -v &

# 3. Test HA discovery
mosquitto_pub -h nebula -t 'homeassistant/sensor/detektor_test/config' \
  -m '{"name": "Detektor Test", "state_topic": "detektor/test/state"}'

# 4. Sprawdź entity w Home Assistant
# Otwórz HA UI i sprawdź Developer Tools > States
# Szukaj: sensor.detektor_test

# 5. Test event flow
curl -X POST http://nebula:8016/api/test-event \
  -d '{"type": "motion_detected", "camera": "front"}'
```

### **🔗 Dokumentacja:**
- **Unified Deployment Guide**: [docs/deployment/README.md](../../deployment/README.md)
- **New Service Guide**: [docs/deployment/guides/new-service.md](../../deployment/guides/new-service.md)
- **Home Assistant Docs**: https://www.home-assistant.io/integrations/mqtt/

### **🔍 Metryki sukcesu bloku:**
- ✅ Serwis w workflow matrix `.github/workflows/deploy-self-hosted.yml`
- ✅ MQTT broker operational
- ✅ HA auto-discovery working
- ✅ Bidirectional communication tested
- ✅ All Detektor entities visible in HA
- ✅ Events trigger HA automations
- ✅ Zero-downtime deployment

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-automation-engine.md](./02-automation-engine.md)
