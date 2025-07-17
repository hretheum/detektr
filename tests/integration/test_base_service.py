"""Integration tests for BaseService."""

import asyncio
import signal
import time
from multiprocessing import Process

import pytest
import requests

from src.examples.example_service import ExampleService


def run_service():
    """Run service in a separate process."""

    async def _run():
        service = ExampleService()
        await service.run()

    asyncio.run(_run())


@pytest.mark.integration
@pytest.mark.slow
class TestBaseServiceIntegration:
    """Integration tests for BaseService."""

    def test_service_lifecycle(self):
        """Test full service lifecycle."""
        # Start service in separate process
        process = Process(target=run_service)
        process.start()

        # Wait for service to start
        time.sleep(2)

        try:
            # Check health endpoint
            response = requests.get("http://localhost:8080/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

            # Check ready endpoint
            response = requests.get("http://localhost:8080/ready")
            assert response.status_code == 200
            assert response.json()["ready"] is True

            # Check info endpoint
            response = requests.get("http://localhost:8080/info")
            assert response.status_code == 200
            info = response.json()
            assert info["name"] == "example-service"
            assert info["version"] == "1.0.0"
            assert info["status"] == "running"
            assert info["uptime"] > 0

            # Check metrics endpoint
            response = requests.get("http://localhost:8080/metrics")
            assert response.status_code == 200
            assert "detektor_example_service" in response.text

            # Test custom endpoint
            response = requests.get("http://localhost:8080/stats")
            assert response.status_code == 200
            stats = response.json()
            assert "processed" in stats
            assert "errors" in stats

            # Test processing endpoint
            response = requests.post(
                "http://localhost:8080/process", json={"id": "test-123"}
            )
            # Could be 200 or 500 (random error)
            assert response.status_code in [200, 500]

        finally:
            # Send SIGTERM for graceful shutdown
            process.terminate()
            process.join(timeout=5)

            # Verify process exited cleanly
            assert process.exitcode == 0 or process.exitcode == -15  # SIGTERM

    def test_graceful_shutdown(self):
        """Test graceful shutdown handling."""
        process = Process(target=run_service)
        process.start()

        # Wait for service to start
        time.sleep(2)

        # Verify service is running
        response = requests.get("http://localhost:8080/health")
        assert response.status_code == 200

        # Send SIGTERM
        process.terminate()

        # Service should shutdown gracefully within 5 seconds
        process.join(timeout=5)

        # Verify process exited
        assert not process.is_alive()

        # Service should no longer respond
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get("http://localhost:8080/health", timeout=1)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests during shutdown."""
        process = Process(target=run_service)
        process.start()

        # Wait for service to start
        await asyncio.sleep(2)

        try:
            # Start multiple concurrent requests
            async def make_request(i):
                """Make async request."""
                import aiohttp

                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.post(
                            "http://localhost:8080/process", json={"id": f"test-{i}"}
                        ) as response:
                            return await response.json()
                    except Exception:
                        return None

            # Start 10 concurrent requests
            tasks = [make_request(i) for i in range(10)]

            # After 1 second, start shutdown
            async def shutdown_after_delay():
                await asyncio.sleep(1)
                process.terminate()

            # Run requests and shutdown concurrently
            shutdown_task = asyncio.create_task(shutdown_after_delay())
            results = await asyncio.gather(*tasks, return_exceptions=True)
            await shutdown_task

            # Some requests should have completed
            successful = [r for r in results if isinstance(r, dict)]
            assert len(successful) > 0

        finally:
            process.join(timeout=5)
            assert not process.is_alive()
