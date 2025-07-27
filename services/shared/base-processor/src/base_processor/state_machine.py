"""Frame state machine implementation."""
import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Set


class FrameState(Enum):
    """Possible states for a frame during processing."""

    RECEIVED = auto()  # Frame received but not validated
    VALIDATED = auto()  # Frame validated and ready for processing
    QUEUED = auto()  # Frame queued for processing
    PROCESSING = auto()  # Frame currently being processed
    COMPLETED = auto()  # Frame processing completed successfully
    FAILED = auto()  # Frame processing failed
    RETRY = auto()  # Frame scheduled for retry
    ARCHIVED = auto()  # Frame archived after processing


class StateTransition(Enum):
    """Valid state transitions."""

    VALIDATE = auto()  # RECEIVED -> VALIDATED
    QUEUE = auto()  # VALIDATED -> QUEUED
    START = auto()  # QUEUED -> PROCESSING
    COMPLETE = auto()  # PROCESSING -> COMPLETED
    FAIL = auto()  # PROCESSING -> FAILED
    RETRY = auto()  # FAILED -> RETRY
    REQUEUE = auto()  # RETRY -> QUEUED
    ARCHIVE = auto()  # COMPLETED/FAILED -> ARCHIVED


# Valid state transitions mapping
VALID_TRANSITIONS: Dict[FrameState, Dict[StateTransition, FrameState]] = {
    FrameState.RECEIVED: {
        StateTransition.VALIDATE: FrameState.VALIDATED,
    },
    FrameState.VALIDATED: {
        StateTransition.QUEUE: FrameState.QUEUED,
    },
    FrameState.QUEUED: {
        StateTransition.START: FrameState.PROCESSING,
    },
    FrameState.PROCESSING: {
        StateTransition.COMPLETE: FrameState.COMPLETED,
        StateTransition.FAIL: FrameState.FAILED,
    },
    FrameState.FAILED: {
        StateTransition.RETRY: FrameState.RETRY,
        StateTransition.ARCHIVE: FrameState.ARCHIVED,
    },
    FrameState.RETRY: {
        StateTransition.REQUEUE: FrameState.QUEUED,
    },
    FrameState.COMPLETED: {
        StateTransition.ARCHIVE: FrameState.ARCHIVED,
    },
}


@dataclass
class FrameMetadata:
    """Metadata associated with a frame."""

    frame_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    state: FrameState = FrameState.RECEIVED
    retry_count: int = 0
    error_history: list = field(default_factory=list)
    processing_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    pass


