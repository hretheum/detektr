# Faza SL-4 / Zadanie 3: Detektor-Coder Agent ML Enhancement

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Detektor-coder ML enhancement focus na intelligent code generation i optimization
2. ML learns from successful code patterns i developer preferences
3. Context-aware suggestions based on project architecture
4. Integration z existing development workflows i coding standards
5. Real-time code completion i architectural recommendations
6. Pattern learning from codebase analysis i developer feedback
-->

## Cel zadania

Wzbogacenie detektor-coder agenta o ML capabilities dla intelligent code generation, architectural decision support, i context-aware optimization suggestions. Agent musi improve development velocity przez personalized code assistance i architectural guidance.

## Blok 0: Prerequisites check

<!--
LLM PROMPT: Ten blok jest OBOWIĄZKOWY dla każdego zadania.
Sprawdź czy wszystkie zależności są spełnione ZANIM rozpoczniesz główne zadanie.
-->

#### Zadania atomowe:
1. **[ ] Weryfikacja działania deployment-specialist ML z Task 2**
   - **Metryka**: Deployment-specialist ML operational z >80% success rate
   - **Walidacja**: `curl -s http://nebula:8096/api/monitoring/deployment-success | jq '.ml_recommendations.success_rate >= 0.8'`
   - **Czas**: 0.5h

2. **[ ] Backup istniejącej detektor-coder konfiguracji**
   - **Metryka**: Complete backup of current detektor-coder setup
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/agents/detektor-coder/` pokazuje config files
   - **Czas**: 0.5h

3. **[ ] Codebase analysis readiness verification**
   - **Metryka**: Access to project codebase z >10k lines of code
   - **Walidacja**: `find /Users/hretheum/dev/bezrobocie/detektor -name "*.py" -exec wc -l {} + | tail -1 | awk '{print ($1 >= 10000)}'`
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: Code Intelligence Data Model

<!--
LLM PROMPT dla bloku:
Dekomponując ten blok:
1. Code generation features muszą capture context, style, i architectural patterns
2. Analysis existing codebase dla pattern extraction i style learning
3. Developer preference tracking (accepted/rejected suggestions)
4. Integration z project structure i coding standards
-->

#### Zadania atomowe:
1. **[ ] Code generation intelligence data model**
   <!--
   LLM PROMPT dla zadania atomowego:
   To zadanie musi:
   - Analyzować existing codebase patterns, architectural decisions
   - Definiować features: code complexity, style patterns, imports, dependencies
   - Include developer feedback na code suggestions (accepted/rejected)
   - Po ukończeniu ZAWSZE wymagać code review przez `/agent code-reviewer`
   -->
   - **Metryka**: Complete data model w TimescaleDB dla code intelligence features
   - **Walidacja**:
     ```bash
     docker exec detektor-postgres psql -U detektor -c "\dt code_intelligence.*" | grep -c "patterns\|suggestions\|feedback\|architecture"
     ```
   - **Code Review**: `/agent code-reviewer` (OBOWIĄZKOWE po implementacji)
   - **Czas**: 4h

2. **[ ] Codebase pattern extraction pipeline**
   - **Metryka**: Pipeline extracts 40+ code patterns i architectural features
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/code-intelligence/extract-patterns \
          -H "Content-Type: application/json" \
          -d '{"codebase_path": "/project", "analysis_type": "full"}' | \
          jq '.extracted_patterns | length >= 40'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

3. **[ ] Developer preference learning system**
   - **Metryka**: System tracks developer coding style i preference patterns
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8097/api/developer-preferences/patterns | jq '.learned_preferences | length >= 5 and .confidence_score >= 0.7'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Project context awareness implementation**
   - **Metryka**: System understands project architecture i provides context-aware suggestions
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/context/analyze-request \
          -d '{"file_path": "services/rtsp-capture/src/main.py", "code_intent": "add_logging"}' | \
          jq '.context_understanding.architecture_layer != null and .suggested_patterns | length >= 3'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

#### Metryki sukcesu bloku:
- Complete code intelligence data model implemented
- Pattern extraction pipeline operational (40+ patterns)
- Developer preference learning active
- Project context awareness working
- Pattern analysis <300ms per request

### Blok 2: Code Generation & Optimization Models

<!--
LLM PROMPT dla bloku:
ML models dla intelligent code generation i optimization recommendations.
Musi być context-aware i follow project coding standards.
-->

#### Zadania atomowe:
1. **[ ] Code completion model training**
   - **Metryka**: Model trained z >90% relevance score na code suggestions
   - **Walidacja**:
     ```bash
     curl -s http://nebula:8097/api/models/code-completion/metrics | jq '.relevance_score >= 0.9 and .context_accuracy >= 0.85'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 5h

