import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from ..extensions import Base


class Provenance(Base):
    __tablename__ = 'provenance'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    pdd_version_id = Column(UUID(as_uuid=True), ForeignKey('pdd_versions.id'), nullable=True)
    sentence_hash = Column(String(64), index=True)
    sentence_text = Column(Text, nullable=False)
    section_path = Column(String(255))
    source_type = Column(String(50), nullable=False)  # document, conversation, test_case
    source_id = Column(UUID(as_uuid=True))
    source_detail = Column(Text)
    actor = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
