# Faza SL-3 / Zadanie 5: Production Hardening

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Security hardening dla all ML components (encryption, access control, audit)
2. Reliability improvements (redundancy, failover, backup/recovery)
3. Performance optimization under production load
4. Compliance z GDPR i other privacy regulations
5. Production-grade monitoring i alerting
-->

## Cel zadania

Hardening całej ML infrastructure dla production reliability, security i compliance. Implementacja redundancy, failover mechanisms, advanced security controls i production-grade monitoring dla enterprise-ready ML system.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja explainability system stability z Zadania 4**
   - **Metryka**: Explainability dashboard operational, explanations clear
   - **Walidacja**: `curl -s http://nebula:8096/api/explainability/health | grep -q "OK" && curl -s http://nebula:3000/api/dashboards/db/explainable-ai-overview | jq '.dashboard.panels | length > 8'`
   - **Czas**: 0.5h

2. **[ ] Current security audit i vulnerability assessment**
   - **Metryka**: Security scan shows current vulnerabilities
   - **Walidacja**: `/scripts/security-scan.sh ml-components | grep -c "HIGH\|CRITICAL"` shows known issues to fix
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: Security Hardening

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. End-to-end encryption dla all ML data flows
2. Advanced access control z RBAC
3. Secrets management i rotation
4. Security audit logging i monitoring
-->

#### Zadania atomowe:
1. **[ ] End-to-end encryption implementation**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Implement TLS 1.3 dla all ML service communication
   - Encrypt ML data at rest w database i MinIO
   - Key rotation policies dla encryption keys
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: All ML communications encrypted, data at rest encrypted
   - **Walidacja**:
     ```bash
     # Check TLS on all ML services
     openssl s_client -connect nebula:8095 -servername nebula < /dev/null | grep -q "TLS"
     # Check database encryption
     docker exec detektor-postgres psql -U detektor -c "SHOW ssl;" | grep -q "on"
     # Check MinIO encryption
     mc admin info minio | grep -q "encryption: enabled"
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 4h

2. **[ ] Role-based access control (RBAC) implementation**
   - **Metryka**: RBAC dla ML services z least privilege principle
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8095/api/admin/users -H "Authorization: Bearer invalid-token" | grep -q "401"
     curl -s http://nebula:8095/api/admin/users -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.users | length > 0'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Secrets management i automated rotation**
   - **Metryka**: All ML secrets w vault z automatic rotation
   - **Walidacja**:
     ```bash
     # Check secrets are not hardcoded
     grep -r "password\|secret\|key" services/ml-* --exclude="*.md" | wc -l | grep -q "0"
     # Check vault integration
     vault kv get secret/ml/database | grep -q "password"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- All ML communications use TLS 1.3
- Data at rest fully encrypted
- RBAC implemented z proper roles
- No hardcoded secrets w codebase
- Automated secrets rotation working

### Blok 2: High Availability i Redundancy

<!--
LLM PROMPT dla bloku:
Production-grade reliability z redundancy i failover.
Musi ensure ML system dostępny 99.9%+ uptime.
-->

#### Zadania atomowe:
1. **[ ] ML service redundancy i load balancing**
   - **Metryka**: Multiple instances każdego ML service z load balancer
   - **Walidacja**:
     ```bash
     docker ps | grep ml-serving | wc -l | grep -q "[2-9]"  # At least 2 instances
     curl -s http://nebula:8097/api/loadbalancer/status | jq '.healthy_backends >= 2'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

2. **[ ] Database clustering i replication**
   - **Metryka**: PostgreSQL master-slave replication dla ML data
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres-master psql -U detektor -c "SELECT client_addr FROM pg_stat_replication;" | grep -q "postgres-slave"
     docker exec detektor-postgres-slave psql -U detektor -c "SELECT pg_is_in_recovery();" | grep -q "t"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Automatic failover mechanisms**
   - **Metryka**: Automatic failover to backup services w <30 seconds
   - **Walidacja**:
     ```bash
     # Simulate primary ML service failure
     docker stop ml-serving-primary
     sleep 35
     curl -s http://nebula:8095/health | grep -q "OK"  # Should still work via backup
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- Multiple instances każdego critical service
- Database replication working correctly
- Automatic failover tested i operational
- Load balancing distributes traffic properly
- 99.9%+ availability target achievable

### Blok 3: Backup i Disaster Recovery

<!--
LLM PROMPT dla bloku:
Comprehensive backup strategy i disaster recovery procedures.
Musi handle complete system failure scenarios.
-->

