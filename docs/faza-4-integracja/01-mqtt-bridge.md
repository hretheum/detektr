# Faza 4 / Zadanie 1: MQTT bridge z metrykami publikacji/subskrypcji

## Cel zadania

Implementować niezawodny most MQTT do komunikacji z Home Assistant z gwarancją dostarczenia i pełnym monitoringiem.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja MQTT broker**
   - **Metryka**: Mosquitto/EMQX running, HA connected
   - **Walidacja**:

     ```bash
     mosquitto_sub -h localhost -t '$SYS/broker/clients/connected' -C 1
     # Returns number >0
     netstat -an | grep 1883
     # Port 1883 listening
     ```

   - **Czas**: 0.5h

2. **[ ] Test HA MQTT integration**
   - **Metryka**: HA receives test messages
   - **Walidacja**:

     ```bash
     mosquitto_pub -h localhost -t "homeassistant/test" -m "ping"
     # Check HA logs for received message
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: MQTT client implementation

#### Zadania atomowe

1. **[ ] Async MQTT client z reconnect**
   - **Metryka**: Auto-reconnect <5s, no message loss
   - **Walidacja**:

     ```python
     client = MQTTBridge(auto_reconnect=True)
     # Kill broker, restart
     assert client.reconnect_count > 0
     assert client.messages_lost == 0
     ```

   - **Czas**: 2h

2. **[ ] Topic structure design**
   - **Metryka**: HA auto-discovery compatible
   - **Walidacja**:

     ```bash
     mosquitto_sub -h localhost -t "homeassistant/+/detektor_+/config" -C 1
     # Returns valid discovery payload
     ```

   - **Czas**: 1.5h

3. **[ ] QoS and retention policies**
   - **Metryka**: Critical messages QoS 2, retain where needed
   - **Walidacja**:

     ```python
     msg = client.publish("detektor/alert", "test", qos=2, retain=True)
     assert msg.is_published()
     assert msg.qos == 2
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Reliable MQTT communication
- HA discovery working
- Message delivery guaranteed

### Blok 2: Message transformation

#### Zadania atomowe

1. **[ ] Event to MQTT mapper**
   - **Metryka**: All event types have MQTT mapping
   - **Walidacja**:

     ```python
     events = [PersonDetected(), MotionDetected(), GestureRecognized()]
     for event in events:
         mqtt_msg = transformer.to_mqtt(event)
         assert mqtt_msg.topic.startswith("detektor/")
         assert json.loads(mqtt_msg.payload)
     ```

   - **Czas**: 2h

2. **[ ] State aggregation logic**
   - **Metryka**: Deduplicate events, aggregate state
   - **Walidacja**:

     ```python
     # Send 10 identical events
     for _ in range(10):
         bridge.process(PersonDetected(camera="front"))
     # Only 1 MQTT message sent
     assert bridge.messages_sent == 1
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Smart event handling
- Reduced message volume
- State consistency

### Blok 3: Monitoring integration

#### Zadania atomowe

1. **[ ] MQTT metrics exporter**
   - **Metryka**: Publish/subscribe rates, errors
   - **Walidacja**:

     ```bash
     curl localhost:8004/metrics | grep mqtt_
     # mqtt_messages_published_total
     # mqtt_connection_status
     # mqtt_publish_latency_seconds
     ```

   - **Czas**: 1.5h

2. **[ ] Message flow dashboard**
   - **Metryka**: Visualize MQTT traffic
   - **Walidacja**:

     ```bash
     # Grafana panel shows message rates
     curl http://localhost:3000/api/dashboards/uid/mqtt-flow
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Complete visibility
- Performance tracked
- Issues detectable

## Całościowe metryki sukcesu zadania

1. **Reliability**: 99.9% message delivery rate
2. **Performance**: <50ms publish latency, 1000+ msg/s
3. **Integration**: HA auto-discovery working

## Deliverables

1. `/services/mqtt-bridge/` - MQTT bridge service
2. `/config/mqtt/` - Topic configurations
3. `/homeassistant/packages/detektor.yaml` - HA integration
4. `/dashboards/mqtt-metrics.json` - MQTT dashboard
5. `/docs/mqtt-topics.md` - Topic documentation

## Narzędzia

- **Eclipse Mosquitto**: MQTT broker
- **paho-mqtt**: Python MQTT client
- **MQTT Explorer**: GUI for debugging
- **mosquitto-clients**: CLI tools

## Zależności

- **Wymaga**:
  - MQTT broker running
  - Home Assistant configured
- **Blokuje**: All HA automations

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| MQTT broker overload | Średnie | Wysoki | Rate limiting, message aggregation | CPU >80% |
| Network partitions | Niskie | Średni | Local queueing, retry logic | Connection failures |

## Rollback Plan

1. **Detekcja problemu**:
   - Message loss >0.1%
   - HA not receiving events
   - Broker unstable

2. **Kroki rollback**:
   - [ ] Enable debug logging
   - [ ] Switch to QoS 0 temporarily
   - [ ] Clear retained messages
   - [ ] Restart with conservative settings

3. **Czas rollback**: <10 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [02-ha-bridge-service.md](./02-ha-bridge-service.md)
