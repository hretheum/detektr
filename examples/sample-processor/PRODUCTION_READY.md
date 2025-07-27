# Production-Ready Sample Processor

This document outlines the production-ready improvements made to the sample processor service.

## Critical Security Improvements

### 1. Request Size Validation
- **Base64 frame data**: Limited to ~7.5MB (10MB base64)
- **Metadata**: Limited to 100KB
- **Total request size**: Limited to 10MB
- **Frame size validation**: Max 100MB per frame in memory

### 2. Input Validation
- Proper base64 validation for frame data
- Metadata size limits to prevent DoS
- Frame dimension and data type validation
- Request header validation

### 3. Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### 4. Host Header Validation
- TrustedHostMiddleware to prevent host header attacks
- Configurable via `ALLOWED_HOSTS` environment variable

### 5. CORS Configuration
- Configurable origins (not wildcard in production)
- Limited to GET and POST methods
- Proper credential handling

### 6. Rate Limiting
- Simple rate limiting middleware
- Configurable via `MAX_REQUESTS_PER_MINUTE`
- Excludes health check endpoints

## Application State Management

### Fixed Global State Issue
- Replaced global variables with `AppState` class
- All state properly encapsulated
- Thread-safe access patterns
- No shared mutable state

## Connection Pooling

### HTTP Client Improvements
- Connection pool with configurable size
- DNS caching (5 minutes TTL)
- Proper connection cleanup
- Configurable timeouts:
  - Connection timeout: 30s default
  - Read timeout: 60s default

### Benefits
- Reduced connection overhead
- Better performance under load
- Prevents connection exhaustion
- Automatic retry on transient failures

## Graceful Shutdown

### Implementation
- Signal handlers for SIGTERM and SIGINT
- Configurable shutdown timeout (30s default)
- Proper cleanup sequence:
  1. Stop accepting new requests
  2. Stop frame consumer
  3. Wait for in-flight requests
  4. Clean up processor resources
  5. Close HTTP sessions

### Timeout Handling
- Forces shutdown after timeout
- Prevents hanging on shutdown
- Logs timeout events

## State Machine Improvements

### Fixed Callback Registration
- Proper state enum imports
- Defensive programming with hasattr checks
- Graceful degradation if state machine unavailable
- Error state transitions on failures

### Resource Management
- Proper resource allocation with context managers
- Fallback handling if resource manager unavailable
- Memory limit validation on frames

## Error Handling

### Consumer Improvements
- Exponential backoff on errors
- Session recreation after repeated failures
- Periodic health checks
- Detailed error logging with types
- Return count of successfully processed frames

### API Improvements
- Proper 503 responses during shutdown
- Detailed error messages
- Request validation before processing
- Timeout handling

## Monitoring and Observability

### Metrics
- Request counting
- Frame processing statistics
- Resource usage tracking
- Error rate monitoring

### Health Checks
- Detailed health status
- Component status tracking
- Shutdown state indication
- Consumer health monitoring

### Logging
- Structured logging with context
- Error type information
- Processing statistics
- Performance metrics

## Configuration

### Environment Variables
See `config/production.env.example` for full list:
- Security settings (CORS, hosts, rate limits)
- Connection pool configuration
- Resource limits
- Timeout settings
- Observability configuration

### Best Practices
1. Use environment-specific configuration
2. Never use wildcard CORS in production
3. Set appropriate resource limits
4. Monitor and adjust timeouts
5. Enable metrics and tracing

## Deployment Recommendations

### Container Configuration
```yaml
resources:
  limits:
    memory: "1Gi"
    cpu: "2"
  requests:
    memory: "512Mi"
    cpu: "1"

livenessProbe:
  httpGet:
    path: /health
    port: 8099
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8099
  initialDelaySeconds: 10
  periodSeconds: 5

lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 15"]
```

### Load Balancer Configuration
- Enable connection draining
- Set appropriate timeouts
- Configure health checks
- Use proper TLS termination

### Monitoring Setup
1. Prometheus metrics endpoint at `/metrics`
2. Distributed tracing with Jaeger
3. Structured logging to centralized system
4. Alert on error rates and resource usage

## Security Checklist

- [ ] Configure CORS origins (not wildcard)
- [ ] Set allowed hosts
- [ ] Enable rate limiting
- [ ] Use HTTPS only
- [ ] Configure proper timeouts
- [ ] Set resource limits
- [ ] Enable security headers
- [ ] Validate all inputs
- [ ] Monitor error rates
- [ ] Regular security updates

## Performance Tuning

### Connection Pool
- Start with 10 connections
- Monitor connection usage
- Increase if seeing connection waits
- Balance with memory usage

### Batch Processing
- Default batch size: 10
- Adjust based on frame size
- Monitor processing latency
- Balance throughput vs latency

### Resource Allocation
- Monitor CPU and memory usage
- Adjust limits based on load
- Use horizontal scaling for high load
- Consider GPU allocation if available

## Testing Production Readiness

### Load Testing
```bash
# Test rate limiting
for i in {1..100}; do curl -X POST http://localhost:8099/process -d '{"frame_data":"test"}' & done

# Test graceful shutdown
kill -TERM <pid>

# Test connection pooling
ab -n 1000 -c 50 http://localhost:8099/health
```

### Security Testing
- Verify CORS headers
- Test host header validation
- Check security headers
- Validate input limits

### Monitoring Testing
- Verify metrics collection
- Test distributed tracing
- Check health endpoints
- Validate error logging
