import json
import os
import queue
import tempfile
import threading
import time

from flask import Blueprint, current_app, jsonify, request

from .. import sandbox
from ..agent.domain_context import build_domain_context
from ..agent.prompts import EXECUTE_LLM_PROMPT
from ..extensions import get_db
from ..jobs import runner
from ..llm import StreamEnd, TextDelta, get_llm
from ..models import PddVersion, TestCase, TestRun
from ..models.code_project import CodeFile, CodeProject
from ..services.assertions import evaluate as evaluate_assertions

test_bp = Blueprint('tests', __name__)


@test_bp.route('/<process_id>/tests/cases', methods=['GET'])
def list_test_cases(process_id):
    db = get_db()
    cases = db.query(TestCase).filter_by(process_id=process_id, is_active=True).order_by(TestCase.created_at).all()
    return jsonify([tc.to_dict() for tc in cases])


@test_bp.route('/<process_id>/tests/cases', methods=['POST'])
def create_test_case(process_id):
    data = request.get_json()
    if not data or not data.get('test_name') or not data.get('input_data'):
        return jsonify({'error': 'test_name and input_data are required'}), 400

    db = get_db()
    tc = TestCase(
        process_id=process_id,
        test_name=data['test_name'],
        description=data.get('description'),
        input_data=data['input_data'],
        expected_assertions=data.get('expected_assertions', {}),
        mock_llm_judge=data.get('mock_llm_judge'),
    )
    db.add(tc)
    db.commit()
    return jsonify(tc.to_dict()), 201


@test_bp.route('/<process_id>/tests/cases/<tc_id>', methods=['PUT'])
def update_test_case(process_id, tc_id):
    db = get_db()
    tc = db.query(TestCase).filter_by(id=tc_id, process_id=process_id).first()
    if not tc:
        return jsonify({'error': 'Test case not found'}), 404

    data = request.get_json() or {}
    for field in ['test_name', 'description', 'input_data', 'expected_assertions', 'mock_llm_judge']:
        if field in data:
            setattr(tc, field, data[field])
    db.commit()
    return jsonify(tc.to_dict())


@test_bp.route('/<process_id>/tests/cases/<tc_id>', methods=['DELETE'])
def delete_test_case(process_id, tc_id):
    db = get_db()
    tc = db.query(TestCase).filter_by(id=tc_id, process_id=process_id).first()
    if not tc:
        return jsonify({'error': 'Test case not found'}), 404
    tc.is_active = False
    db.commit()
    return jsonify({'success': True})


@test_bp.route('/<process_id>/tests/cases/bulk', methods=['POST'])
def bulk_upload_tests(process_id):
    """Bulk upload test cases from a CSV or JSONL file."""
    import csv
    import io

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('csv', 'jsonl'):
        return jsonify({'error': 'Unsupported file type. Use .csv or .jsonl'}), 400

    content = file.read().decode('utf-8')
    db = get_db()
    created = []

    try:
        if ext == 'jsonl':
            for line in content.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                input_data = obj.get('input_data', {})
                if isinstance(input_data, str):
                    input_data = json.loads(input_data)
                expected = obj.get('expected_assertions', {})
                if isinstance(expected, str):
                    expected = json.loads(expected)

                tc = TestCase(
                    process_id=process_id,
                    test_name=obj.get('test_name', 'Untitled'),
                    description=obj.get('description'),
                    input_data=input_data,
                    expected_assertions=expected,
                    mock_llm_judge=obj.get('mock_llm_judge'),
                )
                db.add(tc)
                created.append(tc.test_name)

        elif ext == 'csv':
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                input_data = row.get('input_data', '{}')
                try:
                    input_data = json.loads(input_data)
                except (json.JSONDecodeError, TypeError):
                    input_data = {}

                expected = row.get('expected_assertions', '{}')
                try:
                    expected = json.loads(expected)
                except (json.JSONDecodeError, TypeError):
                    expected = {}

                tc = TestCase(
                    process_id=process_id,
                    test_name=row.get('test_name', 'Untitled'),
                    description=row.get('description'),
                    input_data=input_data,
                    expected_assertions=expected,
                )
                db.add(tc)
                created.append(tc.test_name)

        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to parse file: {str(e)}'}), 400

    return jsonify({'created': created, 'count': len(created)}), 201


