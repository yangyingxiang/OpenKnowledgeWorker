"""Context builder — assembles LLM context from typed sources under a token budget.

Each query mode defines which sources are included and their priority/budget allocation.
"""

from dataclasses import dataclass, field
from enum import Enum

from ..extensions import get_db
from ..models import (
    ChatMessage,
    ChatSession,
    CodeFile,
    CodeProject,
    Document,
    DocumentChunk,
    KnowledgeItem,
    PddVersion,
    Question,
)


class QueryMode(Enum):
    RESEARCH = 'research'
    SME_CHAT = 'sme_chat'
    CODING = 'coding'
    TEST_EXECUTE = 'test_execute'


# Rough char-to-token ratio (conservative for English text)
CHARS_PER_TOKEN = 3.5
DEFAULT_BUDGET_TOKENS = 80_000


@dataclass
class ContextBlock:
    """A single block of context with metadata."""

    source_type: str  # 'document_chunk', 'pdd', 'knowledge', 'question', 'chat', 'code', 'test'
    source_id: str  # ID of the source record
    heading: str  # Display label
    content: str  # The text content
    priority: int = 5  # 1=highest, 10=lowest
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.content)


@dataclass
class AssembledContext:
    """The final assembled context with metadata."""

    blocks: list[ContextBlock] = field(default_factory=list)
    total_chars: int = 0
    total_tokens_est: int = 0
    truncated: bool = False
    source_counts: dict = field(default_factory=dict)

    def to_prompt_text(self) -> str:
        """Render as a single text string for LLM consumption."""
        sections = []
        for block in self.blocks:
            sections.append(f"[{block.source_type.upper()}: {block.heading}]\n{block.content}")
        return '\n\n---\n\n'.join(sections)

    def to_metadata(self) -> dict:
        """Return metadata about what was included."""
        return {
            'total_chars': self.total_chars,
            'total_tokens_est': self.total_tokens_est,
            'truncated': self.truncated,
            'block_count': len(self.blocks),
            'source_counts': self.source_counts,
        }


# Budget allocation per query mode (as fraction of total budget)
MODE_BUDGETS = {
    QueryMode.RESEARCH: {
        'document_chunk': 0.60,
        'pdd': 0.15,
        'knowledge': 0.10,
        'question': 0.10,
        'chat': 0.05,
    },
    QueryMode.SME_CHAT: {
        'chat': 0.35,
        'pdd': 0.25,
        'question': 0.15,
        'knowledge': 0.15,
        'document_chunk': 0.10,
    },
    QueryMode.CODING: {
        'pdd': 0.50,
        'code': 0.20,
        'knowledge': 0.10,
        'document_chunk': 0.10,
        'question': 0.10,
    },
    QueryMode.TEST_EXECUTE: {
        'pdd': 0.30,
        'code': 0.30,
        'test': 0.20,
        'knowledge': 0.10,
        'document_chunk': 0.10,
    },
}


