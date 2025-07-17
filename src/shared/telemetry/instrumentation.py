"""OpenTelemetry auto-instrumentation setup.

This module provides automatic instrumentation for common libraries
without modifying application code.
"""

import contextlib
import os
from typing import Optional

# Import instrumentors - they will check if libraries are installed
try:
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
except ImportError:
    AioHttpClientInstrumentor = None

try:
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
except ImportError:
    AsyncPGInstrumentor = None

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
    FastAPIInstrumentor = None

try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
except ImportError:
    LoggingInstrumentor = None

try:
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
except ImportError:
    Psycopg2Instrumentor = None

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except ImportError:
    RedisInstrumentor = None

try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
except ImportError:
    RequestsInstrumentor = None

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None

try:
    from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor
except ImportError:
    URLLib3Instrumentor = None


def setup_auto_instrumentation() -> None:
    """Configure automatic instrumentation for all supported libraries.

    This function enables tracing for:
    - FastAPI (web framework)
    - SQLAlchemy (ORM)
    - AsyncPG (async PostgreSQL)
    - Redis (caching/message bus)
    - Requests/aiohttp/urllib3 (HTTP clients)
    - Logging (structured logs with trace context)
    """
    # FastAPI instrumentation
    if not os.getenv("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS"):
        # Default exclude health checks
        os.environ[
            "OTEL_PYTHON_FASTAPI_EXCLUDED_URLS"
        ] = "/health,/metrics,/docs,/openapi.json"

    if FastAPIInstrumentor:
        with contextlib.suppress(Exception):
            FastAPIInstrumentor().instrument()

    # Database instrumentation
    if SQLAlchemyInstrumentor:
        with contextlib.suppress(Exception):
            SQLAlchemyInstrumentor().instrument(
                enable_commenter=True,
                commenter_options={
                    "opentelemetry_values": True,
                },
            )

    if AsyncPGInstrumentor:
        with contextlib.suppress(Exception):
            AsyncPGInstrumentor().instrument()

    if Psycopg2Instrumentor:
        with contextlib.suppress(Exception):
            Psycopg2Instrumentor().instrument()

    # Redis instrumentation
    if RedisInstrumentor:
        with contextlib.suppress(Exception):
            RedisInstrumentor().instrument()

    # HTTP client instrumentation
    if RequestsInstrumentor:
        with contextlib.suppress(Exception):
            RequestsInstrumentor().instrument()

    if AioHttpClientInstrumentor:
        with contextlib.suppress(Exception):
            AioHttpClientInstrumentor().instrument()

    if URLLib3Instrumentor:
        with contextlib.suppress(Exception):
            URLLib3Instrumentor().instrument()

    # Logging instrumentation - adds trace context to logs
    if LoggingInstrumentor:
        with contextlib.suppress(Exception):
            LoggingInstrumentor().instrument(set_logging_format=True)


def instrument_app(app: Optional[object] = None) -> None:
    """Instrument a specific FastAPI/Flask application instance.

    Args:
        app: FastAPI or Flask application instance
    """
    if app is None:
        return

    # Check if it's FastAPI
    if FastAPIInstrumentor and hasattr(app, "add_middleware"):
        with contextlib.suppress(Exception):
            FastAPIInstrumentor.instrument_app(app)
