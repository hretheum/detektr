"""
Test suite for observability features - OpenTelemetry and metrics.

Tests cover:
- Trace creation and propagation
- Span attributes and events
- Metrics collection
- Context propagation across async boundaries
"""

import asyncio
import time
from unittest.mock import Mock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from prometheus_client import REGISTRY

# Will be imported after implementation
# from src.observability import (
#     TracedFrameBuffer,
#     init_telemetry,
#     create_frame_span,
#     record_frame_metrics
# )


class TestOpenTelemetryInstrumentation:
    """Tests for OpenTelemetry tracing."""

    @pytest.fixture(autouse=True, scope="class")
    def setup_tracing(self):
        """Set up tracing for the test class."""
        # Create test provider
        provider = TracerProvider()
        exporter = InMemorySpanExporter()
        processor = SimpleSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Set as global tracer
        trace.set_tracer_provider(provider)

        # Store on class
        TestOpenTelemetryInstrumentation.provider = provider
        TestOpenTelemetryInstrumentation.exporter = exporter

        yield

    @pytest.fixture
    def tracer_provider(self):
        """Get tracer provider and exporter for testing."""
        # Clear exporter before each test
        self.__class__.exporter.clear()
        return self.__class__.provider, self.__class__.exporter

    @pytest.fixture
    def tracer(self, tracer_provider):
        """Get test tracer."""
        provider, _ = tracer_provider
        return trace.get_tracer("test-tracer")

    def test_frame_span_creation(self, tracer_provider):
        """Test that frame processing creates proper spans."""
        from src.observability import create_frame_span

        _, exporter = tracer_provider

        # Process a frame with tracing
        frame_id = "frame_001"
        with create_frame_span(frame_id, "camera_01") as span:
            # Simulate frame processing
            time.sleep(0.01)
            span.set_attribute("frame.size", 1920 * 1080 * 3)
            span.add_event("frame.decoded")

        # Check span was exported
        spans = exporter.get_finished_spans()
        assert len(spans) == 1

        frame_span = spans[0]
        assert frame_span.name == f"process_frame_{frame_id}"
        assert frame_span.attributes["frame.id"] == frame_id
        assert frame_span.attributes["camera.id"] == "camera_01"
        assert frame_span.attributes["frame.size"] == 1920 * 1080 * 3

        # Check events
        events = [e.name for e in frame_span.events]
        assert "frame.decoded" in events

    def test_nested_span_hierarchy(self, tracer, tracer_provider):
        """Test nested spans for frame operations."""
        from src.observability import create_frame_span, create_operation_span

        _, exporter = tracer_provider

        # Create nested spans
        with create_frame_span("frame_001", "camera_01") as frame_span:
            with create_operation_span("decode", frame_span) as decode_span:
                decode_span.set_attribute("codec", "h264")
                time.sleep(0.005)

            with create_operation_span("buffer_put", frame_span) as buffer_span:
                buffer_span.set_attribute("buffer.size", 100)
                time.sleep(0.002)

        # Check span hierarchy
        spans = exporter.get_finished_spans()
        assert len(spans) == 3

        # Find spans by name
        span_dict = {s.name: s for s in spans}
        assert "process_frame_frame_001" in span_dict
        assert "decode" in span_dict
        assert "buffer_put" in span_dict

        # Check parent-child relationship
        frame_span = span_dict["process_frame_frame_001"]
        decode_span = span_dict["decode"]
        buffer_span = span_dict["buffer_put"]

        assert decode_span.parent.span_id == frame_span.context.span_id
        assert buffer_span.parent.span_id == frame_span.context.span_id

    @pytest.mark.asyncio
    async def test_async_context_propagation(self, tracer, tracer_provider):
        """Test trace context propagation across async boundaries."""
        from src.observability import TracedRedisQueue, create_frame_span

        _, exporter = tracer_provider

        # Simulate async frame processing pipeline
        async def process_frame_async(frame_id):
            with create_frame_span(frame_id, "camera_01") as span:
                # Async decode
                await asyncio.sleep(0.01)
                span.add_event("frame.decoded")

                # Async buffer operation
                await asyncio.sleep(0.005)
                span.add_event("frame.buffered")

                # Async Redis publish (mocked)
                mock_queue = Mock()
                mock_queue.stream_key = "test_stream"

                async def mock_publish(metadata):
                    return "msg_id_123"

                mock_queue.publish = mock_publish
                queue = TracedRedisQueue(mock_queue)
                await queue.publish_with_trace({"frame_id": frame_id}, span)

        # Process multiple frames concurrently
        await asyncio.gather(
            process_frame_async("frame_001"),
            process_frame_async("frame_002"),
            process_frame_async("frame_003"),
        )

        # Verify all spans were created
        spans = exporter.get_finished_spans()
        frame_spans = [s for s in spans if s.name.startswith("process_frame_")]
        assert len(frame_spans) == 3

        # Each should have proper events
        for span in frame_spans:
            event_names = [e.name for e in span.events]
            assert "frame.decoded" in event_names
            assert "frame.buffered" in event_names

    def test_traced_frame_buffer(self, tracer, tracer_provider):
        """Test TracedFrameBuffer with automatic span creation."""
        from src.observability import TracedFrameBuffer

        _, exporter = tracer_provider

        # Create traced buffer
        buffer = TracedFrameBuffer(capacity=10, camera_id="test_camera")

        # Operations should create spans
        frame_data = b"dummy_frame_data"
        buffer.put("frame_001", frame_data, time.time())
        buffer.put("frame_002", frame_data, time.time())

        retrieved = buffer.get()
        assert retrieved[0] == "frame_001"

        # Check spans were created
        spans = exporter.get_finished_spans()
        span_names = [s.name for s in spans]

        assert "buffer.put" in span_names
        assert "buffer.get" in span_names

        # Check attributes
        put_spans = [s for s in spans if s.name == "buffer.put"]
        assert len(put_spans) == 2
        for span in put_spans:
            assert "frame.id" in span.attributes
            assert "buffer.size" in span.attributes

    def test_error_recording_in_spans(self, tracer, tracer_provider):
        """Test that errors are properly recorded in spans."""
        from src.observability import create_frame_span

        _, exporter = tracer_provider

        # Simulate error during processing
        try:  # noqa: SIM105
            with create_frame_span("frame_error", "camera_01") as span:
                span.add_event("processing.started")
                raise ValueError("Simulated decode error")
        except ValueError:
            pass  # Expected error

        # Check error was recorded
        spans = exporter.get_finished_spans()
        assert len(spans) == 1

        error_span = spans[0]
        assert error_span.status.status_code == StatusCode.ERROR

        # Check error event
        # The exception should be recorded automatically by the span
        error_events = [e for e in error_span.events if "exception" in e.name.lower()]
        assert len(error_events) > 0


