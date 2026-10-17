import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class Document(Base):
    __tablename__ = 'documents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger)
    storage_path = Column(String(1024), nullable=False)
    extracted_text = Column(Text)
    page_count = Column(Integer)
    status = Column(String(50), default='uploaded')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='documents')
    chunks = relationship(
        'DocumentChunk', back_populates='document', cascade='all, delete-orphan', order_by='DocumentChunk.chunk_index'
    )

    @property
    def chunk_count(self):
        return len(self.chunks) if self.chunks else 0

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'original_filename': self.original_filename,
            'mime_type': self.mime_type,
            'file_size_bytes': self.file_size_bytes,
            'page_count': self.page_count,
            'status': self.status,
            'has_extracted_text': bool(self.extracted_text),
            'chunk_count': self.chunk_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
