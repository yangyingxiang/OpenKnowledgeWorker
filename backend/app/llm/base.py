"""Provider-neutral LLM interface used by every agent in the backend.

Message format (provider-neutral, Anthropic-style content blocks):

    {"role": "user" | "assistant", "content": str | [block, ...]}

    block = {"type": "text", "text": ...}
          | {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
          | {"type": "tool_result", "tool_use_id": ..., "content": str}
          | provider-specific blocks (e.g. "thinking"), passed back unchanged

Tools are ``{"name", "description", "input_schema"}`` dicts (JSON Schema input).
Providers translate to and from their own wire formats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional, Union

# Normalized stop reasons
END_TURN = 'end_turn'
TOOL_USE = 'tool_use'
MAX_TOKENS = 'max_tokens'
REFUSAL = 'refusal'


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class LLMResponse:
    text: str
    tool_calls: list = field(default_factory=list)
    stop_reason: str = END_TURN
    # Content blocks to append verbatim as the assistant turn when continuing the
    # conversation (keeps provider-specific blocks such as thinking intact).
    assistant_content: list = field(default_factory=list)
    usage: Optional[dict] = None
    model: Optional[str] = None


@dataclass
class TextDelta:
    """A chunk of streamed assistant text."""

    text: str


@dataclass
class StreamEnd:
    """Final event of a stream, carrying the complete response."""

    response: LLMResponse


StreamEvent = Union[TextDelta, StreamEnd]


class LLMError(RuntimeError):
    """Raised for provider errors, with a message safe to show to users."""


class LLMProvider(ABC):
    """Base class for LLM providers."""

    name = 'base'

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def stream(
        self, *, system: str, messages: list, tools: list = None, max_tokens: int = 32000
    ) -> Iterator[StreamEvent]:
        """Yield TextDelta events, then exactly one StreamEnd."""

    def complete(self, *, system: str, messages: list, tools: list = None, max_tokens: int = 32000) -> LLMResponse:
        """Return the full response (implemented on top of ``stream``)."""
        for event in self.stream(system=system, messages=messages, tools=tools, max_tokens=max_tokens):
            if isinstance(event, StreamEnd):
                return event.response
        raise LLMError(f'{self.name} stream ended without a final response')
