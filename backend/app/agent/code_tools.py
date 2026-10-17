"""Tool registry for the multi-file coding agent."""

import json
import os
import re
from datetime import datetime, timezone

from .. import sandbox
from ..extensions import get_db
from ..models import CodeFile, PddVersion
from .tool_registry import ToolDef, ToolRegistry

# Safety limits
MAX_FILES = 60
MAX_FILE_SIZE = 100_000  # 100KB per file
SUBPROCESS_TIMEOUT = sandbox.DEFAULT_TIMEOUT  # seconds


def _validate_path(path: str) -> str:
    """Validate a file path is safe (relative, no traversal)."""
    path = path.strip().lstrip('/')
    if '..' in path or path.startswith('/') or '\x00' in path:
        raise ValueError(f'Invalid path: {path}')
    if os.path.isabs(path):
        raise ValueError(f'Absolute paths not allowed: {path}')
    return path


def _sync_to_disk(sandbox_path: str, file_path: str, content: str):
    """Write file content to the sandbox directory."""
    full_path = os.path.join(sandbox_path, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)


def _sync_all_files_to_disk(project_id: str, sandbox_path: str):
    """Sync all DB files to disk (used on retry)."""
    db = get_db()
    files = db.query(CodeFile).filter_by(project_id=project_id).all()
    for cf in files:
        _sync_to_disk(sandbox_path, cf.file_path, cf.content)


def _count_pytest_results(output: str) -> dict:
    """Count passed/failed/errored tests from pytest output (verbose lines or summary line)."""
    counts = {
        'passed': output.count(' PASSED'),
        'failed': output.count(' FAILED'),
        'errors': output.count(' ERROR'),
    }
    for key, word in (('passed', 'passed'), ('failed', 'failed'), ('errors', 'error')):
        if counts[key] == 0:
            m = re.search(rf'(\d+) {word}', output)
            if m:
                counts[key] = int(m.group(1))
    return counts


