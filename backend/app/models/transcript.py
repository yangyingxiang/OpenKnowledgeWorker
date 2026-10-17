import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..extensions import Base


class Transcript(Base):
    """Persists a single entry in an agent transcript for debugging and observability."""

    __tablename__ = 'transcripts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    session_key = Column(String(255), nullable=False, index=True)  # groups entries (e.g. project_id, chat session)
    sequence = Column(Integer, nullable=False)  # ordering within session
    entry_type = Column(String(30), nullable=False)  # model_request, model_response, tool_call, tool_result, error
    role = Column(String(20))  # user, assistant, system
    model = Column(String(100))  # model used
    content = Column(Text)  # text content or JSON-serialized payload
    tool_name = Column(String(100))  # for tool_call / tool_result
    tool_input = Column(JSONB)  # tool call input
    tool_output = Column(Text)  # tool result (may be large)
    token_input = Column(Integer)  # input tokens for model_response
    token_output = Column(Integer)  # output tokens for model_response
    duration_ms = Column(Float)  # wall-clock time for this entry
    metadata_ = Column('metadata', JSONB, default=dict)  # extra data (stop_reason, etc.)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'session_key': self.session_key,
            'sequence': self.sequence,
            'entry_type': self.entry_type,
            'role': self.role,
            'model': self.model,
            'content': self.content,
            'tool_name': self.tool_name,
            'tool_input': self.tool_input,
            'tool_output': self.tool_output[:2000]
            if self.tool_output and len(self.tool_output) > 2000
            else self.tool_output,
            'token_input': self.token_input,
            'token_output': self.token_output,
            'duration_ms': self.duration_ms,
            'metadata': self.metadata_,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def to_summary(self):
        return {
            'id': str(self.id),
            'sequence': self.sequence,
            'entry_type': self.entry_type,
            'role': self.role,
            'tool_name': self.tool_name,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
