# Event System

Event-driven architecture adopted from eofek/detektor using Redis Streams.

## Pattern Overview

Based on proven approach from [eofek/detektor analysis](../../../docs/analysis/eofek-detektor-analysis.md):

- Redis Streams instead of simple pub/sub
- Event acknowledgement for reliability
- Structured event format with unique IDs

```python
# Event publishing pattern (from eofek/detektor)
async def publish_event(self, event_type, data):
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'service': self.service_name,
        'data': data
    }
    await self.redis.xadd(stream_name, event)
```

## Implementation

See task decomposition: [03-event-bus-kafka.md](../../../docs/faza-4-integracja/03-event-bus-kafka.md)