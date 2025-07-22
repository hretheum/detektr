"""
Backpressure handling for frame queue.

Implements:
- Adaptive buffer sizing
- Circuit breaker pattern
- Graceful degradation under load
"""
import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from shared.kernel.domain.frame_data import FrameData


class BackpressureState(Enum):
    """State of backpressure mechanism."""

    NORMAL = "normal"
    BACKPRESSURE = "backpressure"
    DROPPING = "dropping"


class CircuitBreakerState(Enum):
    """State of circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking all calls
    HALF_OPEN = "half_open"  # Testing if system recovered


@dataclass
class BackpressureConfig:
    """Configuration for backpressure handling."""

    min_buffer_size: int = 100
    max_buffer_size: int = 10000
    high_watermark: float = 0.8  # Percentage of buffer that triggers backpressure
    low_watermark: float = 0.3  # Percentage of buffer that releases backpressure
    circuit_breaker_threshold: int = 5  # Consecutive failures to open circuit
    circuit_breaker_timeout: float = 30.0  # Seconds before trying to recover
    adaptive_increase_factor: float = 2.0  # Factor to increase buffer size
    adaptive_decrease_factor: float = 0.5  # Factor to decrease buffer size


@dataclass
class BackpressureMetrics:
    """Metrics for backpressure system."""

    frames_sent: int = 0
    frames_received: int = 0
    frames_dropped: int = 0
    backpressure_activations: int = 0
    circuit_breaker_trips: int = 0
    current_buffer_size: int = 0
    max_buffer_size_reached: int = 0
    total_wait_time_ms: float = 0.0


class AdaptiveBuffer:
    """
    Adaptive buffer that adjusts size based on load.

    Increases size under sustained pressure, decreases when idle.
    """

    def __init__(
        self,
        min_size: int,
        max_size: int,
        increase_factor: float = 2.0,
        decrease_factor: float = 0.5,
    ):
        """Initialize adaptive buffer."""
        self.min_size = min_size
        self.max_size = max_size
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.current_size = min_size

        # Track pressure events for adaptation
        self._pressure_events = 0
        self._idle_events = 0
        self._last_adjustment = time.time()
        self._adjustment_interval = 5.0  # Adjust every 5 seconds

    def record_pressure_event(self) -> None:
        """Record a backpressure event."""
        self._pressure_events += 1

    def record_idle_event(self) -> None:
        """Record an idle/low activity event."""
        self._idle_events += 1

    def should_adjust(self) -> bool:
        """Check if it's time to adjust buffer size."""
        return time.time() - self._last_adjustment > self._adjustment_interval

    def adjust_size(self) -> None:
        """Adjust buffer size based on recent activity."""
        # Calculate pressure ratio
        total_events = self._pressure_events + self._idle_events
        if total_events == 0:
            return

        pressure_ratio = self._pressure_events / total_events

        # Adjust size based on pressure
        if pressure_ratio > 0.7:  # High pressure
            new_size = int(self.current_size * self.increase_factor)
            self.current_size = min(new_size, self.max_size)
        elif pressure_ratio < 0.3:  # Low pressure
            new_size = int(self.current_size * self.decrease_factor)
            self.current_size = max(new_size, self.min_size)

        # Reset counters
        self._pressure_events = 0
        self._idle_events = 0
        self._last_adjustment = time.time()


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Protects system from cascading failures by blocking calls
    when error threshold is reached.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._half_open_successes = 0

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        if (
            self._state == CircuitBreakerState.OPEN
            and time.time() - self._last_failure_time > self.recovery_timeout
        ):
            self._state = CircuitBreakerState.HALF_OPEN
            self._half_open_calls = 0
            self._half_open_successes = 0
        return self._state

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        current_state = self.state  # This may update state

        if current_state == CircuitBreakerState.CLOSED:
            return True
        elif current_state == CircuitBreakerState.OPEN:
            return False
        else:  # HALF_OPEN
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_max_calls:
                # All test calls succeeded, close circuit
                self._state = CircuitBreakerState.CLOSED
                self._consecutive_failures = 0
        else:
            self._consecutive_failures = 0

    def record_failure(self) -> None:
        """Record failed operation."""
        self._consecutive_failures += 1
        self._last_failure_time = time.time()

        if (
            self.state == CircuitBreakerState.HALF_OPEN
            or self._consecutive_failures >= self.failure_threshold
        ):
            self._state = CircuitBreakerState.OPEN


