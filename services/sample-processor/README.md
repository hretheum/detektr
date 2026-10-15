# Sample Processor Service

## Overview
Sample processor demonstrating the base processor framework. Consumes frames from Frame Buffer v2 and publishes results to Redis.

## API Endpoints
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Processing statistics

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `SERVICE_PORT` | `8099` | Service HTTP port |
| `FRAME_BUFFER_URL` | `http://frame-buffer-v2:8002` | Frame Buffer v2 URL |
| `PROCESSOR_NAME` | `sample-processor-1` | Unique processor identifier |

## Development
```bash
# Run locally
cd services/sample-processor
python simple_main.py

# Run tests
pytest tests/
```

## Testing
```bash
# Check if processor is consuming frames
curl http://localhost:8099/status

# Manual test with frame injection
curl -X POST http://localhost:8002/test-frame \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

## Deployment
Service is deployed automatically via GitHub Actions when pushed to main branch.

## Monitoring
- Metrics available at `/metrics`
- Traces sent to Jaeger with service name `sample-processor`
- Results published to Redis stream `sample:results`

## Troubleshooting

### Processor not receiving frames
1. Check Frame Buffer v2 is running: `curl http://frame-buffer-v2:8002/health`
2. Check processor is registered: `curl http://frame-buffer-v2:8002/processors`
3. Check Redis stream has frames: `redis-cli XLEN frames:ready:sample-processor-1`

### High memory usage
- Processor processes frames sequentially
- If processing is slow, frames queue up in Redis
- Monitor queue depth at `/status` endpoint
