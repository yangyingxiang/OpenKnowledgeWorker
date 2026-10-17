"""Domain packs: self-contained example processes under ``examples/<pack>/pack.json``.

A pack bundles everything needed to start a process in a new domain: metadata, source
documents (local files and links to third-party documents), golden test cases, the
output contract the engine must satisfy, agent guidance, and optional sample outputs
(PDD, knowledge, open questions) so people can explore without an LLM API key.

See ``examples/README.md`` for the format and ``examples/domain-pack.schema.json``.
"""

import json
import os
import re
import shutil

from ..extensions import get_db
from ..models import CodeFile, CodeProject, KnowledgeItem, PddVersion, Process, Question, TestCase
from .document_ingestion import ingest_document

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_PACKS_DIR = os.path.join(REPO_DIR, 'examples')
REQUIRED_FIELDS = ('id', 'name', 'domain', 'description')


class DomainPackError(ValueError):
    pass


def packs_dir(config=None) -> str:
    return (config or {}).get('DOMAIN_PACKS_DIR') or DEFAULT_PACKS_DIR


def list_packs(base_dir: str) -> list:
    """Summaries of every valid pack in ``base_dir``."""
    packs = []
    if not os.path.isdir(base_dir):
        return packs
    for name in sorted(os.listdir(base_dir)):
        if os.path.isfile(os.path.join(base_dir, name, 'pack.json')):
            try:
                pack = load_pack(os.path.join(base_dir, name))
            except DomainPackError:
                continue
            packs.append({k: pack.get(k) for k in ('id', 'name', 'domain', 'description')})
    return packs


def find_pack(base_dir: str, pack_id: str) -> str:
    """Directory of the pack with this id (``pack_id`` must be a plain folder name)."""
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', pack_id or ''):
        raise DomainPackError(f'Invalid pack id: {pack_id!r}')
    path = os.path.join(base_dir, pack_id)
    if not os.path.isfile(os.path.join(path, 'pack.json')):
        raise DomainPackError(f'Domain pack not found: {pack_id}')
    return path


def load_pack(pack_dir: str) -> dict:
    """Read and validate ``pack.json``; file references are resolved against ``pack_dir``."""
    try:
        with open(os.path.join(pack_dir, 'pack.json')) as f:
            pack = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DomainPackError(f'Cannot read {pack_dir}/pack.json: {e}') from e
    missing = [k for k in REQUIRED_FIELDS if not pack.get(k)]
    if missing:
        raise DomainPackError(f'{pack_dir}/pack.json is missing: {", ".join(missing)}')
    pack['_dir'] = pack_dir
    return pack


def _pack_file(pack: dict, rel_path: str) -> str:
    path = os.path.normpath(os.path.join(pack['_dir'], rel_path))
    if not path.startswith(os.path.normpath(pack['_dir']) + os.sep):
        raise DomainPackError(f'Path escapes the pack directory: {rel_path}')
    if not os.path.isfile(path):
        raise DomainPackError(f'File not found in pack: {rel_path}')
    return path


def _read_json_or_text(pack: dict, value):
    """Fields such as ``sample_input``/``agent_guidance`` may be inline or a file path."""
    if not isinstance(value, str) or not value:
        return value
    if value.endswith('.json'):
        with open(_pack_file(pack, value)) as f:
            return json.load(f)
    if value.endswith(('.md', '.txt')):
        with open(_pack_file(pack, value)) as f:
            return f.read()
    return value


def install_pack(pack: dict, with_sample_outputs: bool = True, name: str = None) -> Process:
    """Create a process from a pack: metadata, local sources, test cases, sample outputs."""
    db = get_db()
    process = Process(
        name=name or pack['name'],
        domain=pack['domain'],
        description=pack['description'],
        key_inputs=pack.get('key_inputs') or [],
        key_outputs=pack.get('key_outputs') or [],
        metadata_={
            'domain_pack': {
                'id': pack['id'],
                'sample_input': _read_json_or_text(pack, pack.get('sample_input')),
                'output_contract': pack.get('output_contract') or {},
                'agent_guidance': _read_json_or_text(pack, pack.get('agent_guidance')),
                'external_sources': [s for s in pack.get('sources', []) if s.get('url')],
            }
        },
    )
    db.add(process)
    db.commit()

    for source in pack.get('sources', []):
        if source.get('path'):
            src = _pack_file(pack, source['path'])
            ingest_document(process.id, os.path.basename(src), lambda dest, src=src: shutil.copyfile(src, dest))

    if pack.get('test_cases'):
        _install_test_cases(process.id, _pack_file(pack, pack['test_cases']))

    if with_sample_outputs:
        _install_sample_outputs(process.id, pack)
        if pack.get('reference_code'):
            _install_reference_code(process.id, pack)

    db.commit()
    return process


