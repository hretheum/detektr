"""Unit tests for BaseService class."""

import asyncio
import signal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.base_service import BaseService, ServiceStatus


@pytest.mark.unit
class TestBaseService:
    """Test BaseService functionality."""

    @pytest.fixture
    def mock_telemetry(self, monkeypatch):
        """Mock telemetry setup."""
        mock_setup = Mock(return_value=Mock())
        monkeypatch.setattr("src.shared.base_service.setup_telemetry", mock_setup)
        return mock_setup

    @pytest.fixture
    def test_service_class(self):
        """Create a test service class."""

        class TestService(BaseService):
            async def start(self):
                """Start test service."""
                await super().start()
                self.custom_started = True

            async def stop(self):
                """Stop test service."""
                self.custom_stopped = True
                await super().stop()

            def setup_routes(self):
                """Setup custom routes."""
                super().setup_routes()

                @self.app.get("/custom")
                async def custom_endpoint():
                    return {"custom": True}

        return TestService

    def test_service_initialization(self, test_service_class, mock_telemetry):
        """Test service initialization."""
        service = test_service_class(name="test-service", version="1.0.0", port=8000)

        assert service.name == "test-service"
        assert service.version == "1.0.0"
        assert service.port == 8000
        assert service.status == ServiceStatus.STOPPED
        assert isinstance(service.app, FastAPI)
        assert service.tracer is not None
        assert service.meter is not None

        # Check telemetry was set up
        mock_telemetry.assert_called_once_with(
            service_name="test-service", service_version="1.0.0"
        )

    def test_health_endpoint(self, test_service_class, mock_telemetry):
        """Test health check endpoint."""
        service = test_service_class("test-service")
        client = TestClient(service.app)

        # When stopped
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"
        assert response.json()["service"] == "test-service"

        # When running
        service.status = ServiceStatus.RUNNING
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_ready_endpoint(self, test_service_class, mock_telemetry):
        """Test readiness endpoint."""
        service = test_service_class("test-service")
        client = TestClient(service.app)

        # When not ready
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["ready"] is False

        # When ready
        service.status = ServiceStatus.RUNNING
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["ready"] is True

    def test_metrics_endpoint(self, test_service_class, mock_telemetry):
        """Test metrics endpoint."""
        service = test_service_class("test-service")
        client = TestClient(service.app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "text/plain; version=0.0.4; charset=utf-8"
        )

    def test_custom_routes(self, test_service_class, mock_telemetry):
        """Test that custom routes can be added."""
        service = test_service_class("test-service")
        client = TestClient(service.app)

        response = client.get("/custom")
        assert response.status_code == 200
        assert response.json()["custom"] is True

    @pytest.mark.asyncio
    async def test_service_start(self, test_service_class, mock_telemetry):
        """Test service start."""
        service = test_service_class("test-service")

        # Mock server
        mock_server = Mock()
        mock_server.startup = AsyncMock()
        mock_server.shutdown = AsyncMock()

        with patch("src.shared.base_service.Server", return_value=mock_server):
            await service.start()

            assert service.status == ServiceStatus.RUNNING
            assert hasattr(service, "custom_started")
            assert service.custom_started is True
            mock_server.startup.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_stop(self, test_service_class, mock_telemetry):
        """Test service stop."""
        service = test_service_class("test-service")
        service.status = ServiceStatus.RUNNING

        # Mock server
        service._server = Mock()
        service._server.shutdown = AsyncMock()

        await service.stop()

        assert service.status == ServiceStatus.STOPPED
        assert hasattr(service, "custom_stopped")
        assert service.custom_stopped is True
        service._server.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, test_service_class, mock_telemetry):
        """Test graceful shutdown handling."""
        service = test_service_class("test-service")
        service.status = ServiceStatus.RUNNING

        # Mock stop method
        service.stop = AsyncMock()

        # Simulate SIGTERM
        with patch("asyncio.create_task") as mock_create_task:
            service._handle_signal(signal.SIGTERM, None)
            mock_create_task.assert_called_once()

            # Get the coroutine that was passed to create_task
            coro = mock_create_task.call_args[0][0]
            await coro

            service.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_method(self, test_service_class, mock_telemetry):
        """Test run method starts and handles shutdown."""
        service = test_service_class("test-service")

        # Mock start and stop
        service.start = AsyncMock()
        service.stop = AsyncMock()

        # Mock signal handler setup
        with patch("signal.signal") as mock_signal:
            # Create a task that will cancel after a short delay
            async def cancel_after_delay():
                await asyncio.sleep(0.1)
                # Find all tasks and cancel them
                for task in asyncio.all_tasks():
                    if task != asyncio.current_task():
                        task.cancel()

            # Start the cancellation task
            asyncio.create_task(cancel_after_delay())

            # Run the service (should exit when cancelled)
            try:
                await service.run()
            except asyncio.CancelledError:
                pass

            # Verify signal handlers were set up
            assert mock_signal.call_count >= 2  # SIGTERM and SIGINT

            # Verify start was called
            service.start.assert_called_once()

    def test_service_info(self, test_service_class, mock_telemetry):
        """Test service info endpoint."""
        service = test_service_class("test-service", version="1.2.3")
        client = TestClient(service.app)

        response = client.get("/info")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "test-service"
        assert data["version"] == "1.2.3"
        assert data["status"] == "stopped"
        assert "uptime" in data
        assert "environment" in data


@pytest.mark.unit
class TestServiceStatus:
    """Test ServiceStatus enum."""

    def test_service_status_values(self):
        """Test ServiceStatus enum values."""
        assert ServiceStatus.STOPPED.value == "stopped"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.RUNNING.value == "running"
        assert ServiceStatus.STOPPING.value == "stopping"
        assert ServiceStatus.ERROR.value == "error"
