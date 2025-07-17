"""
OpenTelemetry telemetry setup module.

Provides centralized configuration for traces, metrics, and logs.
"""

from .config import setup_telemetry
from .instrumentation import instrument_app, setup_auto_instrumentation

__all__ = ["setup_telemetry", "setup_auto_instrumentation", "instrument_app"]
