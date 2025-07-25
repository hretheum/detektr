"""Metrics collection for processors."""
import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ProcessorMetrics:
    """Metrics collector for processor performance."""

    frames_processed: int = 0
    errors_total: int = 0
    processing_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_types: Dict[str, int] = field(default_factory=dict)

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_frame_processed(self, processing_time: float):
        """Record a successfully processed frame."""
        async with self._lock:
            self.frames_processed += 1
            self.processing_times.append(processing_time)

    async def record_error(self, error_type: str):
        """Record a processing error."""
        async with self._lock:
            self.errors_total += 1
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current metrics stats."""
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            min_time = min(self.processing_times)
            max_time = max(self.processing_times)
        else:
            avg_time = min_time = max_time = 0

        return {
            "frames_processed": self.frames_processed,
            "errors_total": self.errors_total,
            "processing_time_avg": avg_time,
            "processing_time_min": min_time,
            "processing_time_max": max_time,
            "error_types": dict(self.error_types),
        }

    def reset(self):
        """Reset all metrics."""
        self.frames_processed = 0
        self.errors_total = 0
        self.processing_times.clear()
        self.error_types.clear()
