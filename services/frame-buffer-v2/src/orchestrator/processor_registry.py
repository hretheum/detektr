"""Processor registry with Redis persistence."""

import json
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from pydantic import BaseModel, validator


class ProcessorInfo(BaseModel):
    """Information about a registered processor."""

    id: str
    capabilities: List[str]
    capacity: int
    queue: str = ""
    endpoint: Optional[str] = None
    health_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = {}

    def __init__(self, **data):
        """Initialize ProcessorInfo with default queue if not provided."""
        if "queue" not in data or not data["queue"]:
            data["queue"] = f"frames:ready:{data['id']}"
        super().__init__(**data)

    @validator("id")
    def validate_id(cls, v):
        """Validate processor ID."""
        if not v or not v.strip():
            raise ValueError("Processor ID cannot be empty")
        return v.strip()

    @validator("capabilities")
    def validate_capabilities(cls, v):
        """Validate capabilities list."""
        if not v:
            raise ValueError("At least one capability is required")
        return v

    @validator("capacity")
    def validate_capacity(cls, v):
        """Validate capacity value."""
        if v <= 0:
            raise ValueError("Capacity must be positive")
        return v

    def to_redis_hash(self) -> Dict[str, str]:
        """Convert to Redis hash format."""
        return {
            "id": self.id,
            "capabilities": json.dumps(self.capabilities),
            "capacity": str(self.capacity),
            "queue": self.queue,
            "endpoint": self.endpoint or "",
            "health_endpoint": self.health_endpoint or "",
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_redis_hash(cls, data: Dict[str, str]) -> "ProcessorInfo":
        """Create from Redis hash data."""
        return cls(
            id=data["id"],
            capabilities=json.loads(data["capabilities"]),
            capacity=int(data["capacity"]),
            queue=data["queue"],
            endpoint=data.get("endpoint") or None,
            health_endpoint=data.get("health_endpoint") or None,
            metadata=json.loads(data.get("metadata", "{}")),
        )

    @classmethod
    def from_registration(cls, registration) -> "ProcessorInfo":
        """Create from ProcessorRegistration model."""
        return cls(
            id=registration.id,
            capabilities=registration.capabilities,
            capacity=registration.capacity,
            queue=registration.queue,
            endpoint=registration.endpoint,
            health_endpoint=registration.health_endpoint,
            metadata=registration.metadata,
        )


class ProcessorRegistry:
    """Registry for managing processor registrations with Redis persistence."""

    def __init__(self, redis_client: aioredis.Redis):
        """Initialize registry with Redis client."""
        self.redis = redis_client
        self.processors_key = "processors:registry"
        self.capabilities_key = "processors:capabilities"

    async def register(self, processor: ProcessorInfo) -> bool:
        """Register a new processor."""
        # Check if already exists
        exists = await self.redis.hexists(self.processors_key, processor.id)
        if exists:
            return False

        # Store processor info
        pipe = self.redis.pipeline()

        # Store in main registry
        pipe.hset(
            self.processors_key, processor.id, json.dumps(processor.to_redis_hash())
        )

        # Index by capabilities
        for capability in processor.capabilities:
            pipe.sadd(f"{self.capabilities_key}:{capability}", processor.id)

        await pipe.execute()
        return True

    async def unregister(self, processor_id: str) -> bool:
        """Unregister a processor."""
        # Get processor info first
        processor = await self.get_processor(processor_id)
        if not processor:
            return False

        pipe = self.redis.pipeline()

        # Remove from main registry
        pipe.hdel(self.processors_key, processor_id)

        # Remove from capability indices
        for capability in processor.capabilities:
            pipe.srem(f"{self.capabilities_key}:{capability}", processor_id)

        await pipe.execute()
        return True

    async def get_processor(self, processor_id: str) -> Optional[ProcessorInfo]:
        """Get processor by ID."""
        data = await self.redis.hget(self.processors_key, processor_id)
        if not data:
            return None

        try:
            processor_data = json.loads(data)
            return ProcessorInfo.from_redis_hash(processor_data)
        except (json.JSONDecodeError, KeyError):
            # Log error in production: logger.error(f"Failed to parse processor data")
            return None

    async def update(self, processor: ProcessorInfo) -> bool:
        """Update processor information."""
        # Check if exists
        existing = await self.get_processor(processor.id)
        if not existing:
            return False

        # If capabilities changed, update indices
        if set(existing.capabilities) != set(processor.capabilities):
            pipe = self.redis.pipeline()

            # Remove from old capability indices
            for cap in existing.capabilities:
                if cap not in processor.capabilities:
                    pipe.srem(f"{self.capabilities_key}:{cap}", processor.id)

            # Add to new capability indices
            for cap in processor.capabilities:
                if cap not in existing.capabilities:
                    pipe.sadd(f"{self.capabilities_key}:{cap}", processor.id)

            await pipe.execute()

        # Update processor data
        await self.redis.hset(
            self.processors_key, processor.id, json.dumps(processor.to_redis_hash())
        )
        return True

    async def find_by_capability(self, capability: str) -> List[ProcessorInfo]:
        """Find all processors with a specific capability."""
        # Get processor IDs with this capability
        processor_ids = await self.redis.smembers(
            f"{self.capabilities_key}:{capability}"
        )

        if not processor_ids:
            return []

        # Batch fetch using pipeline
        pipe = self.redis.pipeline()
        for proc_id in processor_ids:
            pipe.hget(self.processors_key, proc_id)

        results = await pipe.execute()

        processors = []
        for data in results:
            if data:
                try:
                    processor_dict = json.loads(data)
                    processors.append(ProcessorInfo.from_redis_hash(processor_dict))
                except (json.JSONDecodeError, KeyError):
                    continue

        return processors

    async def list_all(self) -> List[ProcessorInfo]:
        """List all registered processors."""
        # Get all processor data
        all_data = await self.redis.hgetall(self.processors_key)

        processors = []
        for proc_data in all_data.values():
            processor_dict = json.loads(proc_data)
            processors.append(ProcessorInfo.from_redis_hash(processor_dict))

        return processors

    async def clear_all(self) -> None:
        """Clear all processors (for testing)."""
        pipe = self.redis.pipeline()

        # Clear main registry
        pipe.delete(self.processors_key)

        # Use SCAN to find and delete capability keys
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=f"{self.capabilities_key}:*", count=100
            )
            if keys:
                pipe.delete(*keys)
            if cursor == 0:
                break

        await pipe.execute()
