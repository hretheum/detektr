"""Database models for the service."""

from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ExampleEntity(Base):
    """Example entity model demonstrating all patterns."""

    __tablename__ = "example_entities"
    __table_args__ = {"schema": "public"}  # Change schema as needed

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Business fields
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    correlation_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)

    # JSON data for flexibility
    data = Column(JSON, nullable=False, default=dict)
    metadata_json = Column("metadata_json", JSON, nullable=False, default=dict)

    # Audit fields
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self):
        """Return string representation."""
        return f"<ExampleEntity(id={self.id}, name={self.name})>"
