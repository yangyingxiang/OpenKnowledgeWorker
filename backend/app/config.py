"""Application configuration, read from environment variables.

See `.env.example` at the repository root for the full list of settings.
"""

import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_DATABASE_URL = 'postgresql+psycopg2://postgres:postgres@localhost:5432/openknowledgeworker'
DEFAULT_FRONTEND_URL = 'http://localhost:3000'
DEFAULT_MODELS = {'anthropic': 'claude-opus-5-5'}


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == '':
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def load_config():
    """Build the Flask config mapping from the current environment."""
    provider = os.environ.get('LLM_PROVIDER', 'anthropic').strip().lower()
    return {
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', DEFAULT_DATABASE_URL),
        'UPLOAD_DIR': os.path.join(BACKEND_DIR, os.environ.get('UPLOAD_DIR', 'uploads')),
        'FRONTEND_URL': os.environ.get('FRONTEND_URL', DEFAULT_FRONTEND_URL),
        'MAX_CONTENT_LENGTH': 50 * 1024 * 1024,  # 50MB upload limit
        # LLM provider (see app/llm/)
        'LLM_PROVIDER': provider,
        'LLM_MODEL': os.environ.get('LLM_MODEL') or DEFAULT_MODELS.get(provider),
        'ANTHROPIC_API_KEY': os.environ.get('ANTHROPIC_API_KEY', ''),
        'LLM_SERVER_FALLBACK': _flag('LLM_SERVER_FALLBACK', True),
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY', ''),
        'OPENAI_BASE_URL': os.environ.get('OPENAI_BASE_URL', ''),
        # Folder with domain packs (defaults to the repository's examples/)
        'DOMAIN_PACKS_DIR': os.environ.get('DOMAIN_PACKS_DIR', ''),
        # Seconds before a sandboxed run of generated code is killed
        'SANDBOX_TIMEOUT': int(os.environ.get('SANDBOX_TIMEOUT', '120')),
    }