class BackpressureHandler:
    """
    Main backpressure handler for frame queue.

    Coordinates adaptive buffering, circuit breaking, and flow control.
    """

    def __init__(
        self,
        config: BackpressureConfig,
        enable_dropping: bool = False,
    ):
        """Initialize backpressure handler."""
        self.config = config
        self.enable_dropping = enable_dropping

        # Initialize components
        self.adaptive_buffer = AdaptiveBuffer(
            min_size=config.min_buffer_size,
            max_size=config.max_buffer_size,
            increase_factor=config.adaptive_increase_factor,
            decrease_factor=config.adaptive_decrease_factor,
        )

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout,
        )

        # Frame buffer
        self._buffer: asyncio.Queue = asyncio.Queue(maxsize=config.min_buffer_size)
        self._state = BackpressureState.NORMAL

        # Metrics
        self._metrics = BackpressureMetrics()

        # Backpressure event for blocking producers
        self._backpressure_event = asyncio.Event()
        self._backpressure_event.set()  # Initially not under backpressure

    @property
    def state(self) -> BackpressureState:
        """Get current backpressure state."""
        return self._state

    def _update_state(self) -> None:
        """Update backpressure state based on buffer level."""
        buffer_level = self._buffer.qsize() / self.adaptive_buffer.current_size

        if self._state == BackpressureState.NORMAL:
            if buffer_level >= self.config.high_watermark:
                self._state = BackpressureState.BACKPRESSURE
                self._backpressure_event.clear()
                self._metrics.backpressure_activations += 1
                self.adaptive_buffer.record_pressure_event()
        elif self._state == BackpressureState.BACKPRESSURE:
            if buffer_level <= self.config.low_watermark:
                self._state = BackpressureState.NORMAL
                self._backpressure_event.set()
            self.adaptive_buffer.record_pressure_event()

        # Update adaptive buffer size if needed
        if self.adaptive_buffer.should_adjust():
            old_size = self.adaptive_buffer.current_size
            self.adaptive_buffer.adjust_size()

            # Resize queue if buffer size changed
            if old_size != self.adaptive_buffer.current_size:
                self._resize_buffer()

    def _resize_buffer(self) -> None:
        """Resize the internal buffer."""
        # Create new queue with new size
        new_buffer: asyncio.Queue[FrameData] = asyncio.Queue(
            maxsize=self.adaptive_buffer.current_size
        )

        # Transfer existing items
        items = []
        while not self._buffer.empty():
            try:
                items.append(self._buffer.get_nowait())
            except asyncio.QueueEmpty:
                break

        for item in items:
            try:
                new_buffer.put_nowait(item)
            except asyncio.QueueFull:
                # Drop excess items if new buffer is smaller
                self._metrics.frames_dropped += 1

        self._buffer = new_buffer

    async def send(self, frame: FrameData, timeout: Optional[float] = None) -> bool:
        """
        Send frame to queue with backpressure handling.

        Returns True if sent, False if dropped/failed.
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            if self.enable_dropping:
                self._metrics.frames_dropped += 1
                return False
            else:
                # Wait for circuit to close
                await asyncio.sleep(1.0)
                return await self.send(frame, timeout)

        try:
            # Wait if under backpressure
            wait_start = time.time()
            if timeout:
                await asyncio.wait_for(self._backpressure_event.wait(), timeout=timeout)
            else:
                await self._backpressure_event.wait()

            wait_time = time.time() - wait_start
            self._metrics.total_wait_time_ms += wait_time * 1000

            # Try to put frame in buffer
            if timeout:
                remaining_timeout = timeout - wait_time
                if remaining_timeout > 0:
                    await asyncio.wait_for(
                        self._buffer.put(frame), timeout=remaining_timeout
                    )
                else:
                    raise asyncio.TimeoutError()
            else:
                await self._buffer.put(frame)

            self._metrics.frames_sent += 1
            self._metrics.current_buffer_size = self._buffer.qsize()
            self._metrics.max_buffer_size_reached = max(
                self._metrics.max_buffer_size_reached, self._buffer.qsize()
            )

            # Update state after send
            self._update_state()

            # Record success
            self.circuit_breaker.record_success()
            return True

        except asyncio.TimeoutError:
            if self.enable_dropping:
                self._metrics.frames_dropped += 1
                return False
            raise
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    async def receive(self, timeout: Optional[float] = None) -> Optional[FrameData]:
        """
        Receive frame from queue.

        Returns None if timeout or no frames available.
        """
        try:
            if timeout:
                frame = await asyncio.wait_for(self._buffer.get(), timeout=timeout)
            else:
                frame = await self._buffer.get()

            self._metrics.frames_received += 1
            self._metrics.current_buffer_size = self._buffer.qsize()

            # Update state after receive
            self._update_state()

            # Record idle event if buffer is low
            if self._buffer.qsize() < self.adaptive_buffer.current_size * 0.2:
                self.adaptive_buffer.record_idle_event()

            return frame  # type: ignore[no-any-return]

        except asyncio.TimeoutError:
            return None
        except Exception:
            self.circuit_breaker.record_failure()
            raise

    def get_metrics(self) -> BackpressureMetrics:
        """Get current metrics."""
        self._metrics.current_buffer_size = self._buffer.qsize()
        return self._metrics
