# Faza SL-1 / Zadanie 2: Security & Privacy Layer

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. GDPR compliance jest priorytetem #1
2. Encryption at rest i in transit jest mandatory
3. PII detection jest automatyczne, nie manual
4. Access control integruje z istniejącym GitHub OAuth
5. Audit trail jest immutable i compliant
-->

## Cel zadania

Implementacja kompleksowej warstwy bezpieczeństwa i prywatności dla ML infrastructure zgodnej z GDPR, z automatyczną detekcją PII, szyfrowaniem danych i pełnym audit trail. System musi być secure by design bez wpływu na performance.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja istniejących security mechanisms**
   - **Metryka**: SOPS + age encryption działa, GitHub OAuth active
   - **Walidacja**: `sops -d .env.sops | grep -q "POSTGRES_PASSWORD"` && `curl -s http://nebula:3000/api/health | jq .oauth.enabled`
   - **Czas**: 0.5h

2. **[ ] Security audit baseline existing ML data**
   - **Metryka**: Scan existing logs/data for potential PII exposure
   - **Walidacja**: `./scripts/security/scan-pii.sh | grep "No PII detected"` returns 0
   - **Czas**: 0.5h

## Dekompozycja na bloki zadań

### Blok 1: Data Encryption Implementation

<!--
LLM PROMPT dla bloku:
Wszystkie ML data muszą być encrypted at rest i in transit.
Używaj istniejącej infrastruktury SOPS gdzie możliwe.
Dodaj nowe encryption tylko tam gdzie SOPS nie wystarczy.
-->

#### Zadania atomowe:
1. **[ ] PostgreSQL transparent data encryption (TDE)**
   - **Metryka**: Wszystkie ML tabele encrypted with AES-256
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT schemaname, tablename, encryption_algorithm FROM pg_encryption_info WHERE schemaname='ml_learning';" | grep -c "AES256"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] MinIO encryption at rest configuration**
   - **Metryka**: MinIO buckets z automatic server-side encryption
   - **Walidacja**:
     ```bash
     mc admin config get minio/ encrypt | grep -q "SSE-S3"
     mc ls --recursive minio/mlflow-artifacts | head -1 | mc stat --json | jq .encryption.algorithm
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

3. **[ ] Redis encryption dla ML namespaces**
   - **Metryka**: Redis AUTH + TLS dla ML connections
   - **Walidação**:
     ```bash
     redis-cli --tls --cert /certs/redis-client.crt --key /certs/redis-client.key --cacert /certs/ca.crt ping
     redis-cli CONFIG GET requirepass | grep -v "^$"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- 100% ML data encrypted at rest (PostgreSQL, MinIO, Redis)
- TLS 1.3 enforced for all ML service communication
- Encryption keys properly managed through SOPS
- Zero performance impact <5ms latency increase
- Compliance audit ready - all encryption verifiable

### Blok 2: PII Detection & Anonymization

<!--
LLM PROMPT dla bloku:
Automatyczna detekcja i anonymization PII w ML data streams.
Musi działać real-time bez blokowania processing.
GDPR compliance od design.
-->

#### Zadania atomowe:
1. **[ ] Automated PII detection pipeline**
   - **Metryka**: ML pipeline z regex + ML-based PII detection (99% accuracy)
   - **Walidação**:
     ```bash
     python -c "from ml_security.pii_detector import PIIDetector; d=PIIDetector(); result=d.detect('John Doe email: john@example.com'); assert 'EMAIL' in result.entities"
     curl -X POST http://nebula:8088/pii/detect -d '{"text":"My SSN is 123-45-6789"}' | jq .entities | grep -q "SSN"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] K-anonymity implementation dla decision data**
   - **Metryka**: All stored decisions k-anonymous with k=5 minimum
   - **Walidação**:
     ```bash
     python scripts/privacy/verify_k_anonymity.py --table=ml_learning.agent_decisions --k=5 | grep "PASSED"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Data retention policy automation**
   - **Metryka**: Automatic deletion after 2 years, compliance verification
   - **Walidão**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM ml_learning.agent_decisions WHERE created_at < NOW() - INTERVAL '2 years';" | grep -q "0"
     crontab -l | grep -q "privacy-cleanup"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- PII detection accuracy >99% na test dataset
- K-anonymity enforced for all ML training data
- GDPR right-to-be-forgotten implementable <24h
- Automated retention policy working
- Real-time anonymization <10ms overhead

### Blok 3: Access Control & Authorization

<!--
LLM PROMPT dla bloku:
RBAC system integrujący z GitHub OAuth.
Principle of least privilege.
Comprehensive audit trail.
-->

