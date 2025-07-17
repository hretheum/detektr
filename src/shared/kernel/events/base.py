"""Base domain event definition."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """Base class for all domain events."""

    event_id: str = field(default_factory=lambda: str(uuid4()), init=False)
    event_type: str = field(default="", init=False)
    occurred_at: datetime = field(default_factory=datetime.now, init=False)
    metadata: Dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Set event type from class name if not set."""
        if not hasattr(self, "event_type") or not self.event_type:
            # Convert class name to snake_case event type
            class_name = self.__class__.__name__
            # Insert underscore before uppercase letters
            event_type = ""
            for i, char in enumerate(class_name):
                if i > 0 and char.isupper() and class_name[i - 1].islower():
                    event_type += "_"
                event_type += char.lower()
            self.event_type = event_type

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "metadata": self.metadata,
            "data": {
                k: v
                for k, v in self.__dict__.items()
                if k not in ["event_id", "event_type", "occurred_at", "metadata"]
            },
        }
