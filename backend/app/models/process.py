import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class Process(Base):
    __tablename__ = 'processes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255))
    description = Column(Text)
    status = Column(String(50), default='draft')
    key_inputs = Column(JSONB, default=list)
    key_outputs = Column(JSONB, default=list)
    metadata_ = Column('metadata', JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    documents = relationship('Document', back_populates='process', cascade='all, delete-orphan')
    pdd_versions = relationship('PddVersion', back_populates='process', cascade='all, delete-orphan')
    chat_sessions = relationship('ChatSession', back_populates='process', cascade='all, delete-orphan')
    knowledge_items = relationship('KnowledgeItem', back_populates='process', cascade='all, delete-orphan')
    questions = relationship('Question', back_populates='process', cascade='all, delete-orphan')
    code_projects = relationship('CodeProject', back_populates='process', cascade='all, delete-orphan')
    test_cases = relationship('TestCase', back_populates='process', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'domain': self.domain,
            'description': self.description,
            'status': self.status,
            'key_inputs': self.key_inputs or [],
            'key_outputs': self.key_outputs or [],
            'metadata': self.metadata_ or {},
            'document_count': len(self.documents) if self.documents else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