#### Zadania atomowe:
1. **[ ] RBAC system dla ML resources**
   - **Metryka**: Role-based access z 4 role levels (viewer, analyst, engineer, admin)
   - **Walidação**:
     ```bash
     curl -H "Authorization: Bearer $VIEWER_TOKEN" http://nebula:5000/api/experiments | jq .permissions.write | grep -q "false"
     curl -H "Authorization: Bearer $ADMIN_TOKEN" http://nebula:5000/api/models/delete | jq .status | grep -q "200"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Integration z GitHub OAuth dla ML services**
   - **Metryka**: Single sign-on dla MLflow, monitoring dashboards
   - **Walidação**:
     ```bash
     curl -s http://nebula:5000/oauth/login | grep -q "github.com/login/oauth"
     curl -s http://nebula:3000/login | grep -q "Sign in with GitHub"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] API key management i rotation**
   - **Metryka**: ML API keys auto-rotate every 90 days, stored in SOPS
   - **Walidação**:
     ```bash
     sops -d .env.sops | grep ML_API_KEY | grep -E "[0-9]{4}-[0-9]{2}-[0-9]{2}" # Date stamp
     python scripts/security/check_key_age.py | grep "All keys within rotation policy"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Complete RBAC system operational
- GitHub OAuth integration working
- API key rotation automated
- Zero unauthorized access attempts successful
- Authentication response time <200ms

### Blok 4: Audit Trail & Compliance

<!--
LLM PROMPT dla bloku:
Immutable audit log dla wszystkich ML operations.
Compliance reporting ready.
Integration z existing logging.
-->

#### Zadania atomowe:
1. **[ ] Immutable audit log implementation**
   - **Metryka**: Blockchain-style immutable log dla all ML decisions/changes
   - **Walidação**:
     ```bash
     python scripts/audit/verify_chain.py | grep "Chain integrity: VALID"
     docker exec detektor-postgres psql -U detektor -c "SELECT COUNT(*) FROM ml_learning.audit_trail WHERE hash_valid=true;" | tail -1
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] GDPR compliance reporting**
   - **Metryka**: Automated reports dla data processing, consent tracking
   - **Walidação**:
     ```bash
     python scripts/compliance/gdpr_report.py --month=$(date +%Y-%m) | grep "Compliance Score: 100%"
     ls -la /reports/gdpr/$(date +%Y/%m)/ | wc -l | grep -q "4" # Weekly reports
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

3. **[ ] Integration z existing observability stack**
   - **Metryka**: Security events w Grafana, alerts w Prometheus
   - **Walidação**:
     ```bash
     curl -s http://nebula:9090/api/v1/query?query=ml_security_events_total | jq '.data.result | length' | grep -q "1"
     curl -s http://nebula:3000/api/dashboards/db/security-overview | jq .dashboard.title | grep -q "Security"
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2h

#### Metryki sukcesu bloku:
- Immutable audit trail operational
- GDPR compliance verified and reportable
- Security monitoring integrated
- Compliance reports auto-generated
- Audit trail search <1 second response

## Całościowe metryki sukcesu zadania

1. **Security Posture**: Zero unencrypted ML data, all communication TLS-secured
2. **Privacy Compliance**: 100% PII detection rate, GDPR compliance verified
3. **Access Control**: RBAC operational, zero unauthorized access
4. **Audit Readiness**: Immutable trail, automated compliance reporting
5. **Performance Impact**: <5% overhead na existing systems

## Deliverables

1. `/services/ml-security/pii-detector/` - PII detection service
2. `/scripts/security/encryption-setup.sh` - Database encryption configuration
3. `/scripts/privacy/k-anonymity.py` - Anonymization pipeline
4. `/scripts/compliance/gdpr-tools.py` - GDPR compliance utilities
5. `/monitoring/grafana/dashboards/security-overview.json` - Security dashboard
6. `/docs/self-learning-agents/security-guide.md` - Security operations guide
7. `.env.sops` updates - Security credentials i keys

## Narzędzia

- **cryptography**: Python library para encryption/decryption
- **spaCy + custom NER**: PII detection w text data
- **PostgreSQL TDE**: Transparent data encryption
- **MinIO SSE**: Server-side encryption para object storage
- **Redis AUTH/TLS**: Secured cache layer
- **GitHub OAuth**: Authentication provider
- **TimescaleDB**: Audit trail storage

## Zależności

- **Wymaga**: 01-ml-infrastructure-setup.md completed
- **Blokuje**: 03-feature-store-config.md (wymaga secure infrastructure)

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Performance degradation from encryption | Średnie | Średni | Benchmark wszystkie operations, optimize queries | Response time >200ms |
| PII false positives breaking pipeline | Średnie | Średni | Extensive testing, manual review queue | >5% false positive rate |
| Compliance audit failure | Niskie | Krytyczny | Regular self-audits, external review | Missing audit trail entries |
| Key rotation breaking services | Niskie | Wysoki | Graceful key transition, rollback plan | Service authentication failures |

## Rollback Plan

1. **Detekcja problemu**: Security incidents, compliance violations, or performance degradation >10%
2. **Kroki rollback**:
   - [ ] Disable PII detection: `docker stop ml-pii-detector`
   - [ ] Fallback encryption: `psql -f scripts/security/disable-tde.sql`
   - [ ] Remove access controls: `kubectl delete -f rbac/ml-roles.yaml`
   - [ ] Restore backup configurations: `cp -r /backups/security-config/ .`
3. **Czas rollback**: <15 min

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [03-feature-store-config.md](./03-feature-store-config.md)
