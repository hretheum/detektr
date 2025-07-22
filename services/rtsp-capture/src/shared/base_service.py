"""Base service class with built-in observability and lifecycle management."""

import asyncio
import os
import signal
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from uvicorn import Config, Server

from shared.telemetry import setup_telemetry
from shared.telemetry.decorators import traced
from shared.telemetry.metrics import get_metrics


class ServiceStatus(Enum):
    """Service status enumeration."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class BaseService:
    """Base service class with telemetry, health checks, and lifecycle management."""

    def __init__(
        self, name: str, version: str = "1.0.0", port: int = 8000, description: str = ""
    ):
        """Initialize base service.

        Args:
            name: Service name
            version: Service version
            port: Port to listen on
            description: Service description
        """
        self.name = name
        self.version = version
        self.port = port
        self.description = description or f"{name} service"

        # Service state
        self.status = ServiceStatus.STOPPED
        self._start_time: Optional[datetime] = None
        self._server: Optional[Server] = None

        # Setup FastAPI app
        self.app = FastAPI(
            title=self.name, version=self.version, description=self.description
        )

        # Setup telemetry
        self._shutdown_telemetry = setup_telemetry(
            service_name=self.name, service_version=self.version
        )

        # Get telemetry instances
        from opentelemetry import metrics, trace

        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        self.metrics = get_metrics(self.name)

        # Setup routes
        self.setup_routes()

    def setup_routes(self):
        """Setup default routes for health, readiness, and metrics."""

        @self.app.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            is_healthy = self.status == ServiceStatus.RUNNING

            response = {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": self.name,
                "version": self.version,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if not is_healthy:
                return Response(
                    content=str(response),
                    status_code=503,
                    media_type="application/json",
                )

            return response

        @self.app.get("/ready")
        async def readiness_check() -> Dict[str, Any]:
            """Readiness check endpoint."""
            is_ready = self.status == ServiceStatus.RUNNING

            response = {
                "ready": is_ready,
                "service": self.name,
                "status": self.status.value,
            }

            if not is_ready:
                return Response(
                    content=str(response),
                    status_code=503,
                    media_type="application/json",
                )

            return response

        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus metrics endpoint."""
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

        @self.app.get("/info")
        async def service_info() -> Dict[str, Any]:
            """Service information endpoint."""
            uptime = None
            if self._start_time:
                uptime = (datetime.utcnow() - self._start_time).total_seconds()

            return {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "status": self.status.value,
                "uptime": uptime,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "port": self.port,
            }

    @traced()
    async def start(self):
        """Start the service."""
        self.status = ServiceStatus.STARTING
        self._start_time = datetime.utcnow()

        # Create server
        config = Config(app=self.app, host="0.0.0.0", port=self.port, log_level="info")
        self._server = Server(config)

        # Start server
        await self._server.startup()

        self.status = ServiceStatus.RUNNING
        self.metrics.set_service_info(
            {"version": self.version, "status": self.status.value}
        )

        print(f"✅ {self.name} started on port {self.port}")

    @traced()
    async def stop(self):
        """Stop the service gracefully."""
        if self.status != ServiceStatus.RUNNING:
            return

        self.status = ServiceStatus.STOPPING
        print(f"🛑 Stopping {self.name}...")

        # Shutdown server
        if self._server:
            await self._server.shutdown()

        # Shutdown telemetry
        if self._shutdown_telemetry:
            self._shutdown_telemetry()

        self.status = ServiceStatus.STOPPED
        print(f"✅ {self.name} stopped")

    def _handle_signal(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        print(f"\n📨 Received signal {signum}")

        # Create task to stop service
        asyncio.create_task(self.stop())

    async def run(self):
        """Run the service with signal handling."""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        try:
            # Start service
            await self.start()

            # Keep running until stopped
            while self.status == ServiceStatus.RUNNING:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            print(f"🚫 {self.name} cancelled")
        except Exception as e:
            print(f"❌ Error in {self.name}: {e}")
            self.status = ServiceStatus.ERROR
            raise
        finally:
            await self.stop()

    def add_middleware(self, middleware_class: type, **kwargs):
        """Add middleware to the FastAPI app.

        Args:
            middleware_class: Middleware class
            **kwargs: Middleware configuration
        """
        self.app.add_middleware(middleware_class, **kwargs)

    def add_exception_handler(self, exc_class: type, handler: Callable):
        """Add exception handler to the FastAPI app.

        Args:
            exc_class: Exception class to handle
            handler: Handler function
        """
        self.app.add_exception_handler(exc_class, handler)

    def mount(self, path: str, app: Any, name: str = None):
        """Mount a sub-application.

        Args:
            path: Path to mount at
            app: Application to mount
            name: Name for the mount
        """
        self.app.mount(path, app, name=name)
