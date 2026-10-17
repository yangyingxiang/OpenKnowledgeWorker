"""Run LLM-generated Python code outside the API server process.

Generated code is untrusted. Everything that executes it goes through this module:

* a separate Python subprocess (never ``import``/``exec`` inside the server),
* an allow-listed environment, so API keys, database URLs and other secrets
  are never visible to generated code,
* a working directory confined to the project's sandbox folder,
* a wall-clock timeout.

This is process isolation, not a security boundary against a determined attacker.
For untrusted multi-user deployments, run the backend itself inside a container or VM
(see SECURITY.md).
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass

DEFAULT_TIMEOUT = 120  # seconds
OUTPUT_LIMIT = 12_000  # characters of stdout/stderr kept

# Only these variables are passed through to sandboxed processes.
SAFE_ENV_KEYS = ('PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TZ', 'SYSTEMROOT', 'TMPDIR', 'TEMP', 'TMP')

RESULT_MARKER = '__OKW_ENGINE_RESULT__'

_ENGINE_RUNNER = f"""
import inspect, json, sys
sys.path.insert(0, '.')
from engine.engine import run_engine
payload = json.load(sys.stdin)
kwargs = {{}}
if payload.get('mock_llm_judge') and 'mock_llm_judge' in inspect.signature(run_engine).parameters:
    kwargs['mock_llm_judge'] = payload['mock_llm_judge']
result = run_engine(payload['case'], **kwargs)
sys.stdout.write('\\n{RESULT_MARKER}' + json.dumps(result, default=str))
"""


@dataclass
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def output(self) -> str:
        text = self.stdout + ('\n' + self.stderr if self.stderr else '')
        return text[:OUTPUT_LIMIT]


def sandbox_env(cwd: str) -> dict:
    """Minimal environment for generated code: no secrets, HOME inside the sandbox."""
    env = {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
    env['HOME'] = cwd
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def run_python(args: list, cwd: str, timeout: int = DEFAULT_TIMEOUT, stdin: str = None) -> SandboxResult:
    """Run ``python <args>`` in ``cwd`` with the sandbox environment."""
    try:
        proc = subprocess.run(
            [sys.executable, *args],
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=sandbox_env(cwd),
        )
        return SandboxResult(proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as e:
        return SandboxResult(-1, _decode(e.stdout), _decode(e.stderr), timed_out=True)


def run_engine(work_dir: str, input_data: dict, timeout: int = DEFAULT_TIMEOUT, mock_llm_judge: dict = None) -> dict:
    """Call ``engine.engine.run_engine(input_data)`` from a generated project in a subprocess.

    Engines whose ``run_engine`` accepts a ``mock_llm_judge`` keyword also receive the test
    case's recorded judgments, so semantic steps are deterministic in golden tests.

    Returns the engine's result dict, or ``{'error': ..., 'trace_steps': [], 'summary': {}}``.
    """
    payload = json.dumps({'case': input_data, 'mock_llm_judge': mock_llm_judge}, default=str)
    result = run_python(['-c', _ENGINE_RUNNER], cwd=work_dir, timeout=timeout, stdin=payload)
    if result.timed_out:
        return _error(f'Engine timed out after {timeout}s')
    marker_at = result.stdout.rfind(RESULT_MARKER)
    if result.returncode != 0 or marker_at < 0:
        detail = (result.stderr or result.stdout).strip()[-OUTPUT_LIMIT:]
        return _error(f'Engine failed (exit code {result.returncode}): {detail}')
    try:
        parsed = json.loads(result.stdout[marker_at + len(RESULT_MARKER) :])
    except json.JSONDecodeError as e:
        return _error(f'Engine returned invalid JSON: {e}')
    if not isinstance(parsed, dict):
        return _error('Engine must return a dict with "trace_steps" and "summary"')
    return parsed


def _error(message: str) -> dict:
    return {'error': message, 'trace_steps': [], 'summary': {}}


def _decode(value) -> str:
    if value is None:
        return ''
    return value.decode(errors='replace') if isinstance(value, bytes) else value
