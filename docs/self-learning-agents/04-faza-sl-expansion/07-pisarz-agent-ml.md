# Faza SL-4 / Zadanie 7: Pisarz Agent ML Enhancement

<!--
LLM PROMPT dla całego zadania:
Analizując to zadanie, upewnij się że:
1. Pisarz agent ML enhancement focus na intelligent content creation i optimization
2. ML learns from successful documentation patterns i writing styles
3. Context-aware content generation based na technical requirements
4. Integration z project documentation i coding standards
5. Automated content quality assessment i improvement suggestions
6. Style adaptation to project i developer preferences
-->

## Cel zadania

Wzbogacenie pisarz agenta o ML capabilities dla intelligent content creation, automated documentation generation, i adaptive writing style optimization. Agent musi improve documentation quality przez context-aware content generation i style learning.

## Blok 0: Prerequisites check

#### Zadania atomowe:
1. **[ ] Weryfikacja działania debugger agents ML z Task 6**
   - **Metryka**: Debugger agents ML operational z >40% faster problem resolution
   - **Walidacja**: `curl -s http://nebula:8100/api/metrics/resolution-speed | jq '.improvement_percentage >= 0.4'`
   - **Czas**: 0.5h

2. **[ ] Backup pisarz agent configuration**
   - **Metryka**: Complete backup of current pisarz agent setup
   - **Walidacja**: `ls -la /opt/detektor/backups/$(date +%Y%m%d)/agents/pisarz/` pokazuje config files
   - **Czas**: 0.5h

3. **[ ] Documentation corpus verification**
   - **Metryka**: Access to documentation examples i writing samples
   - **Walidacja**: `find /Users/hretheum/dev/bezrobocie/detektor/docs -name "*.md" | wc -l | awk '{print ($1 >= 100)}'`
   - **Czas**: 1h

## Dekompozycja na bloki zadań

### Blok 1: Content Intelligence Data Model

#### Zadania atomowe:
1. **[ ] Writing intelligence data model**
   - **Metryka**: Complete data model w TimescaleDB dla content intelligence
   - **Walidacja**: `docker exec detektor-postgres psql -U detektor -c "\dt writing_ml.*" | grep -c "content\|styles\|quality\|feedback"`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

2. **[ ] Content pattern extraction pipeline**
   - **Metryka**: Pipeline extracts 30+ writing patterns z documentation
   - **Walidacja**: `curl -X POST http://nebula:8101/api/writing/extract-patterns -d '{"content_type": "technical_docs"}' | jq '.extracted_patterns | length >= 30'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Style preference learning system**
   - **Metryka**: System learns writing styles z user feedback
   - **Walidacja**: `curl -s http://nebula:8101/api/styles/learned-preferences | jq '.style_patterns | length >= 5 and .confidence >= 0.75'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Content quality assessment framework**
   - **Metryka**: Framework assesses content quality across multiple dimensions
   - **Walidacja**: `curl -X POST http://nebula:8101/api/quality/assess -d '{"content": "test documentation"}' | jq '.quality_scores | length >= 6'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

### Blok 2: Content Generation & Optimization Models

#### Zadania atomowe:
1. **[ ] Context-aware content generation model**
   - **Metryka**: Model generates contextually appropriate content z >85% relevance
   - **Walidacja**: `curl -s http://nebula:8101/api/models/content-generation/metrics | jq '.relevance_score >= 0.85 and .context_accuracy >= 0.8'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 5h

2. **[ ] Documentation structure optimization model**
   - **Metryka**: Model optimizes document structure dla readability i comprehension
   - **Walidacja**: `curl -X POST http://nebula:8101/api/models/structure/optimize -d '{"content": "sample_doc"}' | jq '.structure_improvements | length >= 3'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

3. **[ ] Technical writing enhancement model**
   - **Metryka**: Model improves technical writing clarity i accuracy
   - **Walidacja**: `curl -X POST http://nebula:8101/api/models/enhancement/technical -d '{"text": "technical_content"}' | jq '.improvements | length >= 2 and .clarity_score >= 0.8'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4h

4. **[ ] Automated documentation generation model**
   - **Metryka**: Model generates documentation z code i specifications
   - **Walidacja**: `curl -X POST http://nebula:8101/api/models/auto-generate -d '{"code_context": "sample_service"}' | jq '.generated_sections | length >= 4'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

### Blok 3: Intelligent Writing Assistant Integration

#### Zadania atomowe:
1. **[ ] ML-enhanced pisarz service implementation**
   - **Metryka**: Enhanced service provides intelligent writing assistance
   - **Walidacja**: `curl -X POST http://nebula:8080/api/agents/pisarz/assist -d '{"task": "document_api", "context": "ml_enhanced"}' | jq '.writing_suggestions | length >= 3 and .ml_enhanced == true'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 4.5h

