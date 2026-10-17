"""DocumentChunk model — stores structured chunks extracted from documents."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class DocumentChunk(Base):
    __tablename__ = 'document_chunks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    char_offset = Column(Integer, nullable=False, default=0)
    char_length = Column(Integer, nullable=False)
    page_number = Column(Integer)
    heading_path = Column(String(1024))
    chunk_type = Column(String(50), default='body')  # heading, body, table, list
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship('Document', back_populates='chunks')

    @staticmethod
    def hash_content(text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def to_dict(self):
        return {
            'id': str(self.id),
            'document_id': str(self.document_id),
            'chunk_index': self.chunk_index,
            'content': self.content,
            'content_hash': self.content_hash,
            'char_offset': self.char_offset,
            'char_length': self.char_length,
            'page_number': self.page_number,
            'heading_path': self.heading_path,
            'chunk_type': self.chunk_type,
        }

    def to_summary(self):
        return {
            'id': str(self.id),
            'chunk_index': self.chunk_index,
            'char_length': self.char_length,
            'page_number': self.page_number,
            'heading_path': self.heading_path,
            'chunk_type': self.chunk_type,
            'preview': self.content[:200],
        }
