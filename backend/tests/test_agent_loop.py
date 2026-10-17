from app.agent.chat_agent import run_agent_loop
from app.agent.tool_registry import ToolDef, ToolRegistry
from app.llm import MAX_TOKENS, REFUSAL
from tests.fakes import text_response, tool_response


def _registry(calls):
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name='echo',
            description='Echo the input',
            input_schema={'type': 'object', 'properties': {'value': {'type': 'string'}}},
            handler=lambda value='': calls.append(value) or f'echo:{value}',
        )
    )
    return registry


def test_tool_call_round_trip(app, fake_llm):
    calls = []
    fake_llm.queue(tool_response('echo', {'value': 'hi'}, text='Let me check'), text_response('All done'))
    with app.app_context():
        events = list(run_agent_loop([{'role': 'user', 'content': 'go'}], 'system', _registry(calls)))

    assert calls == ['hi']
    assert [e['type'] for e in events] == ['delta', 'tool_call', 'tool_result', 'delta', 'done']
    # Second request carries the assistant turn verbatim plus the tool result
    second = fake_llm.requests[1]['messages']
    assert second[1]['content'][-1]['type'] == 'tool_use'
    assert second[2]['content'][0] == {'type': 'tool_result', 'tool_use_id': 'call_1', 'content': 'echo:hi'}


def test_max_tokens_triggers_continuation(app, fake_llm):
    fake_llm.queue(text_response('part one', stop_reason=MAX_TOKENS), text_response('part two'))
    with app.app_context():
        events = list(run_agent_loop([{'role': 'user', 'content': 'go'}], 'system', _registry([])))
    assert events[-1] == {'type': 'done', 'text': 'part two', 'stop_reason': 'end_turn'}
    assert 'Continue' in fake_llm.requests[1]['messages'][-1]['content'][0]['text']


def test_refusal_is_reported_as_error(app, fake_llm):
    fake_llm.queue(text_response('', stop_reason=REFUSAL))
    with app.app_context():
        events = list(run_agent_loop([{'role': 'user', 'content': 'go'}], 'system', _registry([])))
    assert events[-1]['type'] == 'error'
