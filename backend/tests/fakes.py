"""Test doubles shared across the test suite."""

from app.llm import END_TURN, TOOL_USE, LLMProvider, LLMResponse, StreamEnd, TextDelta, ToolCall


def text_response(text, stop_reason=END_TURN):
    return LLMResponse(text=text, stop_reason=stop_reason, assistant_content=[{'type': 'text', 'text': text}])


def tool_response(name, tool_input, call_id='call_1', text=''):
    content = ([{'type': 'text', 'text': text}] if text else []) + [
        {'type': 'tool_use', 'id': call_id, 'name': name, 'input': tool_input}
    ]
    return LLMResponse(
        text=text,
        tool_calls=[ToolCall(call_id, name, tool_input)],
        stop_reason=TOOL_USE,
        assistant_content=content,
    )


class ScriptedLLM(LLMProvider):
    """Returns queued responses in order and records every request it receives."""

    name = 'scripted'

    def __init__(self, responses=None):
        super().__init__('scripted-model')
        self.responses = list(responses or [])
        self.requests = []

    def queue(self, *responses):
        self.responses.extend(responses)
        return self

    def stream(self, *, system, messages, tools=None, max_tokens=32000):
        self.requests.append({'system': system, 'messages': [dict(m) for m in messages], 'tools': tools})
        response = self.responses.pop(0) if self.responses else text_response('(no scripted response)')
        if response.text:
            yield TextDelta(response.text)
        yield StreamEnd(response)
