# Base Service Template

This is a template for creating new services in the Detektor project. It includes all the required patterns and best practices.

## Features

- ✅ Full observability (OpenTelemetry tracing, Prometheus metrics, structured logging)
- ✅ Health checks with database connectivity verification
- ✅ Correlation ID propagation
- ✅ Clean architecture with repository pattern
- ✅ Async SQLAlchemy support
- ✅ Docker multi-stage build
- ✅ Type hints and proper error handling
- ✅ Pre-configured for CI/CD deployment

## Quick Start

1. Copy this template to create a new service:
   ```bash
   cp -r services/base-template services/your-service-name
   ```

2. Update the following files:
   - `main.py` - Change SERVICE_NAME and endpoints
   - `Dockerfile` - Update port if needed
   - `requirements.txt` - Add your dependencies

3. Add to GitHub Actions workflow:
   ```yaml
   matrix:
     service: [..., "your-service-name"]
   ```

4. Add to docker-compose.yml and deploy!

## Structure

```
base-template/
├── main.py              # FastAPI application with all patterns
├── models.py            # SQLAlchemy models
├── repositories.py      # Repository pattern for data access
├── telemetry.py         # Observability configuration
├── database.py          # Database connection management
├── requirements.txt     # Python dependencies
├── Dockerfile           # Multi-stage production build
└── README.md           # This file
```

## API Endpoints

- `GET /` - Service info with correlation ID
- `GET /health` - Health check with database status
- `GET /metrics` - Prometheus metrics
- `POST /api/v1/example` - Example endpoint demonstrating all patterns

## Environment Variables

- `SERVICE_NAME` - Name of the service (default: base-template)
- `SERVICE_VERSION` - Version (default: 0.1.0)
- `PORT` - HTTP port (default: 8000)
- `DATABASE_URL` - PostgreSQL connection string
- `OTEL_EXPORTER_OTLP_ENDPOINT` - OpenTelemetry collector endpoint
- `LOG_LEVEL` - Logging level (default: info)

## Testing

```bash
# Unit tests
pytest tests/

# Integration tests
docker-compose -f docker-compose.test.yml up

# Load test
locust -f tests/load_test.py
```
