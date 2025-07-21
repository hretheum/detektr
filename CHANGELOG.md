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
- **Documentation Updates**
  - Updated Phase 2 task completion status
  - Added RTSP Capture API documentation
  - Updated README with current service status
  - Synchronized all deployment documentation

### Changed
- Docker Compose now uses GHCR images for all services
- RTSP service configured on port 8001
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
