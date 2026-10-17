import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class ChatSession(Base):
    __tablename__ = 'chat_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    expert_name = Column(String(255))
    expert_role = Column(String(50))  # SME, DA, Eng
    status = Column(String(50), default='active')  # active, paused, completed
    context_snapshot = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='chat_sessions')
    messages = relationship(
        'ChatMessage', back_populates='session', cascade='all, delete-orphan', order_by='ChatMessage.created_at'
    )

    def to_dict(self, include_messages=False):
        d = {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'expert_name': self.expert_name,
            'expert_role': self.expert_role,
            'status': self.status,
            'message_count': len(self.messages) if self.messages else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            d['messages'] = [m.to_dict() for m in (self.messages or [])]
        return d


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id'), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONB)
    tool_results = Column(JSONB)
    token_count = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship('ChatSession', back_populates='messages')

    def to_dict(self):
        return {
            'id': str(self.id),
            'session_id': str(self.session_id),
            'role': self.role,
            'content': self.content,
            'tool_calls': self.tool_calls,
            'tool_results': self.tool_results,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
