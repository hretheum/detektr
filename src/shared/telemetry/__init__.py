"""
OpenTelemetry telemetry setup module.

Provides centralized configuration for traces, metrics, and logs.
"""

from .config import setup_telemetry

__all__ = ["setup_telemetry"]
