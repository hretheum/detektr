"""
Base Service Template - A complete example service with all required patterns.

This service demonstrates:
- Event sourcing pattern
- Full observability (tracing, metrics, logs)
- Clean architecture with repository pattern
- Health checks with database connectivity
- Correlation ID propagation
- RESTful API design
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from database import get_db, init_db
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from models import ExampleEntity
from pydantic import BaseModel, Field
from repositories import ExampleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from telemetry import (
    ObservabilityMiddleware,
    business_operations_total,
    get_or_create_correlation_id,
    init_telemetry,
    traced,
    track_metrics_middleware,
)

# Configure structured logging
logger = structlog.get_logger()


# API Models
class CreateEntityRequest(BaseModel):
    """Request model for creating an entity."""

    name: str = Field(description="Entity name", min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, description="Entity description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional data")


class UpdateEntityRequest(BaseModel):
    """Request model for updating an entity."""

    name: Optional[str] = Field(default=None, description="Entity name")
    description: Optional[str] = Field(default=None, description="Entity description")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")


class EntityResponse(BaseModel):
    """Response model for entity."""

    id: UUID
    name: str
    description: Optional[str]
    correlation_id: Optional[UUID]
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
    version: str
    database: bool
    checks: Dict[str, bool]


# Service layer
class BaseTemplateService:
    """Service for managing entities."""

    def __init__(self):
        """Initialize service."""
        self.logger = structlog.get_logger()

    @traced("create_entity")
    async def create_entity(
        self, request: CreateEntityRequest, db: AsyncSession
    ) -> ExampleEntity:
        """Create a new entity."""
        correlation_id = get_or_create_correlation_id()

        self.logger.info(
            "creating_entity",
            name=request.name,
            has_description=bool(request.description),
        )

        repo = ExampleRepository(db)
        entity = await repo.create(
            name=request.name,
            description=request.description,
            data=request.data,
            correlation_id=correlation_id,
        )

        business_operations_total.labels(
            operation="create_entity", status="success"
        ).inc()

        self.logger.info(
            "entity_created",
            entity_id=str(entity.id),
            name=entity.name,
        )

        return entity

    @traced("get_entity")
    async def get_entity(
        self, entity_id: UUID, db: AsyncSession
    ) -> Optional[ExampleEntity]:
        """Get entity by ID."""
        self.logger.info("fetching_entity", entity_id=str(entity_id))

        repo = ExampleRepository(db)
        entity = await repo.get_by_id(entity_id)

        if entity:
            business_operations_total.labels(
                operation="get_entity", status="found"
            ).inc()
        else:
            business_operations_total.labels(
                operation="get_entity", status="not_found"
            ).inc()

        return entity

    @traced("list_entities")
    async def list_entities(
        self, db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> List[ExampleEntity]:
        """List all entities with pagination."""
        self.logger.info("listing_entities", limit=limit, offset=offset)

        repo = ExampleRepository(db)
        entities = await repo.get_all(limit=limit, offset=offset)

        business_operations_total.labels(
            operation="list_entities", status="success"
        ).inc()

        return entities

    @traced("update_entity")
    async def update_entity(
        self, entity_id: UUID, request: UpdateEntityRequest, db: AsyncSession
    ) -> Optional[ExampleEntity]:
        """Update entity."""
        self.logger.info("updating_entity", entity_id=str(entity_id))

        repo = ExampleRepository(db)
        update_data = request.model_dump(exclude_unset=True)

        entity = await repo.update(entity_id, **update_data)

        if entity:
            business_operations_total.labels(
                operation="update_entity", status="success"
            ).inc()
        else:
            business_operations_total.labels(
                operation="update_entity", status="not_found"
            ).inc()

        return entity

    @traced("delete_entity")
    async def delete_entity(self, entity_id: UUID, db: AsyncSession) -> bool:
        """Delete entity."""
        self.logger.info("deleting_entity", entity_id=str(entity_id))

        repo = ExampleRepository(db)
        deleted = await repo.delete(entity_id)

        if deleted:
            business_operations_total.labels(
                operation="delete_entity", status="success"
            ).inc()
        else:
            business_operations_total.labels(
                operation="delete_entity", status="not_found"
            ).inc()

        return deleted

    @traced("health_check")
    async def check_health(self, db: AsyncSession) -> Dict[str, bool]:
        """Perform health checks."""
        checks = {
            "service": True,
            "database": await self._check_database(db),
        }

        self.logger.info("health_check_performed", checks=checks)
        return checks

    async def _check_database(self, db: AsyncSession) -> bool:
        """Check database connectivity."""
        try:
            from sqlalchemy import text

            await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error("database_health_check_failed", error=str(e))
            return False


# Create service instance
service = BaseTemplateService()


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("service_starting", service_name=SERVICE_NAME)

    # Initialize telemetry
    init_telemetry()

    # Initialize database
    await init_db()

    logger.info("service_started")

    yield

    logger.info("service_stopping")
    # Cleanup would go here
    logger.info("service_stopped")


# Service configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "base-template")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")

# Create FastAPI app
app = FastAPI(
    title="Base Template Service",
    description="A template service demonstrating all required patterns",
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(ObservabilityMiddleware)
app.middleware("http")(track_metrics_middleware)


# API Endpoints
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check(db: AsyncSession = Depends(get_db)):  # noqa: B008
    """
    Health check endpoint.

    Returns service status and database connectivity.
    """
    checks = await service.check_health(db)

    return HealthResponse(
        status="healthy" if all(checks.values()) else "degraded",
        timestamp=datetime.utcnow(),
        version=SERVICE_VERSION,
        database=checks.get("database", False),
        checks=checks,
    )


@app.post(
    "/api/v1/entities",
    response_model=EntityResponse,
    status_code=201,
    tags=["entities"],
)
async def create_entity(
    request: CreateEntityRequest, db: AsyncSession = Depends(get_db)  # noqa: B008
):
    """
    Create a new entity.

    This endpoint demonstrates all patterns including tracing, metrics, and logging.
    """
    entity = await service.create_entity(request, db)

    return EntityResponse(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        correlation_id=entity.correlation_id,
        data=entity.data,
        metadata=entity.metadata_json,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@app.get(
    "/api/v1/entities/{entity_id}",
    response_model=EntityResponse,
    tags=["entities"],
)
async def get_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    Get entity by ID.

    Returns 404 if entity not found.
    """
    entity = await service.get_entity(entity_id, db)

    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return EntityResponse(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        correlation_id=entity.correlation_id,
        data=entity.data,
        metadata=entity.metadata_json,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@app.get(
    "/api/v1/entities",
    response_model=List[EntityResponse],
    tags=["entities"],
)
async def list_entities(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    limit: int = Query(default=100, ge=1, le=1000),  # noqa: B008
    offset: int = Query(default=0, ge=0),  # noqa: B008
):
    """
    List all entities with pagination.

    Supports limit and offset parameters.
    """
    entities = await service.list_entities(db, limit=limit, offset=offset)

    return [
        EntityResponse(
            id=e.id,
            name=e.name,
            description=e.description,
            correlation_id=e.correlation_id,
            data=e.data,
            metadata=e.metadata_json,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in entities
    ]


@app.put(
    "/api/v1/entities/{entity_id}",
    response_model=EntityResponse,
    tags=["entities"],
)
async def update_entity(
    entity_id: UUID,
    request: UpdateEntityRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    Update entity by ID.

    Only provided fields will be updated.
    """
    entity = await service.update_entity(entity_id, request, db)

    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return EntityResponse(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        correlation_id=entity.correlation_id,
        data=entity.data,
        metadata=entity.metadata_json,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


@app.delete(
    "/api/v1/entities/{entity_id}",
    status_code=204,
    tags=["entities"],
)
async def delete_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    Delete entity by ID.

    Returns 404 if entity not found.
    """
    deleted = await service.delete_entity(entity_id, db)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return None


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/", tags=["info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api": "/api/v1/entities",
            "docs": "/docs",
        },
        "correlation_id": str(get_or_create_correlation_id()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production") == "development",
    )