2. **[ ] Real-time writing improvement suggestions**
   - **Metryka**: System provides real-time suggestions podczas writing
   - **Walidacja**: `curl -X POST http://nebula:8080/api/agents/pisarz/real-time-assist -d '{"partial_content": "introduction text"}' | jq '.suggestions | length >= 2 and .response_time_ms < 200'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Template generation i customization**
   - **Metryka**: System generates customized templates based na project context
   - **Walidacja**: `curl -X POST http://nebula:8080/api/agents/pisarz/generate-template -d '{"doc_type": "api_reference", "project_context": "ml_service"}' | jq '.template_sections | length >= 5'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Content consistency checking**
   - **Metryka**: System checks i ensures content consistency across documentation
   - **Walidacja**: `curl -X POST http://nebula:8080/api/agents/pisarz/check-consistency -d '{"document_set": "project_docs"}' | jq '.consistency_score >= 0.8'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

### Blok 4: Adaptive Content Optimization

#### Zadania atomowe:
1. **[ ] Gradual ML writing assistance rollout (30% → 100%)**
   - **Metryka**: Traffic splitting works dla writing ML assistance
   - **Walidacja**: `curl -X POST http://nebula:8092/api/flags/pisarz-ml -d '{"percentage": 80}'; for i in {1..100}; do curl -s http://nebula:8080/api/agents/pisarz/assist -d '{"task":"test"}' | jq '.ml_assistance_used'; done | grep -c "true"` # Should be ~80
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

2. **[ ] Personalized writing style adaptation**
   - **Metryka**: Agent adapts writing style to user preferences i project standards
   - **Walidacja**: `curl -X POST http://nebula:8101/api/personalization/adapt-style -d '{"user_id": "writer-123", "content_type": "technical_guide"}' | jq '.personalized_guidelines | length >= 5'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3.5h

3. **[ ] Content performance tracking dashboard**
   - **Metryka**: Dashboard tracks content quality i engagement metrics
   - **Walidacja**: `curl -s http://nebula:3000/api/dashboards/db/pisarz-ml | jq '.dashboard.panels[] | select(.title | contains("Content Performance"))'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 3h

4. **[ ] Continuous learning from content feedback**
   - **Metryka**: System learns from content usage i feedback patterns
   - **Walidacja**: `curl -X POST http://nebula:8101/api/feedback/content-outcome -d '{"content_id": "doc-123", "engagement_score": 8.5, "usefulness_rating": 9}' | jq '.learning_updated == true'`
   - **Code Review**: `/agent code-reviewer`
   - **Czas**: 2.5h

## Całościowe metryki sukcesu zadania

1. **Content Quality Improvement**: >30% improvement w content quality scores
2. **Writing Efficiency**: >40% faster documentation creation z ML assistance
3. **Style Consistency**: >90% consistency across project documentation
4. **User Satisfaction**: >85% satisfaction z ML-generated content
5. **Automated Generation**: >70% documentation sections generated automatically

## Deliverables

1. `/services/agents/pisarz-ml/` - ML-enhanced pisarz agent service
2. `/ml/models/writing/` - Trained ML models (generation, structure, enhancement, auto-docs)
3. `/ml/feature-engineering/writing/` - Content pattern extraction pipeline
4. `/scripts/sql/writing-ml-schema.sql` - ML data model dla writing intelligence
5. `/monitoring/grafana/dashboards/pisarz-ml.json` - Content performance dashboard
6. `/templates/documentation/` - ML-generated documentation templates
7. `/docs/agents/pisarz-ml-guide.md` - Operations and usage guide
8. `/tests/agents/pisarz-ml/` - Comprehensive test suite

## Narzędzia

- **Python 3.11**: ML model development (transformers, spacy, nltk)
- **TimescaleDB**: Content patterns i quality metrics storage
- **MLflow**: Model registry dla writing models
- **Redis**: Real-time suggestion caching
- **FastAPI**: ML-enhanced pisarz service API
- **Prometheus**: Content generation metrics
- **Grafana**: Writing performance monitoring

## Zależności

- **Wymaga**: Task 6 completed (Debugger agents ML operational)
- **Umożliwia**: Enhanced documentation i content creation dla all project components

## Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Wpływ | Mitigacja | Early Warning |
|--------|-------------------|-------|-----------|---------------|
| Generated content lacks technical accuracy | Średnie | Wysoki | Technical validation, expert review | Low accuracy scores |
| Style doesn't match project standards | Wysokie | Średni | Style learning, customization | Low consistency scores |
| ML suggestions disrupt writing flow | Średnie | Średni | Async suggestions, user control | Writer complaints |
| Over-reliance on automated generation | Średnie | Średni | Human oversight, quality gates | Declining human writing skills |

## Rollback Plan

1. **Detekcja problemu**: ML writing assistance not effective lub generating poor content
2. **Kroki rollback**:
   - [ ] Immediate: Disable ML assistance: `curl -X POST http://nebula:8092/api/flags/pisarz-ml -d '{"percentage": 0}'`
   - [ ] Service rollback: `docker compose restart pisarz-agent`
   - [ ] Full rollback: `git checkout pre-pisarz-ml && make deploy-agents`
3. **Czas rollback**: <2 min immediate, <10 min full

## Następne kroki

Po ukończeniu tego zadania, przejdź do:
→ [08-agent-chain-optimization.md](./08-agent-chain-optimization.md)

## Learning Outcomes

Po ukończeniu deweloper będzie umiał:
1. **Build intelligent content creation systems** z context awareness i style adaptation
2. **Implement automated documentation generation** z code i specification analysis
3. **Design content quality assessment frameworks** z multi-dimensional scoring
4. **Create personalized writing assistants** based na user preferences i project standards
5. **Monitor content performance** z engagement tracking i continuous improvement
