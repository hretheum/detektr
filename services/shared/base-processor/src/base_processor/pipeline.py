"""Processing pipeline implementation."""
import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar

T = TypeVar("T")


@dataclass
class PipelineStage:
    """Single stage in processing pipeline."""

    name: str
    handler: Callable
    timeout: Optional[float] = None
    skip_on_error: bool = False


class ProcessingPipeline:
    """Configurable processing pipeline with stages."""

    def __init__(self):
        self.stages: List[PipelineStage] = []
        self._before_stage_hooks: Dict[str, List[Callable]] = {}
        self._after_stage_hooks: Dict[str, List[Callable]] = {}

    def add_stage(
        self,
        name: str,
        handler: Callable,
        timeout: Optional[float] = None,
        skip_on_error: bool = False,
    ) -> "ProcessingPipeline":
        """Add a processing stage to the pipeline.

        Args:
            name: Stage name
            handler: Async handler function
            timeout: Optional timeout in seconds
            skip_on_error: Whether to skip this stage on error

        Returns:
            Self for chaining
        """
        stage = PipelineStage(name, handler, timeout, skip_on_error)
        self.stages.append(stage)
        return self

    def before_stage(self, stage_name: str, hook: Callable):
        """Register a hook to run before a stage."""
        if stage_name not in self._before_stage_hooks:
            self._before_stage_hooks[stage_name] = []
        self._before_stage_hooks[stage_name].append(hook)

    def after_stage(self, stage_name: str, hook: Callable):
        """Register a hook to run after a stage."""
        if stage_name not in self._after_stage_hooks:
            self._after_stage_hooks[stage_name] = []
        self._after_stage_hooks[stage_name].append(hook)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pipeline with given context.

        Args:
            context: Initial context dictionary

        Returns:
            Final context after all stages
        """
        result = context.copy()

        for stage in self.stages:
            try:
                # Run before hooks
                await self._run_hooks(
                    self._before_stage_hooks.get(stage.name, []), result
                )

                # Execute stage with timeout if specified
                if stage.timeout:
                    result = await asyncio.wait_for(
                        stage.handler(result), timeout=stage.timeout
                    )
                else:
                    result = await stage.handler(result)

                # Run after hooks
                await self._run_hooks(
                    self._after_stage_hooks.get(stage.name, []), result
                )

            except asyncio.TimeoutError:
                if not stage.skip_on_error:
                    raise TimeoutError(
                        f"Stage '{stage.name}' timed out after {stage.timeout}s"
                    )

            except Exception as e:
                if not stage.skip_on_error:
                    raise
                # Log and continue if skip_on_error is True
                result["_pipeline_errors"] = result.get("_pipeline_errors", [])
                result["_pipeline_errors"].append(
                    {"stage": stage.name, "error": str(e)}
                )

        return result

    async def _run_hooks(self, hooks: List[Callable], context: Dict[str, Any]):
        """Run a list of hooks with context."""
        for hook in hooks:
            if asyncio.iscoroutinefunction(hook):
                await hook(context)
            else:
                hook(context)


class BatchProcessingPipeline(ProcessingPipeline):
    """Pipeline with batch processing support."""

    def __init__(self, batch_size: int = 10):
        super().__init__()
        self.batch_size = batch_size

    async def execute_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute pipeline on a batch of items.

        Args:
            items: List of context dictionaries

        Returns:
            List of results
        """
        results = []

        # Process in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]

            # Process batch concurrently
            batch_results = await asyncio.gather(
                *[self.execute(item) for item in batch], return_exceptions=True
            )

            # Handle results and exceptions
            for idx, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    # Add error info to original item
                    error_result = batch[idx].copy()
                    error_result["_error"] = str(result)
                    results.append(error_result)
                else:
                    results.append(result)

        return results
