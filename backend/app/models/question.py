import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class Question(Base):
    __tablename__ = 'questions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    display_id = Column(String(20))
    text = Column(Text, nullable=False)
    target_roles = Column(JSONB, default=list)
    priority = Column(Integer, default=2)
    status = Column(String(20), default='OPEN')  # OPEN, ANSWERED, DISMISSED
    related_pdd_section = Column(String(255))
    answer = Column(Text)
    answered_by_session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='questions')

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'display_id': self.display_id,
            'text': self.text,
            'target_roles': self.target_roles or [],
            'priority': self.priority,
            'status': self.status,
            'related_pdd_section': self.related_pdd_section,
            'answer': self.answer,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
