"""
Pytest configuration for RTSP capture tests.

Handles cleanup of global state between tests, especially Prometheus metrics.
"""
import contextlib

import prometheus_client
import pytest
from prometheus_client import REGISTRY
from prometheus_client.registry import CollectorRegistry


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """
    Clear Prometheus registry before each test to avoid metric duplication.

    This is necessary because Prometheus uses a global registry that persists
    between tests, causing "Duplicated timeseries in CollectorRegistry" errors.
    """
    # Get all collectors before test
    collectors_before = list(REGISTRY._collector_to_names.keys())

    yield

    # After test, unregister any new collectors
    collectors_after = list(REGISTRY._collector_to_names.keys())
    new_collectors = [c for c in collectors_after if c not in collectors_before]

    for collector in new_collectors:
        with contextlib.suppress(Exception):
            REGISTRY.unregister(collector)


@pytest.fixture
def clean_metrics_registry():
    """
    Provide a clean metrics registry for tests that need isolated metrics.

    Usage:
        def test_metrics(clean_metrics_registry):
            # Your test with isolated metrics
    """
    # Create new registry
    test_registry = CollectorRegistry()

    # Temporarily replace global registry
    original_registry = REGISTRY
    prometheus_client.REGISTRY = test_registry

    yield test_registry

    # Restore original registry
    prometheus_client.REGISTRY = original_registry


@pytest.fixture(scope="function")
def reset_observability_metrics():
    """
    Reset the observability module's metrics initialization flag.

    This allows tests to re-initialize metrics cleanly.
    """
    import src.observability as obs

    # Reset the initialization flag
    obs._metrics_initialized = False

    # Clear metric references
    obs.frame_counter = None
    obs.frame_processing_time = None
    obs.frame_drops_counter = None
    obs.active_connections_gauge = None
    obs.buffer_size_gauge = None
    obs.redis_queue_size_gauge = None

    yield

    # Reset again after test
    obs._metrics_initialized = False
