"""Frame ID generator for unique, time-ordered identifiers."""

import threading
import time
import uuid
from typing import Dict, Optional


class FrameID:
    """Generator for unique frame identifiers."""

    _counter = 0
    _counter_lock = threading.Lock()
    _last_timestamp = 0

    @classmethod
    def generate(
        cls, camera_id: Optional[str] = None, source: Optional[str] = None
    ) -> str:
        """
        Generate a unique, time-ordered frame ID.

        Format: {timestamp_ms}_{source}_{camera_id}_{counter}_{random}

        Args:
            camera_id: Optional camera identifier
            source: Optional source service identifier

        Returns:
            Unique frame ID string
        """
        # Get current timestamp in milliseconds
        timestamp_ns = time.time_ns()
        timestamp_ms = timestamp_ns // 1_000_000

        # Ensure monotonic ordering even with same millisecond
        with cls._counter_lock:
            if timestamp_ms <= cls._last_timestamp:
                timestamp_ms = cls._last_timestamp + 1
            cls._last_timestamp = timestamp_ms
            cls._counter = (cls._counter + 1) % 10000
            counter = cls._counter

        # Components
        parts = [str(timestamp_ms)]

        if source:
            parts.append(source.replace("_", "-"))
        else:
            parts.append("unknown")

        if camera_id:
            parts.append(camera_id.replace("_", "-"))
        else:
            parts.append("default")

        parts.append(f"{counter:04d}")

        # Add random component for extra uniqueness
        random_part = uuid.uuid4().hex[:8]
        parts.append(random_part)

        return "_".join(parts)

    @staticmethod
    def parse(frame_id: str) -> Dict[str, str]:
        """
        Parse frame ID into components.

        Args:
            frame_id: Frame ID to parse

        Returns:
            Dictionary with parsed components
        """
        parts = frame_id.split("_")

        components = {}

        if len(parts) >= 1:
            components["timestamp"] = parts[0]
            components["timestamp_ms"] = int(parts[0])

        if len(parts) >= 2:
            components["source"] = parts[1]

        if len(parts) >= 3:
            components["camera_id"] = parts[2]

        if len(parts) >= 4:
            components["counter"] = parts[3]

        if len(parts) >= 5:
            components["random"] = parts[4]

        components["full_id"] = frame_id

        return components
