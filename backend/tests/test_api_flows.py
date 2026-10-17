"""End-to-end API flows, with a scripted LLM and the bundled mortgage domain pack."""

import io
import json

from app.jobs import runner
from tests.fakes import text_response, tool_response


def _sse_events(resp):
    return [json.loads(line[6:]) for line in resp.get_data(as_text=True).splitlines() if line.startswith('data: ')]


def test_process_crud(client, db_session):
    created = client.post('/api/processes', json={'name': 'Invoice Matching', 'domain': 'Accounts Payable'})
    assert created.status_code == 201
    pid = created.get_json()['id']
    assert client.get(f'/api/processes/{pid}').get_json()['name'] == 'Invoice Matching'
    client.put(f'/api/processes/{pid}', json={'description': 'Three-way match'})
    assert client.get(f'/api/processes/{pid}').get_json()['description'] == 'Three-way match'
    assert client.delete(f'/api/processes/{pid}').status_code in (200, 204)


def test_document_upload_is_chunked(client, db_session, process_id):
    data = {
        'file': (io.BytesIO(b'# Policy\n\n## Approval\n\nInvoices over $10,000 need two approvers.\n'), 'policy.md')
    }
    resp = client.post(f'/api/processes/{process_id}/documents', data=data, content_type='multipart/form-data')
    assert resp.status_code == 201
    doc = resp.get_json()
    assert doc['status'] == 'ready'
    chunks = client.get(f"/api/processes/{process_id}/documents/{doc['id']}/chunks").get_json()
    assert any('two approvers' in c['content'] for c in chunks)


def test_golden_tests_pass_in_code_mode(client, db_session):
    """The pack's reference engine runs in the sandbox and passes every golden test."""
    pid = client.post('/api/domain-packs/mortgage-income-verification/install').get_json()['id']
    events = _sse_events(client.post(f'/api/processes/{pid}/tests/run', json={'mode': 'code'}))
    assert events[0]['type'] == 'job'
    completed = [e for e in events if e['type'] == 'test_complete']
    assert len(completed) == 5
    assert all(e['assertions_passed'] == e['assertions_total'] > 0 for e in completed), completed
    runner.wait(events[0]['job_id'])


def test_research_runs_as_a_resumable_job(client, db_session, process_id, fake_llm):
    data = {'file': (io.BytesIO(b'# Policy\n\nAll invoices need a PO number.\n'), 'policy.md')}
    client.post(f'/api/processes/{process_id}/documents', data=data, content_type='multipart/form-data')
    fake_llm.queue(
        tool_response('write_to_knowledge', {'section': 'Decision Rules', 'content': 'Invoices need a PO number'}),
        text_response('Research complete'),
    )
    events = _sse_events(client.post(f'/api/processes/{process_id}/pdd/research'))
    job_id = events[0]['job_id']
    assert [e['type'] for e in events][-1] == 'done'
    assert 'Invoices need a PO number' in json.dumps(client.get(f'/api/processes/{process_id}/knowledge').get_json())

    resumed = client.get(f'/api/processes/{process_id}/jobs/{job_id}/events?after=1')
    assert [e['type'] for e in _sse_events(resumed)] == [e['type'] for e in events[2:]]
    assert client.get(f'/api/processes/{process_id}/jobs/{job_id}').get_json()['status'] == 'completed'
