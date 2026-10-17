import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class CodeProject(Base):
    __tablename__ = 'code_projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    pdd_version_id = Column(UUID(as_uuid=True), ForeignKey('pdd_versions.id'), nullable=True)
    status = Column(String(50), default='planning')  # planning, coding, testing, fixing, complete, error
    iteration = Column(Integer, default=0)
    max_iterations = Column(Integer, default=10)
    test_summary = Column(JSONB)  # {passed, failed, errors, output}
    agent_log = Column(JSONB, default=list)
    sandbox_path = Column(String(1024))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='code_projects')
    files = relationship(
        'CodeFile', back_populates='project', cascade='all, delete-orphan', order_by='CodeFile.file_path'
    )

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'pdd_version_id': str(self.pdd_version_id) if self.pdd_version_id else None,
            'status': self.status,
            'iteration': self.iteration,
            'max_iterations': self.max_iterations,
            'test_summary': self.test_summary,
            'agent_log': self.agent_log or [],
            'file_count': len(self.files) if self.files else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_with_files(self):
        d = self.to_dict()
        d['files'] = [f.to_dict() for f in (self.files or [])]
        return d


class CodeFile(Base):
    __tablename__ = 'code_files'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('code_projects.id'), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)  # relative path e.g. "engine/steps/phase_1.py"
    content = Column(Text, nullable=False)
    file_type = Column(String(20), default='source')  # source, test, config, init
    version = Column(Integer, default=1)
    pdd_section_ref = Column(String(255))  # optional mapping to PDD section
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    project = relationship('CodeProject', back_populates='files')

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'file_path': self.file_path,
            'content': self.content,
            'file_type': self.file_type,
            'version': self.version,
            'line_count': self.content.count('\n') + 1 if self.content else 0,
            'pdd_section_ref': self.pdd_section_ref,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_summary(self):
        return {
            'id': str(self.id),
            'file_path': self.file_path,
            'file_type': self.file_type,
            'version': self.version,
            'line_count': self.content.count('\n') + 1 if self.content else 0,
        }


class CodeUnit(Base):
    """Function-level code unit linked to PDD sections for fine-grained mapping."""

    __tablename__ = 'code_units'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey('code_projects.id', ondelete='CASCADE'), nullable=False, index=True
    )
    file_id = Column(UUID(as_uuid=True), ForeignKey('code_files.id', ondelete='CASCADE'), nullable=False)
    function_name = Column(String(255), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    pdd_step_id = Column(String(50))  # e.g., "1.1", "2.3"
    pdd_section = Column(String(512))  # section heading
    pdd_rule_ids = Column(JSONB, default=list)  # e.g., ["BR-101", "BR-102"]
    is_stale = Column(String(10), default='fresh')  # fresh, stale, unknown
    stale_reason = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    file = relationship('CodeFile')

    def to_dict(self):
        return {
            'id': str(self.id),
            'project_id': str(self.project_id),
            'file_id': str(self.file_id),
            'function_name': self.function_name,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'pdd_step_id': self.pdd_step_id,
            'pdd_section': self.pdd_section,
            'pdd_rule_ids': self.pdd_rule_ids or [],
            'is_stale': self.is_stale,
            'stale_reason': self.stale_reason,
        }
