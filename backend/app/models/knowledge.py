import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class KnowledgeItem(Base):
    __tablename__ = 'knowledge_items'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    section = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    confidence = Column(String(20), nullable=False, default='TENTATIVE')
    source_type = Column(String(50))  # document, conversation, research, test_case
    source_id = Column(String(255))
    source_detail = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='knowledge_items')

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'section': self.section,
            'content': self.content,
            'confidence': self.confidence,
            'source_type': self.source_type,
            'source_id': self.source_id,
            'source_detail': self.source_detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
