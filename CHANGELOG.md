# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **RTSP Capture Service** (Phase 2, Blocks 0-5 ✅ COMPLETED)
  - Core RTSP client with PyAV library
  - Auto-reconnect mechanism (5s default)
  - Circular frame buffer with zero-copy operations
  - Redis queue integration (synchronous implementation)
  - Full observability with OpenTelemetry tracing
  - Prometheus metrics (frame_counter, processing_time, buffer_size, errors_total)
  - Health check endpoints (/health, /ready, /metrics, /ping)
  - Multi-stage Dockerfile (204MB optimized image)
  - GitHub Actions CI/CD workflow
  - API documentation
  - **Block 5: Successful deployment to Nebula server**
    - Service running at http://nebula:8001
    - Reolink camera properly configured with /Preview_01_main endpoint
    - RTSP URL: rtsp://192.168.1.195:554/Preview_01_main
    - Service status: "degraded" (Redis not initialized - expected at this stage)
- **Frame Buffer Service** (Phase 2, Block 5 ✅ COMPLETED)
  - Standalone service with Redis Streams backend
  - High-performance buffering (80k fps, 0.01ms latency)
  - Dead Letter Queue (DLQ) for failed frames
  - JSON serialization with LZ4 compression support
  - Full observability with OpenTelemetry and Prometheus
  - Health check and metrics endpoints
  - API endpoints: /frames/enqueue, /frames/dequeue, /frames/status, /frames/dlq/clear
  - Multi-stage Dockerfile with non-root user
  - GitHub Actions CI/CD workflow (frame-buffer-deploy.yml)
  - **Successful deployment to Nebula server**
    - Service running at http://nebula:8002
    - Redis backend on port 6379 with persistence
    - All health checks passing
- **Redis/RabbitMQ Configuration** (Phase 2, Block 0 ✅ COMPLETED)
  - Disk space optimization (cleaned 22GB Docker cache)
  - System partition extended by 100GB
  - Created LVM volumes for data persistence:
    - /data/redis (50GB) - Redis data
    - /data/postgres (100GB) - PostgreSQL data
    - /data/frames (50GB) - Frame storage
  - Docker compose override for log rotation
  - Redis memory limit set to 4GB
  - Telegram monitoring service deployed:
    - Disk space alerts (threshold: 80%)
    - Redis memory alerts (threshold: 3.5GB)
    - Container health monitoring (disabled due to Docker socket issue)
  - Fixed Docker network issue - all containers now in single network
  - SOPS encryption configured for secrets
- **Documentation Updates**
  - Updated Phase 2 task completion status
  - Added RTSP Capture API documentation
  - Added Frame Buffer deployment documentation
  - Added Telegram alerts setup documentation
  - Added disk expansion guide for Nebula
  - Updated README with current service status
  - Synchronized all deployment documentation

### Changed
- Docker Compose now uses GHCR images for all services
- RTSP service configured on port 8001
- Docker network configuration changed to external: true to prevent duplicate networks
- Fixed Python import paths (relative to absolute) for containerized deployment
- Fixed GitHub Actions build context (from services/rtsp-capture to root)
- Updated RTSP path from /stream to /Preview_01_main for Reolink cameras

### Fixed
- "Could not import module 'src.main'" error in production deployment
- ImportError with relative imports in containerized environment
- Dockerfile COPY paths to use absolute paths from project root
- CMD in Dockerfile changed from "src.main:app" to "main:app"
- CI/CD pipeline missing dependencies (opentelemetry-instrumentation-redis==0.43b0)
- Test imports failing due to src.shared module (added mocks)

## [0.2.0] - 2025-07-20

### Added
- **CI/CD Infrastructure** - Complete automation pipeline
  - Self-hosted GitHub Actions runner on Nebula server
  - Automated deployment on push to main branch
  - GitHub Container Registry (GHCR) integration
  - Multi-stage Docker builds with optimization
  - Deployment script (`scripts/deploy-local.sh`)
  - Full sudo permissions for github-runner
- **Service Implementations**
  - GPU demo service with YOLO v8 object detection
  - Example services fully operational (example-otel, frame-tracking, echo-service, base-template)
  - Health check endpoints for all services
  - Full observability integration
- **Documentation**
  - Phase 1 completion report
  - CI/CD implementation guide
  - Self-hosted runner setup documentation

### Changed
- Docker base images optimized (python:3.11-slim)
- Port mappings standardized (8005:8000, 8010:8000)
- Project status updated to reflect Phase 1 completion

### Fixed
- SQLAlchemy metadata reserved word conflict (renamed to metadata_json)
- Missing dependency: opentelemetry-exporter-prometheus
- Docker build context paths in all services
- Service startup issues resolved

## [0.1.0] - 2024-07-19

### Added
- Initial project setup (Phase 0 & 1)
- Docker infrastructure with NVIDIA GPU support
- Observability stack (Jaeger, Prometheus, Grafana, Loki)
- OpenTelemetry SDK integration
- Git repository with pre-commit hooks
- CI/CD pipeline with GitHub Actions
- TDD setup with pytest
- SOPS for secrets management
- Project documentation structure