2. **[ ] Architectural decision support model**
   - **Metryka**: Model recommends appropriate architectural patterns z >80% accuracy
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/models/architecture-advisor/recommend \
          -d '{"use_case": "data_processing", "constraints": ["performance", "scalability"]}' | \
          jq '.recommended_patterns | length >= 3 and .confidence >= 0.8'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

3. **[ ] Code optimization suggestion model**
   - **Metryka**: Model identifies optimization opportunities z >75% precision
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/models/optimization/analyze \
          -d '{"code_snippet": "def inefficient_function(): pass", "context": "performance_critical"}' | \
          jq '.optimization_suggestions | length >= 1 and .impact_score >= 0.75'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

4. **[ ] Refactoring recommendation engine**
   - **Metryka**: Engine suggests appropriate refactoring patterns based on code quality metrics
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/models/refactoring/suggestions \
          -d '{"code_complexity": 8.5, "maintainability_index": 45}' | \
          jq '.refactoring_recommendations | length >= 2 and .priority_score >= 0.7'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

#### Metryki sukcesu bloku:
- Code completion model >90% relevance
- Architecture advisor >80% accuracy
- Optimization suggestions >75% precision
- Refactoring recommendations >70% adoption rate
- All models deployed w MLflow registry

### Blok 3: Intelligent Coding Assistant Integration

<!--
LLM PROMPT dla bloku:
Integration ML capabilities z existing detektor-coder agent.
Real-time coding assistance z context awareness.
-->

#### Zadania atomowe:
1. **[ ] ML-enhanced detektor-coder service implementation**
   - **Metryka**: Enhanced service provides intelligent code suggestions i architectural guidance
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/detektor-coder/assist \
          -d '{"task": "implement_service", "context": "ml_enhanced", "requirements": "observability"}' | \
          jq '.code_suggestions | length >= 3 and .architectural_guidance != null and .ml_enhanced == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 5h

2. **[ ] Real-time code completion API**
   - **Metryka**: API provides code completions w <150ms
   - **Walidacja**:
     ```bash
     time curl -X POST http://nebula:8080/api/agents/detektor-coder/complete \
          -d '{"partial_code": "def process_frame(", "file_context": "vision_service.py"}' | \
          jq '.completion_time_ms < 150'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] IDE integration middleware**
   - **Metryka**: Middleware provides seamless integration z popular IDEs (VS Code, PyCharm)
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/detektor-coder/ide/vscode \
          -H "X-IDE-Request: true" \
          -d '{"action": "suggest", "cursor_position": {"line": 42, "column": 15}}' | \
          jq '.ide_compatible == true and .suggestions | length >= 1'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

4. **[ ] Shadow mode learning from coding sessions**
   - **Metryka**: Shadow mode learns from actual coding patterns bez interrupting workflow
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8080/api/agents/detektor-coder/session \
          -d '{"session_id": "test-123", "shadow_mode": true, "coding_activity": "refactoring"}' | \
          jq '.shadow_learning_active == true and .session_recorded == true'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

#### Metryki sukcesu bloku:
- ML-enhanced detektor-coder service operational
- Real-time code completion <150ms
- IDE integration working
- Shadow mode learning active
- Zero disruption to existing workflows

### Blok 4: Personalized Development Experience

<!--
LLM PROMPT dla bloku:
Personalized coding assistance based na developer preferences i project context.
Adaptive learning i continuous improvement.
-->

#### Zadania atomowe:
1. **[ ] Gradual ML coding assistance rollout (15% → 75% → 100%)**
   - **Metryka**: Traffic splitting works dla ML coding suggestions
   - **Walidacja**:
     ```bash
     # Test 75% rollout
     curl -X POST http://nebula:8092/api/flags/detektor-coder-ml -d '{"percentage": 75}'
     for i in {1..100}; do curl -s http://nebula:8080/api/agents/detektor-coder/assist -d '{"task":"test"}' | jq '.ml_assistance_used'; done | grep -c "true" # Should be ~75
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

