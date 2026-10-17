"""Evidence graph API endpoints."""

from flask import Blueprint, jsonify, request

from ..extensions import get_db
from ..models import PddVersion
from ..models.evidence import ChangeEvent, EvidenceLink, EvidenceSpan, PddStatement
from ..services.evidence import (
    auto_link_evidence,
    build_evidence_from_chunks,
    extract_pdd_statements,
    get_impact_of_document_removal,
)

evidence_bp = Blueprint('evidence', __name__)


@evidence_bp.route('/<process_id>/evidence/build', methods=['POST'])
def build_evidence_graph(process_id):
    """Build the full evidence graph: extract statements, create spans, auto-link."""
    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    if not pdd:
        return jsonify({'error': 'No PDD exists'}), 400

    stmt_count = extract_pdd_statements(process_id, str(pdd.id))
    span_count = build_evidence_from_chunks(process_id)
    link_count = auto_link_evidence(process_id, str(pdd.id))

    return jsonify(
        {
            'pdd_version': pdd.version_number,
            'statements_extracted': stmt_count,
            'evidence_spans_created': span_count,
            'links_created': link_count,
        }
    )


@evidence_bp.route('/<process_id>/evidence/statements', methods=['GET'])
def list_statements(process_id):
    """List PDD statements with their evidence link counts."""
    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
    if not pdd:
        return jsonify([])

    statements = db.query(PddStatement).filter_by(pdd_version_id=pdd.id).order_by(PddStatement.statement_index).all()

    section_filter = request.args.get('section')
    if section_filter:
        statements = [s for s in statements if section_filter.lower() in s.section_path.lower()]

    return jsonify([s.to_dict() for s in statements])


@evidence_bp.route('/<process_id>/evidence/statements/<statement_id>/evidence', methods=['GET'])
def get_statement_evidence(process_id, statement_id):
    """Get all evidence spans linked to a specific PDD statement."""
    db = get_db()
    links = db.query(EvidenceLink).filter_by(pdd_statement_id=statement_id).all()
    result = []
    for link in links:
        span = db.query(EvidenceSpan).filter_by(id=link.evidence_span_id).first()
        if span:
            result.append(
                {
                    **span.to_dict(),
                    'link_type': link.link_type,
                    'link_confidence': link.confidence,
                }
            )
    return jsonify(result)


@evidence_bp.route('/<process_id>/evidence/impact/<document_id>', methods=['GET'])
def document_impact(process_id, document_id):
    """Show impact of removing a document: which PDD statements would be affected."""
    result = get_impact_of_document_removal(process_id, document_id)
    return jsonify(result)


@evidence_bp.route('/<process_id>/evidence/changes', methods=['GET'])
def list_changes(process_id):
    """List change events for a process."""
    db = get_db()
    limit = int(request.args.get('limit', 50))
    events = (
        db.query(ChangeEvent)
        .filter_by(process_id=process_id)
        .order_by(ChangeEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([e.to_dict() for e in events])


@evidence_bp.route('/<process_id>/evidence/stats', methods=['GET'])
def evidence_stats(process_id):
    """Get evidence graph statistics."""
    db = get_db()
    pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()

    stmt_count = 0
    linked_stmt_count = 0
    if pdd:
        statements = db.query(PddStatement).filter_by(pdd_version_id=pdd.id).all()
        stmt_count = len(statements)
        linked_stmt_count = sum(1 for s in statements if s.evidence_links)

    span_count = db.query(EvidenceSpan).filter_by(process_id=process_id).count()
    link_count = db.query(EvidenceLink).join(PddStatement).filter(PddStatement.process_id == process_id).count()

    return jsonify(
        {
            'pdd_version': pdd.version_number if pdd else 0,
            'total_statements': stmt_count,
            'linked_statements': linked_stmt_count,
            'unlinked_statements': stmt_count - linked_stmt_count,
            'evidence_spans': span_count,
            'evidence_links': link_count,
            'coverage_pct': round(linked_stmt_count / stmt_count * 100, 1) if stmt_count > 0 else 0,
        }
    )
