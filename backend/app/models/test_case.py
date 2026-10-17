import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..extensions import Base


class TestCase(Base):
    __test__ = False  # not a pytest test class
    __tablename__ = 'test_cases'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    description = Column(Text)
    input_data = Column(JSONB, nullable=False)
    expected_assertions = Column(JSONB, nullable=False)
    mock_llm_judge = Column(JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    process = relationship('Process', back_populates='test_cases')
    test_runs = relationship('TestRun', back_populates='test_case', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'test_name': self.test_name,
            'description': self.description,
            'input_data': self.input_data,
            'expected_assertions': self.expected_assertions,
            'mock_llm_judge': self.mock_llm_judge,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class TestRun(Base):
    __test__ = False  # not a pytest test class
    __tablename__ = 'test_runs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    process_id = Column(UUID(as_uuid=True), ForeignKey('processes.id'), nullable=False)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey('test_cases.id'), nullable=True)
    mode = Column(String(20), nullable=False)  # llm, code, both
    status = Column(String(50), default='running')
    llm_result = Column(JSONB)
    code_result = Column(JSONB)
    assertions_passed = Column(Integer)
    assertions_total = Column(Integer)
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    test_case = relationship('TestCase', back_populates='test_runs')

    def to_dict(self):
        return {
            'id': str(self.id),
            'process_id': str(self.process_id),
            'test_case_id': str(self.test_case_id) if self.test_case_id else None,
            'mode': self.mode,
            'status': self.status,
            'llm_result': self.llm_result,
            'code_result': self.code_result,
            'assertions_passed': self.assertions_passed,
            'assertions_total': self.assertions_total,
            'duration_ms': self.duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