2. **[ ] Personalized coding style adaptation**
   - **Metryka**: Agent adapts suggestions to individual developer preferences
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/personalization/adapt-style \
          -d '{"developer_id": "dev-123", "code_sample": "test_code"}' | \
          jq '.personalized_suggestions | length >= 2 and .adaptation_confidence >= 0.8'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Development productivity dashboard**
   - **Metryka**: Dashboard shows productivity metrics i ML assistance impact
   - **Walidacja**:
     ```bash
     curl -s http://nebula:3000/api/dashboards/db/detektor-coder-ml | jq '.dashboard.panels[] | select(.title | contains("Productivity Impact"))'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Continuous learning from development outcomes**
   - **Metryka**: System learns from code quality metrics i developer feedback
   - **Walidacja**:
     ```bash
     curl -X POST http://nebula:8097/api/feedback/development-outcome \
          -d '{"suggestion_id": "sug-123", "implemented": true, "quality_score": 8.5, "developer_rating": 9}' | \
          jq '.learning_updated == true and .model_retrain_triggered == false'
     ```
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

#### Metryki sukcesu bloku:
- Gradual rollout mechanism working (15%-100%)
- Personalized style adaptation active
- Productivity dashboard operational
- Continuous learning from outcomes working
- Developer satisfaction score >85%

## Całościowe metryki sukcesu zadania

<!--
LLM PROMPT dla metryk całościowych:
Te metryki muszą:
1. Potwierdzać osiągnięcie celu biznesowego zadania
2. Być weryfikowalne przez stakeholdera
3. Agregować najważniejsze metryki z bloków
4. Być SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
-->

1. **Code Quality Improvement**: >25% improvement w code quality metrics (complexity, maintainability)
2. **Development Velocity**: >30% increase w coding productivity through intelligent assistance
3. **Suggestion Accuracy**: >90% relevance score dla ML code suggestions
4. **Response Time**: Code completion i suggestions <150ms dla real-time assistance
5. **Adoption Rate**: >85% developer satisfaction z ML-enhanced coding experience

## Deliverables

<!--
LLM PROMPT: Lista WSZYSTKICH artefaktów które powstaną.
Każdy deliverable musi mieć konkretną ścieżkę i być wymieniony w zadaniu atomowym.
-->

1. `/services/agents/detektor-coder-ml/` - ML-enhanced detektor-coder service
2. `/ml/models/code-intelligence/` - Trained ML models (completion, architecture, optimization, refactoring)
3. `/ml/feature-engineering/code-patterns/` - Code pattern extraction pipeline
4. `/scripts/sql/code-intelligence-schema.sql` - ML data model for code intelligence
5. `/monitoring/grafana/dashboards/detektor-coder-ml.json` - ML coding assistance dashboard
6. `/integration/ide/vscode-extension/` - VS Code integration extension
7. `/integration/ide/pycharm-plugin/` - PyCharm plugin integration
8. `/docs/agents/detektor-coder-ml-guide.md` - Operations and usage guide
9. `/tests/agents/detektor-coder-ml/` - Comprehensive test suite

## Narzędzia

<!--
LLM PROMPT: Wymień TYLKO narzędzia faktycznie używane w zadaniach.
-->

- **Python 3.11**: ML model development (transformers, tree-sitter, ast)
- **TimescaleDB**: Code patterns i intelligence storage
- **MLflow**: Model registry i experiment tracking
- **Redis**: Real-time suggestion caching
- **FastAPI**: ML-enhanced agent service API
- **tree-sitter**: Code parsing i analysis
- **Prometheus**: Development productivity metrics
- **Grafana**: Coding assistance monitoring
- **VS Code API**: IDE integration
- **Language Server Protocol**: Multi-IDE support

## Zależności

- **Wymaga**: Task 2 completed (Deployment-specialist ML operational)
- **Blokuje**: Task 5 (Cross-Agent Learning) - needs coding patterns for sharing

## Ryzyka i mitigacje

<!--
LLM PROMPT dla ryzyk:
Identyfikuj REALNE ryzyka które mogą wystąpić podczas realizacji.
-->

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| ML suggestions disrupt coding flow | Średnie | Wysoki | Async suggestions, user control | Developer complaints |
| Code completion latency | Średnie | Średni | Caching, model optimization | Response time >150ms |
| Suggestions don't match project style | Wysokie | Średni | Style learning, customization | Low adoption rates |
| IDE integration breaks workflows | Niskie | Wysoki | Extensive testing, graceful fallback | IDE compatibility issues |
| Model suggests insecure code | Niskie | Krytyczny | Security pattern training, validation | Security scan failures |

## Rollback Plan

<!--
LLM PROMPT: KAŻDE zadanie musi mieć plan cofnięcia zmian.
-->

1. **Detekcja problemu**: ML suggestions disrupting development lub low adoption
2. **Kroki rollback**:
   - [ ] Immediate: Disable ML assistance: `curl -X POST http://nebula:8092/api/flags/detektor-coder-ml -d '{"percentage": 0}'`
   - [ ] IDE integrations: Disable extensions/plugins
   - [ ] Service rollback: `docker compose restart detektor-coder-agent`
   - [ ] Full rollback: `git checkout pre-coder-ml && make deploy-agents`
3. **Czas rollback**: <2 min immediate, <10 min full

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [04-architecture-advisor-ml.md](./04-architecture-advisor-ml.md)

## Learning Outcomes

Po ukończeniu deweloper będzie umiał:
1. **Build code intelligence systems** z pattern recognition i style learning
2. **Implement real-time code assistance** z context awareness
3. **Integrate ML z development workflows** bez disrupting productivity
4. **Design personalized coding experiences** based na developer preferences
5. **Monitor development productivity** z ML assistance impact tracking
