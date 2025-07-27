# Code Examples - Agent Implementation

## 🤖 Agent Configuration Examples

### 1. Agent Definition (detektor-coder)
```yaml
---
name: detektor-coder
description: Specjalista od implementacji zadań atomowych w projekcie Detektor - TDD, observability-first, Clean Architecture
tools: Read, Write, Edit, MultiEdit, Bash, Grep, Glob, Task
---

Jesteś ekspertem implementacji w projekcie Detektor. Twoja rola to pisanie kodu produkcyjnego zgodnie z najwyższymi standardami projektu.

## 1. **Podstawowe zasady projektu**

- **TDD ZAWSZE**: Test first, implementation second
- **Observability-first**: Każdy serwis ma OpenTelemetry, Prometheus metrics, structured logging
- **Clean Architecture**: Separacja warstw (domain, infrastructure, application)
- **Event-driven**: Komunikacja przez Redis Streams
- **Type hints**: 100% pokrycie w Python 3.11+
- **No hardcoded values**: Wszystko przez config/env
```

### 2. Chain Automation Command
```python
# /nakurwiaj command implementation
class AgentChainExecutor:
    def __init__(self):
        self.agents = {
            "detektor-coder": DetektorCoderAgent(),
            "code-reviewer": CodeReviewerAgent(),
            "deployment-specialist": DeploymentAgent(),
            "documentation-keeper": DocumentationAgent(),
            # ... other agents
        }

    async def execute_block(self, block_number: str):
        """Execute all tasks in a block atomically."""
        tasks = await self.load_block_tasks(block_number)

        for task in tasks:
            agent = self.select_agent(task.description)

            # Execute with quality gates
            result = await self.execute_with_review(agent, task)

            # Update documentation
            await self.agents["documentation-keeper"].sync(result)

            # Mark task complete
            task.mark_complete()
```

## 🔧 SharedFrameBuffer Implementation

### Complete Implementation
```python
"""
Shared Frame Buffer - Singleton pattern for sharing buffer between consumer and API.
"""

import asyncio
import threading
from typing import Optional, List, Dict, Any

from frame_buffer import FrameBuffer
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class SharedFrameBuffer:
    """
    Singleton wrapper for FrameBuffer to ensure shared state between components.

    This class implements a thread-safe singleton pattern to guarantee that
    all parts of the application (consumer, API endpoints) use the same
    FrameBuffer instance.
    """

    _instance: Optional["SharedFrameBuffer"] = None
    _buffer: Optional[FrameBuffer] = None
    _lock = asyncio.Lock()
    _sync_lock = threading.Lock()

    def __new__(cls) -> "SharedFrameBuffer":
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls) -> FrameBuffer:
        """
        Get the shared FrameBuffer instance.

        This method is thread-safe and ensures that only one FrameBuffer
        instance is created, even when called concurrently.

        Returns:
            FrameBuffer: The shared buffer instance
        """
        with tracer.start_as_current_span("shared_buffer.get_instance"):
            if cls._buffer is None:
                async with cls._lock:
                    # Double-check pattern to avoid race conditions
                    if cls._buffer is None:
                        cls._buffer = FrameBuffer()
                        trace.get_current_span().set_attribute(
                            "buffer.initialized", True
                        )
            return cls._buffer
```

### API Integration
```python
from fastapi import FastAPI, Query, HTTPException
from shared_buffer import SharedFrameBuffer

app = FastAPI()

@app.get("/frames/dequeue")
async def dequeue_frame(
    count: int = Query(1, ge=1, le=100, description="Number of frames to dequeue")
):
    """Dequeue frames from the shared buffer."""
    try:
        # Get shared buffer instance
        buffer = await SharedFrameBuffer.get_instance()

        # Get frames with trace context
        frames = []
        for _ in range(min(count, buffer.size())):
            frame = await buffer.get()
            if frame:
                # Extract and propagate trace context
                if "trace_context" in frame:
                    ctx = TraceContext.extract(frame["trace_context"])
                    ctx.add_event("frame.dequeued", {
                        "frame_id": frame.get("frame_id"),
                        "buffer_size": buffer.size()
                    })
                frames.append(frame)

        return {
            "frames": frames,
            "dequeued": len(frames),
            "remaining": buffer.size()
        }

    except Exception as e:
        logger.error(f"Error dequeuing frames: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

## 📊 Code Review Examples

### Before Review (Issues Found)
```python
# ❌ Issues found by code-reviewer agent
def process_frame(frame_data):  # Missing type hints
    """Process a single frame."""  # Incomplete docstring

    # Magic number
    if frame_data['size'] > 1000000:
        return None  # No error handling

    # Blocking call in async context
    result = cv2.process(frame_data['image'])

    # No trace context
    return {
        'result': result,
        'timestamp': datetime.now()  # Not UTC
    }
