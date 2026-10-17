"""Evidence graph service — builds and queries the provenance/evidence graph."""

import hashlib
import re

from ..extensions import get_db
from ..models import Document, DocumentChunk, PddVersion
from ..models.evidence import ChangeEvent, EvidenceLink, EvidenceSpan, PddStatement


def hash_statement(text: str) -> str:
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()


def extract_pdd_statements(process_id: str, pdd_version_id: str):
    """Parse a PDD version into individual statements and store them.

    Returns the count of statements created.
    """
    db = get_db()
    pdd = db.query(PddVersion).filter_by(id=pdd_version_id).first()
    if not pdd or not pdd.content:
        return 0

    # Clear old statements for this version
    db.query(PddStatement).filter_by(pdd_version_id=pdd_version_id).delete()

    lines = pdd.content.split('\n')
    current_section = ''
    statement_index = 0
    statements = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Track section headings
        if stripped.startswith('#'):
            heading_match = re.match(r'^(#{1,6})\s+(.+)', stripped)
            if heading_match:
                current_section = heading_match.group(2).strip()
            continue

        # Skip table formatting lines
        if stripped.startswith('|') and set(stripped.replace('|', '').strip()) <= {'-', ' '}:
            continue

        # Each non-empty, non-heading line is a statement
        stmt = PddStatement(
            process_id=process_id,
            pdd_version_id=pdd_version_id,
            section_path=current_section,
            statement_text=stripped,
            statement_hash=hash_statement(stripped),
            statement_index=statement_index,
        )
        statements.append(stmt)
        statement_index += 1

    db.bulk_save_objects(statements)
    db.commit()
    return len(statements)


def build_evidence_from_chunks(process_id: str):
    """Create evidence spans from all document chunks for a process.

    Returns count of evidence spans created.
    """
    db = get_db()
    chunks = (
        db.query(DocumentChunk)
        .join(Document)
        .filter(Document.process_id == process_id, Document.status == 'ready')
        .all()
    )

    # Clear existing document-sourced evidence
    db.query(EvidenceSpan).filter_by(process_id=process_id, source_type='document').delete()

    spans = []
    for chunk in chunks:
        span = EvidenceSpan(
            process_id=process_id,
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            source_type='document',
            source_id=chunk.document_id,
            span_text=chunk.content,
            char_offset=chunk.char_offset,
            char_length=chunk.char_length,
            heading_path=chunk.heading_path,
            page_number=chunk.page_number,
        )
        spans.append(span)

    db.bulk_save_objects(spans)
    db.commit()
    return len(spans)


def auto_link_evidence(process_id: str, pdd_version_id: str):
    """Auto-link PDD statements to evidence spans using text similarity.

    Simple approach: for each PDD statement, find evidence spans that share
    significant keyword overlap.

    Returns count of links created.
    """
    db = get_db()
    statements = db.query(PddStatement).filter_by(pdd_version_id=pdd_version_id).all()
    evidence_spans = db.query(EvidenceSpan).filter_by(process_id=process_id).all()

    if not statements or not evidence_spans:
        return 0

    # Clear existing auto-links for this version
    stmt_ids = [s.id for s in statements]
    db.query(EvidenceLink).filter(
        EvidenceLink.pdd_statement_id.in_(stmt_ids), EvidenceLink.confidence == 'auto'
    ).delete(synchronize_session=False)

    # Build keyword index for evidence spans
    span_keywords = {}
    for span in evidence_spans:
        keywords = _extract_keywords(span.span_text)
        span_keywords[span.id] = keywords

    links_created = 0
    for stmt in statements:
        stmt_kw = _extract_keywords(stmt.statement_text)
        if not stmt_kw:
            continue

        best_matches = []
        for span in evidence_spans:
            span_kw = span_keywords.get(span.id, set())
            overlap = len(stmt_kw & span_kw)
            if overlap >= 3:  # Require at least 3 keyword overlap
                score = overlap / max(len(stmt_kw), 1)
                best_matches.append((span, score))

        # Link top matches (max 3 per statement)
        best_matches.sort(key=lambda x: -x[1])
        for span, _score in best_matches[:3]:
            link = EvidenceLink(
                pdd_statement_id=stmt.id,
                evidence_span_id=span.id,
                link_type='supports',
                confidence='auto',
            )
            db.add(link)
            links_created += 1

    db.commit()
    return links_created


def get_impact_of_document_removal(process_id: str, document_id: str) -> dict:
    """Given a document, find all PDD statements that rely on it.

    Returns dict with impacted statements and their evidence links.
    """
    db = get_db()
    # Find evidence spans from this document
    spans = (
        db.query(EvidenceSpan)
        .filter_by(
            process_id=process_id,
            document_id=document_id,
        )
        .all()
    )

    if not spans:
        return {'impacted_statements': [], 'span_count': 0}

    span_ids = [s.id for s in spans]
    links = db.query(EvidenceLink).filter(EvidenceLink.evidence_span_id.in_(span_ids)).all()

    stmt_ids = {link.pdd_statement_id for link in links}
    statements = db.query(PddStatement).filter(PddStatement.id.in_(stmt_ids)).all()

    return {
        'span_count': len(spans),
        'link_count': len(links),
        'impacted_statements': [s.to_dict() for s in statements],
    }


def record_change(process_id: str, event_type: str, target_type: str, target_id: str = None, detail: dict = None):
    """Record a change event for audit trail."""
    db = get_db()
    event = ChangeEvent(
        process_id=process_id,
        event_type=event_type,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )
    db.add(event)
    db.commit()
    return event


# ── Internal helpers ���───────────────────────────────────

_STOP_WORDS = {
    'the',
    'a',
    'an',
    'is',
    'are',
    'was',
    'were',
    'be',
    'been',
    'being',
    'have',
    'has',
    'had',
    'do',
    'does',
    'did',
    'will',
    'would',
    'could',
    'should',
    'may',
    'might',
    'shall',
    'can',
    'must',
    'need',
    'to',
    'of',
    'in',
    'for',
    'on',
    'with',
    'at',
    'by',
    'from',
    'as',
    'into',
    'through',
    'during',
    'before',
    'after',
    'above',
    'below',
    'between',
    'out',
    'off',
    'over',
    'under',
    'again',
    'further',
    'then',
    'once',
    'and',
    'but',
    'or',
    'nor',
    'not',
    'so',
    'if',
    'than',
    'that',
    'this',
    'these',
    'those',
    'each',
    'all',
    'both',
    'such',
    'no',
    'only',
    'own',
    'same',
    'too',
    'very',
    'just',
    'also',
    'its',
    'it',
    'they',
    'them',
    'their',
    'he',
    'she',
    'we',
    'you',
    'who',
    'which',
    'what',
    'when',
    'where',
    'how',
}


def _extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text."""
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return {w for w in words if w not in _STOP_WORDS}
