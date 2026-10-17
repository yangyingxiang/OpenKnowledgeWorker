from types import SimpleNamespace

import pytest

from app.llm import END_TURN, MAX_TOKENS, REFUSAL, TOOL_USE, create_provider
from app.llm.anthropic_provider import _strip_before_fallback, _to_response
from app.llm.openai_provider import build_response, to_openai_messages, to_openai_tool


class _Block(dict):
    def to_dict(self):
        return dict(self)


def _message(blocks, stop_reason):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5)
    return SimpleNamespace(content=[_Block(b) for b in blocks], stop_reason=stop_reason, usage=usage, model='m')


def test_anthropic_response_keeps_thinking_blocks_for_replay():
    message = _message(
        [
            {'type': 'thinking', 'thinking': '', 'signature': 'sig'},
            {'type': 'text', 'text': 'Reading the PDD'},
            {'type': 'tool_use', 'id': 't1', 'name': 'read_pdd', 'input': {}},
        ],
        'tool_use',
    )
    response = _to_response(message)
    assert response.stop_reason == TOOL_USE
    assert response.text == 'Reading the PDD'
    assert [c.name for c in response.tool_calls] == ['read_pdd']
    assert response.assistant_content[0]['type'] == 'thinking'


def test_anthropic_stop_reasons():
    assert _to_response(_message([{'type': 'text', 'text': 'hi'}], 'end_turn')).stop_reason == END_TURN
    assert _to_response(_message([{'type': 'text', 'text': 'hi'}], 'max_tokens')).stop_reason == MAX_TOKENS
    assert _to_response(_message([], 'refusal')).stop_reason == REFUSAL


def test_blocks_before_a_mid_output_fallback_are_not_echoed():
    blocks = [
        {'type': 'thinking', 'thinking': ''},
        {'type': 'text', 'text': 'partial'},
        {'type': 'tool_use', 'id': 'x', 'name': 'n', 'input': {}},
        {'type': 'fallback'},
        {'type': 'text', 'text': 'continued'},
    ]
    assert [b['type'] for b in _strip_before_fallback(blocks)] == ['text', 'fallback', 'text']


def test_openai_message_translation():
    messages = [
        {'role': 'user', 'content': 'Start'},
        {
            'role': 'assistant',
            'content': [
                {'type': 'thinking', 'thinking': 'ignored'},
                {'type': 'text', 'text': 'Calling a tool'},
                {'type': 'tool_use', 'id': 'c1', 'name': 'read_pdd', 'input': {'section': 'x'}},
            ],
        },
        {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': 'c1', 'content': 'PDD text'}]},
    ]
    out = to_openai_messages('SYSTEM', messages)
    assert out[0] == {'role': 'system', 'content': 'SYSTEM'}
    assert out[2]['content'] == 'Calling a tool'
    assert out[2]['tool_calls'][0]['function'] == {'name': 'read_pdd', 'arguments': '{"section": "x"}'}
    assert out[3] == {'role': 'tool', 'tool_call_id': 'c1', 'content': 'PDD text'}


def test_openai_tool_and_response_translation():
    tool = to_openai_tool({'name': 'n', 'description': 'd', 'input_schema': {'type': 'object'}})
    assert tool == {'type': 'function', 'function': {'name': 'n', 'description': 'd', 'parameters': {'type': 'object'}}}
    response = build_response('', {0: {'id': 'c1', 'name': 'n', 'arguments': '{"a": 1}'}}, 'tool_calls', None, 'm')
    assert response.stop_reason == TOOL_USE and response.tool_calls[0].input == {'a': 1}
    assert build_response('cut', {}, 'length', None, 'm').stop_reason == MAX_TOKENS


def test_create_provider_from_config():
    anthropic = create_provider({'LLM_PROVIDER': 'anthropic', 'LLM_MODEL': 'claude-opus-5-5', 'ANTHROPIC_API_KEY': 'k'})
    assert anthropic.name == 'anthropic' and anthropic.server_fallback
    ollama = create_provider({'LLM_PROVIDER': 'openai', 'LLM_MODEL': 'llama3', 'OPENAI_BASE_URL': 'http://x/v1'})
    assert ollama.name == 'openai' and ollama.max_tokens_param == 'max_tokens'
    with pytest.raises(ValueError):
        create_provider({'LLM_PROVIDER': 'nope'})
