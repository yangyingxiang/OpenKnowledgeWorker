"""Shared fixtures for integration tests."""

import json as _json
import os
import sqlite3
import uuid
from unittest.mock import patch

# Set environment variables BEFORE importing app modules so that
# create_app() and model definitions pick up SQLite settings.
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')
os.environ.setdefault('FRONTEND_URL', 'http://localhost:3000')

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# SQLite compatibility: register adapters so Python types survive round-trips.
# ---------------------------------------------------------------------------
# Tell sqlite3 how to store uuid.UUID objects
sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
# Tell sqlite3 how to store lists / dicts (JSONB columns)
sqlite3.register_adapter(list, lambda v: _json.dumps(v))
sqlite3.register_adapter(dict, lambda v: _json.dumps(v))

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

import app.extensions as ext
from app.extensions import Base

# Import all models so metadata is populated
from app.models import (  # noqa: F401
    AuditLog,
    ChangeEvent,
    ChatMessage,
    ChatSession,
    CodeFile,
    CodeProject,
    CodeUnit,
    Document,
    DocumentChunk,
    EvidenceLink,
    EvidenceSpan,
    Job,
    KnowledgeItem,
    PddStatement,
    PddVersion,
    Process,
    Provenance,
    Question,
    TestCase,
    TestRun,
    Transcript,
)


def _remap_pg_columns(metadata):
    """Walk every column in metadata and swap PG-specific types for
    SQLite-safe equivalents so that CREATE TABLE works on SQLite."""
    for table in metadata.tables.values():
        for column in table.columns:
            col_type = column.type
            if isinstance(col_type, PG_UUID):
                column.type = String(36)
            elif isinstance(col_type, PG_JSONB):
                column.type = JSON()


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    """Create a Flask app with an in-memory SQLite database for testing."""
    # StaticPool + check_same_thread=False: background job threads share the in-memory DB.
    engine = create_engine('sqlite://', echo=False, poolclass=StaticPool, connect_args={'check_same_thread': False})

    # Enable foreign keys in SQLite
    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.close()

    # Remap PG types to SQLite-compatible types for table creation
    _remap_pg_columns(Base.metadata)

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(bind=engine)
    TestSession = scoped_session(session_factory)

    # Monkey-patch the extensions module so get_db() returns our test session
    ext.engine = engine
    ext.SessionLocal = TestSession
    ext.db = TestSession

    # Patch init_db to be a no-op — we already configured the engine and session
    # above, and the real init_db would try pool_size / max_overflow which SQLite
    # does not support.
    def _noop_init_db(app_obj):
        @app_obj.teardown_appcontext
        def shutdown_session(exception=None):
            TestSession.remove()

    with patch('app.extensions.init_db', side_effect=_noop_init_db):
        from app import create_app as _create_app

        flask_app = _create_app()

    flask_app.config['TESTING'] = True
    flask_app.config['UPLOAD_DIR'] = str(tmp_path_factory.mktemp('uploads'))
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    # Ensure extensions still point to our test engine/session after create_app
    ext.engine = engine
    ext.SessionLocal = TestSession
    ext.db = TestSession

    yield flask_app

    TestSession.remove()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def fake_llm(app):
    """Replace the LLM provider with a scripted fake for the duration of a test."""
    from tests.fakes import ScriptedLLM

    llm = ScriptedLLM()
    app.config['LLM_PROVIDER_INSTANCE'] = llm
    yield llm
    app.config.pop('LLM_PROVIDER_INSTANCE', None)


@pytest.fixture(scope='session')
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """Provide a DB session that cleans up all rows after each test."""
    session = ext.SessionLocal()
    yield session
    session.rollback()
    # Clean up all rows to isolate tests
    for tbl in reversed(Base.metadata.sorted_tables):
        session.execute(tbl.delete())
    session.commit()


@pytest.fixture()
def process_id(db_session):
    """Create a test Process and return its id (as a string)."""
    pid = uuid.uuid4()
    proc = Process(
        id=pid,
        name='Test Process',
        domain='testing',
        description='A process used by integration tests',
        status='draft',
    )
    db_session.add(proc)
    db_session.commit()
    return str(pid)


@pytest.fixture()
def session_id(db_session, process_id):
    """Create a ChatSession for the test process and return its id (as string)."""
    sid = uuid.uuid4()
    cs = ChatSession(
        id=sid,
        process_id=process_id,
        expert_name='Test Expert',
        expert_role='SME',
        status='active',
    )
    db_session.add(cs)
    db_session.commit()
    return str(sid)