@test_bp.route('/<process_id>/tests/run', methods=['POST'])
def run_tests(process_id):
    """Run test cases. mode: llm, code, or both. SSE streaming."""
    data = request.get_json() or {}
    mode = data.get('mode', 'llm')
    test_case_ids = data.get('test_case_ids', [])

    db = get_db()
    if test_case_ids:
        cases = (
            db.query(TestCase)
            .filter(
                TestCase.id.in_(test_case_ids),
                TestCase.process_id == process_id,
                TestCase.is_active.is_(True),
            )
            .all()
        )
    else:
        cases = db.query(TestCase).filter_by(process_id=process_id, is_active=True).all()

    if not cases:
        return jsonify({'error': 'No test cases found'}), 400

    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    pdd_content = pdd.content if pdd else None

    code_project = None
    if mode in ('code', 'both'):
        code_project = (
            db.query(CodeProject)
            .filter_by(process_id=process_id, status='complete')
            .order_by(CodeProject.created_at.desc())
            .first()
        )
    domain_context = build_domain_context(process_id) if mode in ('llm', 'both') else ''

    # Capture data before entering generator (avoid detached session)
    code_project_id = str(code_project.id) if code_project else None
    code_sandbox = code_project.sandbox_path if code_project else None
    case_data = [(str(tc.id), tc.test_name, tc.input_data, tc.expected_assertions, tc.mock_llm_judge) for tc in cases]
    app = current_app._get_current_object()

    def work():
        for tc_id, tc_name, tc_input, tc_assertions, tc_mock_judge in case_data:
            run = TestRun(
                process_id=process_id,
                test_case_id=tc_id,
                mode=mode,
                status='running',
            )
            db_inner = get_db()
            db_inner.add(run)
            db_inner.commit()
            run_id = str(run.id)

            yield (
                {
                    'type': 'test_start',
                    'test_case_id': tc_id,
                    'test_name': tc_name,
                    'run_id': run_id,
                }
            )

            start = time.time()
            llm_result = None
            code_result = None

            if mode == 'both':
                # Run LLM and Code concurrently — merge events via a queue
                evt_queue = queue.Queue()

                worker_args = (app, evt_queue, tc_id, tc_input)
                t_llm = threading.Thread(
                    target=_llm_worker, args=worker_args + (pdd_content, domain_context), daemon=True
                )
                t_code = threading.Thread(
                    target=_code_worker, args=worker_args + (code_project_id, code_sandbox, tc_mock_judge), daemon=True
                )
                t_llm.start()
                t_code.start()

                done_count = 0
                while done_count < 2:
                    try:
                        evt = evt_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if '_done' in evt:
                        done_count += 1
                        continue
                    # Capture final results
                    if evt.get('type') == 'llm_result':
                        llm_result = evt.get('result')
                    elif evt.get('type') == 'code_result':
                        code_result = evt.get('result')
                    yield (evt)

                t_llm.join(timeout=2)
                t_code.join(timeout=2)

            else:
                # Sequential: single engine mode
                if mode == 'llm' and pdd_content:
                    try:
                        for event in _execute_llm_streaming(pdd_content, tc_input, tc_id, domain_context):
                            yield (event)
                            if event.get('type') == 'llm_result':
                                llm_result = event.get('result')
                    except Exception as e:
                        llm_result = {'error': str(e)}
                        yield ({'type': 'error', 'test_case_id': tc_id, 'error': str(e)})

                elif mode == 'code':
                    try:
                        code_result = _run_generated_code(code_project_id, code_sandbox, tc_input, tc_mock_judge)

                        if code_result and 'trace_steps' in code_result:
                            for step in code_result['trace_steps']:
                                yield ({'type': 'code_step', 'test_case_id': tc_id, 'step': step})
                        yield ({'type': 'code_result', 'test_case_id': tc_id, 'result': code_result})
                    except Exception as e:
                        code_result = {'error': str(e)}
                        yield ({'type': 'error', 'test_case_id': tc_id, 'error': f'Code engine: {e}'})

            duration_ms = int((time.time() - start) * 1000)

            # Check assertions (LLM result takes precedence in 'both' mode)
            result_to_check = llm_result or code_result or {}
            assertion_results = evaluate_assertions(result_to_check.get('summary') or {}, tc_assertions or {})
            passed = sum(1 for a in assertion_results if a['passed'])
            total = len(assertion_results)

            # Update run record
            run_obj = db_inner.query(TestRun).filter_by(id=run_id).first()
            if run_obj:
                run_obj.status = 'completed'
                run_obj.llm_result = llm_result
                run_obj.code_result = code_result
                run_obj.assertions_passed = passed
                run_obj.assertions_total = total
                run_obj.duration_ms = duration_ms
                db_inner.commit()

            yield (
                {
                    'type': 'test_complete',
                    'test_case_id': tc_id,
                    'run_id': run_id,
                    'assertions_passed': passed,
                    'assertions_total': total,
                    'assertions': assertion_results,
                    'duration_ms': duration_ms,
                }
            )

        yield ({'type': 'all_done'})

    job_id = runner.submit(app, process_id=process_id, job_type='test_run', work=work)
    return runner.stream(job_id)


