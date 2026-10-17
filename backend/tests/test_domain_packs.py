import json
import os

import pytest

from app.models import CodeProject, Document, KnowledgeItem, PddVersion, Process, Question, TestCase
from app.services.domain_packs import (
    DEFAULT_PACKS_DIR,
    DomainPackError,
    find_pack,
    install_pack,
    list_packs,
    load_pack,
    parse_knowledge_markdown,
    parse_questions_markdown,
)

MORTGAGE = 'mortgage-income-verification'


def test_bundled_packs_are_valid():
    packs = list_packs(DEFAULT_PACKS_DIR)
    assert MORTGAGE in [p['id'] for p in packs]
    for p in packs:
        pack = load_pack(find_pack(DEFAULT_PACKS_DIR, p['id']))
        assert pack['id'] == os.path.basename(pack['_dir']), 'pack id must match its folder name'


def test_find_pack_rejects_path_traversal():
    with pytest.raises(DomainPackError):
        find_pack(DEFAULT_PACKS_DIR, '../backend')


def test_parse_knowledge_markdown():
    items = parse_knowledge_markdown(
        '## Decision Rules\n- Rule one\n  [source: document/x, section 1]\n- [TENTATIVE] Maybe two\n'
    )
    assert items == [
        {
            'section': 'Decision Rules',
            'content': 'Rule one',
            'confidence': 'CONFIRMED',
            'source_detail': 'document/x, section 1',
        },
        {'section': 'Decision Rules', 'content': 'Maybe two', 'confidence': 'TENTATIVE', 'source_detail': None},
    ]


def test_parse_questions_markdown():
    questions = parse_questions_markdown(
        '## Q-ABC [OPEN] Priority: 1\n**Question:** What is X?\n**Target:** SME\n**Related PDD:** Step 1.1\n'
    )
    assert questions == [
        {
            'status': 'OPEN',
            'priority': 1,
            'text': 'What is X?',
            'target_roles': ['SME'],
            'related_pdd_section': 'Step 1.1',
        }
    ]


def test_install_mortgage_pack(app, db_session):
    with app.app_context():
        process = install_pack(load_pack(find_pack(DEFAULT_PACKS_DIR, MORTGAGE)))
        pid = process.id
        assert process.metadata_['domain_pack']['output_contract']['summary']['total_annual']
        assert db_session.query(Document).filter_by(process_id=pid, status='ready').count() == 1
        assert db_session.query(TestCase).filter_by(process_id=pid).count() == 5
        assert db_session.query(PddVersion).filter_by(process_id=pid).count() == 1
        assert db_session.query(KnowledgeItem).filter_by(process_id=pid).count() > 10
        assert db_session.query(Question).filter_by(process_id=pid).count() == 3
        project = db_session.query(CodeProject).filter_by(process_id=pid).one()
        assert project.status == 'complete'


def test_install_without_sample_outputs(app, db_session):
    with app.app_context():
        process = install_pack(load_pack(find_pack(DEFAULT_PACKS_DIR, MORTGAGE)), with_sample_outputs=False)
        assert db_session.query(PddVersion).filter_by(process_id=process.id).count() == 0
        assert db_session.query(CodeProject).filter_by(process_id=process.id).count() == 0


def test_domain_pack_api(client, db_session):
    assert MORTGAGE in [p['id'] for p in client.get('/api/domain-packs').get_json()]
    resp = client.post(f'/api/domain-packs/{MORTGAGE}/install', json={'with_sample_outputs': False})
    assert resp.status_code == 201
    assert db_session.query(Process).filter_by(id=resp.get_json()['id']).count() == 1
    assert client.post('/api/domain-packs/missing/install').status_code == 404


def test_pack_manifest_is_json_schema_valid():
    jsonschema = pytest.importorskip('jsonschema')
    with open(os.path.join(DEFAULT_PACKS_DIR, 'domain-pack.schema.json')) as f:
        schema = json.load(f)
    with open(os.path.join(DEFAULT_PACKS_DIR, MORTGAGE, 'pack.json')) as f:
        jsonschema.validate(json.load(f), schema)
