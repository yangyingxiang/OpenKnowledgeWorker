"""LLM providers. Agents call ``get_llm()`` and never import a vendor SDK directly.

Configure with environment variables (see .env.example):

    LLM_PROVIDER=anthropic   ANTHROPIC_API_KEY=...   LLM_MODEL=claude-opus-5-5
    LLM_PROVIDER=openai      OPENAI_API_KEY=...      LLM_MODEL=gpt-...
    LLM_PROVIDER=openai      OPENAI_BASE_URL=http://localhost:11434/v1  LLM_MODEL=llama3.1  (Ollama)
"""

from flask import current_app

from .base import (  # noqa: F401  (re-exported)
    END_TURN,
    MAX_TOKENS,
    REFUSAL,
    TOOL_USE,
    LLMError,
    LLMProvider,
    LLMResponse,
    StreamEnd,
    TextDelta,
    ToolCall,
)

PROVIDERS = ('anthropic', 'openai')


def create_provider(config) -> LLMProvider:
    """Build a provider from a Flask-style config mapping."""
    provider = (config.get('LLM_PROVIDER') or 'anthropic').lower()
    model = config.get('LLM_MODEL')
    if provider == 'anthropic':
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            model,
            api_key=config.get('ANTHROPIC_API_KEY') or None,
            server_fallback=config.get('LLM_SERVER_FALLBACK', True),
        )
    if provider == 'openai':
        from .openai_provider import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            model, api_key=config.get('OPENAI_API_KEY') or None, base_url=config.get('OPENAI_BASE_URL') or None
        )
    raise ValueError(f'Unknown LLM_PROVIDER {provider!r}; expected one of {PROVIDERS}')


def get_llm() -> LLMProvider:
    """Provider for the current app. Tests replace it via ``app.config['LLM_PROVIDER_INSTANCE']``."""
    instance = current_app.config.get('LLM_PROVIDER_INSTANCE')
    if instance is not None:
        return instance
    return create_provider(current_app.config)
