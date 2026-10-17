"""Evidence graph models — tracks derivation chains across documents, PDD, code, and tests."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class EvidenceSpan(Base):
    """A specific span of text in a source document that serves as evidence."""

    __tablename__ = 'evidence_spans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='SET NULL'), nullable=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey('document_chunks.id', ondelete='SET NULL'), nullable=True)
    source_type = Column(String(50), nullable=False)  # document, chat, knowledge, manual
    source_id = Column(UUID(as_uuid=True))
    span_text = Column(Text, nullable=False)
    char_offset = Column(Integer)
    char_length = Column(Integer)
    heading_path = Column(String(1024))
    page_number = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    links = relationship('EvidenceLink', back_populates='evidence_span', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'document_id': str(self.document_id) if self.document_id else None,
            'chunk_id': str(self.chunk_id) if self.chunk_id else None,
            'source_type': self.source_type,
            'source_id': str(self.source_id) if self.source_id else None,
            'span_text': self.span_text,
            'char_offset': self.char_offset,
            'char_length': self.char_length,
            'heading_path': self.heading_path,
            'page_number': self.page_number,
        }


class PddStatement(Base):
    """A single statement or claim in the PDD, linked to evidence."""

    __tablename__ = 'pdd_statements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    pdd_version_id = Column(UUID(as_uuid=True), ForeignKey('pdd_versions.id'), nullable=False, index=True)
    section_path = Column(String(512), nullable=False)
    statement_text = Column(Text, nullable=False)
    statement_hash = Column(String(64), nullable=False, index=True)
    statement_index = Column(Integer, nullable=False)
    confidence = Column(String(20), default='derived')  # derived, confirmed, manual
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence_links = relationship('EvidenceLink', back_populates='pdd_statement', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': str(self.id),
            'pdd_version_id': str(self.pdd_version_id),
            'section_path': self.section_path,
            'statement_text': self.statement_text,
            'statement_index': self.statement_index,
            'confidence': self.confidence,
            'evidence_count': len(self.evidence_links) if self.evidence_links else 0,
        }


class EvidenceLink(Base):
    """Links a PDD statement to an evidence span (derivation edge)."""

    __tablename__ = 'evidence_links'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pdd_statement_id = Column(
        UUID(as_uuid=True), ForeignKey('pdd_statements.id', ondelete='CASCADE'), nullable=False, index=True
    )
    evidence_span_id = Column(
        UUID(as_uuid=True), ForeignKey('evidence_spans.id', ondelete='CASCADE'), nullable=False, index=True
    )
    link_type = Column(String(50), default='supports')  # supports, contradicts, elaborates
    confidence = Column(String(20), default='auto')  # auto, confirmed, manual
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    pdd_statement = relationship('PddStatement', back_populates='evidence_links')
    evidence_span = relationship('EvidenceSpan', back_populates='links')

    def to_dict(self):
        return {
            'id': str(self.id),
            'pdd_statement_id': str(self.pdd_statement_id),
            'evidence_span_id': str(self.evidence_span_id),
            'link_type': self.link_type,
            'confidence': self.confidence,
        }


class ChangeEvent(Base):
    """Records changes to process artifacts for impact tracking."""

    __tablename__ = 'change_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # doc_added, doc_removed, pdd_updated, chat_answer, code_generated
    target_type = Column(String(50), nullable=False)  # document, pdd_version, chat_session, code_project
    target_id = Column(UUID(as_uuid=True))
    detail = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'event_type': self.event_type,
            'target_type': self.target_type,
            'target_id': str(self.target_id) if self.target_id else None,
            'detail': self.detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
