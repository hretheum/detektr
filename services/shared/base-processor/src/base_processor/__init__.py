"""Base processor framework for AI services."""
from .base import BaseProcessor
from .batch_processor import BatchConfig, BatchProcessor, BatchResult
from .exceptions import ProcessingError, ResourceError, ValidationError
from .metrics import ProcessorMetrics
from .resource_manager import ResourceManager, ResourceStats
from .state_machine import FrameState, FrameStateMachine, StateTransition

__all__ = [
    "BaseProcessor",
    "ProcessingError",
    "ValidationError",
    "ResourceError",
    "ProcessorMetrics",
    "FrameState",
    "StateTransition",
    "FrameStateMachine",
    "ResourceManager",
    "ResourceStats",
    "BatchProcessor",
    "BatchConfig",
    "BatchResult",
]

__version__ = "1.0.0"
