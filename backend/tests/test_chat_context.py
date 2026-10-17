"""Tests for context-aware system prompt selection."""

from unittest.mock import patch

from app.agent.prompts import (
    CHAT_SYSTEM_PROMPT,
    CODE_CHAT_SYSTEM_PROMPT,
    TEST_CHAT_SYSTEM_PROMPT,
)


def _capture_system_prompt(app, process_id, session_id, context_value=None):
    """Helper: POST a message with given context and capture the system_prompt
    that was passed to run_agent_streaming.

    We must consume the SSE response body to trigger the generator, which is
    where the mock is actually called.
    """
    captured = {}

    def _mock_streaming(messages, system_prompt, tool_registry):
        captured['system_prompt'] = system_prompt
        yield {'type': 'delta', 'text': 'ok'}
        yield {'type': 'done', 'text': 'ok', 'stop_reason': 'end_turn'}

    body = {'content': 'test message'}
    if context_value is not None:
        body['context'] = context_value

    with patch('app.api.chat.run_agent_streaming', side_effect=_mock_streaming):
        c = app.test_client()
        resp = c.post(
            f'/api/processes/{process_id}/chat/sessions/{session_id}/message',
            json=body,
        )
        assert resp.status_code == 200
        # Consume the SSE stream so the generator (and our mock) actually runs
        _ = resp.get_data(as_text=True)

    return captured.get('system_prompt', '')


def test_default_context_uses_chat_prompt(app, db_session, process_id, session_id):
    """When no context is specified, the default 'sop' maps to CHAT_SYSTEM_PROMPT."""
    prompt = _capture_system_prompt(app, process_id, session_id)
    # The prompt may have PDD content appended, so check it starts with the expected base
    assert prompt.startswith(CHAT_SYSTEM_PROMPT)


def test_code_context_uses_code_prompt(app, db_session, process_id, session_id):
    """When context='code', CODE_CHAT_SYSTEM_PROMPT is used."""
    prompt = _capture_system_prompt(app, process_id, session_id, context_value='code')
    assert prompt.startswith(CODE_CHAT_SYSTEM_PROMPT)


def test_tests_context_uses_test_prompt(app, db_session, process_id, session_id):
    """When context='tests', TEST_CHAT_SYSTEM_PROMPT is used."""
    prompt = _capture_system_prompt(app, process_id, session_id, context_value='tests')
    assert prompt.startswith(TEST_CHAT_SYSTEM_PROMPT)


def test_unknown_context_falls_back_to_chat_prompt(app, db_session, process_id, session_id):
    """An unrecognised context value falls back to CHAT_SYSTEM_PROMPT."""
    prompt = _capture_system_prompt(app, process_id, session_id, context_value='unknown')
    assert prompt.startswith(CHAT_SYSTEM_PROMPT)
