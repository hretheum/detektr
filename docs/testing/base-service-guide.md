# BaseService Implementation Guide

## Overview

The `BaseService` class provides a consistent foundation for all microservices in the Detektor project. It includes built-in observability, health checks, and graceful shutdown handling.

## Quick Start

### Creating a New Service

```python
from src.shared.base_service import BaseService

class MyService(BaseService):
    """Example service implementation."""

    def __init__(self):
        super().__init__(
            name="my-service",
            version="1.0.0",
            port=8001
        )

    async def start(self):
        """Start service-specific logic."""
        self.logger.info("Starting MyService")
        # Initialize your service components here
        await self._setup_routes()

    async def stop(self):
        """Stop service-specific logic."""
        self.logger.info("Stopping MyService")
        # Cleanup service components here

    async def _setup_routes(self):
        """Setup service-specific routes."""
        @self.app.get("/api/example")
        async def example_endpoint():
            with self.tracer.start_as_current_span("example_operation"):
                self.metrics.increment_requests()
                return {"message": "Hello from MyService"}
```

### Running the Service

```python
# main.py
import asyncio
from my_service import MyService

async def main():
    service = MyService()
    await service.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Built-in Features

### 1. Health Checks

Every service automatically exposes:

- `GET /health` - Basic health status
- `GET /ready` - Readiness probe for Kubernetes

```python
# Customize health checks
class MyService(BaseService):
    async def _health_check(self) -> dict:
        """Custom health check logic."""
        try:
            # Check database connection
            await self.db.ping()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
```

### 2. Observability

#### Tracing

```python
from opentelemetry import trace

class MyService(BaseService):
    async def process_data(self, data):
        # Automatic span creation
        with self.tracer.start_as_current_span("process_data") as span:
            span.set_attribute("data.size", len(data))

            # Process data
            result = await self._transform_data(data)

            span.set_attribute("result.items", len(result))
            return result
```

#### Metrics

```python
class MyService(BaseService):
    async def handle_request(self, request):
        # Track metrics
        self.metrics.increment_requests()

        start_time = time.time()
        try:
            result = await self._process_request(request)
            self.metrics.increment_successes()
            return result
        except Exception as e:
            self.metrics.increment_errors()
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.observe_duration(duration)
```

#### Logging

```python
class MyService(BaseService):
    async def process_frame(self, frame_id: str):
        # Structured logging with correlation
        self.logger.info(
            "Processing frame",
            extra={
                "frame_id": frame_id,
                "service": self.name,
                "operation": "process_frame"
            }
        )
```

### 3. Graceful Shutdown

The BaseService handles SIGTERM and SIGINT signals automatically:

```python
class MyService(BaseService):
    async def stop(self):
        """Custom cleanup on shutdown."""
        self.logger.info("Graceful shutdown initiated")

        # Stop accepting new requests
        await self.connection_pool.close()

        # Finish processing current requests
        await self.task_queue.join()

        # Close resources
        await self.db.close()

        self.logger.info("Graceful shutdown completed")
```

## Testing with BaseService

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, Mock
from my_service import MyService

class TestMyService:
    @pytest.fixture
    async def service(self):
        """Create service for testing."""
        service = MyService()
        # Mock external dependencies
        service.db = AsyncMock()
        service.cache = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check endpoint."""
        service.db.ping = AsyncMock(return_value=True)

        health = await service._health_check()

        assert health["status"] == "healthy"
        assert health["database"] == "connected"

    @pytest.mark.asyncio
    async def test_process_data_success(self, service):
        """Test successful data processing."""
        test_data = [1, 2, 3]

        result = await service.process_data(test_data)

        assert len(result) == 3
        service.db.save.assert_called_once()
```

### Integration Testing

```python
import pytest
from testcontainers.postgres import PostgresContainer
from my_service import MyService

@pytest.mark.integration
class TestMyServiceIntegration:
    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start PostgreSQL for integration tests."""
        container = PostgresContainer("postgres:15-alpine")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    async def service(self, postgres_container):
        """Create service with real database."""
        service = MyService()
        service.db_url = postgres_container.get_connection_url()
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self, service):
        """Test complete service flow with real dependencies."""
        # Test with real database, cache, etc.
        result = await service.process_data([1, 2, 3])
        assert result is not None
```

## Configuration

### Environment Variables

