"""Frame tracking library for distributed tracing of video frames."""

from .context import TraceContext
from .frame_id import FrameID
from .metadata import FrameMetadata, ProcessingStage
from .search import FrameSearchClient, FrameTrace, quick_search

__version__ = "1.0.0"
__all__ = [
    "FrameID",
    "FrameMetadata",
    "ProcessingStage",
    "TraceContext",
    "FrameSearchClient",
    "FrameTrace",
    "quick_search",
]
