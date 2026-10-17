"""Job model — tracks long-running background tasks."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..extensions import Base


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # research, coding, test_run, evidence_build, ingestion
    status = Column(String(20), nullable=False, default='queued')  # queued, running, completed, failed, cancelled
    progress_pct = Column(Integer, default=0)
    progress_message = Column(String(512))
    result_summary = Column(JSONB)
    error_message = Column(Text)
    target_id = Column(UUID(as_uuid=True))  # Optional: e.g., code_project_id, test_run_id
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def start(self):
        self.status = 'running'
        self.started_at = datetime.now(timezone.utc)

    def complete(self, summary=None):
        self.status = 'completed'
        self.progress_pct = 100
        self.completed_at = datetime.now(timezone.utc)
        if summary:
            self.result_summary = summary

    def fail(self, error_message):
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)

    def cancel(self):
        self.status = 'cancelled'
        self.completed_at = datetime.now(timezone.utc)

    def update_progress(self, pct, message=None):
        self.progress_pct = min(pct, 99)
        if message:
            self.progress_message = message

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'job_type': self.job_type,
            'status': self.status,
            'progress_pct': self.progress_pct,
            'progress_message': self.progress_message,
            'result_summary': self.result_summary,
            'error_message': self.error_message,
            'target_id': str(self.target_id) if self.target_id else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'duration_ms': int((self.completed_at - self.started_at).total_seconds() * 1000)
            if self.completed_at and self.started_at
            else None,
        }
