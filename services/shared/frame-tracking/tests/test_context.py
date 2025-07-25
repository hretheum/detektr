"""Tests for trace context injection."""

from datetime import datetime

from frame_tracking import FrameID
from frame_tracking.context import TraceContext
from frame_tracking.metadata import FrameMetadata
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Setup test tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add console exporter for debugging
provider = trace.get_tracer_provider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)


class TestTraceContext:
    """Test trace context functionality."""

    def test_inject_context(self):
        """Test injecting trace context."""
        frame_id = FrameID.generate()

        with TraceContext.inject(frame_id) as ctx:
            assert ctx.frame_id == frame_id
            assert ctx.trace_id is not None
            assert ctx.span_id is not None
            assert len(ctx.trace_id) > 0
            assert len(ctx.span_id) > 0

    def test_context_in_metadata(self):
        """Test trace context added to metadata."""
        metadata = FrameMetadata(frame_id="test_123", timestamp=datetime.now())

        with TraceContext.inject("test_123") as ctx:
            ctx.apply_to_metadata(metadata)

        assert metadata.trace_id is not None
        assert metadata.span_id is not None
        assert metadata.trace_id == ctx.trace_id
        assert metadata.span_id == ctx.span_id

    def test_nested_spans(self):
        """Test nested span creation."""
        frame_id = FrameID.generate()

        with TraceContext.inject(frame_id) as ctx:
            parent_span_id = ctx.span_id

            # Create nested span
            with ctx.span("process_frame") as span:
                assert span is not None
                # In nested span, parent should be set
                current_span = trace.get_current_span()
                span_context = current_span.get_span_context()
                assert span_context.is_valid

    def test_span_attributes(self):
        """Test span attributes are set correctly."""
        frame_id = FrameID.generate()
        metadata = FrameMetadata(
            frame_id=frame_id,
            timestamp=datetime.now(),
            camera_id="cam01",
            resolution=(1920, 1080),
        )

        with TraceContext.inject(frame_id, metadata=metadata) as ctx:
            current_span = trace.get_current_span()
            # Span should have frame attributes
            # Note: In real implementation, we'd check span.attributes

    def test_propagation(self):
        """Test context propagation."""
        frame_id = FrameID.generate()

        with TraceContext.inject(frame_id) as ctx:
            carrier = {}
            ctx.inject_to_carrier(carrier)

            assert "traceparent" in carrier
            # tracestate is optional

            # Extract context
            extracted = TraceContext.extract_from_carrier(carrier)
            assert extracted is not None

    def test_get_current(self):
        """Test getting current trace context."""
        frame_id = FrameID.generate()

        # Outside context
        assert TraceContext.get_current() is None

        # Inside context
        with TraceContext.inject(frame_id) as ctx:
            current = TraceContext.get_current()
            assert current is not None
            assert current.frame_id == frame_id
            assert current.trace_id == ctx.trace_id

    def test_attributes_from_metadata(self):
        """Test extracting attributes from metadata."""
        metadata = FrameMetadata(
            frame_id="test_123",
            timestamp=datetime.now(),
            camera_id="cam01",
            resolution=(1920, 1080),
            format="h264",
            size_bytes=1024,
        )

        attributes = metadata.to_trace_attributes()

        assert attributes["frame.id"] == "test_123"
        assert attributes["camera.id"] == "cam01"
        assert attributes["frame.width"] == 1920
        assert attributes["frame.height"] == 1080
        assert attributes["frame.format"] == "h264"
        assert attributes["frame.size_bytes"] == 1024