class TestPrometheusMetrics:
    """Tests for Prometheus metrics export."""

    @pytest.fixture
    def metrics_registry(self):
        """Create clean metrics registry."""
        # Reset observability module to force re-initialization
        import src.observability as obs

        obs._metrics_initialized = False
        obs.frame_counter = None
        obs.frame_processing_time = None
        obs.frame_drops_counter = None
        obs.active_connections_gauge = None
        obs.buffer_size_gauge = None
        obs.redis_queue_size_gauge = None

        from src.observability import init_metrics

        return init_metrics()

    def test_frame_processing_metrics(self, metrics_registry):
        """Test frame processing metrics collection."""
        from src.observability import (
            active_connections_gauge,
            frame_counter,
            frame_drops_counter,
            frame_processing_time,
        )

        # Simulate frame processing
        frame_counter.labels(camera_id="camera_01", status="success").inc()
        frame_counter.labels(camera_id="camera_01", status="success").inc()
        frame_counter.labels(camera_id="camera_01", status="error").inc()

        # Record processing times
        frame_processing_time.labels(camera_id="camera_01", operation="decode").observe(
            0.010
        )
        frame_processing_time.labels(camera_id="camera_01", operation="decode").observe(
            0.012
        )
        frame_processing_time.labels(camera_id="camera_01", operation="buffer").observe(
            0.001
        )

        # Record drops
        frame_drops_counter.labels(camera_id="camera_01", reason="buffer_full").inc()

        # Update connections
        active_connections_gauge.labels(camera_id="camera_01").set(1)

        # Verify metrics
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY).decode("utf-8")

        assert (
            'frames_processed_total{camera_id="camera_01",status="success"} 2.0'
            in metrics_output
        )
        assert (
            'frames_processed_total{camera_id="camera_01",status="error"} 1.0'
            in metrics_output
        )
        assert (
            'frame_drops_total{camera_id="camera_01",reason="buffer_full"} 1.0'
            in metrics_output
        )
        assert 'active_rtsp_connections{camera_id="camera_01"} 1.0' in metrics_output

    def test_histogram_buckets(self, metrics_registry):
        """Test histogram bucket configuration for latency metrics."""
        from src.observability import frame_processing_time

        # Record various latencies
        latencies = [0.001, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.000]

        for latency in latencies:
            frame_processing_time.labels(
                camera_id="camera_01", operation="end_to_end"
            ).observe(latency)

        # Check bucket counts
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY).decode("utf-8")

        # Should have proper buckets for sub-second latencies
        assert 'le="0.001"' in metrics_output
        assert 'le="0.01"' in metrics_output
        assert 'le="0.1"' in metrics_output
        assert 'le="1.0"' in metrics_output

    def test_metrics_labels_cardinality(self, metrics_registry):
        """Test that metrics labels don't explode cardinality."""
        from src.observability import get_metrics_labels

        # Test label sanitization
        labels = get_metrics_labels(
            camera_id="camera_01_very_long_name_that_should_be_truncated",
            operation="decode",
        )

        assert len(labels["camera_id"]) <= 50  # Reasonable limit
        assert labels["operation"] in ["decode", "buffer", "publish", "end_to_end"]

    @pytest.mark.asyncio
    async def test_metrics_in_async_context(self, metrics_registry):
        """Test metrics collection in async operations."""
        from src.observability import async_timed_operation

        @async_timed_operation("test_operation", "camera_01")
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "result"

        # Run operation multiple times
        results = await asyncio.gather(
            slow_operation(), slow_operation(), slow_operation()
        )

        assert all(r == "result" for r in results)

        # Check metrics were recorded
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY).decode("utf-8")

        assert (
            'frame_processing_duration_seconds_count{camera_id="camera_01",'
            'operation="test_operation"} 3.0' in metrics_output
        )


