"""API response models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    service: str
    error: Optional[str] = None


class ProcessorResponse(BaseModel):
    """Processor response model."""

    id: str
    capabilities: List[str]
    capacity: int
    queue: str
    endpoint: Optional[str] = None
    health_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    status_code: int
    request_id: Optional[str] = None
