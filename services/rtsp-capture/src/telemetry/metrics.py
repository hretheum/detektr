"""Simple metrics module."""
import logging

logger = logging.getLogger(__name__)


class SimpleMetrics:
    """Simple metrics collector."""

    def __init__(self, service_name: str):
        """Initialize metrics collector for a service."""
        self.service_name = service_name
        self._counters = {}
        self._gauges = {}

    def increment_errors(self, error_type: str, **kwargs):
        """Increment error counter."""
        key = f"{self.service_name}_errors_{error_type}"
        self._counters[key] = self._counters.get(key, 0) + 1
        logger.debug(f"Incremented {key}: {self._counters[key]}")

    def record_processing_time(self, stage: str, duration: float, **kwargs):
        """Record processing time."""
        key = f"{self.service_name}_processing_{stage}"
        if key not in self._gauges:
            self._gauges[key] = []
        self._gauges[key].append(duration)
        logger.debug(f"Recorded {key}: {duration}s")

    def set_service_info(self, info: dict):
        """Set service information."""
        logger.info(f"Service info for {self.service_name}: {info}")

    def increment_frames_processed(self, count: int = 1, **kwargs):
        """Increment frames processed counter."""
        key = f"{self.service_name}_frames_processed"
        self._counters[key] = self._counters.get(key, 0) + count
        logger.debug(f"Incremented {key}: {self._counters[key]}")


def get_metrics(service_name: str) -> SimpleMetrics:
    """Get metrics instance for a service."""
    return SimpleMetrics(service_name)
