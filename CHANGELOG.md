# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