```

### After Review (Fixed by detektor-coder)
```python
# ✅ After code-reviewer feedback
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timezone
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Constants
MAX_FRAME_SIZE_BYTES = 1_000_000  # 1MB

async def process_frame(frame_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single frame with full observability.

    Args:
        frame_data: Dictionary containing frame information
            - image: Frame bytes
            - size: Size in bytes
            - frame_id: Unique frame identifier
            - trace_context: OpenTelemetry trace context

    Returns:
        Processed frame data or None if frame is too large

    Raises:
        FrameProcessingError: If processing fails
    """
    with tracer.start_as_current_span("process_frame") as span:
        span.set_attribute("frame.id", frame_data.get("frame_id"))
        span.set_attribute("frame.size", frame_data.get("size", 0))

        # Validate frame size
        if frame_data.get('size', 0) > MAX_FRAME_SIZE_BYTES:
            span.add_event("frame.rejected", {"reason": "size_exceeded"})
            logger.warning(
                f"Frame {frame_data.get('frame_id')} rejected: "
                f"size {frame_data.get('size')} exceeds {MAX_FRAME_SIZE_BYTES}"
            )
            return None

        try:
            # Non-blocking processing
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                cv2.process,
                frame_data['image']
            )

            # Return with proper timestamp and trace
            return {
                'result': result,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'frame_id': frame_data.get('frame_id'),
                'trace_id': trace.get_current_span().get_span_context().trace_id
            }

        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            raise FrameProcessingError(
                f"Failed to process frame {frame_data.get('frame_id')}: {str(e)}"
            )
```

## 🔄 Agent Chain Implementation

### Task Pattern Matching
```python
import re
from typing import Dict, Callable, Optional

class TaskRouter:
    """Routes tasks to appropriate agents based on patterns."""

    def __init__(self):
        self.patterns: Dict[str, str] = {
            r"(?i)(implement|create|add|napisz|stwórz|dodaj)": "detektor-coder",
            r"(?i)(debug|fix|investigate|napraw|zbadaj)": "debugger",
            r"(?i)(deploy|deployment|ci/cd|wdróż)": "deployment-specialist",
            r"(?i)(refactor|optimize|improve|zoptymalizuj)": "architecture-advisor",
            r"(?i)(review|check|validate|sprawdź)": "code-reviewer",
            r"(?i)(document|readme|docs)": "documentation-keeper",
        }

    def route_task(self, task_description: str) -> str:
        """Determine which agent should handle the task."""
        for pattern, agent in self.patterns.items():
            if re.search(pattern, task_description):
                return agent

        # Default to coder for unknown tasks
        return "detektor-coder"
```

### Quality Gate Implementation
```python
class QualityGate:
    """Enforces quality standards between agent tasks."""

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations

    async def execute_with_review(
        self,
        implementation_agent: Agent,
        review_agent: Agent,
        task: Task
    ) -> TaskResult:
        """Execute task with mandatory review cycles."""

        iteration = 0
        while iteration < self.max_iterations:
            # Implementation phase
            with tracer.start_as_current_span(f"iteration_{iteration}"):
                result = await implementation_agent.execute(task)

                # Review phase
                review = await review_agent.review(result)

                if review.approved:
                    span = trace.get_current_span()
                    span.set_attribute("iterations_needed", iteration + 1)
                    span.set_attribute("review.approved", True)
                    return result

                # Prepare feedback for next iteration
                task = task.with_feedback(review.issues)
                iteration += 1

        # Max iterations reached
        raise QualityGateExceeded(
            f"Failed to pass review after {self.max_iterations} iterations"
        )
```

## 🚀 Deployment Automation

### GitHub Actions Integration
```yaml
# .github/workflows/agent-triggered-deploy.yml
name: Agent Triggered Deployment

on:
  push:
    branches: [main]
    # Only when pushed by agent commits

jobs:
  detect-agent-commit:
    runs-on: ubuntu-latest
    outputs:
      is-agent: ${{ steps.check.outputs.is-agent }}

    steps:
      - name: Check if agent commit
        id: check
        run: |
          if [[ "${{ github.event.head_commit.message }}" =~ (feat|fix|chore):.+\[agent:[a-z-]+\] ]]; then
            echo "is-agent=true" >> $GITHUB_OUTPUT
          else
            echo "is-agent=false" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: detect-agent-commit
    if: needs.detect-agent-commit.outputs.is-agent == 'true'
    runs-on: self-hosted

    steps:
      - uses: actions/checkout@v4

      - name: Deploy with verification
        run: |
          ./scripts/deploy.sh production deploy
          ./scripts/deploy.sh production verify

      - name: Notify agent of deployment
        run: |
          curl -X POST ${{ secrets.AGENT_WEBHOOK }} \
            -H "Content-Type: application/json" \
            -d '{
              "status": "deployed",
              "commit": "${{ github.sha }}",
              "services": ["frame-buffer", "rtsp-capture"]
            }'
```

### Agent Deployment Monitoring
```python
class DeploymentSpecialist(Agent):
    """Monitors and manages deployments."""

    async def monitor_deployment(self, commit_sha: str) -> DeploymentResult:
        """Monitor GitHub Actions deployment."""

        with tracer.start_as_current_span("monitor_deployment") as span:
            span.set_attribute("commit.sha", commit_sha)

            # Check GitHub Actions
            run = await self.get_workflow_run(commit_sha)

            # Monitor in real-time
            while run.status in ["queued", "in_progress"]:
                await asyncio.sleep(10)
                run = await self.refresh_run_status(run.id)

                # Log progress
                logger.info(f"Deployment {run.id}: {run.status}")
                span.add_event(f"status.{run.status}")

            if run.conclusion == "success":
                # Verify health checks
                health_ok = await self.verify_health_checks()
                span.set_attribute("health_checks.passed", health_ok)

                if health_ok:
                    return DeploymentResult.success(run)
                else:
                    # Trigger rollback
                    await self.rollback(commit_sha)
                    return DeploymentResult.failed("Health checks failed")

            return DeploymentResult.failed(run.conclusion)
```

## 📝 Documentation Sync

### Documentation Keeper Implementation
```python
class DocumentationKeeper(Agent):
    """Maintains documentation consistency across the project."""

    def __init__(self):
        self.tracked_files = [
            "PROJECT_CONTEXT.md",
            "architektura_systemu.md",
            "README.md",
            "docs/TROUBLESHOOTING.md",
        ]

    async def sync_after_task(self, task: CompletedTask):
        """Update all relevant documentation after task completion."""

        updates = []

        # Update task status
        if task.has_checkbox:
            updates.append(
                self.update_checkbox(task.file, task.line, completed=True)
            )

        # Update service registry
        if task.added_service:
            updates.append(
                self.add_service_to_registry(
                    task.service_name,
                    task.service_port
                )
            )

        # Update troubleshooting if issues were fixed
        if task.fixed_issues:
            updates.append(
                self.document_solution(task.problem, task.solution)
            )

        # Execute all updates
        await asyncio.gather(*updates)

        # Verify consistency
        inconsistencies = await self.check_consistency()
        if inconsistencies:
            await self.fix_inconsistencies(inconsistencies)
```

## 🎯 Complete Chain Example

### Full Execution Flow
```python
# User command: /nakurwiaj blok-4.1

async def handle_nakurwiaj(block_id: str):
    """Execute entire block with agent chain."""

    # 1. Load block tasks
    block = await load_block(block_id)
    logger.info(f"Executing block {block_id} with {len(block.tasks)} tasks")

    # 2. Execute each task
    for i, task in enumerate(block.tasks):
        logger.info(f"Task {i+1}/{len(block.tasks)}: {task.description}")

        # Select primary agent
        agent = agent_router.route_task(task.description)

        # Execute with quality gates
        async with tracer.start_as_current_span(f"task_{i+1}") as span:
            span.set_attribute("task.description", task.description)
            span.set_attribute("agent.primary", agent)

            try:
                # Implementation
                result = await agents[agent].execute(task)

                # Mandatory code review
                review = await agents["code-reviewer"].review(result)

                # Fix loop if needed
                iterations = 0
                while not review.approved and iterations < 3:
                    result = await agents[agent].fix_issues(
                        result,
                        review.issues
                    )
                    review = await agents["code-reviewer"].review(result)
                    iterations += 1

                # Update documentation
                await agents["documentation-keeper"].sync(result)

                # Mark complete
                task.mark_complete()

            except Exception as e:
                logger.error(f"Task failed: {e}")
                span.record_exception(e)
                raise

    # 3. Commit and deploy
    commit_msg = f"feat: completed {block_id} - {block.description}"
    commit_sha = await git_commit_and_push(commit_msg)

    # 4. Monitor deployment
    deployment = await agents["deployment-specialist"].monitor(commit_sha)

    return {
        "block": block_id,
        "tasks_completed": len(block.tasks),
        "deployment": deployment.status,
        "total_time": span.end_time - span.start_time
    }
```
