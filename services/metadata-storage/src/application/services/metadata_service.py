"""Metadata service for business logic orchestration."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.domain.models.frame_metadata import FrameMetadata, FrameMetadataCreate
from src.infrastructure.repositories.metadata_repository import IMetadataRepository

logger = logging.getLogger(__name__)


class MetadataService:
    """Service for managing frame metadata."""

    def __init__(self, repository: IMetadataRepository):
        """Initialize metadata service."""
        self.repository = repository

    async def store_metadata(self, metadata_dict: Dict) -> FrameMetadata:
        """Store frame metadata."""
        try:
            # Convert dict to domain model
            metadata_create = FrameMetadataCreate(
                frame_id=metadata_dict["frame_id"],
                timestamp=datetime.fromisoformat(metadata_dict["timestamp"]),
                camera_id=metadata_dict["camera_id"],
                sequence_number=metadata_dict.get("sequence_number", 0),
                metadata=metadata_dict.get("metadata", {}),
            )

            # Store in repository
            result = await self.repository.create(metadata_create)
            logger.info(f"Stored metadata for frame {result.frame_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to store metadata: {e}")
            raise

    async def store_metadata_batch(self, metadata_list: List[Dict]) -> int:
        """Store multiple metadata records."""
        try:
            # Convert to domain models
            metadata_creates = []
            for metadata_dict in metadata_list:
                metadata_creates.append(
                    FrameMetadataCreate(
                        frame_id=metadata_dict["frame_id"],
                        timestamp=datetime.fromisoformat(metadata_dict["timestamp"]),
                        camera_id=metadata_dict["camera_id"],
                        sequence_number=metadata_dict.get("sequence_number", 0),
                        metadata=metadata_dict.get("metadata", {}),
                    )
                )

            # Batch store
            count = await self.repository.create_batch(metadata_creates)
            logger.info(f"Stored {count} metadata records")
            return count

        except Exception as e:
            logger.error(f"Failed to store metadata batch: {e}")
            raise

    async def get_metadata(self, frame_id: str) -> Optional[FrameMetadata]:
        """Get metadata by frame ID."""
        try:
            result = await self.repository.get_by_frame_id(frame_id)
            if result:
                logger.debug(f"Retrieved metadata for frame {frame_id}")
            else:
                logger.warning(f"Metadata not found for frame {frame_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            raise

    async def get_camera_history(
        self,
        camera_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[FrameMetadata]:
        """Get metadata history for camera."""
        try:
            if not end_time:
                end_time = datetime.now()

            results = await self.repository.get_by_time_range(
                start_time=start_time,
                end_time=end_time,
                camera_id=camera_id,
                limit=limit,
            )
            logger.info(f"Retrieved {len(results)} records for camera {camera_id}")
            return results
        except Exception as e:
            logger.error(f"Failed to get camera history: {e}")
            raise
