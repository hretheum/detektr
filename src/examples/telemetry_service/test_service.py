"""Test script for the example telemetry service."""

import asyncio
import json
import logging
import random
import time
from typing import List

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceTester:
    """Test client for the example telemetry service."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        """Initialize tester.

        Args:
            base_url: Base URL of the service
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def test_health_check(self) -> bool:
        """Test health check endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Health check: {data}")

            return data.get("status") == "healthy"

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def test_metrics_endpoint(self) -> bool:
        """Test metrics endpoint."""
        try:
            response = await self.client.get(f"{self.base_url}/metrics")
            response.raise_for_status()

            data = response.json()
            logger.info(f"Metrics info: {data}")

            return "metrics" in data

        except Exception as e:
            logger.error(f"Metrics endpoint failed: {e}")
            return False

    async def test_frame_processing(self, frame_count: int = 5) -> List[dict]:
        """Test frame processing endpoint.

        Args:
            frame_count: Number of frames to process

        Returns:
            List of processing results
        """
        results = []

        for i in range(frame_count):
            frame_id = f"test_frame_{int(time.time() * 1000)}_{i:03d}"
            camera_id = f"test_camera_{random.randint(1, 3):03d}"

            frame_data = {
                "frame_id": frame_id,
                "camera_id": camera_id,
                "frame_data": {
                    "width": random.choice([1920, 1280, 640]),
                    "height": random.choice([1080, 720, 480]),
                    "format": "rgb24",
                    "timestamp": time.time(),
                    "size_bytes": random.randint(100000, 500000),
                },
            }

            try:
                response = await self.client.post(
                    f"{self.base_url}/process", json=frame_data
                )
                response.raise_for_status()

                result = response.json()
                results.append(result)

                logger.info(f"Processed frame {frame_id}: {result['status']}")

                # Add small delay between requests
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Frame processing failed for {frame_id}: {e}")
                results.append(
                    {"frame_id": frame_id, "status": "error", "error": str(e)}
                )

        return results

    async def test_frame_retrieval(self, frame_ids: List[str]) -> List[dict]:
        """Test frame result retrieval.

        Args:
            frame_ids: List of frame IDs to retrieve

        Returns:
            List of retrieval results
        """
        results = []

        for frame_id in frame_ids:
            try:
                response = await self.client.get(f"{self.base_url}/frames/{frame_id}")
                response.raise_for_status()

                result = response.json()
                results.append(result)

                logger.info(f"Retrieved frame {frame_id}")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Frame {frame_id} not found")
                    results.append({"frame_id": frame_id, "status": "not_found"})
                else:
                    logger.error(f"Retrieval failed for {frame_id}: {e}")
                    results.append(
                        {"frame_id": frame_id, "status": "error", "error": str(e)}
                    )
            except Exception as e:
                logger.error(f"Retrieval failed for {frame_id}: {e}")
                results.append(
                    {"frame_id": frame_id, "status": "error", "error": str(e)}
                )

        return results

    async def test_camera_stats(self, camera_ids: List[str]) -> List[dict]:
        """Test camera statistics endpoint.

        Args:
            camera_ids: List of camera IDs to get stats for

        Returns:
            List of camera stats
        """
        results = []

        for camera_id in camera_ids:
            try:
                response = await self.client.get(
                    f"{self.base_url}/cameras/{camera_id}/stats"
                )
                response.raise_for_status()

                result = response.json()
                results.append(result)

                logger.info(f"Camera {camera_id} stats: {result['stats']}")

            except Exception as e:
                logger.error(f"Stats retrieval failed for {camera_id}: {e}")
                results.append(
                    {"camera_id": camera_id, "status": "error", "error": str(e)}
                )

        return results

    async def test_simulation(self) -> dict:
        """Test simulation endpoint."""
        try:
            response = await self.client.post(f"{self.base_url}/simulate")
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Simulation completed: {result['total_frames']} frames, {result['success_count']} successful"
            )

            return result

        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return {"status": "error", "error": str(e)}

    async def run_comprehensive_test(self) -> dict:
        """Run comprehensive test suite."""
        logger.info("Starting comprehensive test suite...")

        results = {
            "health_check": False,
            "metrics": False,
            "frame_processing": [],
            "frame_retrieval": [],
            "camera_stats": [],
            "simulation": {},
            "start_time": time.time(),
        }

        try:
            # Test health check
            results["health_check"] = await self.test_health_check()

            # Test metrics endpoint
            results["metrics"] = await self.test_metrics_endpoint()

            # Test frame processing
            processing_results = await self.test_frame_processing(10)
            results["frame_processing"] = processing_results

            # Extract frame IDs for retrieval test
            frame_ids = [
                r["frame_id"]
                for r in processing_results
                if r.get("status") == "success"
            ]

            # Test frame retrieval
            if frame_ids:
                retrieval_results = await self.test_frame_retrieval(frame_ids[:5])
                results["frame_retrieval"] = retrieval_results

            # Test camera stats
            camera_ids = list(
                set(r["camera_id"] for r in processing_results if "camera_id" in r)
            )
            if camera_ids:
                stats_results = await self.test_camera_stats(camera_ids[:3])
                results["camera_stats"] = stats_results

            # Test simulation
            simulation_result = await self.test_simulation()
            results["simulation"] = simulation_result

            results["end_time"] = time.time()
            results["total_duration"] = results["end_time"] - results["start_time"]

            logger.info(
                f"Comprehensive test completed in {results['total_duration']:.2f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Comprehensive test failed: {e}")
            results["error"] = str(e)
            return results

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    """Run the test suite."""
    tester = ServiceTester()

    try:
        # Wait for service to be ready
        logger.info("Waiting for service to be ready...")
        for i in range(30):  # Wait up to 30 seconds
            if await tester.test_health_check():
                logger.info("Service is ready!")
                break
            await asyncio.sleep(1)
        else:
            logger.error("Service did not become ready in time")
            return

        # Run comprehensive test
        results = await tester.run_comprehensive_test()

        # Print summary
        print("\\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Health Check: {'✓' if results['health_check'] else '✗'}")
        print(f"Metrics Endpoint: {'✓' if results['metrics'] else '✗'}")
        print(
            f"Frame Processing: {sum(1 for r in results['frame_processing'] if r.get('status') == 'success')}/{len(results['frame_processing'])} successful"
        )
        print(
            f"Frame Retrieval: {sum(1 for r in results['frame_retrieval'] if r.get('status') != 'error')}/{len(results['frame_retrieval'])} successful"
        )
        print(
            f"Camera Stats: {sum(1 for r in results['camera_stats'] if r.get('status') != 'error')}/{len(results['camera_stats'])} successful"
        )
        print(
            f"Simulation: {'✓' if results['simulation'].get('total_frames', 0) > 0 else '✗'}"
        )
        print(f"Total Duration: {results.get('total_duration', 0):.2f}s")

        # Check observability
        print("\\nOBSERVABILITY ENDPOINTS:")
        print("- Jaeger UI: http://localhost:16686")
        print("- Prometheus: http://localhost:9090")
        print("- Grafana: http://localhost:3000 (admin/admin)")
        print("- Service Health: http://localhost:8080/health")
        print("- Service Metrics: http://localhost:8080/metrics")

    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
