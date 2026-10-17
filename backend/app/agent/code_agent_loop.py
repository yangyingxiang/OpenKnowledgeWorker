"""Multi-file coding agent loop: plan → code → test → fix → iterate."""

import json
import os
import tempfile

from ..extensions import get_db
from ..models import CodeProject, PddVersion
from ..services.transcript import TranscriptRecorder
from .chat_agent import run_agent_loop
from .code_tools import create_coding_tools
from .domain_context import build_domain_context

CODING_AGENT_SYSTEM_PROMPT = """\
You are a senior Python engineer building a production-quality, multi-file Python \
codebase from a Process Definition Document (PDD).

## Available Tools
- read_pdd(section?) — Read the PDD content (or a specific section)
- write_file(path, content, file_type?, pdd_section?) — Write/update a project file
- read_file(path) — Read an existing project file
- list_files() — List all files in the project
- delete_file(path) — Remove a project file
- run_tests(test_path?, verbose?) — Execute pytest and return results
- run_module(path?, code?) — Execute a Python file or code snippet
- mark_phase(phase, detail?) — Signal phase transitions (planning/coding/testing/fixing/complete)

## Your Workflow

### Phase 1: Plan (call mark_phase("planning"))
1. Call read_pdd() to read the full PDD
2. Analyze the phases, steps, variables, and business rules
3. Plan your file structure mentally

### Phase 2: Code (call mark_phase("coding"))
Write files in this order:

1. **engine/models.py** — Core data models:
   - `TraceStep` dataclass with fields: step_id, title, decision (PASS/FLAG/EXCLUDE/SKIP), \
result_value, result_label, rule_citation, rationale, method, inputs, duration_ms
   - `EngineState` dataclass for accumulated state across steps

2. **engine/__init__.py** — Package init, exports `run_engine`

3. **engine/utils.py** — Shared helpers (safe dict access, numeric parsing, date helpers)

4. **engine/steps/__ init__.py** — Steps package init

5. **engine/steps/phase_N.py** — One file per PDD phase. Each file contains:
   - One function per PDD step (e.g., `step_1_1_validate_inputs(case, state)`)
   - Each function creates and appends a TraceStep to state.trace
   - Functions operate on the input case dict and mutate EngineState

6. **engine/engine.py** — Main orchestrator:
   - `run_engine(case: dict) -> dict` entry point
   - Imports and calls all step functions in order
   - Returns `{{"trace_steps": [...], "summary": {{...}}}}`
   - The summary MUST include flags, step_decisions, step_values, and every key in the
     Output contract (see Domain context below)

### Phase 3: Test (call mark_phase("testing"))
Write test files:

1. **tests/conftest.py** — Pytest fixtures:
   - Sample input fixture(s) based on the Input format in the Domain context
   - Use realistic test data that exercises the business rules

2. **tests/test_steps.py** — Unit tests for individual step functions:
   - Import step functions directly
   - Test happy path and edge cases
   - Verify TraceStep output (decision, result_value)

3. **tests/test_engine.py** — Integration tests:
   - Call `run_engine()` with test data
   - Verify every Output contract key in the summary
   - Verify step count matches PDD step count
   - Verify all step_decisions are valid

### Phase 4: Execute Tests
Call run_tests() to execute pytest.

### Phase 5: Fix (call mark_phase("fixing") if tests fail)
If tests fail:
1. Read the test output carefully
2. Identify the root cause (wrong logic, missing import, bad data access)
3. Fix the relevant file(s) using write_file
4. Re-run tests
5. Repeat up to {max_iterations} times

### Phase 6: Complete (call mark_phase("complete"))
When all tests pass, call mark_phase("complete", "All N tests passing").

## Code Style Rules

1. **No external dependencies** — Only Python stdlib. No pip packages except pytest for tests.
2. **Safe data access** — Always use `.get()` with defaults for dict lookups
3. **Type hints** — Add type hints to function signatures
4. **Docstrings** — Brief docstrings on public functions
5. **Error handling** — Wrap step logic in try/except, set decision="ERROR" on failure
6. **Small files** — Each file should be under 300 lines. Split large phases into multiple files.
7. **Imports** — Use relative imports within the engine package

## Input Data
The engine receives one case as a dict. Its structure is shown in the Domain context \
(when available) and described by the PDD's Variable Reference section.

## Critical Output Format
The `run_engine()` function MUST return:
```python
{{
    "trace_steps": [
        {{
            "step_id": "1.1",
            "title": "Step title from PDD",
            "decision": "PASS",  # PASS, FLAG, EXCLUDE, SKIP
            "result_value": 1250,
            "result_label": "Human-readable result",
            "rule_citation": "Business Rule ID",
            "rationale": "Explanation",
            "method": "deterministic",  # or "heuristic"
            "inputs": {{"key": "value"}},
            "duration_ms": 0
        }}
    ],
    "summary": {{
        # ...every key in the Output contract...
        "flags": ["list of flags"],
        "step_decisions": {{"1.1": "PASS", "1.2": "FLAG"}},
        "step_values": {{"1.1": 1250}}
    }}
}}
```

## Stop Conditions
- Call mark_phase("complete") when all tests pass
- If after {max_iterations} fix attempts tests still fail, call mark_phase("complete", \
"Partial: X/Y tests passing. Remaining failures: ...") with a summary of what still fails
- Do NOT give up early — always attempt to fix failures

## IMPORTANT
- Write ALL files before running tests for the first time
- Each step function should correspond to exactly one PDD step
- The engine must be importable: `from engine.engine import run_engine`
- Test files go in `tests/` directory (not inside `engine/`)
"""


