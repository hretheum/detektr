"""Tests for observability features."""
import asyncio
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from base_processor import BaseProcessor
from base_processor.logging import LoggingMixin, ProcessingContext
from base_processor.metrics_decorators import PROCESSOR_METRICS, MetricsContext
from base_processor.tracing import ProcessorSpan, setup_tracing
from prometheus_client import REGISTRY


class ObservableProcessor(BaseProcessor):
    """Test processor with observability."""

    async def process_frame(self, frame: np.ndarray, metadata: dict) -> dict:
        """Simple processing for testing."""
        await asyncio.sleep(0.01)  # Simulate processing
        return {"processed": True, "shape": frame.shape}


class TestTracing:
    """Test OpenTelemetry tracing integration."""

    @pytest.fixture
    def processor(self):
        """Create test processor."""
        return ObservableProcessor("test-processor")

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame."""
        return np.zeros((100, 100, 3), dtype=np.uint8)

    @pytest.mark.asyncio
    async def test_tracing_mixin_initialization(self, processor):
        """Test tracing mixin initializes tracer."""
        assert hasattr(processor, "tracer")
        assert processor.tracer is not None

    @pytest.mark.asyncio
    async def test_processor_span_context(self, processor):
        """Test ProcessorSpan context manager."""
        with ProcessorSpan(
            processor.tracer, "test_operation", processor.name, frame_id="test_123"
        ) as span:
            assert span is not None
            # Span should be recording
            assert span.is_recording()

    @pytest.mark.asyncio
    async def test_tracing_in_process_method(self, processor, sample_frame):
        """Test tracing is active during processing."""
        await processor.initialize()

        # Mock tracer to verify spans are created
        with patch.object(processor, "tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.start_span.return_value = mock_span

            metadata = {"frame_id": "test_123"}
            await processor.process(sample_frame, metadata)

            # Verify span was started
            assert mock_tracer.start_span.called

    def test_setup_tracing(self):
        """Test tracing setup function."""
        provider = setup_tracing(
            service_name="test-service", otlp_endpoint="http://localhost:4317"
        )

        assert provider is not None
        assert provider.resource.attributes["service.name"] == "test-service"


class TestMetrics:
    """Test Prometheus metrics integration."""

    @pytest.fixture
    def processor(self):
        """Create test processor."""
        return ObservableProcessor("metrics-test-processor")

    @pytest.fixture
    def sample_frame(self):
        """Create sample frame."""
        return np.zeros((100, 100, 3), dtype=np.uint8)

    def test_metrics_mixin_initialization(self, processor):
        """Test metrics mixin initializes correctly."""
        assert hasattr(processor, "count_frames")
        assert hasattr(processor, "record_error")
        assert hasattr(processor, "set_active_frames")

    @pytest.mark.asyncio
    async def test_metrics_collection_during_processing(self, processor, sample_frame):
        """Test metrics are collected during frame processing."""
        await processor.initialize()

        # Get initial metrics
        initial_frames = (
            PROCESSOR_METRICS["frames_processed"]
            ._metrics.get(
                (("processor", processor.name), ("status", "success")), Mock(_value=0)
            )
            ._value
        )

        # Process frame
        metadata = {"frame_id": "test_123"}
        await processor.process(sample_frame, metadata)

        # Check metrics were incremented
        final_frames = (
            PROCESSOR_METRICS["frames_processed"]
            ._metrics.get(
                (("processor", processor.name), ("status", "success")), Mock(_value=0)
            )
            ._value
        )

        assert final_frames > initial_frames

    @pytest.mark.asyncio
    async def test_error_metrics(self, processor, sample_frame):
        """Test error metrics collection."""
        await processor.initialize()

        # Mock process_frame to raise error
        async def failing_process(frame, metadata):
            raise ValueError("Test error")

        processor.process_frame = failing_process

        # Get initial error count
        initial_errors = (
            PROCESSOR_METRICS["errors"]
            ._metrics.get(
                (("processor", processor.name), ("error_type", "ValueError")),
                Mock(_value=0),
            )
            ._value
        )

        # Process should fail
        metadata = {"frame_id": "test_123"}
        with pytest.raises(ValueError):
            await processor.process(sample_frame, metadata)

        # Check error was counted
        final_errors = (
            PROCESSOR_METRICS["errors"]
            ._metrics.get(
                (("processor", processor.name), ("error_type", "ValueError")),
                Mock(_value=0),
            )
            ._value
        )

        assert final_errors > initial_errors

    def test_metrics_context_manager(self):
        """Test MetricsContext context manager."""
        processor_name = "test-processor"

        # Check initial active frames
        initial_active = (
            PROCESSOR_METRICS["active_frames"]
            ._metrics.get((("processor", processor_name),), Mock(_value=0))
            ._value
        )

        with MetricsContext(processor_name, "test_operation"):
            # Active frames should be incremented
            during_active = (
                PROCESSOR_METRICS["active_frames"]
                ._metrics.get((("processor", processor_name),), Mock(_value=0))
                ._value
            )
            assert during_active > initial_active

        # Active frames should be decremented after exit
        final_active = (
            PROCESSOR_METRICS["active_frames"]
            ._metrics.get((("processor", processor_name),), Mock(_value=0))
            ._value
        )
        assert final_active == initial_active


class TestLogging:
    """Test structured logging integration."""

    @pytest.fixture
    def processor(self):
        """Create test processor."""
        return ObservableProcessor("logging-test-processor")

    def test_logging_mixin_initialization(self, processor):
        """Test logging mixin initializes logger."""
        assert hasattr(processor, "logger")
        assert hasattr(processor, "log_with_context")
        assert processor.logger is not None

    def test_processing_context(self):
        """Test ProcessingContext context manager."""
        from base_processor.logging import (
            correlation_id_var,
            frame_id_var,
            processor_name_var,
        )

        # Check initial context is empty
        assert correlation_id_var.get() == ""
        assert frame_id_var.get() == ""
        assert processor_name_var.get() == ""

        # Enter context
        with ProcessingContext("test-processor", "frame_123", "corr_123"):
            assert processor_name_var.get() == "test-processor"
            assert frame_id_var.get() == "frame_123"
            assert correlation_id_var.get() == "corr_123"

        # Context should be cleared
        assert correlation_id_var.get() == ""
        assert frame_id_var.get() == ""
        assert processor_name_var.get() == ""

    @pytest.mark.asyncio
    async def test_logging_during_processing(self, processor):
        """Test logging happens during processing."""
        await processor.initialize()

        # Mock logger to capture calls
        with patch.object(processor, "log_with_context") as mock_log:
            sample_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            metadata = {"frame_id": "test_123"}

            await processor.process(sample_frame, metadata)

            # Verify logging calls were made
            assert mock_log.called

            # Check for start and completion logs
            log_messages = [call[0][1] for call in mock_log.call_args_list]
            assert any("Starting frame processing" in msg for msg in log_messages)
            assert any("Frame processing completed" in msg for msg in log_messages)

    def test_child_logger_creation(self, processor):
        """Test child logger creation with bindings."""
        child_logger = processor.create_child_logger(
            component="test_component", operation="test_operation"
        )

        assert child_logger is not None
        # Child logger should have parent bindings plus new ones