```python
class MyService(BaseService):
    def __init__(self):
        super().__init__(
            name="my-service",
            version=os.getenv("SERVICE_VERSION", "1.0.0"),
            port=int(os.getenv("SERVICE_PORT", "8001"))
        )

        # Service-specific config
        self.db_url = os.getenv("DATABASE_URL")
        self.redis_url = os.getenv("REDIS_URL")
        self.api_timeout = int(os.getenv("API_TIMEOUT", "30"))
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${SERVICE_PORT}/health || exit 1

CMD ["python", "-m", "src.services.my_service"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  my-service:
    build: .
    environment:
      - SERVICE_NAME=my-service
      - SERVICE_PORT=8001
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379
      - OTLP_ENDPOINT=http://jaeger:4317
    ports:
      - "8001:8001"
    depends_on:
      - postgres
      - redis
      - jaeger
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Best Practices

### 1. Service Naming

```python
# Good: Use kebab-case for service names
service = BaseService(name="face-detection-service")

# Bad: Inconsistent naming
service = BaseService(name="FaceDetection_Service")
```

### 2. Error Handling

```python
class MyService(BaseService):
    async def risky_operation(self):
        try:
            result = await external_api_call()
            return result
        except HTTPException as e:
            self.logger.error("API call failed", extra={"error": str(e)})
            self.metrics.increment_api_errors()
            raise ServiceError(f"External API error: {e}")
        except Exception as e:
            self.logger.exception("Unexpected error in risky_operation")
            self.metrics.increment_unexpected_errors()
            raise
```

### 3. Resource Management

```python
class MyService(BaseService):
    async def start(self):
        # Initialize resources
        self.db_pool = await create_connection_pool(self.db_url)
        self.redis_client = await create_redis_client(self.redis_url)

    async def stop(self):
        # Clean up resources
        if hasattr(self, 'db_pool'):
            await self.db_pool.close()
        if hasattr(self, 'redis_client'):
            await self.redis_client.close()
```

### 4. Circuit Breaker Pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class MyService(BaseService):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def call_external_service(self, data):
        """Call external service with retry logic."""
        try:
            response = await self.http_client.post("/api/process", json=data)
            return response.json()
        except Exception as e:
            self.logger.warning(f"External service call failed: {e}")
            self.metrics.increment_external_failures()
            raise
```

## Advanced Features

### Custom Middleware

```python
from fastapi import Request
import time

class MyService(BaseService):
    async def start(self):
        await super().start()

        @self.app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            return response
```

### Background Tasks

```python
import asyncio
from contextlib import asynccontextmanager

class MyService(BaseService):
    def __init__(self):
        super().__init__(name="background-service")
        self.background_tasks = set()

    async def start(self):
        await super().start()

        # Start background tasks
        task = asyncio.create_task(self._periodic_cleanup())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def stop(self):
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)

        await super().stop()

    async def _periodic_cleanup(self):
        """Run cleanup every hour."""
        while True:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # 1 hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup task failed: {e}")
                await asyncio.sleep(60)  # Retry in 1 minute
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH is set
   export PYTHONPATH=/app
   python -m src.services.my_service
   ```

2. **Missing Environment Variables**
   ```python
   # Add validation in __init__
   def __init__(self):
       super().__init__(name="my-service")

       self.db_url = os.getenv("DATABASE_URL")
       if not self.db_url:
           raise ValueError("DATABASE_URL environment variable is required")
   ```

3. **Health Check Failures**
   ```python
   async def _health_check(self):
       checks = {}

       # Database check
       try:
           await self.db.ping()
           checks["database"] = "healthy"
       except Exception as e:
           checks["database"] = f"unhealthy: {e}"

       # Determine overall status
       overall_status = "healthy" if all(
           status == "healthy" for status in checks.values()
       ) else "unhealthy"

       return {"status": overall_status, "checks": checks}
   ```

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger("src.shared.base_service").setLevel(logging.DEBUG)

# Add telemetry debugging
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
```

## Migration from Legacy Services

### Step-by-Step Migration

1. **Inherit from BaseService**
   ```python
   # Before
   class LegacyService:
       def __init__(self):
           self.app = FastAPI()

   # After
   class MigratedService(BaseService):
       def __init__(self):
           super().__init__(name="migrated-service")
   ```

2. **Move Initialization to start()**
   ```python
   # Before: Everything in __init__
   def __init__(self):
       self.db = Database()
       self.cache = Redis()

   # After: Use start() method
   async def start(self):
       self.db = await Database.create()
       self.cache = await Redis.create()
   ```

3. **Add Cleanup to stop()**
   ```python
   async def stop(self):
       await self.db.close()
       await self.cache.close()
   ```

4. **Update Health Checks**
   ```python
   async def _health_check(self):
       # Implement service-specific health checks
       return {"status": "healthy"}
   ```

## Summary

The BaseService provides:

- ✅ Consistent service architecture
- ✅ Built-in observability (tracing, metrics, logging)
- ✅ Health checks and readiness probes
- ✅ Graceful shutdown handling
- ✅ FastAPI integration
- ✅ Easy testing with mocks and containers
- ✅ Docker and Kubernetes ready

Use this as the foundation for all new services in the Detektor project to ensure consistency and reliability.
