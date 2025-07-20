"""Repository pattern for database operations."""

from typing import List, Optional
from uuid import UUID

import structlog
from models import ExampleEntity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ExampleRepository:
    """Repository for example entity operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
        self.logger = structlog.get_logger()

    async def create(
        self,
        name: str,
        description: str = None,
        data: dict = None,
        correlation_id: UUID = None,
    ) -> ExampleEntity:
        """Create a new entity."""
        entity = ExampleEntity(
            name=name,
            description=description,
            data=data or {},
            correlation_id=correlation_id,
        )

        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)

        self.logger.info(
            "entity_created",
            entity_id=str(entity.id),
            name=name,
        )

        return entity

    async def get_by_id(self, entity_id: UUID) -> Optional[ExampleEntity]:
        """Get entity by ID."""
        query = select(ExampleEntity).where(ExampleEntity.id == entity_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ExampleEntity]:
        """Get all entities with pagination."""
        query = (
            select(ExampleEntity)
            .limit(limit)
            .offset(offset)
            .order_by(ExampleEntity.created_at.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, entity_id: UUID, **kwargs) -> Optional[ExampleEntity]:
        """Update entity by ID."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return None

        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        await self.db.flush()
        await self.db.refresh(entity)

        self.logger.info(
            "entity_updated",
            entity_id=str(entity_id),
            updated_fields=list(kwargs.keys()),
        )

        return entity

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity by ID."""
        entity = await self.get_by_id(entity_id)
        if not entity:
            return False

        await self.db.delete(entity)
        await self.db.flush()

        self.logger.info("entity_deleted", entity_id=str(entity_id))
        return True
