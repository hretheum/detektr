"""Frame tracking library for distributed tracing of video frames."""

from .context import TraceContext
from .frame_id import FrameID
from .metadata import FrameMetadata, ProcessingStage

__version__ = "1.0.0"
__all__ = ["FrameID", "FrameMetadata", "ProcessingStage", "TraceContext"]
