# Metrics System

Metrics architecture adopted from eofek/detektor with abstraction layer pattern.

## Pattern Overview

Based on proven approach from [eofek/detektor analysis](../../../docs/analysis/eofek-detektor-analysis.md):

```python
# Metrics adapter pattern (from eofek/detektor)
class DetectionMetrics:
    def increment_detections(self):
        detection_metrics.increment_detections()
    
    def observe_detection_time(self, time):
        detection_metrics.observe_detection_time(time)
```

## Key Metrics

From eofek/detektor analysis:
- `frames_processed`: Counter
- `frames_dropped`: Counter  
- `processing_delay`: Histogram
- `gpu_usage`: Gauge
- `detection_time`: Histogram
- `total_detections`: Counter

## Implementation

See task decomposition: [06-frame-tracking-design.md](../../../docs/faza-1-fundament/06-frame-tracking-design.md)