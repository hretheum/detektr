"""Test that fixtures are working correctly."""

from unittest.mock import Mock

import pytest
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.kernel.domain import Frame, ProcessingState


@pytest.mark.unit
class TestFixtures:
    """Test fixture availability and functionality."""

    def test_tracer_fixture(self, tracer):
        """Test that tracer fixture is available."""
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

        # Test creating a span
        with tracer.start_as_current_span("test_span") as span:
            assert span is not None
            assert span.is_recording()

    def test_memory_exporter_fixture(self, memory_exporter, tracer):
        """Test that memory exporter captures spans."""
        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.attribute", "value")

        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test_span"
        assert spans[0].attributes["test.attribute"] == "value"

    @pytest.mark.asyncio
    async def test_db_session_fixture(self, db_session):
        """Test that database session fixture is available."""
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)

        # Test basic query
        result = await db_session.execute("SELECT 1")
        assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_redis_client_fixture(self, redis_client):
        """Test that Redis client fixture is available."""
        assert redis_client is not None

        # Test basic operations
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        assert value == "test_value"

    def test_message_queue_fixture(self, message_queue):
        """Test that message queue fixture is available."""
        assert message_queue is not None
        assert isinstance(message_queue, Mock)
        assert hasattr(message_queue, "publish")
        assert hasattr(message_queue, "subscribe")

    def test_sample_frame_fixture(self, sample_frame):
        """Test that sample frame fixture creates valid frame."""
        assert sample_frame is not None
        assert isinstance(sample_frame, Frame)
        assert sample_frame.camera_id == "test_camera_01"
        assert sample_frame.state == ProcessingState.CAPTURED

    def test_mock_metrics_fixture(self, mock_metrics):
        """Test that mock metrics fixture is available."""
        assert mock_metrics is not None
        assert hasattr(mock_metrics, "increment_frames_processed")
        assert hasattr(mock_metrics, "record_processing_time")

        # Test that methods can be called
        mock_metrics.increment_frames_processed(1)
        mock_metrics.increment_frames_processed.assert_called_once_with(1)

    def test_environment_fixture(self):
        """Test that test environment is set up."""
        import os

        assert os.getenv("ENVIRONMENT") == "test"
        assert os.getenv("LOG_LEVEL") == "DEBUG"
        assert os.getenv("OTLP_ENDPOINT") == "http://localhost:4317"

    def test_benchmark_data_fixture(self, benchmark_data):
        """Test that benchmark data fixture provides test data."""
        assert "small" in benchmark_data
        assert "medium" in benchmark_data
        assert "large" in benchmark_data
        assert len(benchmark_data["small"]) == 100
        assert len(benchmark_data["medium"]) == 1000
        assert len(benchmark_data["large"]) == 10000


@pytest.mark.integration
class TestContainerFixtures:
    """Test container-based fixtures."""

    def test_postgres_container_fixture(self, postgres_container):
        """Test that PostgreSQL container is available."""
        assert postgres_container is not None
        assert postgres_container.get_connection_url() is not None

    def test_redis_container_fixture(self, redis_container):
        """Test that Redis container is available."""
        assert redis_container is not None
        port = redis_container.get_exposed_port(6379)
        assert port is not None
