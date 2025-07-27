# Frame Buffer v2 - Intelligent Frame Orchestrator

## Overview

Frame Buffer v2 is a complete redesign of the frame buffering service, transforming it from a passive buffer into an intelligent orchestrator that manages frame distribution across multiple processors.

## Key Features

- **Event-Driven Architecture**: Uses Redis Streams for reliable message passing
- **Smart Routing**: Routes frames based on processor capabilities and load
- **Backpressure Control**: Prevents overload with intelligent throttling
- **Full Observability**: OpenTelemetry tracing and Prometheus metrics
- **Horizontal Scalability**: Both orchestrators and processors can scale independently

## Architecture

```
RTSP Capture → Redis Stream → Frame Orchestrator → Processor Queues → Processors
                                       ↓
                              Processor Registry
                                       ↓
                              Health Monitor
```

## Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Redis 7+
- PostgreSQL 15+

### Quick Start

1. **Set up development environment:**
   ```bash
   make setup
   ```

2. **Start test environment:**
   ```bash
   make test-env-up
   ```

3. **Run tests:**
   ```bash
   make test
   ```

4. **Start development:**
   ```bash
   make dev
   ```

### Testing

The project follows Test-Driven Development (TDD) methodology:

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-performance

# Run tests in watch mode
make test-watch
```

### Code Quality

```bash
# Format code
make format

# Run linting
make lint

# Type checking
make type-check

# All checks
make check
```

## Project Structure

```
frame-buffer-v2/
├── src/
│   ├── orchestrator/      # Core orchestration logic
│   ├── processors/        # Processor management
│   ├── backpressure/      # Backpressure control
│   ├── health/           # Health monitoring
│   ├── api/              # REST API endpoints
│   ├── models/           # Data models
│   ├── telemetry/        # Tracing and metrics
│   └── migration/        # Migration tools
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── performance/      # Performance tests
└── scripts/              # Utility scripts
```

## Implementation Status

- [x] Test environment setup
- [x] Project structure
- [ ] CI/CD pipeline
- [ ] Data models
- [ ] Core orchestrator
- [ ] Event-driven pipeline
- [ ] Advanced features
- [ ] Production hardening
- [ ] Migration tools

## Documentation

- [Architecture Design](../../docs/frame-buffer-redesign.md)
- [Implementation Plan](../../docs/frame-buffer-implementation-plan.md)
