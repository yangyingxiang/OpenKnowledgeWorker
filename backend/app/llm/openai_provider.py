"""OpenAI-compatible provider (OpenAI, Azure OpenAI, Ollama, vLLM, LiteLLM, ...).

Uses the Chat Completions API with function calling. Point ``OPENAI_BASE_URL`` at any
compatible server, e.g. ``http://localhost:11434/v1`` for Ollama.
"""

import json
from typing import Iterator

import openai

from .base import (
    END_TURN,
    MAX_TOKENS,
    TOOL_USE,
    LLMError,
    LLMProvider,
    LLMResponse,
    StreamEnd,
    StreamEvent,
    TextDelta,
    ToolCall,
)


class OpenAICompatibleProvider(LLMProvider):
    name = 'openai'

    def __init__(self, model: str, api_key: str = None, base_url: str = None):
        super().__init__(model)
        # Local servers such as Ollama ignore the key but the SDK requires one.
        self.client = openai.OpenAI(api_key=api_key or 'not-needed', base_url=base_url or None)
        # api.openai.com expects max_completion_tokens; most compatible servers use max_tokens.
        self.max_tokens_param = 'max_tokens' if base_url else 'max_completion_tokens'

    def stream(self, *, system, messages, tools=None, max_tokens=32000) -> Iterator[StreamEvent]:
        kwargs = {
            'model': self.model,
            'messages': to_openai_messages(system, messages),
            'stream': True,
            self.max_tokens_param: max_tokens,
        }
        if tools:
            kwargs['tools'] = [to_openai_tool(t) for t in tools]

        text_parts, calls, finish_reason, usage = [], {}, None, None
        try:
            for chunk in self.client.chat.completions.create(**kwargs):
                if getattr(chunk, 'usage', None):
                    usage = {'input_tokens': chunk.usage.prompt_tokens, 'output_tokens': chunk.usage.completion_tokens}
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.delta
                if delta.content:
                    text_parts.append(delta.content)
                    yield TextDelta(delta.content)
                for tc in delta.tool_calls or []:
                    entry = calls.setdefault(tc.index, {'id': None, 'name': '', 'arguments': ''})
                    if tc.id:
                        entry['id'] = tc.id
                    if tc.function and tc.function.name:
                        entry['name'] += tc.function.name
                    if tc.function and tc.function.arguments:
                        entry['arguments'] += tc.function.arguments
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
        except openai.APIStatusError as e:
            raise LLMError(f'OpenAI-compatible API error ({e.status_code}): {e.message}') from e
        except openai.APIConnectionError as e:
            raise LLMError(f'Could not reach the OpenAI-compatible API: {e}') from e

        yield StreamEnd(build_response(''.join(text_parts), calls, finish_reason, usage, self.model))


def build_response(text: str, calls: dict, finish_reason: str, usage, model) -> LLMResponse:
    tool_calls = []
    for index in sorted(calls):
        call = calls[index]
        try:
            args = json.loads(call['arguments']) if call['arguments'] else {}
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCall(call['id'] or f'call_{index}', call['name'], args))

    if finish_reason == 'length':
        stop_reason = MAX_TOKENS
    elif tool_calls:
        stop_reason = TOOL_USE
    else:
        stop_reason = END_TURN

    content = [{'type': 'text', 'text': text}] if text else []
    content += [{'type': 'tool_use', 'id': c.id, 'name': c.name, 'input': c.input} for c in tool_calls]
    return LLMResponse(
        text=text, tool_calls=tool_calls, stop_reason=stop_reason, assistant_content=content, usage=usage, model=model
    )


def to_openai_tool(tool: dict) -> dict:
    return {
        'type': 'function',
        'function': {
            'name': tool['name'],
            'description': tool.get('description', ''),
            'parameters': tool.get('input_schema') or {'type': 'object', 'properties': {}},
        },
    }


def to_openai_messages(system: str, messages: list) -> list:
    """Translate neutral content-block messages into Chat Completions messages."""
    out = [{'role': 'system', 'content': system}] if system else []
    for msg in messages:
        role, content = msg['role'], msg['content']
        if isinstance(content, str):
            out.append({'role': role, 'content': content})
            continue
        texts = [b['text'] for b in content if b.get('type') == 'text']
        if role == 'assistant':
            entry = {'role': 'assistant', 'content': '\n'.join(texts) or None}
            tool_uses = [b for b in content if b.get('type') == 'tool_use']
            if tool_uses:
                entry['tool_calls'] = [
                    {
                        'id': b['id'],
                        'type': 'function',
                        'function': {'name': b['name'], 'arguments': json.dumps(b.get('input') or {})},
                    }
                    for b in tool_uses
                ]
            out.append(entry)
        else:
            # Tool results must directly follow the assistant message that requested them.
            for b in content:
                if b.get('type') == 'tool_result':
                    out.append(
                        {'role': 'tool', 'tool_call_id': b['tool_use_id'], 'content': _result_text(b.get('content'))}
                    )
            if texts:
                out.append({'role': 'user', 'content': '\n'.join(texts)})
    return out


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(b.get('text', '') for b in content if isinstance(b, dict))
    return json.dumps(content)