class TestObservabilityIntegration:
    """Integration tests for tracing + metrics together."""

    @pytest.fixture
    def full_observability(self, tracer_provider, metrics_registry):
        """Set up both tracing and metrics."""
        return tracer_provider, metrics_registry

    @pytest.mark.asyncio
    async def test_traced_and_metered_pipeline(self, full_observability):
        """Test full pipeline with both tracing and metrics."""
        from src.observability import (
            TracedFrameBuffer,
            TracedRedisQueue,
            create_frame_span,
            frame_counter,
            frame_processing_time,
        )

        (_, exporter), _ = full_observability

        # Create instrumented components
        buffer = TracedFrameBuffer(capacity=10)
        redis_mock = Mock()
        redis_mock.xadd = Mock(return_value=b"1234567890-0")
        queue = TracedRedisQueue(redis_mock)

        # Process frame with full instrumentation
        frame_id = "frame_001"
        camera_id = "camera_01"

        with create_frame_span(frame_id, camera_id) as span:
            start_time = time.time()

            # Decode simulation
            await asyncio.sleep(0.01)
            span.add_event("frame.decoded")

            # Buffer
            buffer.put(frame_id, b"frame_data", time.time())
            span.add_event("frame.buffered")

            # Publish
            await queue.publish_with_trace(
                {"frame_id": frame_id, "timestamp": time.time()}, span
            )
            span.add_event("frame.published")

            # Record metrics
            frame_counter.labels(camera_id=camera_id, status="success").inc()
            frame_processing_time.labels(
                camera_id=camera_id, operation="end_to_end"
            ).observe(time.time() - start_time)

        # Verify tracing
        spans = exporter.get_finished_spans()
        assert len(spans) >= 3  # frame span + operation spans

        # Verify metrics
        from prometheus_client import generate_latest

        metrics_output = generate_latest(REGISTRY).decode("utf-8")
        assert (
            f'frames_processed_total{{camera_id="{camera_id}",status="success"}} 1.0'
            in metrics_output
        )


@pytest.mark.parametrize("num_frames", [10, 100, 1000])
def test_observability_performance_impact(num_frames):
    """Test performance impact of observability instrumentation."""
    from src.frame_buffer import CircularFrameBuffer
    from src.observability import TracedFrameBuffer

    # Use realistic frame data (1920x1080 RGB ~ 6MB)
    frame_data = b"x" * (1920 * 1080 * 3)

    # Baseline: uninstrumented buffer
    plain_buffer = CircularFrameBuffer(capacity=1000)
    start = time.perf_counter()

    for i in range(num_frames):
        plain_buffer.put(f"frame_{i}", frame_data, time.time())
        if i % 2 == 0:
            plain_buffer.get()

    baseline_time = time.perf_counter() - start

    # With instrumentation
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    traced_buffer = TracedFrameBuffer(capacity=1000)
    start = time.perf_counter()

    for i in range(num_frames):
        traced_buffer.put(f"frame_{i}", frame_data, time.time())
        if i % 2 == 0:
            traced_buffer.get()

    instrumented_time = time.perf_counter() - start

    # Overhead should be minimal (<10%) for realistic workloads
    overhead_percent = ((instrumented_time - baseline_time) / baseline_time) * 100
    print(f"\nObservability overhead for {num_frames} frames: {overhead_percent:.2f}%")

    # For very small operations (10 frames), allow higher overhead
    max_overhead = 50 if num_frames == 10 else 10
    assert (
        overhead_percent < max_overhead
    ), f"Overhead {overhead_percent:.2f}% exceeds {max_overhead}% limit"
