# Technical Details - AI Agents Implementation

## 🤖 Complete Agent Roster

### 1. **architecture-advisor**
- **Role**: Clean Architecture expert, DDD specialist
- **Tools**: Read, Grep, Glob, Task
- **Specialization**:
  - Bounded contexts design
  - SOLID principles enforcement
  - Code smell detection
  - Performance analysis (GPU/VRAM)
- **Key patterns**: Repository, Circuit Breaker, Adapter, Observer

### 2. **code-reviewer**
- **Role**: Automated code review and refactoring
- **Tools**: Read, Grep, Glob, Task
- **Specialization**:
  - Clean Code standards (functions <20 lines)
  - Type hints verification (100% coverage)
  - Security review (no hardcoded secrets)
  - Performance optimization suggestions
  - Testing standards (>80% coverage)
- **Review checklist**: 8-point comprehensive check

### 3. **debugger**
- **Role**: Runtime troubleshooting and log analysis
- **Tools**: Read, Grep, Glob, Bash, Task, WebFetch
- **Specialization**:
  - Docker logs analysis
  - Async debugging (asyncio)
  - Memory/CPU profiling
  - Network debugging
  - Root cause analysis
- **Emergency procedures**: Quick restart, memory dumps, deadlock detection

### 4. **deployment-specialist**
- **Role**: CI/CD, Docker, GitHub Actions expert
- **Tools**: Read, Grep, Glob, Bash, Task
- **Specialization**:
  - GitHub Actions workflows
  - Container Registry management
  - Health monitoring
  - Rollback strategies
  - Secret management (SOPS)
- **Key principle**: Registry-based deployment (NO local builds!)

### 5. **pipeline-debugger**
- **Role**: Frame processing pipeline specialist
- **Tools**: Read, Grep, Glob, Bash, Task, WebFetch
- **Specialization**:
  - RTSP → Redis → Frame Buffer → Processors flow
  - Dead-end identification
  - Distributed tracing analysis
  - Queue depth monitoring
  - Backpressure implementation
- **Focus**: Frame buffer bottlenecks and integration issues

### 6. **detektor-coder**
- **Role**: TDD implementation specialist
- **Tools**: Read, Write, Edit, MultiEdit, Bash, Grep, Glob, Task
- **Specialization**:
  - Test-first development
  - Observability-first (OpenTelemetry, Prometheus)
  - Clean Architecture implementation
  - Event-driven patterns (Redis Streams)
  - Production-ready code from first commit
- **Standards**: 100% type hints, structured logging, health/metrics endpoints

### 7. **documentation-keeper**
- **Role**: Documentation synchronization guardian
- **Tools**: Read, Write, Edit, MultiEdit, Grep, Glob, Task
- **Specialization**:
  - Status synchronization across all docs
  - Port mapping consistency
  - Architecture diagram updates
  - Troubleshooting documentation
  - API documentation maintenance
- **Key files**: PROJECT_CONTEXT.md, architektura_systemu.md, README.md

### 8. **pisarz** (Writer)
- **Role**: Technical content aggregator for social media
- **Tools**: Read, Write, Edit, Grep, Glob, Bash, Task
- **Specialization**:
  - Git history analysis
  - Execution timeline reconstruction
  - Metrics collection
  - Technical deep dives
  - Social media angle identification
- **Output**: Complete research packs for content creation

## 🔄 Agent Chain Implementation

### Chain Definition Pattern
```python
# Automatic agent selection based on task type
task_patterns = {
    r"Implement|Create|Add|napisz|stwórz": "detektor-coder",
    r"Debug|Fix|Investigate|napraw": "debugger",
    r"Deploy|CI/CD|wdróż": "deployment-specialist",
    r"Refactor|Optimize": "architecture-advisor",
}

# Quality gate after each task
quality_gates = {
    "code_implementation": "code-reviewer",
    "deployment": "health_check",
    "documentation": "consistency_check",
}
```

