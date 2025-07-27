"""Processor client library for frame processing.

This library provides a base class for implementing frame processors in the
Detektor system. Processors consume frames from Redis Streams, process them,
and optionally publish results.

Example usage:

    class FaceDetectionProcessor(ProcessorClient):
        async def process_frame(self, frame_data: Dict[bytes, bytes]) -> Optional[Dict]:
            frame_id = frame_data[b"frame_id"].decode()
            image_data = frame_data[b"data"]

            # Process image
            faces = await self.detect_faces(image_data)

            return {
                "frame_id": frame_id,
                "faces_count": len(faces),
                "faces": faces
            }

    async def main():
        async with FaceDetectionProcessor(
            processor_id="face-detector-1",
            capabilities=["face_detection"],
            orchestrator_url="http://orchestrator:8002",
            capacity=20,
            result_stream="frames:faces"
        ) as processor:
            # Processor runs until interrupted
            await asyncio.Event().wait()
"""

from .client import ProcessorClient

__all__ = ["ProcessorClient"]
