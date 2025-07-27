"""Tests for REST API endpoints."""

import pytest
from httpx import AsyncClient

from src.api.app import app


@pytest.mark.asyncio
async def test_processor_registration_api():
    """Test processor registration via API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register processor
        response = await client.post(
            "/api/v1/processors/register",
            json={
                "id": "test-proc",
                "capabilities": ["face_detection"],
                "capacity": 100,
                "queue": "frames:ready:test-proc",
            },
        )
        assert response.status_code == 201
        assert response.json()["id"] == "test-proc"

        # List processors
        response = await client.get("/api/v1/processors")
        assert response.status_code == 200
        assert len(response.json()) == 1

        # Get specific processor
        response = await client.get("/api/v1/processors/test-proc")
        assert response.status_code == 200
        assert response.json()["capabilities"] == ["face_detection"]

        # Unregister
        response = await client.delete("/api/v1/processors/test-proc")
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_registration():
    """Test duplicate processor registration fails."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First registration
        response = await client.post(
            "/api/v1/processors/register",
            json={
                "id": "dup-proc",
                "capabilities": ["detection"],
                "capacity": 50,
                "queue": "frames:ready:dup-proc",
            },
        )
        assert response.status_code == 201

        # Duplicate registration should fail
        response = await client.post(
            "/api/v1/processors/register",
            json={
                "id": "dup-proc",
                "capabilities": ["detection"],
                "capacity": 50,
                "queue": "frames:ready:dup-proc",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_processor():
    """Test getting nonexistent processor returns 404."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/processors/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_processor():
    """Test updating processor information."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register processor
        await client.post(
            "/api/v1/processors/register",
            json={
                "id": "update-proc",
                "capabilities": ["detection"],
                "capacity": 50,
                "queue": "frames:ready:update-proc",
            },
        )

        # Update processor
        response = await client.put(
            "/api/v1/processors/update-proc",
            json={
                "id": "update-proc",
                "capabilities": ["detection", "tracking"],
                "capacity": 100,
                "queue": "frames:ready:update-proc",
                "metadata": {"version": "2.0"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["capabilities"] == ["detection", "tracking"]
        assert data["capacity"] == 100
        assert data["metadata"]["version"] == "2.0"


@pytest.mark.asyncio
async def test_find_by_capability():
    """Test finding processors by capability."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register multiple processors
        processors = [
            {
                "id": "face-proc-1",
                "capabilities": ["face_detection"],
                "capacity": 100,
                "queue": "frames:ready:face-1",
            },
            {
                "id": "face-proc-2",
                "capabilities": ["face_detection", "emotion_detection"],
                "capacity": 100,
                "queue": "frames:ready:face-2",
            },
            {
                "id": "object-proc-1",
                "capabilities": ["object_detection"],
                "capacity": 100,
                "queue": "frames:ready:object-1",
            },
        ]

        for proc in processors:
            await client.post("/api/v1/processors/register", json=proc)

        # Find face detection processors
        response = await client.get(
            "/api/v1/processors/search?capability=face_detection"
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert all("face_detection" in p["capabilities"] for p in results)


@pytest.mark.asyncio
async def test_invalid_processor_data():
    """Test validation of processor data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Missing required fields
        response = await client.post(
            "/api/v1/processors/register",
            json={"id": "invalid-proc", "capabilities": ["test"]},  # Missing capacity
        )
        assert response.status_code == 422

        # Invalid capacity
        response = await client.post(
            "/api/v1/processors/register",
            json={
                "id": "invalid-proc",
                "capabilities": ["test"],
                "capacity": -10,  # Negative capacity
                "queue": "test",
            },
        )
        assert response.status_code == 422

        # Empty capabilities
        response = await client.post(
            "/api/v1/processors/register",
            json={
                "id": "invalid-proc",
                "capabilities": [],  # Empty
                "capacity": 10,
                "queue": "test",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_docs():
    """Test OpenAPI documentation is available."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert "openapi" in response.json()
        assert "paths" in response.json()
