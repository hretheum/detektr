#!/usr/bin/env python3
"""Main entry point for metadata-storage service."""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Histogram,
    generate_latest,
)

from src.application.services.metadata_service import MetadataService
from src.infrastructure.database.connection_pool import ConnectionPool
from src.infrastructure.repositories.metadata_repository import (
    TimescaleMetadataRepository,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter(
    "metadata_storage_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)
request_duration = Histogram(
    "metadata_storage_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)


class ServiceState:
    """Service state management."""

    def __init__(self):
        """Initialize service state."""
        self.pool: ConnectionPool = None
        self.metadata_service: MetadataService = None
        self.healthy = False
        self.start_time = datetime.now()


state = ServiceState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting metadata-storage service...")

    # Initialize connection pool
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://detektor:detektor_pass@192.168.1.193:5432/detektor_db",
    )
    state.pool = ConnectionPool(db_url, min_size=5, max_size=20)

    # Initialize repository and service
    repository = TimescaleMetadataRepository(state.pool)
    state.metadata_service = MetadataService(repository)

    # Wait for database connection
    retries = 5
    while retries > 0:
        try:
            await state.pool.get_connection()
            state.healthy = True
            logger.info("Database connection established")
            break
        except Exception as e:
            retries -= 1
            logger.warning(f"Database connection failed, retries left: {retries}")
            if retries > 0:
                await asyncio.sleep(5)
            else:
                logger.error(f"Failed to connect to database: {e}")
                sys.exit(1)

    logger.info("metadata-storage service started successfully")

    yield

    # Cleanup
    logger.info("Shutting down metadata-storage service...")
    if state.pool:
        await state.pool.close()
    logger.info("metadata-storage service stopped")


# Create FastAPI app
app = FastAPI(
    title="Metadata Storage Service",
    description="TimescaleDB-based metadata storage for Detektor",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    if not state.healthy:
        raise HTTPException(status_code=503, detail="Service unhealthy")

    uptime = (datetime.now() - state.start_time).total_seconds()

    return {
        "status": "healthy",
        "service": "metadata-storage",
        "uptime_seconds": uptime,
        "database": "connected" if state.pool else "disconnected",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.post("/metadata")
async def create_metadata(metadata: dict) -> Dict:
    """Create new frame metadata."""
    try:
        # Record metrics
        with request_duration.labels(method="POST", endpoint="/metadata").time():
            result = await state.metadata_service.store_metadata(metadata)
            request_count.labels(
                method="POST", endpoint="/metadata", status="200"
            ).inc()
            return {"success": True, "frame_id": result.frame_id}
    except Exception as e:
        request_count.labels(method="POST", endpoint="/metadata", status="500").inc()
        logger.error(f"Failed to store metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metadata/{frame_id}")
async def get_metadata(frame_id: str) -> Dict:
    """Get metadata by frame ID."""
    try:
        with request_duration.labels(
            method="GET", endpoint="/metadata/{frame_id}"
        ).time():
            result = await state.metadata_service.get_metadata(frame_id)
            if not result:
                request_count.labels(
                    method="GET", endpoint="/metadata/{frame_id}", status="404"
                ).inc()
                raise HTTPException(status_code=404, detail="Metadata not found")
            request_count.labels(
                method="GET", endpoint="/metadata/{frame_id}", status="200"
            ).inc()
            return result.dict()
    except HTTPException:
        raise
    except Exception as e:
        request_count.labels(
            method="GET", endpoint="/metadata/{frame_id}", status="500"
        ).inc()
        logger.error(f"Failed to get metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def handle_shutdown(signum, frame):
    """Handle shutdown signal."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Get configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8005"))

    # Start server
    logger.info(f"Starting metadata-storage service on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