class FrameStateMachine:
    """State machine for managing frame lifecycle."""

    def __init__(self):
        """Initialize frame state machine."""
        self._frames: Dict[str, FrameMetadata] = {}
        self._state_callbacks: Dict[FrameState, list] = {
            state: [] for state in FrameState
        }
        self._transition_callbacks: Dict[StateTransition, list] = {
            trans: [] for trans in StateTransition
        }
        self._lock = asyncio.Lock()

    async def register_frame(self, frame_id: str, **metadata) -> FrameMetadata:
        """Register a new frame in the state machine.

        Args:
            frame_id: Unique frame identifier
            **metadata: Additional metadata

        Returns:
            FrameMetadata object
        """
        async with self._lock:
            if frame_id in self._frames:
                raise ValueError(f"Frame {frame_id} already registered")

            frame_meta = FrameMetadata(frame_id=frame_id, custom_data=metadata)
            self._frames[frame_id] = frame_meta

            # Trigger state callbacks
            await self._trigger_state_callbacks(frame_id, FrameState.RECEIVED)

            return frame_meta

    async def transition(
        self, frame_id: str, transition: StateTransition, **data
    ) -> FrameState:
        """Perform a state transition for a frame.

        Args:
            frame_id: Frame identifier
            transition: Transition to perform
            **data: Additional data to store

        Returns:
            New frame state

        Raises:
            InvalidStateTransition: If transition is not valid
        """
        async with self._lock:
            if frame_id not in self._frames:
                raise ValueError(f"Frame {frame_id} not found")

            frame_meta = self._frames[frame_id]
            current_state = frame_meta.state

            # Check if transition is valid
            if current_state not in VALID_TRANSITIONS:
                raise InvalidStateTransition(
                    f"No transitions defined from state {current_state}"
                )

            if transition not in VALID_TRANSITIONS[current_state]:
                raise InvalidStateTransition(
                    f"Transition {transition} not valid from state {current_state}"
                )

            # Get new state
            new_state = VALID_TRANSITIONS[current_state][transition]

            # Update metadata
            frame_meta.state = new_state
            frame_meta.custom_data.update(data)

            # Special handling for specific transitions
            if transition == StateTransition.FAIL and "error" in data:
                frame_meta.error_history.append(
                    {"timestamp": datetime.now(), "error": data["error"]}
                )
            elif transition == StateTransition.RETRY:
                frame_meta.retry_count += 1
            elif transition == StateTransition.COMPLETE and "result" in data:
                frame_meta.result = data["result"]

            # Trigger callbacks
            await self._trigger_transition_callbacks(frame_id, transition)
            await self._trigger_state_callbacks(frame_id, new_state)

            return new_state

    def get_frame_state(self, frame_id: str) -> Optional[FrameState]:
        """Get current state of a frame.

        Args:
            frame_id: Frame identifier

        Returns:
            Current frame state or None if not found
        """
        frame_meta = self._frames.get(frame_id)
        return frame_meta.state if frame_meta else None

    def get_frame_metadata(self, frame_id: str) -> Optional[FrameMetadata]:
        """Get metadata for a frame.

        Args:
            frame_id: Frame identifier

        Returns:
            Frame metadata or None if not found
        """
        return self._frames.get(frame_id)

    def get_frames_by_state(self, state: FrameState) -> list[str]:
        """Get all frames in a specific state.

        Args:
            state: Frame state to filter by

        Returns:
            List of frame IDs in the given state
        """
        return [
            frame_id for frame_id, meta in self._frames.items() if meta.state == state
        ]

    def on_state_enter(self, state: FrameState, callback: Callable):
        """Register callback for when a frame enters a state.

        Args:
            state: State to watch
            callback: Async callback function
        """
        self._state_callbacks[state].append(callback)

    def on_transition(self, transition: StateTransition, callback: Callable):
        """Register callback for a specific transition.

        Args:
            transition: Transition to watch
            callback: Async callback function
        """
        self._transition_callbacks[transition].append(callback)

    async def _trigger_state_callbacks(self, frame_id: str, state: FrameState):
        """Trigger callbacks for state entry."""
        for callback in self._state_callbacks[state]:
            with suppress(Exception):
                if asyncio.iscoroutinefunction(callback):
                    await callback(frame_id, self._frames[frame_id])
                else:
                    callback(frame_id, self._frames[frame_id])

    async def _trigger_transition_callbacks(
        self, frame_id: str, transition: StateTransition
    ):
        """Trigger callbacks for transition."""
        for callback in self._transition_callbacks[transition]:
            with suppress(Exception):
                if asyncio.iscoroutinefunction(callback):
                    await callback(frame_id, self._frames[frame_id])
                else:
                    callback(frame_id, self._frames[frame_id])

    def cleanup(self, states_to_clean: Set[FrameState] = None):
        """Remove frames in specified states.

        Args:
            states_to_clean: Set of states to clean up, defaults to ARCHIVED
        """
        if states_to_clean is None:
            states_to_clean = {FrameState.ARCHIVED}

        frames_to_remove = []
        for frame_id, meta in self._frames.items():
            if meta.state in states_to_clean:
                frames_to_remove.append(frame_id)

        for frame_id in frames_to_remove:
            del self._frames[frame_id]

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about frame states.

        Returns:
            Dictionary with state counts and other metrics
        """
        stats = {
            "total_frames": len(self._frames),
            "state_counts": {},
            "retry_stats": {
                "total_retries": 0,
                "max_retry_count": 0,
                "frames_with_retries": 0,
            },
        }

        # Count frames by state
        for state in FrameState:
            stats["state_counts"][state.name] = len(self.get_frames_by_state(state))

        # Calculate retry statistics
        for meta in self._frames.values():
            if meta.retry_count > 0:
                stats["retry_stats"]["total_retries"] += meta.retry_count
                stats["retry_stats"]["frames_with_retries"] += 1
                stats["retry_stats"]["max_retry_count"] = max(
                    stats["retry_stats"]["max_retry_count"], meta.retry_count
                )

        return stats


class StateMachineMixin:
    """Mixin to add state machine functionality to processors."""

    def __init__(self, *args, **kwargs):
        """Initialize state machine mixin."""
        super().__init__(*args, **kwargs)
        self.state_machine = FrameStateMachine()
        self._setup_state_callbacks()

    def _setup_state_callbacks(self):
        """Set up default state callbacks."""
        # Log state transitions
        async def log_state_change(frame_id: str, metadata: FrameMetadata):
            self.log_with_context(
                "info",
                f"Frame {frame_id} entered state {metadata.state.name}",
                frame_id=frame_id,
                state=metadata.state.name,
                retry_count=metadata.retry_count,
            )

        # Register logging for all states
        for state in FrameState:
            self.state_machine.on_state_enter(state, log_state_change)

    async def track_frame_lifecycle(self, frame_id: str, metadata: Dict[str, Any]):
        """Track frame through its lifecycle."""
        # Register frame - remove frame_id from metadata to avoid duplicate argument
        clean_metadata = {k: v for k, v in metadata.items() if k != "frame_id"}
        await self.state_machine.register_frame(frame_id, **clean_metadata)

        # Move through validation
        await self.state_machine.transition(frame_id, StateTransition.VALIDATE)
        await self.state_machine.transition(frame_id, StateTransition.QUEUE)

        return frame_id
