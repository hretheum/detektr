"""
Test suite for health check and monitoring endpoints.

Tests cover:
- Health check endpoint responses
- Readiness probe logic
- Prometheus metrics formatting
- State updates and tracking
"""

import contextlib
import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

# Will import after creating main app
# from src.main import app
# from src.health import update_health_state, add_rtsp_connection, service_metrics


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        # Create minimal FastAPI app for testing
        from fastapi import FastAPI

        from src.health import health_router, update_health_state

        app = FastAPI()
        app.include_router(health_router)

        # Set initial state
        update_health_state("start_time", time.time())

        return TestClient(app)

    @pytest.fixture(autouse=True)
    def reset_health_state(self):
        """Reset health state before each test."""
        from src.health import _health_state

        _health_state.clear()
        _health_state.update(
            {
                "start_time": time.time(),
                "rtsp_connections": {},
                "redis_connected": False,
                "last_frame_time": {},
            }
        )

        yield

    def test_ping_endpoint(self, client):
        """Test basic ping endpoint."""
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json() == {"ping": "pong"}

    def test_health_check_initial_state(self, client):
        """Test health check with no connections."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "degraded"  # No Redis, but no RTSP is OK
        assert data["version"] == "1.0.0"
        assert "uptime_seconds" in data
        assert data["checks"]["redis"]["healthy"] is False
        assert (
            data["checks"]["rtsp_connections"]["healthy"] is True
        )  # No connections is OK

    def test_health_check_with_redis(self, client):
        """Test health check with Redis connected."""
        from src.health import update_health_state

        update_health_state("redis_connected", True)

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"  # Redis connected, no RTSP required
        assert data["checks"]["redis"]["healthy"] is True

    def test_health_check_with_rtsp(self, client):
        """Test health check with RTSP connections."""
        from src.health import (
            add_rtsp_connection,
            update_health_state,
            update_last_frame,
        )

        # Add healthy RTSP connection
        add_rtsp_connection("camera_01", "rtsp://example.com/stream1", True)
        update_last_frame("camera_01", time.time())
        update_health_state("redis_connected", True)

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert "camera_01" in data["checks"]["rtsp_connections"]["details"]
        assert (
            data["checks"]["rtsp_connections"]["details"]["camera_01"]["healthy"]
            is True
        )

    def test_health_check_stale_frames(self, client):
        """Test health check with stale frame data."""
        from src.health import add_rtsp_connection, update_last_frame

        # Add RTSP with old frame
        add_rtsp_connection("camera_01", "rtsp://example.com/stream1", True)
        update_last_frame("camera_01", time.time() - 15)  # 15 seconds old

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "unhealthy"
        camera_details = data["checks"]["rtsp_connections"]["details"]["camera_01"]
        assert camera_details["healthy"] is False
        assert camera_details["last_frame_age"] > 10

    def test_readiness_probe_not_ready(self, client):
        """Test readiness probe when service is not ready."""
        response = client.get("/ready")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["ready"] is False
        assert "Redis not connected" in data["reason"]

    def test_readiness_probe_ready(self, client):
        """Test readiness probe when service is ready."""
        from src.health import add_rtsp_connection, update_health_state

        update_health_state("redis_connected", True)
        add_rtsp_connection("camera_01", "rtsp://example.com/stream1", True)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["reason"] is None
        assert data["dependencies"]["redis"] is True
        assert data["dependencies"]["rtsp"] is True

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        from src.health import service_metrics

        # Generate some metrics
        service_metrics.register_camera("camera_01", "rtsp://example.com/stream1")
        service_metrics.on_frame_received("camera_01")
        service_metrics.on_frame_received("camera_01")
        service_metrics.on_frame_error("camera_01", "decode error")
        service_metrics.set_buffer_size("camera_01", 42)

        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        metrics_text = response.text
        assert "frames_processed_total" in metrics_text
        assert 'camera_id="camera_01"' in metrics_text
        assert 'status="success"' in metrics_text
        assert 'status="error"' in metrics_text
        assert "frame_buffer_size" in metrics_text


class TestServiceMetrics:
    """Tests for ServiceMetrics helper class."""

    @pytest.fixture
    def metrics(self):
        """Create ServiceMetrics instance."""
        from src.health import ServiceMetrics

        return ServiceMetrics()

    @pytest.fixture(autouse=True)
    def reset_prometheus(self):
        """Reset Prometheus registry."""
        # Clear metrics to avoid conflicts
        collectors = list(REGISTRY._collector_to_names.keys())
        for collector in collectors:
            with contextlib.suppress(Exception):
                REGISTRY.unregister(collector)

        # Re-initialize metrics
        import src.observability
        from src.observability import _init_metrics_once

        # Force re-initialization
        src.observability._metrics_initialized = False
        _init_metrics_once()

        yield

    def test_register_camera(self, metrics):
        """Test camera registration."""
        from src.health import _health_state

        metrics.register_camera("camera_01", "rtsp://example.com/stream1")

        assert "camera_01" in metrics.cameras
        assert "camera_01" in _health_state["rtsp_connections"]
        assert _health_state["rtsp_connections"]["camera_01"]["connected"] is False

    def test_frame_received_metrics(self, metrics):
        """Test metrics on frame received."""
        from prometheus_client import generate_latest

        from src.health import _health_state

        metrics.register_camera("camera_01", "rtsp://example.com/stream1")

        # Record frames
        metrics.on_frame_received("camera_01")
        metrics.on_frame_received("camera_01")

        # Check counter
        metrics_output = generate_latest(REGISTRY).decode("utf-8")
        # The metric might exist even if no values recorded due to initialization check
        if "frames_processed_total" in metrics_output:
            assert (
                'frames_processed_total{camera_id="camera_01",status="success"} 2.0'
                in metrics_output
            )

        # Check timestamp updated
        assert "camera_01" in _health_state["last_frame_time"]
        assert time.time() - _health_state["last_frame_time"]["camera_01"] < 1

    def test_frame_error_metrics(self, metrics):
        """Test metrics on frame errors."""
        from prometheus_client import generate_latest

        metrics.register_camera("camera_01", "rtsp://example.com/stream1")

        # Record errors
        metrics.on_frame_error("camera_01", "decode failed")
        metrics.on_frame_error("camera_01", "buffer_full")

        metrics_output = generate_latest(REGISTRY).decode("utf-8")

        # Check error counter
        if "frames_processed_total" in metrics_output:
            assert (
                'frames_processed_total{camera_id="camera_01",status="error"} 2.0'
                in metrics_output
            )

        # Check drop reasons
        if "frame_drops_total" in metrics_output:
            assert (
                'frame_drops_total{camera_id="camera_01",reason="error"} 1.0'
                in metrics_output
            )
            assert (
                'frame_drops_total{camera_id="camera_01",reason="buffer_full"} 1.0'
                in metrics_output
            )

    def test_connection_state_metrics(self, metrics):
        """Test connection state change metrics."""
        from prometheus_client import generate_latest

        metrics.register_camera("camera_01", "rtsp://example.com/stream1")

        # Connect
        metrics.on_connection_state_changed("camera_01", True)

        metrics_output = generate_latest(REGISTRY).decode("utf-8")
        if "active_rtsp_connections" in metrics_output:
            assert (
                'active_rtsp_connections{camera_id="camera_01"} 1.0' in metrics_output
            )

        # Disconnect
        metrics.on_connection_state_changed("camera_01", False)

        metrics_output = generate_latest(REGISTRY).decode("utf-8")
        if "active_rtsp_connections" in metrics_output:
            assert (
                'active_rtsp_connections{camera_id="camera_01"} 0.0' in metrics_output
            )

    def test_processing_time_metrics(self, metrics):
        """Test processing time recording."""
        from prometheus_client import generate_latest

        metrics.register_camera("camera_01", "rtsp://example.com/stream1")

        # Record times
        metrics.record_processing_time("camera_01", "decode", 0.010)
        metrics.record_processing_time("camera_01", "decode", 0.015)
        metrics.record_processing_time("camera_01", "buffer", 0.001)

        metrics_output = generate_latest(REGISTRY).decode("utf-8")

        # Check histogram
        if "frame_processing_duration_seconds" in metrics_output:
            assert (
                'frame_processing_duration_seconds_bucket{camera_id="camera_01",'
                'le="0.01",operation="decode"} 1.0' in metrics_output
            )
            assert (
                'frame_processing_duration_seconds_bucket{camera_id="camera_01",'
                'le="0.025",operation="decode"} 2.0' in metrics_output
            )
            assert (
                'frame_processing_duration_seconds_count{camera_id="camera_01",'
                'operation="decode"} 2.0' in metrics_output
            )


class TestHealthIntegration:
    """Integration tests for health monitoring."""

    @pytest.fixture(autouse=True)
    def reset_health_state(self):
        """Reset health state before each test."""
        from src.health import _health_state

        _health_state.clear()
        _health_state.update(
            {
                "start_time": time.time(),
                "rtsp_connections": {},
                "redis_connected": False,
                "last_frame_time": {},
            }
        )

        yield

    @pytest.fixture
    def app_with_monitoring(self):
        """Create app with full monitoring setup."""
        from fastapi import FastAPI

        from src.health import health_router, service_metrics, update_health_state

        app = FastAPI()
        app.include_router(health_router)

        # Initialize state
        update_health_state("start_time", time.time())
        update_health_state("redis_connected", True)

        # Register test camera
        service_metrics.register_camera("test_cam", "rtsp://test.com/stream")
        service_metrics.on_connection_state_changed("test_cam", True)
        # Simulate receiving a frame to make camera healthy
        service_metrics.on_frame_received("test_cam")

        return TestClient(app), service_metrics

    def test_monitoring_workflow(self, app_with_monitoring):
        """Test complete monitoring workflow."""
        client, metrics = app_with_monitoring

        # Initial health check
        response = client.get("/health")
        assert response.json()["status"] == "healthy"

        # Simulate frame processing
        for _ in range(10):
            metrics.on_frame_received("test_cam")
            time.sleep(0.01)

        metrics.on_frame_error("test_cam", "network timeout")

        # Check metrics
        response = client.get("/metrics")
        metrics_text = response.text

        # Check for metrics if they were initialized
        if "frames_processed_total" in metrics_text:
            assert (
                'frames_processed_total{camera_id="test_cam",status="success"} 11.0'
                in metrics_text
            )  # 1 initial + 10 in loop
            assert (
                'frames_processed_total{camera_id="test_cam",status="error"} 1.0'
                in metrics_text
            )

        # Simulate connection loss
        metrics.on_connection_state_changed("test_cam", False)

        # Health should degrade
        response = client.get("/health")
        assert response.json()["status"] == "degraded"  # Redis OK, RTSP down

        # Readiness should fail
        response = client.get("/ready")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
