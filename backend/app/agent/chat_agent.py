"""Tool-calling agent loop shared by the research, SME chat, and coding agents."""

import time

from ..llm import MAX_TOKENS, REFUSAL, LLMError, StreamEnd, TextDelta, get_llm
from .tool_registry import ToolRegistry

MAX_TOOL_ROUNDS = 30
MAX_OUTPUT_TOKENS = 32000
CONTINUE_PROMPT = 'Continue. You were cut off mid-response. Keep going from where you left off.'


def run_agent_loop(
    messages, system_prompt, tool_registry: ToolRegistry, max_rounds=MAX_TOOL_ROUNDS, transcript_recorder=None
):
    """Run the agent tool-calling loop, yielding events for SSE streaming.

    Yields dicts with types: 'delta', 'tool_call', 'tool_result', 'done', 'error'.
    If ``transcript_recorder`` is given, every model request/response and tool call
    is persisted for debugging.
    """
    llm = get_llm()
    tools = tool_registry.get_tool_schemas()
    current_messages = list(messages)
    recorder = _SafeRecorder(transcript_recorder)
    response = None

    for round_num in range(max_rounds):
        recorder.call('record_model_request', current_messages, system_prompt, llm.model)
        t0 = time.time()
        try:
            for event in llm.stream(
                system=system_prompt, messages=current_messages, tools=tools or None, max_tokens=MAX_OUTPUT_TOKENS
            ):
                if isinstance(event, TextDelta):
                    yield {'type': 'delta', 'text': event.text}
                elif isinstance(event, StreamEnd):
                    response = event.response
        except LLMError as e:
            recorder.call('record_error', str(e), context='model_request')
            yield {'type': 'error', 'error': str(e)}
            return

        recorder.call(
            'record_model_response',
            response.text,
            [{'id': c.id, 'name': c.name, 'input': c.input} for c in response.tool_calls],
            response.usage,
            (time.time() - t0) * 1000,
            response.stop_reason,
        )

        if response.stop_reason == REFUSAL:
            yield {'type': 'error', 'error': 'The model declined this request.'}
            return

        # Append the assistant turn exactly as returned (keeps thinking blocks etc.).
        if response.assistant_content:
            current_messages.append({'role': 'assistant', 'content': response.assistant_content})

        if not response.tool_calls:
            if response.stop_reason == MAX_TOKENS and round_num < max_rounds - 1:
                current_messages.append({'role': 'user', 'content': [{'type': 'text', 'text': CONTINUE_PROMPT}]})
                continue
            yield {'type': 'done', 'text': response.text, 'stop_reason': response.stop_reason}
            return

        tool_results = []
        for call in response.tool_calls:
            yield {'type': 'tool_call', 'name': call.name, 'input': call.input}
            recorder.call('record_tool_call', call.name, call.input)
            t1 = time.time()
            result = tool_registry.execute(call.name, call.input)
            recorder.call('record_tool_result', call.name, result, (time.time() - t1) * 1000)
            tool_results.append({'type': 'tool_result', 'tool_use_id': call.id, 'content': result})
            yield {'type': 'tool_result', 'name': call.name, 'result': result}

        current_messages.append({'role': 'user', 'content': tool_results})

    yield {'type': 'done', 'text': response.text if response else '', 'stop_reason': 'max_rounds'}


def run_agent_streaming(messages, system_prompt, tool_registry: ToolRegistry, max_rounds=MAX_TOOL_ROUNDS):
    """Streaming agent loop used by the research and chat endpoints."""
    yield from run_agent_loop(messages, system_prompt, tool_registry, max_rounds=max_rounds)


class _SafeRecorder:
    """Calls transcript-recorder methods, never letting recording break the agent."""

    def __init__(self, recorder):
        self.recorder = recorder

    def call(self, method, *args, **kwargs):
        if self.recorder is None:
            return
        try:
            getattr(self.recorder, method)(*args, **kwargs)
        except Exception:
            pass
