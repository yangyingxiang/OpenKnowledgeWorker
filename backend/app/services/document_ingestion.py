"""Document text extraction and chunking for PDF, HTML, and Markdown files."""

import os
import re

# Chunk size limits
TARGET_CHUNK_CHARS = 1500
MAX_CHUNK_CHARS = 3000
MIN_CHUNK_CHARS = 100


def extract_text(file_path, mime_type):
    """Extract text content from a document file.

    Returns (full_text, page_count) tuple.
    """
    if mime_type == 'application/pdf':
        return _extract_pdf(file_path)
    elif mime_type in ('text/html', 'application/xhtml+xml'):
        return _extract_html(file_path)
    elif mime_type in ('text/markdown', 'text/plain'):
        return _extract_markdown(file_path)
    else:
        return None


def extract_chunks(full_text, mime_type, page_count=None):
    """Split extracted text into structured chunks.

    Returns list of dicts with keys:
        content, chunk_index, char_offset, char_length,
        page_number, heading_path, chunk_type
    """
    if not full_text:
        return []

    if mime_type == 'application/pdf' and page_count:
        return _chunk_pdf_text(full_text, page_count)
    else:
        return _chunk_structured_text(full_text)


# ── Extraction ──────────────────────────────────────────


def _extract_pdf(file_path):
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return '\n\n'.join(pages), len(reader.pages)
    except Exception as e:
        return f"[PDF extraction error: {e}]", 0


def _extract_html(file_path):
    try:
        from bs4 import BeautifulSoup

        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        return soup.get_text(separator='\n'), None
    except Exception as e:
        return f"[HTML extraction error: {e}]", None


def _extract_markdown(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, None
    except Exception as e:
        return f"[Markdown extraction error: {e}]", None


# ── Chunking ────────────────────────────────────────────

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)
_SECTION_BREAK_RE = re.compile(r'\n\s*\n')


def _chunk_structured_text(text):
    """Chunk markdown/plain text by headings and paragraph breaks."""
    chunks = []
    current_headings = []
    sections = _split_by_headings(text)

    offset = 0
    for section in sections:
        heading, body, level = section['heading'], section['body'], section['level']

        if heading and level is not None:
            # Update heading stack
            while len(current_headings) > 0 and current_headings[-1][1] >= level:
                current_headings.pop()
            current_headings.append((heading, level))

        heading_path = ' > '.join(h[0] for h in current_headings) if current_headings else None
        full_section = (f"{'#' * level} {heading}\n{body}" if heading else body).strip()

        if not full_section:
            continue

        # If section is small enough, keep as one chunk
        if len(full_section) <= MAX_CHUNK_CHARS:
            chunks.append(
                {
                    'content': full_section,
                    'chunk_index': len(chunks),
                    'char_offset': offset,
                    'char_length': len(full_section),
                    'page_number': None,
                    'heading_path': heading_path,
                    'chunk_type': 'heading' if heading and not body.strip() else 'body',
                }
            )
        else:
            # Split large section into paragraph-based sub-chunks
            for sub in _split_paragraphs(full_section, heading_path):
                sub['chunk_index'] = len(chunks)
                sub['char_offset'] = offset + sub['char_offset']
                chunks.append(sub)

        offset += len(full_section) + 1  # +1 for the join separator

    return chunks


def _split_by_headings(text):
    """Split text into sections by markdown headings."""
    sections = []
    lines = text.split('\n')
    current_heading = None
    current_level = None
    current_body_lines = []

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            # Flush previous section
            if current_heading is not None or current_body_lines:
                sections.append(
                    {
                        'heading': current_heading,
                        'body': '\n'.join(current_body_lines),
                        'level': current_level,
                    }
                )
            current_heading = m.group(2).strip()
            current_level = len(m.group(1))
            current_body_lines = []
        else:
            current_body_lines.append(line)

    # Flush last section
    if current_heading is not None or current_body_lines:
        sections.append(
            {
                'heading': current_heading,
                'body': '\n'.join(current_body_lines),
                'level': current_level,
            }
        )

    return sections


