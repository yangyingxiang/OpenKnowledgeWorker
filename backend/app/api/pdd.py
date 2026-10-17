import difflib

from flask import Blueprint, current_app, jsonify, request

from ..agent.chat_agent import run_agent_streaming
from ..agent.prompts import RESEARCH_SYSTEM_PROMPT
from ..agent.tool_registry import create_process_tools
from ..context.builder import ContextBuilder, QueryMode
from ..extensions import get_db
from ..jobs import runner
from ..models import Document, PddVersion, Provenance

pdd_bp = Blueprint('pdd', __name__)


@pdd_bp.route('/<process_id>/pdd', methods=['GET'])
def get_current_pdd(process_id):
    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    if not pdd:
        return jsonify({'content': '', 'version_number': 0, 'message': 'No PDD yet'})
    return jsonify(pdd.to_dict())


@pdd_bp.route('/<process_id>/pdd/versions', methods=['GET'])
def list_versions(process_id):
    db = get_db()
    versions = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).all()
    return jsonify(
        [
            {
                'id': str(v.id),
                'version_number': v.version_number,
                'change_summary': v.change_summary,
                'change_source': v.change_source,
                'created_at': v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]
    )


@pdd_bp.route('/<process_id>/pdd/versions/<version_id>', methods=['GET'])
def get_version(process_id, version_id):
    db = get_db()
    pdd = db.query(PddVersion).filter_by(id=version_id, process_id=process_id).first()
    if not pdd:
        return jsonify({'error': 'Version not found'}), 404
    return jsonify(pdd.to_dict())


@pdd_bp.route('/<process_id>/pdd/diff/<v1_id>/<v2_id>', methods=['GET'])
def diff_versions(process_id, v1_id, v2_id):
    db = get_db()
    v1 = db.query(PddVersion).filter_by(id=v1_id, process_id=process_id).first()
    v2 = db.query(PddVersion).filter_by(id=v2_id, process_id=process_id).first()
    if not v1 or not v2:
        return jsonify({'error': 'Version not found'}), 404

    diff = list(
        difflib.unified_diff(
            v1.content.splitlines(keepends=True),
            v2.content.splitlines(keepends=True),
            fromfile=f'v{v1.version_number}',
            tofile=f'v{v2.version_number}',
        )
    )
    return jsonify(
        {
            'diff': ''.join(diff),
            'v1': v1.version_number,
            'v2': v2.version_number,
        }
    )


@pdd_bp.route('/<process_id>/pdd', methods=['PUT'])
def manual_edit_pdd(process_id):
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'content is required'}), 400

    db = get_db()
    current = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()

    new_version = PddVersion(
        process_id=process_id,
        version_number=(current.version_number + 1) if current else 1,
        content=data['content'],
        change_summary=data.get('change_summary', 'Manual edit'),
        change_source='manual_edit',
        parent_version_id=current.id if current else None,
    )
    db.add(new_version)
    db.commit()
    return jsonify(new_version.to_dict())


@pdd_bp.route('/<process_id>/pdd/research', methods=['POST'])
def research_process(process_id):
    """Trigger autonomous research to generate/update the PDD from documents."""
    db = get_db()
    docs = db.query(Document).filter_by(process_id=process_id, status='ready').all()
    if not docs:
        return jsonify({'error': 'No documents uploaded yet'}), 400

    # Build research context using context builder (budgeted)
    ctx_builder = ContextBuilder(process_id, QueryMode.RESEARCH, budget_tokens=80_000)
    assembled = ctx_builder.build()
    context_text = assembled.to_prompt_text()
    meta = assembled.to_metadata()

    tool_registry = create_process_tools(process_id)

    messages = [
        {
            'role': 'user',
            'content': (
                "Please analyze the following documents and create a comprehensive PDD.\n\n"
                "Available documents:\n"
                + '\n'.join([f"- {d.original_filename} (ID: {d.id})" for d in docs])
                + f"\n\nContext ({meta['block_count']} blocks, ~{meta['total_tokens_est']} tokens):\n"
                + context_text
            ),
        }
    ]

    doc_count = len(docs)

    def work():
        yield {'type': 'status', 'status': 'started', 'message': f'Analyzing {doc_count} documents...'}
        yield from run_agent_streaming(messages, RESEARCH_SYSTEM_PROMPT, tool_registry)

    job_id = runner.submit(current_app._get_current_object(), process_id=process_id, job_type='research', work=work)
    return runner.stream(job_id)


@pdd_bp.route('/<process_id>/pdd/context', methods=['GET'])
def get_research_context(process_id):
    """Preview the assembled context for a research query (debugging)."""
    mode_str = request.args.get('mode', 'research')
    budget = int(request.args.get('budget', 80000))
    mode = QueryMode(mode_str) if mode_str in [m.value for m in QueryMode] else QueryMode.RESEARCH

    ctx_builder = ContextBuilder(process_id, mode, budget_tokens=budget)
    assembled = ctx_builder.build()
    return jsonify(
        {
            **assembled.to_metadata(),
            'blocks': [
                {
                    'source_type': b.source_type,
                    'heading': b.heading,
                    'priority': b.priority,
                    'char_count': b.char_count,
                    'preview': b.content[:200],
                }
                for b in assembled.blocks
            ],
        }
    )


@pdd_bp.route('/<process_id>/pdd/provenance', methods=['GET'])
def get_provenance(process_id):
    db = get_db()
    current_pdd = (
        db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    )
    if not current_pdd:
        return jsonify([])

    provenance = db.query(Provenance).filter_by(process_id=process_id, pdd_version_id=current_pdd.id).all()
    return jsonify(
        [
            {
                'id': str(p.id),
                'sentence_hash': p.sentence_hash,
                'sentence_text': p.sentence_text,
                'section_path': p.section_path,
                'source_type': p.source_type,
                'source_id': str(p.source_id) if p.source_id else None,
                'source_detail': p.source_detail,
                'actor': p.actor,
            }
            for p in provenance
        ]
    )
