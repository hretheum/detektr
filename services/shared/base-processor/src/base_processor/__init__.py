"""Base processor framework for AI services."""
from .base import BaseProcessor
from .exceptions import ProcessingError, ValidationError
from .metrics import ProcessorMetrics

__all__ = [
    "BaseProcessor",
    "ProcessingError",
    "ValidationError",
    "ProcessorMetrics",
]

__version__ = "1.0.0"
