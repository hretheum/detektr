# Faza 4 / Zadanie 4: REST/GraphQL API gateway

## Cel zadania

Zbudować unified API gateway zapewniający spójny, bezpieczny dostęp do wszystkich mikroserwisów Detektor z obsługą REST i GraphQL.

## Blok 0: Prerequisites check

#### Zadania atomowe

1. **[ ] Weryfikacja mikroserwisów**
   - **Metryka**: Wszystkie serwisy expose internal APIs
   - **Walidacja**:

     ```bash
     # Check service endpoints
     for service in detection automation management monitoring; do
         curl -s http://detektor-$service:8080/health | jq '.status'
     done
     # All should return "healthy"

     # List internal APIs
     ./scripts/list-internal-apis.sh
     # Should show 10+ endpoints
     ```

   - **Czas**: 0.5h

2. **[ ] Analiza API gateway options**
   - **Metryka**: Wybór między Kong, Traefik, custom FastAPI
   - **Walidacja**:

     ```bash
     # Document decision
     cat docs/architecture/api-gateway-comparison.md
     # Should include performance benchmarks, feature matrix
     ```

   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Gateway infrastructure and routing

#### Zadania atomowe

1. **[ ] API gateway deployment**
   - **Metryka**: Gateway handling all service routes, <10ms overhead
   - **Walidacja**:

     ```bash
     # Deploy gateway
     docker-compose -f docker-compose.gateway.yml up -d

     # Test routing
     curl http://localhost:8000/api/v1/detection/status
     curl http://localhost:8000/api/v1/automation/rules
     curl http://localhost:8000/api/v1/management/cameras

     # Measure overhead
     ./scripts/gateway-latency-test.sh
     # Direct: 5ms, Through gateway: <15ms
     ```

   - **Czas**: 2.5h

2. **[ ] Service discovery integration**
   - **Metryka**: Automatic route updates when services scale
   - **Walidacja**:

     ```python
     from src.gateway.discovery import ServiceRegistry

     registry = ServiceRegistry()

     # Check discovered services
     services = registry.get_services()
     assert len(services) >= 4

     # Test dynamic updates
     # Scale detection service
     os.system("docker-compose scale detection=3")
     time.sleep(10)

     endpoints = registry.get_endpoints("detection")
     assert len(endpoints) == 3
     ```

   - **Czas**: 2h

