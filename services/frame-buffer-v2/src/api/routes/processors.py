"""Processor management API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.models import ProcessorResponse
from src.models import ProcessorRegistration
from src.orchestrator.processor_registry import ProcessorInfo, ProcessorRegistry

router = APIRouter()


async def get_registry(request: Request) -> ProcessorRegistry:
    """Get registry from app state."""
    return request.app.state.registry


@router.post(
    "/register",
    status_code=201,
    response_model=ProcessorResponse,
    summary="Register a new processor",
    description="Register a new processor with its capabilities and capacity",
)
async def register_processor(
    registration: ProcessorRegistration,
    registry: ProcessorRegistry = Depends(get_registry),
) -> ProcessorInfo:
    """Register a new processor."""

    # Convert to ProcessorInfo
    processor = ProcessorInfo.from_registration(registration)

    # Register
    success = await registry.register(processor)
    if not success:
        raise HTTPException(409, "Processor already registered")

    return processor


@router.get(
    "/",
    response_model=List[ProcessorResponse],
    summary="List all processors",
    description="Get a list of all registered processors",
)
async def list_processors(
    registry: ProcessorRegistry = Depends(get_registry),
) -> List[ProcessorInfo]:
    """List all registered processors."""
    return await registry.list_all()


@router.get(
    "/{processor_id}",
    response_model=ProcessorResponse,
    summary="Get processor by ID",
    description="Get detailed information about a specific processor",
)
async def get_processor(
    processor_id: str, registry: ProcessorRegistry = Depends(get_registry)
) -> ProcessorInfo:
    """Get specific processor by ID."""

    processor = await registry.get_processor(processor_id)
    if not processor:
        raise HTTPException(404, f"Processor {processor_id} not found")

    return processor


@router.put("/{processor_id}")
async def update_processor(
    processor_id: str, registration: ProcessorRegistration, request: Request
) -> ProcessorInfo:
    """Update processor information."""
    registry = request.app.state.registry

    # Ensure ID matches
    if registration.id != processor_id:
        raise HTTPException(400, "Processor ID mismatch")

    # Convert to ProcessorInfo
    processor = ProcessorInfo.from_registration(registration)

    # Update
    success = await registry.update(processor)
    if not success:
        raise HTTPException(404, f"Processor {processor_id} not found")

    return processor


@router.delete("/{processor_id}", status_code=204)
async def unregister_processor(processor_id: str, request: Request):
    """Unregister a processor."""
    registry = request.app.state.registry

    success = await registry.unregister(processor_id)
    if not success:
        raise HTTPException(404, f"Processor {processor_id} not found")


@router.get("/search/")
async def find_by_capability(capability: str, request: Request) -> List[ProcessorInfo]:
    """Find processors by capability."""
    registry = request.app.state.registry
    return await registry.find_by_capability(capability)
