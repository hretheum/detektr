"""Example FrameProcessor service implemented with TDD."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.shared.base_service import BaseService
from src.shared.kernel.domain import Frame, ProcessingState
from src.shared.telemetry.decorators import traced
from src.shared.telemetry.frame_tracking import set_frame_context


@dataclass
class ProcessingResult:
    """Result of frame processing."""

    frame_id: str
    success: bool
    detections: Dict[str, List[Any]]
    processing_time_ms: float
    errors: Dict[str, str] = None

    def __post_init__(self):
        """Initialize errors dict if None."""
        if self.errors is None:
            self.errors = {}


class ProcessingError(Exception):
    """Frame processing error."""

    def __init__(self, message: str, frame_id: str):
        """Initialize error with frame context."""
        super().__init__(message)
        self.frame_id = frame_id


class FrameProcessor(BaseService):
    """Example frame processor service with TDD implementation."""

    def __init__(
        self,
        face_detector: Any = None,
        object_detector: Any = None,
        frame_repository: Any = None,
        event_publisher: Any = None,
        processing_timeout: float = 30.0,
    ):
        """Initialize frame processor.

        Args:
            face_detector: Face detection service
            object_detector: Object detection service
            frame_repository: Frame persistence repository
            event_publisher: Event publishing service
            processing_timeout: Max processing time in seconds
        """
        super().__init__(
            name="frame-processor",
            version="1.0.0",
            port=8081,
            description="Example frame processor with TDD",
        )

        self.face_detector = face_detector
        self.object_detector = object_detector
        self.frame_repository = frame_repository
        self.event_publisher = event_publisher
        self.processing_timeout = processing_timeout

        # Processing stats
        self.processed_count = 0
        self.error_count = 0

    @traced(span_name="process_frame")
    async def process_frame(self, frame: Frame) -> ProcessingResult:
        """Process a single frame.

        Args:
            frame: Frame to process

        Returns:
            ProcessingResult with detections

        Raises:
            ProcessingError: If processing fails completely
        """
        start_time = datetime.now()

        # Set frame context for tracing
        set_frame_context(frame)

        # Validate frame
        self.validate_frame(frame)

        # Update frame state
        frame.transition_to(ProcessingState.PROCESSING)

        # Process with timeout
        try:
            result = await asyncio.wait_for(
                self._process_frame_internal(frame), timeout=self.processing_timeout
            )
            return result
        except asyncio.TimeoutError:
            raise ProcessingError(
                f"Frame processing timeout after {self.processing_timeout}s",
                str(frame.id),
            )

    async def _process_frame_internal(self, frame: Frame) -> ProcessingResult:
        """Internal frame processing logic."""
        # Run detections in parallel
        detections, errors = await self._run_detections(frame)
        
        # Determine success and update frame state
        success = self._update_frame_state(frame, errors)
        
        # Enrich frame with metadata
        frame = await self.enrich_frame(frame, detections)
        
        # Persist frame and handle errors
        await self._persist_frame(frame, errors)
        
        # Publish processing event
        await self._publish_event_safe(frame, detections, errors)
        
        # Update metrics and calculate result
        return self._finalize_processing(frame, success, detections, errors)

    async def _run_detections(self, frame: Frame) -> Tuple[Dict[str, List[Any]], Dict[str, str]]:
        """Run face and object detection in parallel."""
        detections = {"faces": [], "objects": []}
        errors = {}
        
        # Run detections in parallel
        face_task = self._detect_faces(frame)
        object_task = self._detect_objects(frame)
        
        # Gather results
        face_result, object_result = await asyncio.gather(
            face_task, object_task, return_exceptions=True
        )
        
        # Handle face detection results
        if isinstance(face_result, Exception):
            errors["face_detection"] = str(face_result)
            self.metrics.increment_errors("face_detection")
        else:
            detections["faces"] = face_result
        
        # Handle object detection results
        if isinstance(object_result, Exception):
            errors["object_detection"] = str(object_result)
            self.metrics.increment_errors("object_detection")
        else:
            detections["objects"] = object_result
        
        return detections, errors
    
    def _update_frame_state(self, frame: Frame, errors: Dict[str, str]) -> bool:
        """Update frame state based on processing results."""
        success = len(errors) == 0 or len(errors) < 2
        
        if success:
            frame.mark_as_completed()
        else:
            frame.mark_as_failed(str(errors))
        
        return success
    
    async def _persist_frame(self, frame: Frame, errors: Dict[str, str]) -> None:
        """Save frame to repository with error handling."""
        try:
            await self.frame_repository.save(frame)
        except Exception as e:
            if len(errors) >= 2:  # Already have multiple errors
                raise ProcessingError(
                    f"Failed to process frame {frame.id}: {e}", str(frame.id)
                )
            errors["save"] = str(e)
    
    async def _publish_event_safe(self, frame: Frame, detections: Dict[str, List[Any]], errors: Dict[str, str]) -> None:
        """Publish processing event with error handling."""
        try:
            await self._publish_processing_event(frame, detections, errors)
        except Exception as e:
            self.metrics.increment_errors("event_publish")
    
    def _finalize_processing(self, frame: Frame, success: bool, detections: Dict[str, List[Any]], errors: Dict[str, str]) -> ProcessingResult:
        """Calculate metrics and create processing result."""
        # Calculate processing time
        processing_time = (datetime.now() - frame.created_at).total_seconds() * 1000
        
        # Update metrics
        self.processed_count += 1
        if not success:
            self.error_count += 1
        
        self.metrics.increment_frames_processed()
        self.metrics.record_processing_time("total", processing_time / 1000)
        
        return ProcessingResult(
            frame_id=str(frame.id),
            success=success,
            detections=detections,
            processing_time_ms=processing_time,
            errors=errors,
        )

    async def _detect_faces(self, frame: Frame) -> List[Dict[str, Any]]:
        """Detect faces in frame."""
        with self.tracer.start_as_current_span("detect_faces") as span:
            span.set_attribute("frame.id", str(frame.id))

            if self.face_detector is None:
                return []

            result = await self.face_detector.detect(frame)
            span.set_attribute("face.count", len(result))

            self.metrics.increment_detections("face", count=len(result))
            return result

    async def _detect_objects(self, frame: Frame) -> List[Dict[str, Any]]:
        """Detect objects in frame."""
        with self.tracer.start_as_current_span("detect_objects") as span:
            span.set_attribute("frame.id", str(frame.id))

            if self.object_detector is None:
                return []

            result = await self.object_detector.detect(frame)
            span.set_attribute("object.count", len(result))

            self.metrics.increment_detections("object", count=len(result))
            return result

    def validate_frame(self, frame: Frame) -> None:
        """Validate frame before processing.

        Args:
            frame: Frame to validate

        Raises:
            ValueError: If frame is invalid
        """
        if frame.state == ProcessingState.COMPLETED:
            raise ValueError(f"Frame {frame.id} already processed")

        if frame.state == ProcessingState.FAILED:
            raise ValueError(f"Frame {frame.id} already failed")

    async def enrich_frame(
        self, frame: Frame, detections: Dict[str, List[Any]]
    ) -> Frame:
        """Enrich frame with detection metadata.

        Args:
            frame: Frame to enrich
            detections: Detection results

        Returns:
            Enriched frame
        """
        # Add detection counts
        frame.metadata["face_count"] = len(detections.get("faces", []))
        frame.metadata["object_count"] = len(detections.get("objects", []))

        # Extract object types
        object_types = set()
        for obj in detections.get("objects", []):
            if "class" in obj:
                object_types.add(obj["class"])

        frame.metadata["object_types"] = list(object_types)

        # Add processing timestamp
        frame.metadata["processed_at"] = datetime.now().isoformat()

        return frame

    async def _publish_processing_event(
        self, frame: Frame, detections: Dict[str, List[Any]], errors: Dict[str, str]
    ) -> None:
        """Publish frame processing event."""
        if self.event_publisher is None:
            return

        event = {
            "type": "frame.processed",
            "frame_id": str(frame.id),
            "camera_id": frame.camera_id,
            "timestamp": datetime.now().isoformat(),
            "detections": detections,
            "errors": errors,
            "success": len(errors) == 0,
        }

        await self.event_publisher.publish(event)

    def setup_routes(self):
        """Setup frame processor specific routes."""
        super().setup_routes()

        @self.app.post("/process")
        async def process_frame_endpoint(frame_data: Dict[str, Any]):
            """Process frame via API."""
            # Create frame from data
            frame = Frame.create(
                camera_id=frame_data["camera_id"],
                timestamp=datetime.fromisoformat(frame_data["timestamp"]),
            )

            # Process
            result = await self.process_frame(frame)

            return {
                "frame_id": result.frame_id,
                "success": result.success,
                "detections": result.detections,
                "processing_time_ms": result.processing_time_ms,
                "errors": result.errors,
            }

        @self.app.get("/stats")
        async def get_processing_stats():
            """Get processing statistics."""
            return {
                "processed": self.processed_count,
                "errors": self.error_count,
                "success_rate": (self.processed_count - self.error_count)
                / max(1, self.processed_count),
            }