#### Zadania atomowe:
1. **[ ] Automated ML data backup system**
   - **Metryka**: Daily backups wszystkich ML data z verification
   - **Walidacja**:
     ```bash
     ls -la /opt/detektor/backups/$(date +%Y-%m-%d)/ml/ | grep -q "models\|features\|decisions"
     /scripts/backup-verify.sh ml-data-$(date +%Y-%m-%d) | grep -q "VALID"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Model registry backup i versioning**
   - **Metryka**: All ML models backed up z complete version history
   - **Walidacja**:
     ```bash
     mc ls backup-bucket/mlflow-models/ | wc -l | grep -q "[1-9]"
     curl -s http://nebula:5000/api/2.0/mlflow/model-versions/search | jq '.model_versions | length > 0'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Disaster recovery procedures i testing**
   - **Metryka**: Complete disaster recovery tested z <4 hour RTO
   - **Walidacja**:
     ```bash
     # Test disaster recovery (in staging)
     time /scripts/disaster-recovery-test.sh
     # Should complete in <4 hours with all services restored
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

#### Metryki sukcesu bloku:
- Automated daily backups working
- Model versioning comprehensive
- Disaster recovery procedures tested
- Recovery Time Objective <4 hours
- Recovery Point Objective <1 hour

### Blok 4: Production Monitoring i Alerting

<!--
LLM PROMPT dla bloku:
Enterprise-grade monitoring z proactive alerting.
Musi detect issues before they impact users.
-->

#### Zadania atomowe:
1. **[ ] Advanced ML metrics monitoring**
   - **Metryka**: 50+ ML-specific metrics monitored w Prometheus
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9090/api/v1/label/__name__/values | jq '.data[]' | grep -c "ml_" | awk '{print ($1 >= 50)}'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

2. **[ ] Proactive alerting system**
   - **Metryka**: 15+ alert rules dla ML system health
   - **Walidacja**:
     ```bash
     curl -s http://nebula:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.alert | contains("ML")) | .alert' | wc -l | grep -q "1[5-9]"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

3. **[ ] SLA monitoring i compliance tracking**
   - **Metryka**: SLA metrics tracked z automated compliance reporting
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8093/api/sla/ml-services/current | jq '.uptime_percentage > 99.9 and .response_time_p95 < 100'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Comprehensive ML metrics collection
- Proactive alerting preventing issues
- SLA compliance automatically tracked
- Alert noise minimized (<5 false positives/day)
- Observability covers entire ML pipeline

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Security Compliance**: All ML data encrypted, RBAC implemented, security audit passed
2. **High Availability**: 99.9%+ uptime achieved z automatic failover <30 seconds
3. **Backup Completeness**: All ML data backed up daily z <4 hour disaster recovery
4. **Monitoring Excellence**: 50+ metrics monitored, proactive alerting operational
5. **Production Readiness**: System passes enterprise security i reliability standards

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/security/ml-tls-config/` - TLS configuration dla ML services
2. `/security/rbac-policies/` - Role-based access control policies
3. `/scripts/backup/ml-automated-backup.sh` - Automated backup system
4. `/scripts/disaster-recovery/` - Complete disaster recovery procedures
5. `/monitoring/prometheus/rules/ml-production-alerts.yml` - Production alerting rules
6. `/monitoring/grafana/dashboards/ml-sla-monitoring.json` - SLA monitoring dashboard
7. `/docs/self-learning-agents/production-operations-guide.md` - Complete operations manual
8. `/scripts/security/ml-security-audit.sh` - Security auditing tools

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **HashiCorp Vault**: Secrets management i rotation
- **nginx**: Load balancing i TLS termination
- **PostgreSQL Streaming Replication**: Database clustering
- **MinIO**: Encrypted object storage dla ML artifacts
- **Prometheus**: Advanced metrics collection
- **Grafana**: SLA monitoring dashboards
- **SOPS + age**: Secret encryption w Git

## Zależności

- **Wymaga**: 04-explainable-ai-dashboard.md ukończone (explainability operational)
- **Blokuje**: 06-performance-optimization.md (final performance tuning)

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Security changes break existing functionality | Średnie | Wysoki | Extensive testing, staged rollout | Service health checks fail |
| Performance impact z encryption | Średnie | Średni | Benchmark each change, optimize | Latency increases >10% |
| Backup storage costs high | Niskie | Średni | Retention policies, compression | Storage costs >$500/month |
| Complex failover scenarios | Średnie | Średni | Thorough testing, documentation | Failover tests fail |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: Security changes impact performance lub functionality
2. **Kroki rollback**:
   - [ ] Disable new security features: Revert to previous configuration
   - [ ] Remove redundancy: Fall back to single instances if needed
   - [ ] Restore backup: Use previous working configuration
   - [ ] Validate: Ensure all services operational
3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [06-performance-optimization.md](./06-performance-optimization.md)