class ContextBuilder:
    """Builds context for LLM queries from typed sources.

    Usage:
        ctx = ContextBuilder(process_id, QueryMode.RESEARCH)
        result = ctx.build(budget_tokens=80000)
    """

    def __init__(
        self,
        process_id: str,
        mode: QueryMode,
        budget_tokens: int = DEFAULT_BUDGET_TOKENS,
        session_id: str | None = None,
        pdd_sections: list[str] | None = None,
    ):
        self.process_id = process_id
        self.mode = mode
        self.budget_tokens = budget_tokens
        self.budget_chars = int(budget_tokens * CHARS_PER_TOKEN)
        self.session_id = session_id
        self.pdd_sections = pdd_sections

    def build(self) -> AssembledContext:
        """Assemble context under the token budget."""
        allocations = MODE_BUDGETS.get(self.mode, MODE_BUDGETS[QueryMode.RESEARCH])
        all_blocks: list[ContextBlock] = []

        # Gather blocks from each source type
        for source_type, fraction in allocations.items():
            source_budget = int(self.budget_chars * fraction)
            blocks = self._gather_source(source_type, source_budget)
            all_blocks.extend(blocks)

        # Sort by priority, then trim to budget
        all_blocks.sort(key=lambda b: b.priority)

        result = AssembledContext()
        remaining = self.budget_chars

        for block in all_blocks:
            if block.char_count <= remaining:
                result.blocks.append(block)
                remaining -= block.char_count
                result.source_counts[block.source_type] = result.source_counts.get(block.source_type, 0) + 1
            else:
                # Try to include a truncated version
                if remaining > 200:
                    truncated = ContextBlock(
                        source_type=block.source_type,
                        source_id=block.source_id,
                        heading=block.heading + ' (truncated)',
                        content=block.content[: remaining - 20] + '\n... [truncated]',
                        priority=block.priority,
                    )
                    result.blocks.append(truncated)
                    result.source_counts[block.source_type] = result.source_counts.get(block.source_type, 0) + 1
                result.truncated = True
                break

        result.total_chars = sum(b.char_count for b in result.blocks)
        result.total_tokens_est = int(result.total_chars / CHARS_PER_TOKEN)
        return result

    def _gather_source(self, source_type: str, budget_chars: int) -> list[ContextBlock]:
        """Gather and rank blocks from a single source type."""
        if source_type == 'document_chunk':
            return self._gather_document_chunks(budget_chars)
        elif source_type == 'pdd':
            return self._gather_pdd(budget_chars)
        elif source_type == 'knowledge':
            return self._gather_knowledge(budget_chars)
        elif source_type == 'question':
            return self._gather_questions(budget_chars)
        elif source_type == 'chat':
            return self._gather_chat(budget_chars)
        elif source_type == 'code':
            return self._gather_code(budget_chars)
        elif source_type == 'test':
            return self._gather_tests(budget_chars)
        return []

    def _gather_document_chunks(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        chunks = (
            db.query(DocumentChunk)
            .join(Document)
            .filter(Document.process_id == self.process_id, Document.status == 'ready')
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        blocks = []
        used = 0
        for chunk in chunks:
            if used + chunk.char_length > budget:
                continue
            doc = chunk.document
            blocks.append(
                ContextBlock(
                    source_type='document_chunk',
                    source_id=str(chunk.id),
                    heading=f'{doc.original_filename} > {chunk.heading_path or f"chunk {chunk.chunk_index}"}',
                    content=chunk.content,
                    priority=3,
                )
            )
            used += chunk.char_length
        return blocks

    def _gather_pdd(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        pdd = (
            db.query(PddVersion)
            .filter_by(process_id=self.process_id)
            .order_by(PddVersion.version_number.desc())
            .first()
        )
        if not pdd or not pdd.content:
            return []

        content = pdd.content

        # If specific sections requested, extract them
        if self.pdd_sections:
            selected = []
            for section_name in self.pdd_sections:
                extracted = self._extract_pdd_section(content, section_name)
                if extracted:
                    selected.append(extracted)
            if selected:
                content = '\n\n'.join(selected)

        if len(content) > budget:
            content = content[: budget - 20] + '\n... [PDD truncated]'

        return [
            ContextBlock(
                source_type='pdd',
                source_id=str(pdd.id),
                heading=f'PDD v{pdd.version_number}',
                content=content,
                priority=1,  # PDD is highest priority
            )
        ]

    def _gather_knowledge(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        items = (
            db.query(KnowledgeItem)
            .filter_by(process_id=self.process_id)
            .order_by(KnowledgeItem.created_at.desc())
            .all()
        )
        blocks = []
        used = 0
        # Confirmed items first
        sorted_items = sorted(items, key=lambda k: 0 if k.confidence == 'CONFIRMED' else 1)
        for item in sorted_items:
            text = f"[{item.confidence}] {item.section}: {item.content}"
            if used + len(text) > budget:
                continue
            blocks.append(
                ContextBlock(
                    source_type='knowledge',
                    source_id=str(item.id),
                    heading=f'{item.section} ({item.confidence})',
                    content=text,
                    priority=4,
                )
            )
            used += len(text)
        return blocks

    def _gather_questions(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        questions = (
            db.query(Question)
            .filter_by(process_id=self.process_id)
            .order_by(Question.priority.desc(), Question.created_at.desc())
            .all()
        )
        blocks = []
        used = 0
        # Open questions first
        sorted_q = sorted(questions, key=lambda q: (0 if q.status == 'OPEN' else 1, -q.priority))
        for q in sorted_q:
            text = f"[{q.status}] Q{q.display_id}: {q.text}"
            if q.answer:
                text += f"\n  Answer: {q.answer}"
            if used + len(text) > budget:
                continue
            blocks.append(
                ContextBlock(
                    source_type='question',
                    source_id=str(q.id),
                    heading=f'Q{q.display_id} ({q.status})',
                    content=text,
                    priority=5 if q.status == 'OPEN' else 7,
                )
            )
            used += len(text)
        return blocks

    def _gather_chat(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        if self.session_id:
            sessions = [db.query(ChatSession).filter_by(id=self.session_id, process_id=self.process_id).first()]
            sessions = [s for s in sessions if s]
        else:
            sessions = (
                db.query(ChatSession)
                .filter_by(process_id=self.process_id)
                .order_by(ChatSession.updated_at.desc())
                .limit(3)
                .all()
            )

        blocks = []
        used = 0
        for session in sessions:
            messages = (
                db.query(ChatMessage)
                .filter_by(session_id=session.id)
                .order_by(ChatMessage.created_at.desc())
                .limit(20)
                .all()
            )
            messages.reverse()
            lines = []
            for msg in messages:
                role = msg.role.upper()
                lines.append(f"{role}: {msg.content[:500]}")
            text = '\n'.join(lines)
            if used + len(text) > budget:
                text = text[: budget - used - 20] + '\n... [chat truncated]'
            if not text.strip():
                continue
            blocks.append(
                ContextBlock(
                    source_type='chat',
                    source_id=str(session.id),
                    heading=f'Chat with {session.expert_name} ({session.expert_role})',
                    content=text,
                    priority=6,
                )
            )
            used += len(text)
        return blocks

    def _gather_code(self, budget: int) -> list[ContextBlock]:
        db = get_db()
        project = (
            db.query(CodeProject).filter_by(process_id=self.process_id).order_by(CodeProject.created_at.desc()).first()
        )
        if not project:
            return []

        files = db.query(CodeFile).filter_by(project_id=project.id).order_by(CodeFile.file_path).all()
        blocks = []
        used = 0
        for f in files:
            # For coding context, include file summaries with truncated content
            content = f.content
            if len(content) > 2000:
                content = content[:2000] + '\n... [file truncated]'
            if used + len(content) > budget:
                continue
            blocks.append(
                ContextBlock(
                    source_type='code',
                    source_id=str(f.id),
                    heading=f'{f.file_path} (v{f.version})',
                    content=content,
                    priority=4,
                )
            )
            used += len(content)
        return blocks

    def _gather_tests(self, budget: int) -> list[ContextBlock]:
        from ..models import TestCase

        db = get_db()
        cases = (
            db.query(TestCase).filter_by(process_id=self.process_id, is_active=True).order_by(TestCase.created_at).all()
        )
        blocks = []
        used = 0
        for tc in cases:
            import json

            text = f"Test: {tc.test_name}\n"
            if tc.description:
                text += f"Description: {tc.description}\n"
            text += f"Input: {json.dumps(tc.input_data)[:500]}\n"
            text += f"Expected: {json.dumps(tc.expected_assertions)[:500]}"
            if used + len(text) > budget:
                continue
            blocks.append(
                ContextBlock(
                    source_type='test',
                    source_id=str(tc.id),
                    heading=tc.test_name,
                    content=text,
                    priority=5,
                )
            )
            used += len(text)
        return blocks

    @staticmethod
    def _extract_pdd_section(content: str, section_name: str) -> str | None:
        """Extract a named section from PDD content."""
        lines = content.split('\n')
        in_section = False
        section_lines = []
        section_level = 0

        for line in lines:
            if section_name.lower() in line.lower() and line.startswith('#'):
                in_section = True
                section_level = len(line) - len(line.lstrip('#'))
                section_lines.append(line)
            elif in_section:
                if line.startswith('#'):
                    current_level = len(line) - len(line.lstrip('#'))
                    if current_level <= section_level:
                        break
                section_lines.append(line)

        return '\n'.join(section_lines) if section_lines else None
