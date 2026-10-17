"""Anthropic (Claude) provider, using the official ``anthropic`` SDK."""

from typing import Iterator

import anthropic

from .base import (
    END_TURN,
    MAX_TOKENS,
    REFUSAL,
    TOOL_USE,
    LLMError,
    LLMProvider,
    LLMResponse,
    StreamEnd,
    StreamEvent,
    TextDelta,
    ToolCall,
)

# Models that support server-side refusal fallbacks (`fallbacks: "default"`).
_FALLBACK_MODELS = ('claude-fable-5-1', 'claude-fable-5', 'claude-opus-5-5', 'claude-opus-5', 'claude-sonnet-5-5')
_FALLBACK_BETA = 'server-side-fallback-2026-07-01'
_MODEL_INTERNAL_BLOCKS = {'thinking', 'redacted_thinking', 'tool_use', 'server_tool_use'}


class AnthropicProvider(LLMProvider):
    name = 'anthropic'

    def __init__(self, model: str, api_key: str = None, server_fallback: bool = True):
        super().__init__(model)
        # With no explicit key the SDK resolves credentials from the environment.
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.server_fallback = server_fallback and self.model in _FALLBACK_MODELS

    def stream(self, *, system, messages, tools=None, max_tokens=32000) -> Iterator[StreamEvent]:
        kwargs = {'model': self.model, 'max_tokens': max_tokens, 'system': system, 'messages': messages}
        if tools:
            kwargs['tools'] = tools
        try:
            if self.server_fallback:
                # On a safety decline, the API re-runs the request on a fallback model.
                stream_ctx = self.client.beta.messages.stream(
                    betas=[_FALLBACK_BETA], extra_body={'fallbacks': 'default'}, **kwargs
                )
            else:
                stream_ctx = self.client.messages.stream(**kwargs)
            with stream_ctx as stream:
                for event in stream:
                    if event.type == 'content_block_delta' and event.delta.type == 'text_delta':
                        yield TextDelta(event.delta.text)
                message = stream.get_final_message()
        except anthropic.APIStatusError as e:
            raise LLMError(f'Anthropic API error ({e.status_code}): {e.message}') from e
        except anthropic.APIConnectionError as e:
            raise LLMError(f'Could not reach the Anthropic API: {e}') from e
        yield StreamEnd(_to_response(message))


def _to_response(message) -> LLMResponse:
    blocks = [block.to_dict() for block in message.content]
    blocks = _strip_before_fallback(blocks)
    text = ''.join(b.get('text', '') for b in blocks if b.get('type') == 'text')
    tool_calls = [ToolCall(b['id'], b['name'], b.get('input') or {}) for b in blocks if b.get('type') == 'tool_use']
    stop = message.stop_reason
    if stop == 'refusal':
        stop_reason = REFUSAL
    elif stop == 'max_tokens':
        stop_reason = MAX_TOKENS
    elif tool_calls:
        stop_reason = TOOL_USE
    else:
        stop_reason = END_TURN
    usage = (
        {'input_tokens': message.usage.input_tokens, 'output_tokens': message.usage.output_tokens}
        if message.usage
        else None
    )
    return LLMResponse(
        text=text,
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        assistant_content=blocks,
        usage=usage,
        model=message.model,
    )


def _strip_before_fallback(blocks: list) -> list:
    """After a mid-output fallback, drop model-internal blocks that precede the last
    ``fallback`` marker; they must not be echoed back (text blocks are kept)."""
    last = max((i for i, b in enumerate(blocks) if b.get('type') == 'fallback'), default=-1)
    if last < 0:
        return blocks
    kept = [b for b in blocks[:last] if b.get('type') not in _MODEL_INTERNAL_BLOCKS]
    return kept + blocks[last:]
