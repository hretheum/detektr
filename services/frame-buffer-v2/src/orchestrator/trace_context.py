"""Trace context propagation for distributed tracing."""

import json
import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def generate_trace_id() -> str:
    """Generate a 128-bit trace ID."""
    return secrets.token_hex(16)  # 16 bytes = 128 bits


def generate_span_id() -> str:
    """Generate a 64-bit span ID."""
    return secrets.token_hex(8)  # 8 bytes = 64 bits


MAX_BAGGAGE_ITEMS = 32
MAX_BAGGAGE_SIZE = 8192  # bytes


@dataclass
class TraceContext:
    """W3C Trace Context for distributed tracing."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: str = "01"  # 01 = sampled
    trace_state: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def create(cls, sampled: bool = True) -> "TraceContext":
        """Create a new trace context."""
        return cls(
            trace_id=generate_trace_id(),
            span_id=generate_span_id(),
            trace_flags="01" if sampled else "00",
        )

    def create_child_span(self) -> "TraceContext":
        """Create a child span with the same trace ID."""
        # Limit baggage size to prevent memory issues
        baggage = {}
        total_size = 0
        for k, v in list(self.baggage.items())[:MAX_BAGGAGE_ITEMS]:
            item_size = len(k) + len(v)
            if total_size + item_size > MAX_BAGGAGE_SIZE:
                break
            baggage[k] = v
            total_size += item_size

        return TraceContext(
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
            trace_state=self.trace_state.copy(),
            baggage=baggage,
        )

    def is_sampled(self) -> bool:
        """Check if trace is sampled."""
        return self.trace_flags == "01"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
            "trace_state": self.trace_state,
            "attributes": self.attributes,
            "baggage": self.baggage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceContext":
        """Create from dictionary."""
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            trace_flags=data.get("trace_flags", "01"),
            trace_state=data.get("trace_state", {}),
            attributes=data.get("attributes", {}),
            baggage=data.get("baggage", {}),
        )

    def to_traceparent(self) -> str:
        """Convert to W3C traceparent header format."""
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags}"

    @classmethod
    def from_traceparent(cls, traceparent: str) -> "TraceContext":
        """Parse W3C traceparent header."""
        parts = traceparent.split("-")
        if len(parts) != 4:
            raise ValueError(f"Invalid traceparent format: {traceparent}")

        version, trace_id, span_id, trace_flags = parts
        if version != "00":
            raise ValueError(f"Unsupported trace version: {version}")

        return cls(trace_id=trace_id, span_id=span_id, trace_flags=trace_flags)

    def add_attribute(self, key: str, value: Any):
        """Add an attribute to the trace context."""
        self.attributes[key] = value

    def set_baggage(self, key: str, value: str):
        """Set baggage item."""
        self.baggage[key] = value

    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage item."""
        return self.baggage.get(key)


class TraceContextManager:
    """Manager for trace context operations."""

    def __init__(self, sampling_rate: float = 1.0):
        """Initialize trace context manager.

        Args:
            sampling_rate: Probability of sampling traces (0.0 to 1.0)
        """
        self.sampling_rate = sampling_rate

    def create_context(self, force_sample: Optional[bool] = None) -> TraceContext:
        """Create a new trace context with sampling decision."""
        if force_sample is not None:
            sampled = force_sample
        else:
            sampled = random.random() < self.sampling_rate

        return TraceContext.create(sampled=sampled)

    def extract_from_headers(self, headers: Dict[str, str]) -> Optional[TraceContext]:
        """Extract trace context from HTTP headers."""
        traceparent = headers.get("traceparent")
        if not traceparent:
            return None

        try:
            ctx = TraceContext.from_traceparent(traceparent)

            # Extract tracestate if present
            tracestate = headers.get("tracestate")
            if tracestate:
                # Parse tracestate (simplified - real implementation would be more complex)
                for item in tracestate.split(","):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        ctx.trace_state[key.strip()] = value.strip()

            # Extract baggage if present
            baggage = headers.get("baggage")
            if baggage:
                for item in baggage.split(","):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        ctx.baggage[key.strip()] = value.strip()

            return ctx
        except Exception:
            return None

    def inject_to_headers(self, ctx: TraceContext, headers: Dict[str, str]):
        """Inject trace context into HTTP headers."""
        # Add traceparent
        headers["traceparent"] = ctx.to_traceparent()

        # Add tracestate if present
        if ctx.trace_state:
            headers["tracestate"] = ",".join(
                f"{k}={v}" for k, v in ctx.trace_state.items()
            )

        # Add baggage if present
        if ctx.baggage:
            headers["baggage"] = ",".join(f"{k}={v}" for k, v in ctx.baggage.items())

    def extract_from_message(
        self, message: Dict[bytes, bytes]
    ) -> Optional[TraceContext]:
        """Extract trace context from Redis message."""
        trace_data = message.get(b"trace_context")
        if not trace_data:
            return None

        try:
            if isinstance(trace_data, bytes):
                trace_data = trace_data.decode()

            trace_dict = json.loads(trace_data)
            return TraceContext.from_dict(trace_dict)
        except Exception:
            return None

    def inject_to_message(self, ctx: TraceContext, message: Dict[str, Any]):
        """Inject trace context into Redis message."""
        message["trace_context"] = json.dumps(ctx.to_dict())


class TraceSpan:
    """Context manager for trace spans."""

    def __init__(
        self,
        name: str,
        ctx: TraceContext,
        manager: Optional[TraceContextManager] = None,
    ):
        """Initialize trace span.

        Args:
            name: Span name
            ctx: Parent trace context
            manager: Trace context manager
        """
        self.name = name
        self.parent_ctx = ctx
        self.manager = manager or TraceContextManager()
        self.ctx: Optional[TraceContext] = None
        self.start_time: Optional[float] = None

    async def __aenter__(self) -> TraceContext:
        """Enter span context."""
        self.ctx = self.parent_ctx.create_child_span()
        self.ctx.add_attribute("span.name", self.name)
        self.start_time = time.monotonic()  # Use monotonic time for duration
        self.wall_time = time.time()  # Store wall time if needed
        return self.ctx

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit span context."""
        if self.ctx and self.start_time:
            duration_ms = int((time.monotonic() - self.start_time) * 1000)
            self.ctx.add_attribute("duration_ms", duration_ms)

            if exc_type:
                self.ctx.add_attribute("error", True)
                self.ctx.add_attribute("error.type", exc_type.__name__)
                self.ctx.add_attribute("error.message", str(exc_val))


def create_trace_span(name: str, ctx: TraceContext) -> TraceSpan:
    """Create a trace span context manager."""
    return TraceSpan(name, ctx)