def _install_test_cases(process_id, path):
    db = get_db()
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            case = json.loads(line)
            db.add(
                TestCase(
                    process_id=process_id,
                    test_name=case.get('test_name', 'Untitled'),
                    description=case.get('description'),
                    input_data=case.get('input_data') or {},
                    expected_assertions=case.get('expected_assertions') or {},
                    mock_llm_judge=case.get('mock_llm_judge'),
                )
            )
    db.commit()


def _install_sample_outputs(process_id, pack):
    outputs = pack.get('sample_outputs') or {}
    db = get_db()
    if outputs.get('pdd'):
        with open(_pack_file(pack, outputs['pdd'])) as f:
            db.add(
                PddVersion(
                    process_id=process_id,
                    version_number=1,
                    content=f.read(),
                    change_summary='Sample PDD from the domain pack',
                    change_source='research',
                )
            )
    if outputs.get('knowledge'):
        with open(_pack_file(pack, outputs['knowledge'])) as f:
            for item in parse_knowledge_markdown(f.read()):
                db.add(KnowledgeItem(process_id=process_id, source_type='document', **item))
    if outputs.get('questions'):
        with open(_pack_file(pack, outputs['questions'])) as f:
            for i, q in enumerate(parse_questions_markdown(f.read()), start=1):
                db.add(Question(process_id=process_id, display_id=f'Q-{i:04d}', **q))
    db.commit()


def _install_reference_code(process_id, pack):
    """Install a hand-written engine package as a completed code project.

    ``reference_code`` points at a folder containing an ``engine/`` package with
    ``engine/engine.py:run_engine`` (the same contract generated code follows).
    """
    root = os.path.normpath(os.path.join(pack['_dir'], pack['reference_code']))
    engine_dir = os.path.join(root, 'engine')
    if not root.startswith(os.path.normpath(pack['_dir']) + os.sep) or not os.path.isdir(engine_dir):
        raise DomainPackError(f"reference_code must contain an engine/ package: {pack['reference_code']}")

    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    project = CodeProject(
        process_id=process_id,
        pdd_version_id=pdd.id if pdd else None,
        status='complete',
        agent_log=[{'phase': 'complete', 'detail': 'Reference implementation from the domain pack'}],
    )
    db.add(project)
    db.commit()
    for dirpath, dirnames, filenames in os.walk(engine_dir):
        dirnames[:] = sorted(d for d in dirnames if d != '__pycache__')
        for filename in sorted(filenames):
            if not filename.endswith('.py'):
                continue
            full = os.path.join(dirpath, filename)
            with open(full) as f:
                content = f.read()
            db.add(
                CodeFile(
                    project_id=project.id,
                    file_path=os.path.relpath(full, root).replace(os.sep, '/'),
                    content=content,
                    file_type='init' if filename == '__init__.py' else 'source',
                )
            )
    db.commit()


_SOURCE_RE = re.compile(r'\[source:\s*(.*?)\]\s*$')


def parse_knowledge_markdown(text: str) -> list:
    """Parse ``## Section`` headings with ``- item`` bullets (and indented ``[source: ...]``)."""
    items, section = [], None
    for line in text.splitlines():
        if line.startswith('## '):
            section = line[3:].strip()
        elif line.startswith('- ') and section:
            content = line[2:].strip()
            confidence = 'CONFIRMED'
            if content.startswith('[TENTATIVE]'):
                confidence, content = 'TENTATIVE', content[len('[TENTATIVE]') :].strip()
            items.append(
                {'section': section[:100], 'content': content, 'confidence': confidence, 'source_detail': None}
            )
        elif items and line.strip().startswith('[source:'):
            match = _SOURCE_RE.search(line.strip())
            if match:
                items[-1]['source_detail'] = match.group(1)
    return items


_QUESTION_HEADER_RE = re.compile(r'^## \S+ \[(\w+)\] Priority: (\d+)')


def parse_questions_markdown(text: str) -> list:
    """Parse the ``## Q-... [OPEN] Priority: N`` / ``**Question:**`` format."""
    questions, current = [], None
    for line in text.splitlines():
        header = _QUESTION_HEADER_RE.match(line)
        if header:
            current = {'status': header.group(1).upper(), 'priority': int(header.group(2)), 'text': ''}
            questions.append(current)
        elif current is not None and line.startswith('**Question:**'):
            current['text'] = line[len('**Question:**') :].strip()
        elif current is not None and line.startswith('**Related PDD:**'):
            current['related_pdd_section'] = line[len('**Related PDD:**') :].strip()[:255]
        elif current is not None and line.startswith('**Target:**'):
            current['target_roles'] = [r.strip() for r in line[len('**Target:**') :].split(',') if r.strip()]
    return [q for q in questions if q['text']]
