"""Example service using BaseService."""

import asyncio
import random
from typing import Any, Dict

from src.shared.base_service import BaseService
from src.shared.telemetry.decorators import traced


class ExampleService(BaseService):
    """Example service demonstrating BaseService usage."""

    def __init__(self):
        """Initialize example service."""
        super().__init__(
            name="example-service",
            version="1.0.0",
            port=8080,
            description="Example service demonstrating BaseService features",
        )

        # Service state
        self.processed_count = 0
        self.error_count = 0
        self._processing_task = None

    def setup_routes(self):
        """Setup service-specific routes."""
        super().setup_routes()

        @self.app.get("/stats")
        async def get_stats() -> Dict[str, Any]:
            """Get service statistics."""
            return {
                "processed": self.processed_count,
                "errors": self.error_count,
                "error_rate": self.error_count / max(1, self.processed_count),
            }

        @self.app.post("/process")
        @traced(span_name="process_request")
        async def process_request(data: Dict[str, Any]) -> Dict[str, Any]:
            """Process a request."""
            # Simulate processing
            await asyncio.sleep(random.uniform(0.1, 0.5))

            # Random chance of error
            if random.random() < 0.1:
                self.error_count += 1
                self.metrics.increment_errors("processing_error")
                raise ValueError("Random processing error")

            self.processed_count += 1
            self.metrics.increment_frames_processed()

            return {"status": "processed", "id": data.get("id", "unknown")}

    async def start(self):
        """Start the service."""
        await super().start()

        # Start background processing
        self._processing_task = asyncio.create_task(self._background_processor())

        print(f"🚀 {self.name} ready to process requests")

    async def stop(self):
        """Stop the service."""
        print(f"🛑 Stopping {self.name}...")

        # Cancel background task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        await super().stop()

    async def _background_processor(self):
        """Background processing task."""
        while True:
            try:
                await asyncio.sleep(5)

                # Simulate background work
                with self.tracer.start_as_current_span("background_process"):
                    self.metrics.record_processing_time(
                        "background", random.uniform(0.01, 0.1)
                    )

                    print(
                        f"📊 Stats: {self.processed_count} processed, "
                        f"{self.error_count} errors"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Background processor error: {e}")
                self.metrics.increment_errors("background_error")


async def main():
    """Run the example service."""
    service = ExampleService()

    try:
        await service.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