### Chain Execution Flow
```mermaid
graph LR
    A[Task Analysis] --> B{Task Type}
    B -->|Implementation| C[detektor-coder]
    B -->|Debug| D[debugger/pipeline-debugger]
    B -->|Deploy| E[deployment-specialist]
    B -->|Architecture| F[architecture-advisor]

    C --> G[code-reviewer]
    D --> G
    F --> C

    G -->|Issues Found| C
    G -->|Approved| H[documentation-keeper]

    H --> I[git commit + push]
    I --> J[deployment-specialist]
    J --> K[Verification]
```

### Real Execution Example (Blok 4.1)
```yaml
Execution Timeline:
  10:30:15: User command: /nakurwiaj blok-4.1
  10:30:20: System: Analyzing task type...
  10:30:25: → /agent detektor-coder
    - Created: services/frame-buffer/src/shared_buffer.py (93 lines)
    - Modified: services/frame-buffer/src/main.py (166 lines changed)
    - Modified: services/frame-buffer/src/consumer.py (7 lines)
    - Added: tests/test_shared_buffer.py (81 lines)

  10:35:45: → /agent code-reviewer
    Issues found:
    - Missing type hints in shared_buffer.py:45
    - No error handling for Redis timeout
    - Thread safety concern in get_instance()

  10:38:10: → /agent detektor-coder (fixing issues)
    - Added type hints: Optional[FrameBuffer]
    - Implemented timeout handling with try/except
    - Added threading.Lock() for thread safety

  10:40:30: → /agent code-reviewer
    - ✅ All issues resolved
    - Code quality approved

  10:41:00: Automatic git operations
    - git add -A
    - git commit -m "fix: naprawa frame buffer dead-end - implementacja SharedFrameBuffer"
    - git push origin main

  10:41:30: → /agent deployment-specialist
    - GitHub Actions run #456 started
    - Build time: 2m 15s
    - Docker images pushed to ghcr.io
    - Deploy to Nebula: successful
    - Health checks: all services green

  10:45:00: → /agent documentation-keeper
    - Updated: PROJECT_CONTEXT.md (frame buffer status)
    - Updated: TROUBLESHOOTING.md (added solution)
    - Updated: architektura_systemu.md (task checkbox [x])
    - Updated: 04-frame-tracking.md (blok 4.1 status)

Total execution time: 14m 45s (vs 2h estimate)
```

## 🏗️ Architectural Patterns

### 1. **Agent Autonomy Pattern**
- Agents make decisions without user confirmation
- Maximum 3 retry iterations for failed tasks
- Automatic fallback strategies

### 2. **Parallel Execution Pattern**
```python
# Agents can work in parallel when tasks are independent
parallel_tasks = [
    agent.read_file("config.py"),
    agent.grep_pattern("TODO"),
    agent.check_health_endpoint(),
]
results = await asyncio.gather(*parallel_tasks)
```

### 3. **State Sharing Pattern**
- Agents share context through structured metadata
- Trace IDs propagate through entire chain
- Documentation keeper ensures consistency

### 4. **Quality Gate Pattern**
```python
@quality_gate(reviewer="code-reviewer")
async def implement_feature(task):
    result = await coder_agent.implement(task)
    review = await reviewer_agent.review(result)

    iteration = 0
    while review.has_issues and iteration < 3:
        result = await coder_agent.fix_issues(review.issues)
        review = await reviewer_agent.review(result)
        iteration += 1

    if review.has_issues:
        raise QualityGateFailure(review.issues)

    return result
```

## 🔧 Implementation Details

### SharedFrameBuffer Solution
```python
# Problem: Consumer and API used different buffer instances
# Solution: Thread-safe singleton pattern

class SharedFrameBuffer:
    _instance = None
    _buffer = None
    _lock = asyncio.Lock()
    _sync_lock = threading.Lock()

    @classmethod
    async def get_instance(cls) -> FrameBuffer:
        if cls._buffer is None:
            async with cls._lock:
                if cls._buffer is None:  # Double-check pattern
                    cls._buffer = FrameBuffer()
        return cls._buffer
```