def run_coding_agent(process_id: str, project_id: str):
    """Generator that yields SSE events for the coding agent.

    Creates a sandbox, sets up tools, and runs the agent loop.
    """
    db = get_db()

    # Get project and PDD
    project = db.query(CodeProject).filter_by(id=project_id).first()
    if not project:
        yield {'type': 'error', 'error': 'Project not found'}
        return

    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    if not pdd:
        yield {'type': 'error', 'error': 'No PDD exists yet'}
        return

    # Create or reuse sandbox
    if not project.sandbox_path or not os.path.exists(project.sandbox_path):
        sandbox = tempfile.mkdtemp(prefix='okw_code_')
        project.sandbox_path = sandbox
        db.commit()
    else:
        sandbox = project.sandbox_path

    # Initialize sandbox structure
    for d in ['engine', 'engine/steps', 'tests']:
        os.makedirs(os.path.join(sandbox, d), exist_ok=True)

    # If retrying, sync existing files to disk
    from .code_tools import _sync_all_files_to_disk

    _sync_all_files_to_disk(str(project_id), sandbox)

    # Create tool registry
    tool_registry = create_coding_tools(
        process_id=str(process_id),
        project_id=str(project_id),
        sandbox_path=sandbox,
    )

    # Format prompt with max_iterations
    system_prompt = CODING_AGENT_SYSTEM_PROMPT.format(
        max_iterations=project.max_iterations or 10,
    )
    domain_context = build_domain_context(process_id)
    if domain_context:
        system_prompt += '\n\n' + domain_context

    # Initial message
    pdd_preview = pdd.content[:2000] if len(pdd.content) > 2000 else pdd.content
    messages = [
        {
            'role': 'user',
            'content': (
                f"Generate a production-quality multi-file Python codebase for this PDD.\n\n"
                f"PDD Preview (first 2000 chars — use read_pdd() for the full document):\n"
                f"{pdd_preview}\n\n"
                f"Follow the workflow: plan → code → test → fix → iterate until all tests pass.\n"
                f"Start by calling mark_phase('planning') and then read_pdd() to read the full PDD."
            ),
        }
    ]

    yield {'type': 'status', 'status': 'planning', 'project_id': str(project_id)}

    # Create transcript recorder
    recorder = TranscriptRecorder(process_id=str(process_id), session_key=str(project_id))

    # Run the agent loop
    for event in run_agent_loop(messages, system_prompt, tool_registry, max_rounds=60, transcript_recorder=recorder):
        # Enrich events with project context
        event['project_id'] = str(project_id)

        # Track phase changes from mark_phase tool calls
        if event.get('type') == 'tool_call' and event.get('name') == 'mark_phase':
            phase = event.get('input', {}).get('phase', '')
            if phase:
                yield {'type': 'status', 'status': phase, 'project_id': str(project_id)}

        # Enrich file writes
        if event.get('type') == 'tool_result' and event.get('name') == 'write_file':
            try:
                result = json.loads(event.get('result', '{}'))
                if result.get('status') == 'ok':
                    yield {
                        'type': 'file_written',
                        'path': result.get('path'),
                        'version': result.get('version'),
                        'lines': result.get('lines'),
                        'project_id': str(project_id),
                    }
            except (json.JSONDecodeError, AttributeError):
                pass

        # Enrich test results
        if event.get('type') == 'tool_result' and event.get('name') == 'run_tests':
            try:
                result = json.loads(event.get('result', '{}'))
                yield {
                    'type': 'test_output',
                    'passed': result.get('passed', 0),
                    'failed': result.get('failed', 0),
                    'errors': result.get('errors', 0),
                    'output': result.get('output', ''),
                    'project_id': str(project_id),
                }
                # Update project test summary
                db_inner = get_db()
                proj = db_inner.query(CodeProject).filter_by(id=project_id).first()
                if proj:
                    proj.test_summary = {
                        'passed': result.get('passed', 0),
                        'failed': result.get('failed', 0),
                        'errors': result.get('errors', 0),
                        'output': result.get('output', '')[:2000],
                    }
                    db_inner.commit()
            except (json.JSONDecodeError, AttributeError):
                pass

        yield event

    # Final status update
    db_final = get_db()
    proj = db_final.query(CodeProject).filter_by(id=project_id).first()
    if proj and proj.status not in ('complete', 'error'):
        proj.status = 'complete'
        db_final.commit()

    yield {
        'type': 'done',
        'project_id': str(project_id),
        'status': proj.status if proj else 'unknown',
        'test_summary': proj.test_summary if proj else None,
    }
