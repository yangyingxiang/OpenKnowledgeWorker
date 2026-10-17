"""Integration tests for the chat API endpoints."""

import uuid
from unittest.mock import patch

from app.models import ChatSession


def test_create_session(app, db_session, process_id):
    """POST to create a chat session returns 201 with session data."""
    c = app.test_client()
    resp = c.post(
        f'/api/processes/{process_id}/chat/sessions',
        json={'expert_name': 'Alice', 'expert_role': 'DA'},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['expert_name'] == 'Alice'
    assert data['expert_role'] == 'DA'
    assert data['status'] == 'active'
    # Should include the welcome message
    assert 'messages' in data
    assert len(data['messages']) >= 1
    assert data['messages'][0]['role'] == 'system'


def test_list_sessions(app, db_session, process_id):
    """GET lists all sessions for a process."""
    c = app.test_client()
    # Create two sessions
    c.post(f'/api/processes/{process_id}/chat/sessions', json={'expert_name': 'Bob'})
    c.post(f'/api/processes/{process_id}/chat/sessions', json={'expert_name': 'Carol'})

    resp = c.get(f'/api/processes/{process_id}/chat/sessions')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 2
    names = {s['expert_name'] for s in data}
    assert 'Bob' in names
    assert 'Carol' in names


def test_get_session(app, db_session, process_id):
    """GET a specific session returns it with messages."""
    c = app.test_client()
    create_resp = c.post(
        f'/api/processes/{process_id}/chat/sessions',
        json={'expert_name': 'Dave'},
    )
    sid = create_resp.get_json()['id']

    resp = c.get(f'/api/processes/{process_id}/chat/sessions/{sid}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['id'] == sid
    assert data['expert_name'] == 'Dave'
    assert 'messages' in data


def test_send_message_requires_content(app, db_session, process_id, session_id):
    """POST a message without content returns 400."""
    c = app.test_client()
    resp = c.post(
        f'/api/processes/{process_id}/chat/sessions/{session_id}/message',
        json={},
    )
    assert resp.status_code == 400
    assert 'content' in resp.get_json().get('error', '').lower()


def test_send_message_inactive_session(app, db_session, process_id, session_id):
    """POST a message to an inactive session returns 400."""
    # Mark the session as completed
    session = db_session.query(ChatSession).filter_by(id=session_id).first()
    session.status = 'completed'
    db_session.commit()

    c = app.test_client()
    resp = c.post(
        f'/api/processes/{process_id}/chat/sessions/{session_id}/message',
        json={'content': 'Hello'},
    )
    assert resp.status_code == 400
    assert 'not active' in resp.get_json().get('error', '').lower()


def test_send_message_accepts_context(app, db_session, process_id, session_id):
    """POST a message with context='code' is accepted (SSE streaming)."""

    def _mock_streaming(messages, system_prompt, tool_registry):
        yield {'type': 'delta', 'text': 'Hello from mock'}
        yield {'type': 'done', 'text': 'Hello from mock', 'stop_reason': 'end_turn'}

    with patch('app.api.chat.run_agent_streaming', side_effect=_mock_streaming):
        c = app.test_client()
        resp = c.post(
            f'/api/processes/{process_id}/chat/sessions/{session_id}/message',
            json={'content': 'Tell me about the code', 'context': 'code'},
        )
        # SSE endpoint returns 200 with text/event-stream
        assert resp.status_code == 200
        assert 'text/event-stream' in resp.content_type


def test_send_message_streams_events(app, db_session, process_id, session_id):
    """Verify the SSE endpoint actually yields events from the mocked agent."""

    def _mock_streaming(messages, system_prompt, tool_registry):
        yield {'type': 'delta', 'text': 'Mock reply'}
        yield {'type': 'done', 'text': 'Mock reply', 'stop_reason': 'end_turn'}

    with patch('app.api.chat.run_agent_streaming', side_effect=_mock_streaming):
        c = app.test_client()
        resp = c.post(
            f'/api/processes/{process_id}/chat/sessions/{session_id}/message',
            json={'content': 'Hi there'},
        )
        raw = resp.get_data(as_text=True)
        # Should contain SSE-formatted events
        assert 'data:' in raw
        # Should contain our mock text somewhere
        assert 'Mock reply' in raw


def test_send_message_not_found_session(app, db_session, process_id):
    """POST to a non-existent session returns 404."""
    fake_sid = str(uuid.uuid4())
    c = app.test_client()
    resp = c.post(
        f'/api/processes/{process_id}/chat/sessions/{fake_sid}/message',
        json={'content': 'Hi'},
    )
    assert resp.status_code == 404