3. **[ ] Request routing rules**
   - **Metryka**: Path-based and header-based routing
   - **Walidacja**:

     ```bash
     # Test path routing
     curl http://localhost:8000/api/v1/detection/process
     # Routes to detection service

     # Test header routing (API version)
     curl -H "X-API-Version: v2" http://localhost:8000/api/detection/process
     # Routes to v2 endpoint

     # Test load balancing
     for i in {1..100}; do
         curl -s http://localhost:8000/api/v1/detection/health | \
         jq -r '.instance_id'
     done | sort | uniq -c
     # Should show even distribution
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- All services accessible through gateway
- Dynamic service discovery working
- Intelligent routing rules

### Blok 2: API design and documentation

#### Zadania atomowe

1. **[ ] REST API standardization**
   - **Metryka**: Consistent API design across all services
   - **Walidacja**:

     ```python
     # Test API consistency
     import requests

     base_url = "http://localhost:8000/api/v1"
     endpoints = [
         "/detection/events",
         "/automation/rules",
         "/management/cameras"
     ]

     for endpoint in endpoints:
         response = requests.get(f"{base_url}{endpoint}")

         # Check standard response format
         assert "data" in response.json()
         assert "meta" in response.json()
         assert response.headers["X-Request-ID"]
         assert response.headers["X-Response-Time"]

     # Test error format
     response = requests.get(f"{base_url}/invalid")
     error = response.json()
     assert error["error"]["code"]
     assert error["error"]["message"]
     ```

   - **Czas**: 2h

2. **[ ] GraphQL schema design**
   - **Metryka**: Unified GraphQL schema for all services
   - **Walidacja**:

     ```graphql
     # Test GraphQL endpoint
     query {
       cameras {
         id
         name
         status
         currentDetections {
           type
           confidence
           timestamp
         }
       }

       automationRules(active: true) {
         id
         name
         lastTriggered
         executionCount
       }

       systemHealth {
         services {
           name
           status
           uptime
         }
       }
     }

     # Validate with curl
     curl -X POST http://localhost:8000/graphql \
          -H "Content-Type: application/json" \
          -d '{"query": "{ __schema { types { name } } }"}'
     ```

   - **Czas**: 2.5h

3. **[ ] OpenAPI/Swagger generation**
   - **Metryka**: Auto-generated, always up-to-date API docs
   - **Walidacja**:

     ```bash
     # Access Swagger UI
     curl http://localhost:8000/docs

     # Validate OpenAPI spec
     curl http://localhost:8000/openapi.json | \
          openapi-spec-validator -

     # Check all endpoints documented
     curl http://localhost:8000/openapi.json | \
          jq '.paths | keys | length'
     # Should be 20+
     ```

   - **Czas**: 1.5h

#### Metryki sukcesu bloku

- Consistent API design
- Complete GraphQL schema
- Interactive documentation

### Blok 3: Security and performance

#### Zadania atomowe

1. **[ ] Authentication/Authorization**
   - **Metryka**: JWT/OAuth2 support, role-based access
   - **Walidacja**:

     ```python
     # Test authentication
     import jwt
     import requests

     # Get token
     response = requests.post("http://localhost:8000/auth/token", json={
         "username": "admin",
         "password": "secure_password"
     })
     token = response.json()["access_token"]

     # Decode and verify
     decoded = jwt.decode(token, options={"verify_signature": False})
     assert decoded["sub"] == "admin"
     assert "roles" in decoded

     # Test protected endpoint
     headers = {"Authorization": f"Bearer {token}"}
     response = requests.get(
         "http://localhost:8000/api/v1/management/users",
         headers=headers
     )
     assert response.status_code == 200

     # Test without token
     response = requests.get("http://localhost:8000/api/v1/management/users")
     assert response.status_code == 401
     ```

   - **Czas**: 2.5h

2. **[ ] Rate limiting and throttling**
   - **Metryka**: Per-user/IP rate limits, graceful degradation
   - **Walidacja**:

     ```bash
     # Test rate limiting
     for i in {1..150}; do
         curl -s -o /dev/null -w "%{http_code}\n" \
              http://localhost:8000/api/v1/detection/process
     done | sort | uniq -c
     # Should show:
     # 100 200  (successful)
     # 50 429   (rate limited)

     # Check headers
     curl -i http://localhost:8000/api/v1/detection/status | \
          grep -E "X-RateLimit-"
     # X-RateLimit-Limit: 100
     # X-RateLimit-Remaining: 99
     # X-RateLimit-Reset: 1737000000
     ```

   - **Czas**: 1.5h

3. **[ ] Response caching**
   - **Metryka**: Redis cache integration, smart invalidation
   - **Walidacja**:

     ```python
     import time
     import requests

     # First request (cache miss)
     start = time.time()
     response1 = requests.get("http://localhost:8000/api/v1/cameras")
     time1 = time.time() - start

     # Second request (cache hit)
     start = time.time()
     response2 = requests.get("http://localhost:8000/api/v1/cameras")
     time2 = time.time() - start

     assert response1.json() == response2.json()
     assert time2 < time1 * 0.1  # 10x faster
     assert response2.headers["X-Cache-Status"] == "HIT"

     # Test cache invalidation
     requests.post("http://localhost:8000/api/v1/cameras",
                  json={"name": "new_camera"})

     response3 = requests.get("http://localhost:8000/api/v1/cameras")
     assert response3.headers["X-Cache-Status"] == "MISS"
     assert len(response3.json()["data"]) > len(response1.json()["data"])
     ```

   - **Czas**: 2h

#### Metryki sukcesu bloku

- Secure API access
- Rate limiting protects services
- Effective caching strategy

## Całościowe metryki sukcesu zadania

1. **Performance**: <10ms gateway overhead, 10,000+ req/s capacity
2. **Security**: OAuth2/JWT auth, rate limiting, CORS configured
3. **Developer Experience**: Interactive docs, GraphQL playground, consistent APIs
4. **Reliability**: 99.9% uptime, graceful degradation

## Deliverables

1. `/src/gateway/` - API gateway implementation
2. `/src/gateway/routers/` - Service-specific routers
3. `/src/gateway/graphql/schema.graphql` - Unified GraphQL schema
4. `/src/gateway/middleware/` - Auth, rate limit, caching middleware
5. `/config/gateway/routes.yaml` - Routing configuration
6. `/docs/api/` - API documentation
7. `/dashboards/api-gateway-metrics.json` - Monitoring dashboard

## Narzędzia

- **FastAPI/Kong/Traefik**: API Gateway framework
- **Strawberry/GraphQL**: GraphQL implementation
- **Redis**: Response caching
- **JWT/OAuth2**: Authentication
- **OpenAPI Generator**: Client SDK generation

## Zależności

- **Wymaga**:
  - All microservices operational
  - Redis for caching
  - Service discovery mechanism
- **Blokuje**:
  - External integrations
  - Mobile app development
  - Third-party access

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Gateway becomes bottleneck | Średnie | Wysoki | Horizontal scaling, caching | Response time increase |
| Service discovery lag | Niskie | Średni | Health check tuning, cache TTL | 5xx errors spike |
| Cache invalidation bugs | Wysokie | Średni | Conservative TTLs, cache tags | Stale data complaints |
| Security vulnerabilities | Średnie | Wysoki | Regular updates, security scanning | Failed auth attempts |

## Rollback Plan

1. **Detekcja problemu**:
   - Gateway errors >1%
   - Response time degradation
   - Authentication failures

2. **Kroki rollback**:
   - [ ] Enable bypass mode: `GATEWAY_BYPASS=true`
   - [ ] Direct service access via ports
   - [ ] Clear cache: `redis-cli -n 2 FLUSHDB`
   - [ ] Restore previous config: `kubectl rollout undo deployment/api-gateway`
   - [ ] Switch to backup gateway if available

3. **Czas rollback**: <5 min

## Blok 5: DEPLOYMENT NA SERWERZE NEBULA

### 🎯 **NOWA PROCEDURA - UŻYJ UNIFIED DOCUMENTATION**

**Wszystkie procedury deploymentu** znajdują się w: `docs/deployment/services/api-gateway.md`

### Zadania atomowe

1. **[ ] Deploy via CI/CD pipeline**
   - **Metryka**: Automated deployment to Nebula via GitHub Actions
   - **Walidacja**: `git push origin main` triggers deployment
   - **Procedura**: [docs/deployment/services/api-gateway.md#deploy](docs/deployment/services/api-gateway.md#deploy)

2. **[ ] Konfiguracja Kong/Traefik na Nebuli**
   - **Metryka**: API Gateway routing all services
   - **Walidacja**: Single entry point working
   - **Procedura**: [docs/deployment/services/api-gateway.md#gateway-setup](docs/deployment/services/api-gateway.md#gateway-setup)

3. **[ ] Authentication/Authorization**
   - **Metryka**: JWT/API key validation
   - **Walidacja**: Protected endpoints secure
   - **Procedura**: [docs/deployment/services/api-gateway.md#authentication](docs/deployment/services/api-gateway.md#authentication)

4. **[ ] Rate limiting i caching**
   - **Metryka**: Rate limits enforced, cache hit >80%
   - **Walidacja**: Load test with limits
   - **Procedura**: [docs/deployment/services/api-gateway.md#rate-limiting](docs/deployment/services/api-gateway.md#rate-limiting)

5. **[ ] Performance test gateway**
   - **Metryka**: <10ms added latency
   - **Walidacja**: Benchmark via CI/CD
   - **Procedura**: [docs/deployment/services/api-gateway.md#performance-testing](docs/deployment/services/api-gateway.md#performance-testing)

### **🚀 JEDNA KOMENDA DO WYKONANIA:**
```bash
# Cały Blok 5 wykonuje się automatycznie:
git push origin main
```

### **📋 Walidacja sukcesu:**
```bash
# Sprawdź deployment:
curl http://nebula/api/health

# Test routing:
curl http://nebula/api/v1/face-recognition/health
curl http://nebula/api/v1/object-detection/health

# Test auth:
curl -H "Authorization: Bearer invalid" http://nebula/api/v1/protected
```

### **🔗 Linki do procedur:**
- **Deployment Guide**: [docs/deployment/services/api-gateway.md](docs/deployment/services/api-gateway.md)
- **Quick Start**: [docs/deployment/quick-start.md](docs/deployment/quick-start.md)
- **Troubleshooting**: [docs/deployment/troubleshooting/common-issues.md](docs/deployment/troubleshooting/common-issues.md)

### **🔍 Metryki sukcesu bloku:**
- ✅ Single API entry point for all services
- ✅ Authentication/authorization working
- ✅ Rate limiting protecting backend
- ✅ Response caching operational
- ✅ <10ms gateway overhead
- ✅ Zero-downtime deployment via CI/CD

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [05-e2e-integration-tests.md](./05-e2e-integration-tests.md)
