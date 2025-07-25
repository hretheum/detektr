# Frame Tracking Library

Distributed tracing library for tracking video frames through the processing pipeline.

## Features

- Unique, time-ordered frame IDs
- Frame metadata with serialization
- OpenTelemetry trace context injection
- Thread-safe ID generation

## Installation

```bash
pip install -e .
```

## Usage

```python
from frame_tracking import FrameID, FrameMetadata, TraceContext

# Generate unique frame ID
frame_id = FrameID.generate(camera_id="cam01", source="rtsp-capture")

# Create frame metadata
metadata = FrameMetadata(
    frame_id=frame_id,
    timestamp=time.time(),
    camera_id="cam01",
    resolution=(1920, 1080),
    format="h264"
)

# Inject trace context
with TraceContext.inject(frame_id) as ctx:
    # Process frame with automatic tracing
    process_frame(metadata)
```