@test_bp.route('/<process_id>/tests/runs', methods=['GET'])
def list_runs(process_id):
    db = get_db()
    runs = db.query(TestRun).filter_by(process_id=process_id).order_by(TestRun.created_at.desc()).limit(50).all()
    return jsonify([r.to_dict() for r in runs])


@test_bp.route('/<process_id>/tests/runs/<run_id>', methods=['GET'])
def get_run(process_id, run_id):
    db = get_db()
    run = db.query(TestRun).filter_by(id=run_id, process_id=process_id).first()
    if not run:
        return jsonify({'error': 'Run not found'}), 404
    return jsonify(run.to_dict())


def _llm_worker(app, evt_queue, tc_id, tc_input, pdd_content, domain_context):
    """Thread target for 'both' mode: stream the LLM execution into ``evt_queue``."""
    with app.app_context():
        try:
            for evt in _execute_llm_streaming(pdd_content, tc_input, tc_id, domain_context):
                evt_queue.put(evt)
        except Exception as e:
            evt_queue.put({'type': 'error', 'test_case_id': tc_id, 'error': str(e)})
        evt_queue.put({'_done': 'llm'})


def _code_worker(app, evt_queue, tc_id, tc_input, code_project_id, code_sandbox, mock_judge=None):
    """Thread target for 'both' mode: run the generated engine and queue its trace."""
    with app.app_context():
        try:
            result = _run_generated_code(code_project_id, code_sandbox, tc_input, mock_judge)
            for step in result.get('trace_steps') or []:
                evt_queue.put({'type': 'code_step', 'test_case_id': tc_id, 'step': step})
            evt_queue.put({'type': 'code_result', 'test_case_id': tc_id, 'result': result})
        except Exception as e:
            evt_queue.put({'type': 'error', 'test_case_id': tc_id, 'error': f'Code engine: {e}'})
        evt_queue.put({'_done': 'code'})


def _execute_llm_streaming(pdd_content, input_data, test_case_id, domain_context=''):
    """Execute a test case by having the LLM follow the PDD.

    Yields llm_delta events with raw text chunks, then a final llm_result.
    """
    system = EXECUTE_LLM_PROMPT + ('\n\n' + domain_context if domain_context else '')
    messages = [
        {
            'role': 'user',
            'content': (
                f"Execute the following PDD against the case data.\n\n"
                f"PDD:\n{pdd_content}\n\n"
                f"Case data:\n{json.dumps(input_data, indent=2)}\n\n"
                f"Walk through each step and provide results as JSON with:\n"
                f'{{"trace_steps": [...], "summary": {{...}}}}'
            ),
        }
    ]

    collected_text = ''
    for event in get_llm().stream(system=system, messages=messages, max_tokens=32000):
        if isinstance(event, TextDelta):
            collected_text += event.text
            yield {'type': 'llm_delta', 'test_case_id': test_case_id, 'text': event.text}
        elif isinstance(event, StreamEnd):
            collected_text = event.response.text or collected_text

    result = _parse_llm_json(collected_text)
    result['_raw_text'] = collected_text
    yield {'type': 'llm_result', 'test_case_id': test_case_id, 'result': result}


def _parse_llm_json(text: str) -> dict:
    """Parse the full LLM response into a result dict."""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return {'raw_response': text, 'summary': {}, 'trace_steps': []}


def _run_generated_code(project_id, sandbox_path, input_data, mock_judge=None):
    """Run the latest completed code project against one case, in a sandboxed subprocess."""
    if not project_id:
        return {
            'error': 'No generated code found. Generate code first on the Code page.',
            'trace_steps': [],
            'summary': {},
        }

    work_dir = sandbox_path
    if not work_dir or not os.path.exists(work_dir):
        # Sandbox folder is gone (e.g. server restarted): rebuild it from the stored files.
        work_dir = tempfile.mkdtemp(prefix='okw_exec_')
        files = (
            get_db()
            .query(CodeFile)
            .filter(CodeFile.project_id == project_id, CodeFile.file_type.in_(['source', 'init']))
            .all()
        )
        for cf in files:
            fpath = os.path.join(work_dir, cf.file_path)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, 'w') as f:
                f.write(cf.content)

    result = sandbox.run_engine(
        work_dir, input_data, timeout=current_app.config.get('SANDBOX_TIMEOUT', 120), mock_llm_judge=mock_judge
    )
    return _normalize_trace(result)


def _normalize_trace(result: dict) -> dict:
    """Ensure every trace step has decision/result_value, whatever the generated engine emitted."""
    for step in result.get('trace_steps', []) or []:
        if step.get('decision') is None:
            raw = step.get('result') or step.get('result_value')
            step.setdefault('result_value', raw)
            step.setdefault('result_label', str(raw) if raw is not None else None)
            step['decision'] = 'INFO'
        else:
            step.setdefault('result_value', step.get('result'))
    return result