def _split_paragraphs(text, heading_path):
    """Split a large section into paragraph-based sub-chunks."""
    paragraphs = _SECTION_BREAK_RE.split(text)
    sub_chunks = []
    current_chunk = ''
    chunk_offset = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 > TARGET_CHUNK_CHARS and current_chunk:
            sub_chunks.append(
                {
                    'content': current_chunk.strip(),
                    'chunk_index': 0,  # Will be reassigned
                    'char_offset': chunk_offset,
                    'char_length': len(current_chunk.strip()),
                    'page_number': None,
                    'heading_path': heading_path,
                    'chunk_type': 'body',
                }
            )
            chunk_offset += len(current_chunk)
            current_chunk = ''

        current_chunk += para + '\n\n'

    if current_chunk.strip():
        sub_chunks.append(
            {
                'content': current_chunk.strip(),
                'chunk_index': 0,
                'char_offset': chunk_offset,
                'char_length': len(current_chunk.strip()),
                'page_number': None,
                'heading_path': heading_path,
                'chunk_type': 'body',
            }
        )

    return sub_chunks


def _chunk_pdf_text(text, page_count):
    """Chunk PDF text using page boundaries (pages separated by \\n\\n)."""
    # PDF pages were joined with \n\n in _extract_pdf
    raw_pages = text.split('\n\n')
    chunks = []
    offset = 0

    for page_idx, page_text in enumerate(raw_pages):
        page_text = page_text.strip()
        if not page_text:
            offset += 2  # skip the \n\n separator
            continue

        page_num = page_idx + 1

        if len(page_text) <= MAX_CHUNK_CHARS:
            chunks.append(
                {
                    'content': page_text,
                    'chunk_index': len(chunks),
                    'char_offset': offset,
                    'char_length': len(page_text),
                    'page_number': page_num if page_num <= page_count else None,
                    'heading_path': None,
                    'chunk_type': 'body',
                }
            )
        else:
            # Large page — split by paragraphs
            for sub in _split_paragraphs(page_text, None):
                sub['chunk_index'] = len(chunks)
                sub['char_offset'] = offset + sub['char_offset']
                sub['page_number'] = page_num if page_num <= page_count else None
                chunks.append(sub)

        offset += len(page_text) + 2

    # Try to detect heading paths from the text within PDF pages
    _infer_pdf_headings(chunks)

    return chunks


def _infer_pdf_headings(chunks):
    """Best-effort: detect heading-like patterns in PDF chunks."""
    heading_re = re.compile(r'^([A-Z][A-Za-z0-9 ,&\-/]+(?:\n|$))', re.MULTILINE)
    current_heading = None

    for chunk in chunks:
        m = heading_re.search(chunk['content'][:200])
        if m:
            candidate = m.group(1).strip()
            if len(candidate) < 120 and not candidate.endswith('.'):
                current_heading = candidate
        if current_heading:
            chunk['heading_path'] = current_heading


def guess_mime(filename):
    ext = os.path.splitext(filename)[1].lower()
    return {
        '.pdf': 'application/pdf',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.md': 'text/markdown',
        '.txt': 'text/markdown',
    }.get(ext, 'text/plain')


def ingest_document(process_id, filename, save):
    """Store a source document, extract its text, and chunk it.

    ``save(path)`` writes the file's bytes to ``path`` (e.g. ``FileStorage.save`` for
    uploads, or a copy for local files). Returns the committed ``Document``; on
    extraction failure its status is ``error``.
    """
    from ..extensions import get_db
    from ..models import Document, DocumentChunk
    from ..utils.file_storage import new_storage_path

    db = get_db()
    mime_type = guess_mime(filename)
    storage_path = new_storage_path(process_id, filename)
    save(storage_path)

    doc = Document(
        process_id=process_id,
        original_filename=filename,
        mime_type=mime_type,
        file_size_bytes=os.path.getsize(storage_path),
        storage_path=storage_path,
        status='processing',
    )
    db.add(doc)
    db.commit()

    try:
        result = extract_text(storage_path, mime_type)
        text, page_count = result if isinstance(result, tuple) else (result, None)
        doc.extracted_text = text
        doc.page_count = page_count
        doc.status = 'ready'
        for cd in extract_chunks(text, mime_type, page_count):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=cd['chunk_index'],
                    content=cd['content'],
                    content_hash=DocumentChunk.hash_content(cd['content']),
                    char_offset=cd['char_offset'],
                    char_length=cd['char_length'],
                    page_number=cd.get('page_number'),
                    heading_path=cd.get('heading_path'),
                    chunk_type=cd.get('chunk_type', 'body'),
                )
            )
    except Exception as e:
        doc.status = 'error'
        doc.extracted_text = f'[Extraction error: {e}]'

    db.commit()
    return doc
