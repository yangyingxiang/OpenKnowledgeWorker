import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class PddVersion(Base):
    __tablename__ = 'pdd_versions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    change_summary = Column(Text)
    change_source = Column(String(50))  # research, chat, manual_edit, code_agent
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey('pdd_versions.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    process = relationship('Process', back_populates='pdd_versions')
    parent = relationship('PddVersion', remote_side=[id])

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'version_number': self.version_number,
            'content': self.content,
            'change_summary': self.change_summary,
            'change_source': self.change_source,
            'parent_version_id': str(self.parent_version_id) if self.parent_version_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
