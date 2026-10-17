"""Integration tests for the tool registry (create_process_tools)."""

import json

from app.agent.tool_registry import create_process_tools
from app.models import KnowledgeItem, Question, TestCase

# ── Registration tests ─────────────────────────────────────────────────


def test_base_tools_registered(app, db_session, process_id, session_id):
    """All base PDD / knowledge / question / document tools are registered."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        expected = {
            'read_pdd',
            'propose_pdd_edit',
            'edit_pdd_text',
            'read_knowledge',
            'write_to_knowledge',
            'create_question',
            'resolve_question',
            'view_open_questions',
            'read_document',
            'list_documents',
            'read_document_chunks',
            'validate_pdd',
        }
        registered = set(registry.tools.keys())
        missing = expected - registered
        assert not missing, f'Missing base tools: {missing}'


def test_code_tools_registered(app, db_session, process_id, session_id):
    """Code-related tools are registered."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        expected = {'list_code_files', 'read_code_file', 'update_code_file', 'navigate_to_file'}
        registered = set(registry.tools.keys())
        missing = expected - registered
        assert not missing, f'Missing code tools: {missing}'


def test_test_tools_registered(app, db_session, process_id, session_id):
    """Test-case tools are registered."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        expected = {
            'list_test_cases',
            'read_test_case',
            'create_test_case',
            'update_test_case',
            'delete_test_case',
            'bulk_create_tests',
        }
        registered = set(registry.tools.keys())
        missing = expected - registered
        assert not missing, f'Missing test tools: {missing}'


def test_all_tools_always_registered(app, db_session, process_id, session_id):
    """ALL tools (base + code + test) are unconditionally registered."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        all_expected = {
            # base
            'read_pdd',
            'propose_pdd_edit',
            'edit_pdd_text',
            'read_knowledge',
            'write_to_knowledge',
            'create_question',
            'resolve_question',
            'view_open_questions',
            'read_document',
            'list_documents',
            'read_document_chunks',
            'validate_pdd',
            # code
            'list_code_files',
            'read_code_file',
            'update_code_file',
            'navigate_to_file',
            # test
            'list_test_cases',
            'read_test_case',
            'create_test_case',
            'update_test_case',
            'delete_test_case',
            'bulk_create_tests',
        }
        registered = set(registry.tools.keys())
        missing = all_expected - registered
        assert not missing, f'Missing tools: {missing}'
        assert len(registered) >= len(all_expected)


# ── Functional tool tests ──────────────────────────────────────────────


def test_write_to_knowledge(app, db_session, process_id, session_id):
    """write_to_knowledge creates a KnowledgeItem row."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(
            registry.execute(
                'write_to_knowledge',
                {
                    'section': 'Decision Rules',
                    'content': 'If income < 50k, flag for review.',
                    'confidence': 'CONFIRMED',
                },
            )
        )
        assert result['success'] is True
        item = db_session.query(KnowledgeItem).filter_by(process_id=process_id).first()
        assert item is not None
        assert item.section == 'Decision Rules'
        assert item.confidence == 'CONFIRMED'


def test_create_question(app, db_session, process_id, session_id):
    """create_question creates a Question row with a display_id."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(
            registry.execute(
                'create_question',
                {
                    'text': 'What is the minimum income threshold?',
                    'priority': 1,
                },
            )
        )
        assert result['success'] is True
        assert result['display_id'] == 'Q-0001'
        q = db_session.query(Question).filter_by(process_id=process_id).first()
        assert q is not None
        assert q.status == 'OPEN'


def test_resolve_question(app, db_session, process_id, session_id):
    """resolve_question changes a question's status to ANSWERED."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        # Create first
        registry.execute('create_question', {'text': 'Some question?'})
        # Resolve
        result = json.loads(
            registry.execute(
                'resolve_question',
                {
                    'display_id': 'Q-0001',
                    'answer': 'The answer is 42.',
                },
            )
        )
        assert result['success'] is True
        q = db_session.query(Question).filter_by(process_id=process_id).first()
        assert q.status == 'ANSWERED'
        assert q.answer == 'The answer is 42.'


def test_create_test_case(app, db_session, process_id, session_id):
    """create_test_case creates a TestCase row."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(
            registry.execute(
                'create_test_case',
                {
                    'name': 'happy_path',
                    'input_data': {'borrower': 'Alice', 'income': 100000},
                    'description': 'Basic happy path test',
                    'expected_assertions': [{'field': 'total_annual', 'op': 'eq', 'value': 100000}],
                },
            )
        )
        assert result['success'] is True
        assert result['test_name'] == 'happy_path'
        tc = db_session.query(TestCase).filter_by(process_id=process_id).first()
        assert tc is not None
        assert tc.test_name == 'happy_path'
        assert tc.is_active is True


def test_update_test_case(app, db_session, process_id, session_id):
    """update_test_case modifies an existing test case."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        registry.execute(
            'create_test_case',
            {
                'name': 'update_me',
                'input_data': {'x': 1},
            },
        )
        result = json.loads(
            registry.execute(
                'update_test_case',
                {
                    'test_name_or_id': 'update_me',
                    'description': 'Updated description',
                    'input_data': {'x': 2},
                },
            )
        )
        assert result['success'] is True
        tc = db_session.query(TestCase).filter_by(process_id=process_id, test_name='update_me').first()
        assert tc.description == 'Updated description'


def test_delete_test_case(app, db_session, process_id, session_id):
    """delete_test_case soft-deletes by setting is_active=False."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        registry.execute(
            'create_test_case',
            {
                'name': 'delete_me',
                'input_data': {'x': 1},
            },
        )
        result = json.loads(
            registry.execute(
                'delete_test_case',
                {
                    'test_name_or_id': 'delete_me',
                },
            )
        )
        assert result['success'] is True
        tc = db_session.query(TestCase).filter_by(process_id=process_id, test_name='delete_me').first()
        assert tc.is_active is False


def test_bulk_create_tests(app, db_session, process_id, session_id):
    """bulk_create_tests creates multiple TestCase rows at once."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(
            registry.execute(
                'bulk_create_tests',
                {
                    'tests': [
                        {'name': 'bulk_1', 'input_data': {'a': 1}},
                        {'name': 'bulk_2', 'input_data': {'b': 2}},
                        {'name': 'bulk_3', 'input_data': {'c': 3}},
                    ],
                },
            )
        )
        assert result['success'] is True
        assert result['count'] == 3
        count = db_session.query(TestCase).filter_by(process_id=process_id, is_active=True).count()
        assert count == 3


def test_navigate_to_file(app, db_session, process_id, session_id):
    """navigate_to_file returns the file_path and line info."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(
            registry.execute(
                'navigate_to_file',
                {
                    'file_path': 'engine/main.py',
                    'line_start': 10,
                    'line_end': 20,
                },
            )
        )
        assert result['file_path'] == 'engine/main.py'
        assert result['line_start'] == 10
        assert result['line_end'] == 20


def test_list_code_files_no_project(app, db_session, process_id, session_id):
    """list_code_files returns error when no code project exists."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(registry.execute('list_code_files', {}))
        assert 'error' in result
        assert 'No code project' in result['error']


def test_validate_pdd_no_content(app, db_session, process_id, session_id):
    """validate_pdd returns error when no PDD exists."""
    with app.app_context():
        registry = create_process_tools(process_id, session_id=session_id)
        result = json.loads(registry.execute('validate_pdd', {}))
        assert result['valid'] is False
        assert len(result['errors']) > 0
