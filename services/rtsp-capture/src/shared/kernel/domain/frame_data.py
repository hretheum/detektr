"""Frame data model for serialization purposes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class FrameData:
    """
    Frame data container for serialization.

    This is a simpler data structure compared to Frame entity,
    designed specifically for efficient serialization and transport.
    """

    id: str
    timestamp: datetime
    camera_id: str
    sequence_number: int
    image_data: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_frame(
        cls, frame: Any, image_data: np.ndarray, sequence_number: int
    ) -> "FrameData":
        """Create FrameData from Frame entity."""
        return cls(
            id=str(frame.id),
            timestamp=frame.timestamp,
            camera_id=frame.camera_id,
            sequence_number=sequence_number,
            image_data=image_data,
            metadata=frame.metadata.copy(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "camera_id": self.camera_id,
            "sequence_number": self.sequence_number,
            "image_data": self.image_data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrameData":
        """Create from dictionary after deserialization."""
        return cls(**data)
