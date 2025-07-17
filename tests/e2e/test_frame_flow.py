"""End-to-end tests for complete frame processing flow."""

import asyncio
import time
from datetime import datetime

import pytest
import requests
from testcontainers.compose import DockerCompose

from src.shared.kernel.domain import Frame


@pytest.mark.e2e
@pytest.mark.slow
class TestFrameFlowE2E:
    """End-to-end tests simulating real usage."""

    @pytest.fixture(scope="class")
    def docker_services(self):
        """Start all services using docker-compose."""
        compose = DockerCompose(
            filepath=".", compose_file_name="docker-compose.test.yml", pull=True
        )

        with compose:
            # Wait for services to be ready
            time.sleep(10)
            yield compose

    @pytest.fixture
    def service_urls(self, docker_services):
        """Get service URLs."""
        return {
            "frame_processor": "http://localhost:8081",
            "prometheus": "http://localhost:9090",
            "jaeger": "http://localhost:16686",
        }

    def wait_for_service(self, url: str, timeout: int = 30):
        """Wait for service to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health")
                if response.status_code == 200:
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(1)

        return False

    @pytest.mark.asyncio
    async def test_complete_frame_journey(self, service_urls):
        """Test complete frame journey from API to storage."""
        processor_url = service_urls["frame_processor"]

        # Wait for service
        assert self.wait_for_service(processor_url), "Frame processor not ready"

        # Submit frame for processing
        frame_data = {
            "camera_id": "e2e_test_camera",
            "timestamp": datetime.now().isoformat(),
        }

        response = requests.post(f"{processor_url}/process", json=frame_data)

        assert response.status_code == 200
        result = response.json()

        # Verify response
        assert result["success"] is True
        assert "frame_id" in result
        assert result["processing_time_ms"] > 0
        assert "detections" in result

        frame_id = result["frame_id"]

        # Verify metrics were recorded
        time.sleep(2)  # Wait for metrics to be scraped

        metrics_response = requests.get(f"{processor_url}/metrics")
        assert metrics_response.status_code == 200
        metrics_text = metrics_response.text

        assert "detektor_frame_processor_frames_processed_total" in metrics_text
        assert "detektor_frame_processor_processing_duration_seconds" in metrics_text

        # Verify trace was created
        traces_response = requests.get(
            f"{service_urls['jaeger']}/api/traces",
            params={"service": "frame-processor", "limit": 10},
        )

        if traces_response.status_code == 200:
            traces = traces_response.json()
            # Should have at least one trace
            assert len(traces.get("data", [])) > 0

    @pytest.mark.asyncio
    async def test_concurrent_e2e_processing(self, service_urls):
        """Test system handles concurrent requests."""
        processor_url = service_urls["frame_processor"]

        assert self.wait_for_service(processor_url)

        # Create multiple concurrent requests
        async def submit_frame(i: int):
            """Submit frame via HTTP."""
            import aiohttp

            async with aiohttp.ClientSession() as session:
                frame_data = {
                    "camera_id": f"e2e_cam_{i}",
                    "timestamp": datetime.now().isoformat(),
                }

                async with session.post(
                    f"{processor_url}/process", json=frame_data
                ) as response:
                    return await response.json()

        # Submit 20 frames concurrently
        results = await asyncio.gather(
            *[submit_frame(i) for i in range(20)], return_exceptions=True
        )

        # Verify most succeeded
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful) >= 18  # Allow for some failures

        # Check service stats
        stats_response = requests.get(f"{processor_url}/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()

        assert stats["processed"] >= 18
        assert stats["success_rate"] >= 0.9

    @pytest.mark.asyncio
    async def test_observability_integration(self, service_urls):
        """Test observability stack captures all signals."""
        processor_url = service_urls["frame_processor"]
        prometheus_url = service_urls["prometheus"]

        assert self.wait_for_service(processor_url)

        # Process some frames
        for i in range(5):
            frame_data = {
                "camera_id": f"observability_test_{i}",
                "timestamp": datetime.now().isoformat(),
            }
            requests.post(f"{processor_url}/process", json=frame_data)
            await asyncio.sleep(0.5)

        # Wait for metrics collection
        time.sleep(5)

        # Query Prometheus for metrics
        query_response = requests.get(
            f"{prometheus_url}/api/v1/query",
            params={
                "query": "rate(detektor_frame_processor_frames_processed_total[1m])"
            },
        )

        if query_response.status_code == 200:
            data = query_response.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                # Should have metrics
                assert len(results) > 0

                # Verify rate is positive
                for result in results:
                    value = float(result["value"][1])
                    assert value > 0

    def test_service_health_monitoring(self, service_urls):
        """Test health check endpoints work correctly."""
        processor_url = service_urls["frame_processor"]

        assert self.wait_for_service(processor_url)

        # Check all monitoring endpoints
        endpoints = ["/health", "/ready", "/info", "/metrics"]

        for endpoint in endpoints:
            response = requests.get(f"{processor_url}{endpoint}")
            assert response.status_code == 200

            if endpoint == "/info":
                info = response.json()
                assert info["name"] == "frame-processor"
                assert info["status"] == "running"
                assert info["uptime"] > 0