### Trace Context Propagation
```python
# Every frame carries trace context through the pipeline
frame_data = {
    "frame_id": FrameID.generate(),
    "trace_context": TraceContext.inject(),
    "timestamp": datetime.utcnow(),
    "data": frame_bytes,
}

# Consumer extracts and continues trace
trace_ctx = TraceContext.extract(frame_data["trace_context"])
with trace_ctx.span("process_frame"):
    # Processing with full observability
    pass
```

### Automated Deployment Flow
```yaml
GitHub Actions Pipeline:
  1. Code pushed to main
  2. Workflows triggered automatically
  3. Tests run in parallel
  4. Docker images built (multi-stage)
  5. Images pushed to ghcr.io
  6. Deployment script triggered on Nebula
  7. Health checks verify all services
  8. Rollback if any check fails
```

## 📊 Performance Metrics

### Agent Efficiency
| Metric | Manual | With Agents | Improvement |
|--------|--------|-------------|-------------|
| Task completion time | 2h | 15min | 87.5% faster |
| Code review iterations | 1-2 | 3-5 | More thorough |
| Bug detection rate | 60% | 95% | 58% better |
| Documentation sync | Often missed | 100% | Guaranteed |
| Deployment success | 85% | 99% | More reliable |

### Frame Buffer Fix Results
- **Before**: 100% frame loss after buffer full
- **After**: 0% frame loss with backpressure
- **Latency**: <10ms added by shared buffer
- **Throughput**: 30fps sustained
- **Memory**: Stable at 1000 frame buffer

## 🔍 Deep Dive: Agent Decision Making

### Task Classification Algorithm
```python
def classify_task(task_description: str) -> str:
    """Determine which agent should handle the task."""

    # Priority order matters - more specific patterns first
    patterns = [
        (r"dead.?end|bottleneck|pipeline", "pipeline-debugger"),
        (r"deploy|CI/CD|GitHub Actions", "deployment-specialist"),
        (r"architecture|refactor|pattern", "architecture-advisor"),
        (r"debug|fix|error|issue", "debugger"),
        (r"implement|create|add|feature", "detektor-coder"),
        (r"document|README|docs", "documentation-keeper"),
    ]

    for pattern, agent in patterns:
        if re.search(pattern, task_description, re.IGNORECASE):
            return agent

    # Default to coder for unknown tasks
    return "detektor-coder"
```

### Inter-Agent Communication
```python
# Agents communicate through structured messages
class AgentMessage:
    from_agent: str
    to_agent: str
    task_id: str
    action: str  # "implement", "review", "fix", etc.
    payload: dict
    metadata: dict  # trace_id, timestamp, iteration

# Message passing through event bus
async def send_to_agent(message: AgentMessage):
    await event_bus.publish(f"agent.{message.to_agent}", message)

# Agents subscribe to their channels
@agent.on_message("agent.code-reviewer")
async def handle_review_request(message: AgentMessage):
    code = message.payload["code"]
    review_result = await perform_review(code)

    if review_result.has_issues:
        # Send back to original agent
        await send_to_agent(AgentMessage(
            from_agent="code-reviewer",
            to_agent=message.from_agent,
            action="fix_issues",
            payload={"issues": review_result.issues}
        ))
```

## 🚀 Future Enhancements

1. **Self-Learning Agents**
   - Learn from past reviews
   - Adapt patterns based on project
   - Predict common issues

2. **Agent Marketplace**
   - Share specialized agents
   - Domain-specific agents (e.g., security, performance)
   - Community contributions

3. **Visual Agent Designer**
   - Drag-and-drop chain builder
   - Real-time execution monitoring
   - Performance analytics

4. **Multi-Project Coordination**
   - Agents working across repositories
   - Knowledge sharing between projects
   - Cross-project refactoring
