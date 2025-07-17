"""Frame processor with full observability."""

import asyncio
import logging
import random
import time
from typing import Any, Dict, Optional

from src.shared.telemetry import (
    get_metrics,
    increment_detections,
    record_processing_time,
    traced,
    traced_frame,
)

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Frame processor with distributed tracing and metrics."""

    def __init__(self, storage):
        """Initialize frame processor.

        Args:
            storage: Storage instance for persisting results
        """
        self.storage = storage
        self.metrics = get_metrics("frame_processor")
        self.is_running = True

        logger.info("Frame processor initialized")

    @traced_frame("frame_id")
    async def process_frame(
        self, frame_id: str, camera_id: str, frame_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a frame with full observability.

        Args:
            frame_id: Unique frame identifier
            camera_id: Camera identifier
            frame_data: Frame data and metadata

        Returns:
            Processing results
        """
        start_time = time.time()

        try:
            # Simulate frame preprocessing
            preprocessed_data = await self._preprocess_frame(frame_id, frame_data)

            # Run AI detection tasks in parallel
            face_task = asyncio.create_task(
                self._detect_faces(frame_id, preprocessed_data)
            )
            object_task = asyncio.create_task(
                self._detect_objects(frame_id, preprocessed_data)
            )

            # Wait for face detection to complete first (needed for gesture analysis)
            face_results = await face_task

            # Run gesture analysis if faces were detected
            gesture_task = None
            if face_results["faces_detected"] > 0:
                gesture_task = asyncio.create_task(
                    self._analyze_gestures(frame_id, face_results)
                )

            # Wait for object detection
            object_results = await object_task

            # Wait for gesture analysis if it was started
            gesture_results = None
            if gesture_task:
                gesture_results = await gesture_task

            # Combine results
            combined_results = await self._combine_results(
                frame_id, face_results, object_results, gesture_results
            )

            # Store results
            await self._store_results(frame_id, camera_id, combined_results)

            # Record processing metrics
            total_time = time.time() - start_time
            record_processing_time(
                "frame_processor", "total", total_time, camera_id=camera_id
            )

            # Record frame size metrics
            if "width" in frame_data and "height" in frame_data:
                self.metrics.record_frame_size(
                    frame_data["width"], frame_data["height"], {"camera_id": camera_id}
                )

            logger.info(f"Frame {frame_id} processed successfully in {total_time:.3f}s")

            return combined_results

        except Exception as e:
            self.metrics.increment_errors(
                "processing_error",
                {
                    "error_type": type(e).__name__,
                    "camera_id": camera_id,
                },
            )
            logger.error(f"Error processing frame {frame_id}: {e}", exc_info=True)
            raise

    @traced
    async def _preprocess_frame(
        self, frame_id: str, frame_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Preprocess frame data."""
        start_time = time.time()

        # Simulate preprocessing (normalization, resizing, etc.)
        await asyncio.sleep(random.uniform(0.01, 0.03))

        preprocessed = {
            "frame_id": frame_id,
            "normalized": True,
            "resized": True,
            "format": frame_data.get("format", "rgb24"),
            "width": frame_data.get("width", 1920),
            "height": frame_data.get("height", 1080),
        }

        # Record preprocessing time
        duration = time.time() - start_time
        record_processing_time("frame_processor", "preprocessing", duration)

        return preprocessed

    @traced
    async def _detect_faces(
        self, frame_id: str, frame_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect faces in frame."""
        start_time = time.time()

        # Simulate face detection
        await asyncio.sleep(random.uniform(0.05, 0.15))

        faces_detected = random.randint(0, 4)
        confidence_scores = [random.uniform(0.7, 0.99) for _ in range(faces_detected)]

        results = {
            "frame_id": frame_id,
            "faces_detected": faces_detected,
            "face_locations": [
                (random.randint(0, 500), random.randint(0, 500))
                for _ in range(faces_detected)
            ],
            "confidence_scores": confidence_scores,
            "average_confidence": sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0,
        }

        # Record metrics
        duration = time.time() - start_time
        record_processing_time("frame_processor", "face_detection", duration)

        if faces_detected > 0:
            increment_detections("frame_processor", "face", faces_detected)

        return results

    @traced
    async def _detect_objects(
        self, frame_id: str, frame_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect objects in frame."""
        start_time = time.time()

        # Simulate object detection
        await asyncio.sleep(random.uniform(0.08, 0.18))

        object_classes = ["person", "car", "bicycle", "dog", "cat", "chair", "table"]
        objects_detected = random.randint(0, 6)
        detected_objects = random.choices(object_classes, k=objects_detected)
        confidence_scores = [random.uniform(0.6, 0.95) for _ in range(objects_detected)]

        results = {
            "frame_id": frame_id,
            "objects_detected": objects_detected,
            "object_classes": detected_objects,
            "confidence_scores": confidence_scores,
            "average_confidence": sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0,
        }

        # Record metrics
        duration = time.time() - start_time
        record_processing_time("frame_processor", "object_detection", duration)

        # Record detections by type
        for obj_class in detected_objects:
            increment_detections("frame_processor", "object", 1, object_class=obj_class)

        return results

    @traced
    async def _analyze_gestures(
        self, frame_id: str, face_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze gestures in frame."""
        start_time = time.time()

        # Simulate gesture analysis
        await asyncio.sleep(random.uniform(0.1, 0.2))

        gesture_types = ["wave", "thumbs_up", "peace_sign", "pointing", "clapping"]
        gestures_detected = random.randint(0, min(2, face_data["faces_detected"]))
        detected_gestures = random.choices(gesture_types, k=gestures_detected)
        confidence_scores = [
            random.uniform(0.75, 0.95) for _ in range(gestures_detected)
        ]

        results = {
            "frame_id": frame_id,
            "gestures_detected": gestures_detected,
            "gesture_types": detected_gestures,
            "confidence_scores": confidence_scores,
            "average_confidence": sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0,
        }

        # Record metrics
        duration = time.time() - start_time
        record_processing_time("frame_processor", "gesture_analysis", duration)

        if gestures_detected > 0:
            increment_detections("frame_processor", "gesture", gestures_detected)

        return results

    @traced
    async def _combine_results(
        self,
        frame_id: str,
        face_results: Dict[str, Any],
        object_results: Dict[str, Any],
        gesture_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Combine all detection results."""
        start_time = time.time()

        # Simulate result combination logic
        await asyncio.sleep(random.uniform(0.005, 0.015))

        combined = {
            "frame_id": frame_id,
            "timestamp": time.time(),
            "faces": face_results,
            "objects": object_results,
            "gestures": gesture_results,
            "summary": {
                "total_detections": (
                    face_results["faces_detected"]
                    + object_results["objects_detected"]
                    + (gesture_results["gestures_detected"] if gesture_results else 0)
                ),
                "has_faces": face_results["faces_detected"] > 0,
                "has_objects": object_results["objects_detected"] > 0,
                "has_gestures": gesture_results["gestures_detected"] > 0
                if gesture_results
                else False,
            },
        }

        # Record metrics
        duration = time.time() - start_time
        record_processing_time("frame_processor", "result_combination", duration)

        return combined

    @traced
    async def _store_results(
        self, frame_id: str, camera_id: str, results: Dict[str, Any]
    ) -> None:
        """Store processing results."""
        start_time = time.time()

        try:
            await self.storage.store_frame_results(frame_id, camera_id, results)

            # Record metrics
            duration = time.time() - start_time
            record_processing_time("frame_processor", "storage", duration)

        except Exception as e:
            self.metrics.increment_errors(
                "storage_error",
                {
                    "error_type": type(e).__name__,
                    "camera_id": camera_id,
                },
            )
            raise

    async def shutdown(self):
        """Gracefully shutdown the processor."""
        logger.info("Shutting down frame processor...")
        self.is_running = False
        logger.info("Frame processor shutdown complete")