def create_coding_tools(process_id: str, project_id: str, sandbox_path: str) -> ToolRegistry:
    """Create a ToolRegistry with all tools for the coding agent."""
    registry = ToolRegistry()

    # --- read_pdd ---
    def read_pdd(section=None):
        db = get_db()
        pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        if not pdd:
            return json.dumps({'content': '', 'message': 'No PDD exists yet'})
        content = pdd.content
        if section:
            lines = content.split('\n')
            in_section = False
            section_lines = []
            for line in lines:
                if section.lower() in line.lower() and line.startswith('#'):
                    in_section = True
                elif in_section and line.startswith('#') and len(line) - len(line.lstrip('#')) <= 2:
                    break
                if in_section:
                    section_lines.append(line)
            content = '\n'.join(section_lines) if section_lines else f'Section "{section}" not found'
        return json.dumps({'content': content})

    registry.register(
        ToolDef(
            name='read_pdd',
            description='Read the current Process Definition Document. Optionally filter to a specific section by name.',
            input_schema={
                'type': 'object',
                'properties': {
                    'section': {
                        'type': 'string',
                        'description': 'Optional section name to read (e.g. "Process", "Variables")',
                    }
                },
            },
            handler=read_pdd,
        )
    )

    # --- write_file ---
    def write_file(path: str, content: str, file_type: str = 'source', pdd_section: str = None):
        path = _validate_path(path)
        if len(content) > MAX_FILE_SIZE:
            return json.dumps({'error': f'File too large ({len(content)} bytes, max {MAX_FILE_SIZE})'})

        db = get_db()
        existing_count = db.query(CodeFile).filter_by(project_id=project_id).count()

        existing = db.query(CodeFile).filter_by(project_id=project_id, file_path=path).first()
        if existing:
            existing.content = content
            existing.file_type = file_type
            existing.version += 1
            if pdd_section:
                existing.pdd_section_ref = pdd_section
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            version = existing.version
        else:
            if existing_count >= MAX_FILES:
                return json.dumps({'error': f'Max files ({MAX_FILES}) reached'})
            cf = CodeFile(
                project_id=project_id,
                file_path=path,
                content=content,
                file_type=file_type,
                pdd_section_ref=pdd_section,
            )
            db.add(cf)
            db.commit()
            version = 1

        _sync_to_disk(sandbox_path, path, content)
        line_count = content.count('\n') + 1
        return json.dumps({'status': 'ok', 'path': path, 'version': version, 'lines': line_count})

    registry.register(
        ToolDef(
            name='write_file',
            description='Write or update a file in the project. Creates parent directories automatically.',
            input_schema={
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Relative file path (e.g. "engine/steps/phase_1.py")'},
                    'content': {'type': 'string', 'description': 'The full file content'},
                    'file_type': {
                        'type': 'string',
                        'enum': ['source', 'test', 'config', 'init'],
                        'description': 'Type of file (default: source)',
                    },
                    'pdd_section': {'type': 'string', 'description': 'Optional PDD section this file implements'},
                },
                'required': ['path', 'content'],
            },
            handler=write_file,
        )
    )

    # --- read_file ---
    def read_file(path: str):
        path = _validate_path(path)
        db = get_db()
        cf = db.query(CodeFile).filter_by(project_id=project_id, file_path=path).first()
        if not cf:
            return json.dumps({'error': f'File not found: {path}'})
        return json.dumps({'path': cf.file_path, 'content': cf.content, 'version': cf.version})

    registry.register(
        ToolDef(
            name='read_file',
            description='Read an existing file from the project.',
            input_schema={
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Relative file path to read'},
                },
                'required': ['path'],
            },
            handler=read_file,
        )
    )

    # --- list_files ---
    def list_files():
        db = get_db()
        files = db.query(CodeFile).filter_by(project_id=project_id).order_by(CodeFile.file_path).all()
        return json.dumps([f.to_summary() for f in files])

    registry.register(
        ToolDef(
            name='list_files',
            description='List all files in the project with their paths, types, and line counts.',
            input_schema={'type': 'object', 'properties': {}},
            handler=list_files,
        )
    )

    # --- delete_file ---
    def delete_file(path: str):
        path = _validate_path(path)
        db = get_db()
        cf = db.query(CodeFile).filter_by(project_id=project_id, file_path=path).first()
        if not cf:
            return json.dumps({'error': f'File not found: {path}'})
        db.delete(cf)
        db.commit()
        full_path = os.path.join(sandbox_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
        return json.dumps({'status': 'ok', 'deleted': path})

    registry.register(
        ToolDef(
            name='delete_file',
            description='Delete a file from the project.',
            input_schema={
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Relative file path to delete'},
                },
                'required': ['path'],
            },
            handler=delete_file,
        )
    )

    # --- run_tests ---
    def run_tests(test_path: str = None, verbose: bool = True):
        args = ['-m', 'pytest']
        if verbose:
            args.append('-v')
        args.extend(['--tb=short', '--no-header', '-p', 'no:cacheprovider'])
        if test_path:
            args.append(_validate_path(test_path))

        result = sandbox.run_python(args, cwd=sandbox_path, timeout=SUBPROCESS_TIMEOUT)
        if result.timed_out:
            return json.dumps({'error': f'Tests timed out after {SUBPROCESS_TIMEOUT}s', 'returncode': -1})
        output = result.output
        return json.dumps(
            {
                'returncode': result.returncode,
                **_count_pytest_results(output),
                'output': output,
            }
        )

    registry.register(
        ToolDef(
            name='run_tests',
            description='Execute pytest on the project. Returns pass/fail counts and output. Use this after writing test files to verify correctness.',
            input_schema={
                'type': 'object',
                'properties': {
                    'test_path': {
                        'type': 'string',
                        'description': 'Optional specific test file to run (e.g. "tests/test_engine.py")',
                    },
                    'verbose': {'type': 'boolean', 'description': 'Show verbose test output (default: true)'},
                },
            },
            handler=run_tests,
        )
    )

    # --- run_module ---
    def run_module(path: str = None, code: str = None):
        """Run a Python module or arbitrary code snippet in the sandbox."""
        if code:
            args = ['-c', code]
        elif path:
            args = [_validate_path(path)]
        else:
            return json.dumps({'error': 'Provide either path or code'})

        result = sandbox.run_python(args, cwd=sandbox_path, timeout=SUBPROCESS_TIMEOUT)
        if result.timed_out:
            return json.dumps({'error': f'Execution timed out after {SUBPROCESS_TIMEOUT}s'})
        return json.dumps({'returncode': result.returncode, 'output': result.output})

    registry.register(
        ToolDef(
            name='run_module',
            description='Execute a Python file or code snippet in the sandbox. Use this to test individual modules or run quick checks.',
            input_schema={
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'Python file to execute'},
                    'code': {'type': 'string', 'description': 'Python code snippet to execute (alternative to path)'},
                },
            },
            handler=run_module,
        )
    )

    # --- mark_phase ---
    def mark_phase(phase: str, detail: str = ''):
        """Signal a phase transition. Used by the agent to track progress."""
        from ..models import CodeProject

        db = get_db()
        proj = db.query(CodeProject).filter_by(id=project_id).first()
        if proj:
            proj.status = phase
            if phase == 'testing':
                proj.iteration = (proj.iteration or 0) + 1
            log_entry = {
                'phase': phase,
                'detail': detail,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            if proj.agent_log is None:
                proj.agent_log = []
            proj.agent_log = proj.agent_log + [log_entry]
            db.commit()
        return json.dumps({'status': 'ok', 'phase': phase})

    registry.register(
        ToolDef(
            name='mark_phase',
            description='Signal the current phase of development. Call this when transitioning between phases.',
            input_schema={
                'type': 'object',
                'properties': {
                    'phase': {
                        'type': 'string',
                        'enum': ['planning', 'coding', 'testing', 'fixing', 'complete'],
                        'description': 'Current development phase',
                    },
                    'detail': {'type': 'string', 'description': 'Brief description of what is happening'},
                },
                'required': ['phase'],
            },
            handler=mark_phase,
        )
    )

    return registry
