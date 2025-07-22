"""
HTTP endpoint for Prometheus metrics scraping.

Provides /metrics endpoint for queue metrics.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from shared.queue.metrics import MetricsEnabledBackpressureHandler


class QueueMetricsApp:
    """FastAPI application for serving queue metrics."""

    def __init__(self) -> None:
        """Initialize metrics app."""
        self.app = FastAPI(
            title="Queue Metrics",
            description="Prometheus metrics for frame queue",
            version="1.0.0",
        )
        self._setup_routes()
        self._handler: Optional[MetricsEnabledBackpressureHandler] = None

    def _setup_routes(self) -> None:
        """Set up API routes."""

        @self.app.get("/metrics", response_class=Response)
        async def metrics() -> Response:
            """Prometheus metrics endpoint."""
            # Update metrics if handler is available
            if self._handler:
                self._handler.metrics_collector.update_metrics()

            # Generate Prometheus format metrics
            metrics_data = generate_latest()
            return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

        @self.app.get("/health")
        async def health() -> Dict[str, Any]:
            """Health check endpoint."""
            status = "healthy"
            details = {}

            if self._handler:
                metrics = self._handler.metrics_collector.get_current_metrics()
                details = {
                    "queue_depth": metrics["queue_depth"],
                    "throughput_sent": metrics["throughput_sent"],
                    "throughput_received": metrics["throughput_received"],
                    "circuit_breaker_state": metrics["circuit_breaker_state"],
                    "adaptive_buffer_size": metrics["adaptive_buffer_size"],
                }

                # Check if circuit breaker is open
                if metrics["circuit_breaker_state"] == 1:  # OPEN
                    status = "degraded"

            return {
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "details": details,
            }

        @self.app.get("/")
        async def root() -> Dict[str, Any]:
            """Root endpoint with links."""
            return {
                "service": "Queue Metrics",
                "endpoints": {
                    "metrics": "/metrics",
                    "health": "/health",
                    "docs": "/docs",
                },
            }

    def set_handler(self, handler: MetricsEnabledBackpressureHandler) -> None:
        """Set the queue handler to monitor."""
        self._handler = handler


def create_metrics_server(
    handler: Optional[MetricsEnabledBackpressureHandler] = None,
) -> FastAPI:
    """
    Create metrics server application.

    Args:
        handler: Optional queue handler to monitor

    Returns:
        FastAPI application instance
    """
    metrics_app = QueueMetricsApp()
    if handler:
        metrics_app.set_handler(handler)
    return metrics_app.app


# Example usage
if __name__ == "__main__":
    import uvicorn

    from shared.queue.backpressure import BackpressureConfig

    # Create handler with metrics
    config = BackpressureConfig()
    handler = MetricsEnabledBackpressureHandler(
        config=config, queue_name="example_queue"
    )

    # Create and run metrics server
    app = create_metrics_server(handler)
    uvicorn.run(app, host="0.0.0.0", port=9090)  # nosec B104
