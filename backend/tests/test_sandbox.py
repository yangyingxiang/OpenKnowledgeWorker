import os
import textwrap

from app import sandbox


def _write_engine(tmp_path, body):
    pkg = tmp_path / 'engine'
    pkg.mkdir()
    (pkg / '__init__.py').write_text('')
    (pkg / 'engine.py').write_text(textwrap.dedent(body))
    return str(tmp_path)


def test_run_engine_returns_result(tmp_path):
    work = _write_engine(
        tmp_path,
        """
        def run_engine(case):
            print('engine output on stdout is ignored')
            return {'trace_steps': [], 'summary': {'doubled': case['x'] * 2}}
        """,
    )
    assert sandbox.run_engine(work, {'x': 21})['summary'] == {'doubled': 42}


def test_secrets_are_not_visible_to_generated_code(tmp_path, monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-secret')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://secret')
    work = _write_engine(
        tmp_path,
        """
        import os
        def run_engine(case):
            return {'trace_steps': [], 'summary': {'env': sorted(os.environ)}}
        """,
    )
    env_keys = sandbox.run_engine(work, {})['summary']['env']
    assert 'ANTHROPIC_API_KEY' not in env_keys
    assert 'DATABASE_URL' not in env_keys


def test_engine_runs_in_a_separate_process(tmp_path):
    work = _write_engine(
        tmp_path,
        """
        import os
        def run_engine(case):
            return {'trace_steps': [], 'summary': {'pid': os.getpid()}}
        """,
    )
    assert sandbox.run_engine(work, {})['summary']['pid'] != os.getpid()


def test_engine_exception_is_reported(tmp_path):
    work = _write_engine(tmp_path, "def run_engine(case):\n    raise ValueError('boom')\n")
    result = sandbox.run_engine(work, {})
    assert 'boom' in result['error'] and result['summary'] == {}


def test_timeout(tmp_path):
    work = _write_engine(tmp_path, "import time\ndef run_engine(case):\n    time.sleep(10)\n")
    assert 'timed out' in sandbox.run_engine(work, {}, timeout=1)['error']


def test_mock_judge_passed_only_when_accepted(tmp_path):
    work = _write_engine(
        tmp_path,
        """
        def run_engine(case, mock_llm_judge=None):
            return {'trace_steps': [], 'summary': {'judge': mock_llm_judge}}
        """,
    )
    result = sandbox.run_engine(work, {}, mock_llm_judge={'1.3': {'decision': True}})
    assert result['summary']['judge'] == {'1.3': {'decision': True}}
