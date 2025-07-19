# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Frame Buffer implementation with exceptional performance (Phase 2, Task 2)
  - In-memory queue with AsyncIO achieving 80,239 fps
  - Backpressure handling with adaptive buffer sizing (100-10,000 frames)
  - Dead Letter Queue with automatic retry (exponential backoff)
  - Circuit Breaker pattern for graceful degradation
  - Prometheus metrics export on `/metrics` endpoint
  - Health check endpoint on `/health`
  - Frame serialization with MessagePack and LZ4 compression
  - Comprehensive test suite (unit + integration)
- RTSP Capture Service - Block 1 implementation
  - Basic frame capture from RTSP stream
  - OpenCV integration
  - Health check endpoint
- Frame serialization infrastructure (Block 2)
  - MessagePack binary serialization
  - Optional LZ4 compression
  - Performance: <5ms for Full HD frame

### Changed
- Updated project documentation to reflect completed tasks
- Enhanced architecture documentation with implementation details

### Fixed
- Various linting issues (flake8, mypy, black)
- Import optimizations

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
