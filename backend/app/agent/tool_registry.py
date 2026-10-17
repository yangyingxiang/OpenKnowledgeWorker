"""Tool registry for agent tool-calling loops."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable

from ..extensions import get_db
from ..models import (
    CodeFile,
    CodeProject,
    Document,
    DocumentChunk,
    KnowledgeItem,
    PddVersion,
    Provenance,
    Question,
    TestCase,
)
from ..models.code_project import CodeUnit


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict
    handler: Callable


class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool_def: ToolDef):
        self.tools[tool_def.name] = tool_def

    def get_tool_schemas(self):
        return [
            {
                'name': t.name,
                'description': t.description,
                'input_schema': t.input_schema,
            }
            for t in self.tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> str:
        if name not in self.tools:
            return json.dumps({'error': f'Unknown tool: {name}'})
        try:
            result = self.tools[name].handler(**arguments)
            return result if isinstance(result, str) else json.dumps(result)
        except Exception as e:
            return json.dumps({'error': str(e)})


def create_process_tools(process_id, session_id=None):
    """Create a ToolRegistry with all tools for a given process.

    Registers PDD/knowledge/question tools plus code and test tools so the
    agent can interact with any page the user is on.
    """
    registry = ToolRegistry()

    def read_pdd(section=None):
        db = get_db()
        pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        if not pdd:
            return json.dumps({'content': '', 'message': 'No PDD exists yet'})
        content = pdd.content
        if section:
            lines = content.split('\n')
            in_section = False
            section_lines = []
            for line in lines:
                if section.lower() in line.lower() and line.startswith('#'):
                    in_section = True
                elif in_section and line.startswith('#') and len(line) - len(line.lstrip('#')) <= 2:
                    break
                if in_section:
                    section_lines.append(line)
            content = '\n'.join(section_lines) if section_lines else f'Section "{section}" not found'
        return json.dumps({'content': content, 'version': pdd.version_number})

    registry.register(
        ToolDef(
            name='read_pdd',
            description='Read the current PDD content, optionally filtered to a specific section.',
            input_schema={
                'type': 'object',
                'properties': {'section': {'type': 'string', 'description': 'Optional section name to read'}},
            },
            handler=read_pdd,
        )
    )

    def propose_pdd_edit(section_path, new_content, reason, source_detail=''):
        db = get_db()
        current = (
            db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        )

        current_content = current.content if current else ''
        current_version = current.version_number if current else 0

        if section_path == 'full':
            updated_content = new_content
        else:
            updated_content = _merge_section(current_content, section_path, new_content)

        new_version = PddVersion(
            process_id=process_id,
            version_number=current_version + 1,
            content=updated_content,
            change_summary=reason,
            change_source='chat' if session_id else 'research',
            parent_version_id=current.id if current else None,
        )
        db.add(new_version)

        # Record provenance for new sentences
        source_type = 'conversation' if session_id else 'research'
        for sentence in _extract_sentences(new_content):
            prov = Provenance(
                process_id=process_id,
                pdd_version_id=new_version.id,
                sentence_hash=hashlib.sha256(sentence.encode()).hexdigest(),
                sentence_text=sentence,
                section_path=section_path,
                source_type=source_type,
                source_id=session_id,
                source_detail=source_detail or reason,
            )
            db.add(prov)

        db.commit()
        return json.dumps({'success': True, 'version': current_version + 1, 'message': f'PDD updated: {reason}'})

    registry.register(
        ToolDef(
            name='propose_pdd_edit',
            description='Write or update a section of the PDD. The new_content should include its own markdown header. Use section_path values like: "purpose", "key_concepts", "variables", "outputs", "process", "business_rules", "decision_priority", or "full" for complete replacement.',
            input_schema={
                'type': 'object',
                'properties': {
                    'section_path': {
                        'type': 'string',
                        'description': 'Section ID: "purpose", "key_concepts", "variables", "outputs", "process", "business_rules", "decision_priority", or "full"',
                    },
                    'new_content': {
                        'type': 'string',
                        'description': 'The full content for this section, including its markdown header',
                    },
                    'reason': {'type': 'string', 'description': 'Why this change is being made'},
                    'source_detail': {'type': 'string', 'description': 'Specific source detail'},
                },
                'required': ['section_path', 'new_content', 'reason'],
            },
            handler=propose_pdd_edit,
        )
    )

    def edit_pdd_text(find_text, replace_text, reason, source_detail=''):
        """Find and replace specific text in the PDD — fast for targeted edits."""
        db = get_db()
        current = (
            db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        )
        if not current or not current.content:
            return json.dumps({'error': 'No PDD exists yet'})
        if find_text not in current.content:
            return json.dumps({'error': f'Text not found in PDD: "{find_text[:80]}"'})

        updated_content = current.content.replace(find_text, replace_text, 1)
        new_version = PddVersion(
            process_id=process_id,
            version_number=current.version_number + 1,
            content=updated_content,
            change_summary=reason,
            change_source='chat' if session_id else 'research',
            parent_version_id=current.id,
        )
        db.add(new_version)

        source_type = 'conversation' if session_id else 'research'
        for sentence in _extract_sentences(replace_text):
            prov = Provenance(
                process_id=process_id,
                pdd_version_id=new_version.id,
                sentence_hash=hashlib.sha256(sentence.encode()).hexdigest(),
                sentence_text=sentence,
                section_path='find_replace',
                source_type=source_type,
                source_id=session_id,
                source_detail=source_detail or reason,
            )
            db.add(prov)

        db.commit()
        return json.dumps(
            {
                'success': True,
                'version': current.version_number + 1,
                'message': f'PDD updated: {reason}',
                'find_text': find_text,
                'replace_text': replace_text,
            }
        )

    registry.register(
        ToolDef(
            name='edit_pdd_text',
            description='Find and replace specific text in the PDD. PREFERRED for targeted edits '
            '(changing a number, rewording a sentence, fixing a term). Much faster than '
            'propose_pdd_edit because you only specify the text to find and its replacement. '
            'Use propose_pdd_edit only for rewriting entire sections.',
            input_schema={
                'type': 'object',
                'properties': {
                    'find_text': {
                        'type': 'string',
                        'description': 'Exact text to find in the PDD (include enough context to be unique)',
                    },
                    'replace_text': {'type': 'string', 'description': 'Replacement text'},
                    'reason': {'type': 'string', 'description': 'Why this change is being made'},
                    'source_detail': {'type': 'string', 'description': 'Specific source detail'},
                },
                'required': ['find_text', 'replace_text', 'reason'],
            },
            handler=edit_pdd_text,
        )
    )

    def read_knowledge(section=None):
        db = get_db()
        query = db.query(KnowledgeItem).filter_by(process_id=process_id)
        if section:
            query = query.filter_by(section=section)
        items = query.order_by(KnowledgeItem.created_at.desc()).all()
        return json.dumps([i.to_dict() for i in items])

    registry.register(
        ToolDef(
            name='read_knowledge',
            description='Read knowledge items for this process, optionally filtered by section.',
            input_schema={
                'type': 'object',
                'properties': {'section': {'type': 'string', 'description': 'Optional section filter'}},
            },
            handler=read_knowledge,
        )
    )

    def write_to_knowledge(section, content, confidence='TENTATIVE', source_detail=''):
        db = get_db()
        item = KnowledgeItem(
            process_id=process_id,
            section=section,
            content=content,
            confidence=confidence,
            source_type='conversation' if session_id else 'research',
            source_id=str(session_id) if session_id else None,
            source_detail=source_detail,
        )
        db.add(item)
        db.commit()
        return json.dumps({'success': True, 'id': str(item.id)})

    registry.register(
        ToolDef(
            name='write_to_knowledge',
            description='Add a new knowledge item learned from documents or conversation.',
            input_schema={
                'type': 'object',
                'properties': {
                    'section': {
                        'type': 'string',
                        'description': 'Knowledge section (e.g., "Data Sources", "Decision Rules")',
                    },
                    'content': {'type': 'string', 'description': 'The knowledge content'},
                    'confidence': {'type': 'string', 'enum': ['CONFIRMED', 'TENTATIVE']},
                    'source_detail': {'type': 'string'},
                },
                'required': ['section', 'content'],
            },
            handler=write_to_knowledge,
        )
    )

    def create_question(text, priority=2, target_roles=None, related_pdd_section=None):
        db = get_db()
        count = db.query(Question).filter_by(process_id=process_id).count()
        q = Question(
            process_id=process_id,
            display_id=f'Q-{count + 1:04d}',
            text=text,
            priority=priority,
            target_roles=target_roles or ['SME'],
            related_pdd_section=related_pdd_section,
        )
        db.add(q)
        db.commit()
        return json.dumps({'success': True, 'display_id': q.display_id})

    registry.register(
        ToolDef(
            name='create_question',
            description='Create a new open question for domain experts.',
            input_schema={
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'The question text'},
                    'priority': {'type': 'integer', 'description': '1=blocking, 2=important, 3=nice-to-have'},
                    'target_roles': {'type': 'array', 'items': {'type': 'string'}},
                    'related_pdd_section': {'type': 'string'},
                },
                'required': ['text'],
            },
            handler=create_question,
        )
    )

    def resolve_question(display_id, answer):
        db = get_db()
        q = db.query(Question).filter_by(process_id=process_id, display_id=display_id).first()
        if not q:
            return json.dumps({'error': f'Question {display_id} not found'})
        q.status = 'ANSWERED'
        q.answer = answer
        q.answered_by_session_id = session_id
        db.commit()
        return json.dumps({'success': True, 'display_id': display_id})

    registry.register(
        ToolDef(
            name='resolve_question',
            description='Mark a question as answered.',
            input_schema={
                'type': 'object',
                'properties': {
                    'display_id': {'type': 'string', 'description': 'Question ID (e.g., Q-0001)'},
                    'answer': {'type': 'string', 'description': 'The answer'},
                },
                'required': ['display_id', 'answer'],
            },
            handler=resolve_question,
        )
    )

    def view_open_questions():
        db = get_db()
        questions = (
            db.query(Question)
            .filter_by(process_id=process_id, status='OPEN')
            .order_by(Question.priority, Question.created_at)
            .all()
        )
        return json.dumps([q.to_dict() for q in questions])

    registry.register(
        ToolDef(
            name='view_open_questions',
            description='View all open questions for this process.',
            input_schema={'type': 'object', 'properties': {}},
            handler=view_open_questions,
        )
    )

    def read_document(document_id):
        db = get_db()
        doc = db.query(Document).filter_by(id=document_id, process_id=process_id).first()
        if not doc:
            return json.dumps({'error': 'Document not found'})
        return json.dumps(
            {
                'filename': doc.original_filename,
                'content': doc.extracted_text or '[No extracted text available]',
            }
        )

    registry.register(
        ToolDef(
            name='read_document',
            description='Read the extracted text of an uploaded document.',
            input_schema={
                'type': 'object',
                'properties': {
                    'document_id': {'type': 'string', 'description': 'UUID of the document'},
                },
                'required': ['document_id'],
            },
            handler=read_document,
        )
    )

    def list_documents():
        db = get_db()
        docs = db.query(Document).filter_by(process_id=process_id, status='ready').all()
        return json.dumps(
            [
                {
                    'id': str(d.id),
                    'filename': d.original_filename,
                    'chunk_count': d.chunk_count,
                    'page_count': d.page_count,
                }
                for d in docs
            ]
        )

    registry.register(
        ToolDef(
            name='list_documents',
            description='List all available documents for this process with chunk counts.',
            input_schema={'type': 'object', 'properties': {}},
            handler=list_documents,
        )
    )

    def read_document_chunks(document_id, heading_filter=None):
        db = get_db()
        query = (
            db.query(DocumentChunk)
            .join(Document)
            .filter(
                Document.process_id == process_id,
                DocumentChunk.document_id == document_id,
            )
            .order_by(DocumentChunk.chunk_index)
        )
        if heading_filter:
            query = query.filter(DocumentChunk.heading_path.ilike(f'%{heading_filter}%'))
        chunks = query.all()
        if not chunks:
            return json.dumps({'error': 'No chunks found'})
        return json.dumps(
            [
                {
                    'index': c.chunk_index,
                    'heading': c.heading_path,
                    'page': c.page_number,
                    'type': c.chunk_type,
                    'content': c.content,
                }
                for c in chunks
            ]
        )

    registry.register(
        ToolDef(
            name='read_document_chunks',
            description='Read document chunks, optionally filtered by heading path. More structured than read_document.',
            input_schema={
                'type': 'object',
                'properties': {
                    'document_id': {'type': 'string', 'description': 'UUID of the document'},
                    'heading_filter': {
                        'type': 'string',
                        'description': 'Optional heading path substring to filter chunks',
                    },
                },
                'required': ['document_id'],
            },
            handler=read_document_chunks,
        )
    )

    def validate_pdd():
        """Programmatically validate PDD consistency and return errors."""
        db = get_db()
        pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        if not pdd or not pdd.content:
            return json.dumps({'errors': ['No PDD content found'], 'valid': False})

        content = pdd.content
        errors = []

        # Extract Variable Reference entries
        vr_vars = set()
        vr_section = re.search(r'## Variable Reference.*?(?=\n## )', content, re.DOTALL)
        if vr_section:
            for line in vr_section.group().split('\n'):
                m = re.match(r'\|\s*`?(\w+)`?\s*\|', line)
                if m and m.group(1).lower() not in ('variable', '---', ''):
                    vr_vars.add(m.group(1))

        # Extract Output entries
        output_vars = set()
        out_section = re.search(r'## Outputs.*?(?=\n## )', content, re.DOTALL)
        if out_section:
            for line in out_section.group().split('\n'):
                m = re.match(r'\|\s*`?(\w+)`?\s*\|', line)
                if m and m.group(1).lower() not in ('output', '---', ''):
                    output_vars.add(m.group(1))

        # Extract PDL variables
        pdl_blocks = re.findall(r'<!-- pdl\n(.*?)-->', content, re.DOTALL)
        given_vars = set()
        set_vars = set()
        all_pdl_vars = set()
        decides_missing_else = []

        keywords = {
            'given',
            'decide',
            'if',
            'else',
            'set',
            'return',
            'for',
            'each',
            'in',
            'and',
            'or',
            'not',
            'true',
            'false',
            'null',
            'none',
        }

        for block in pdl_blocks:
            tokens = re.findall(r'\b([a-z][a-z0-9_]+)\b', block)
            all_pdl_vars.update(t for t in tokens if t not in keywords)

            has_decide = False
            has_else = False
            decide_name = ''
            for line in block.split('\n'):
                stripped = line.strip()
                if stripped.startswith('GIVEN '):
                    for v in stripped[6:].split(','):
                        v = v.strip()
                        if v:
                            given_vars.add(v)
                m = re.match(r'SET\s+(\w+)\s*[+=]', stripped)
                if m:
                    set_vars.add(m.group(1))
                m = re.match(r'RETURN\s+(.*)', stripped)
                if m:
                    for v in m.group(1).split(','):
                        v = v.strip()
                        if v and re.match(r'^\w+$', v):
                            set_vars.add(v)
                if stripped.startswith('DECIDE'):
                    has_decide = True
                    decide_name = stripped
                if re.match(r'^ELSE\s*:', stripped) or stripped == 'ELSE:' or stripped == 'ELSE':
                    has_else = True

            if has_decide and not has_else:
                decides_missing_else.append(decide_name)

        # Check A: GIVEN vars missing from VR
        missing_from_vr = given_vars - vr_vars - output_vars
        for v in sorted(missing_from_vr):
            errors.append(f'GIVEN variable `{v}` is not in Variable Reference or Outputs')

        # Check B: Dead VR entries
        dead_vr = vr_vars - all_pdl_vars
        for v in sorted(dead_vr):
            errors.append(f'Variable Reference entry `{v}` is never used in any PDL block')

        # Check C: Dual-listed
        dual = vr_vars & output_vars
        for v in sorted(dual):
            errors.append(f'`{v}` appears in both Variable Reference and Outputs — pick one')

        # Check D: Outputs not produced
        for v in sorted(output_vars):
            if v not in set_vars:
                errors.append(f'Output `{v}` is never SET or RETURNed in any PDL block')

        # Check E: DECIDE without ELSE
        for d in decides_missing_else:
            errors.append(f'DECIDE block missing ELSE fallthrough: {d}')

        # Check F: Steps missing description or PDL block
        step_headers = list(re.finditer(r'^####\s+Step\s+([\d.]+):\s*(.+)', content, re.MULTILINE))
        steps_without_pdl = []
        steps_without_desc = []
        for idx, match in enumerate(step_headers):
            step_num = match.group(1)
            step_title = match.group(2).strip()
            start = match.end()
            end = step_headers[idx + 1].start() if idx + 1 < len(step_headers) else len(content)
            block = content[start:end]
            # Check for PDL block
            if '<!-- pdl' not in block:
                steps_without_pdl.append(f'{step_num}: {step_title}')
            # Check for meaningful description (non-whitespace text before PDL or end)
            desc_part = re.split(r'<!-- pdl', block)[0].strip()
            # Remove markdown formatting artifacts
            desc_text = re.sub(r'[#*_`\-|]', '', desc_part).strip()
            if len(desc_text) < 20:
                steps_without_desc.append(f'{step_num}: {step_title}')

        for s in steps_without_pdl:
            errors.append(f'Step {s} is missing a PDL block')
        for s in steps_without_desc:
            errors.append(f'Step {s} is missing a narrative description (< 20 chars)')

        return json.dumps(
            {
                'valid': len(errors) == 0,
                'error_count': len(errors),
                'errors': errors,
                'stats': {
                    'vr_entries': len(vr_vars),
                    'outputs': len(output_vars),
                    'given_vars': len(given_vars),
                    'pdl_blocks': len(pdl_blocks),
                    'steps_total': len(step_headers),
                    'steps_with_pdl': len(step_headers) - len(steps_without_pdl),
                    'steps_with_desc': len(step_headers) - len(steps_without_desc),
                },
            },
            indent=2,
        )

    registry.register(
        ToolDef(
            name='validate_pdd',
            description='Validate PDD consistency: checks that all GIVEN variables exist in Variable Reference, '
            'all VR entries are used in PDL, no variables are dual-listed in VR and Outputs, '
            'all outputs are produced, all DECIDE blocks have ELSE clauses, '
            'and every step has both a narrative description and a PDL block.',
            input_schema={'type': 'object', 'properties': {}},
            handler=validate_pdd,
        )
    )

    # ── Code tools ────────────────────────────────────────────────────

    def _get_latest_project():
        db = get_db()
        return db.query(CodeProject).filter_by(process_id=process_id).order_by(CodeProject.created_at.desc()).first()

    def list_code_files():
        """List all files in the latest code project."""
        project = _get_latest_project()
        if not project:
            return json.dumps({'error': 'No code project exists yet'})
        return json.dumps([f.to_summary() for f in project.files])

    registry.register(
        ToolDef(
            name='list_code_files',
            description='List all files in the latest code project with paths, types, and line counts.',
            input_schema={'type': 'object', 'properties': {}},
            handler=list_code_files,
        )
    )

    def read_code_file(file_path):
        """Read the content of a specific code file. Also returns any
        CodeUnit rows for the file so the agent has function→line-range
        anchors and PDD-section mappings for accurate navigation."""
        project = _get_latest_project()
        if not project:
            return json.dumps({'error': 'No code project exists yet'})
        db = get_db()
        f = db.query(CodeFile).filter_by(project_id=project.id, file_path=file_path).first()
        if not f:
            return json.dumps({'error': f'File not found: {file_path}'})
        units = db.query(CodeUnit).filter_by(project_id=project.id, file_id=f.id).order_by(CodeUnit.start_line).all()
        return json.dumps(
            {
                'file_path': f.file_path,
                'content': f.content,
                'version': f.version,
                'file_type': f.file_type,
                'code_units': [
                    {
                        'function_name': u.function_name,
                        'start_line': u.start_line,
                        'end_line': u.end_line,
                        'pdd_step_id': u.pdd_step_id,
                        'pdd_section': u.pdd_section,
                        'pdd_rule_ids': u.pdd_rule_ids or [],
                    }
                    for u in units
                ],
            }
        )

    registry.register(
        ToolDef(
            name='read_code_file',
            description='Read the full content of a file in the code project.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Relative file path, e.g. engine/main.py'}
                },
                'required': ['file_path'],
            },
            handler=read_code_file,
        )
    )

    def update_code_file(file_path, new_content, reason=''):
        """Update a code file's content."""
        project = _get_latest_project()
        if not project:
            return json.dumps({'error': 'No code project exists yet'})
        db = get_db()
        f = db.query(CodeFile).filter_by(project_id=project.id, file_path=file_path).first()
        if not f:
            return json.dumps({'error': f'File not found: {file_path}'})
        f.content = new_content
        f.version += 1
        db.commit()
        return json.dumps(
            {'success': True, 'file_path': file_path, 'version': f.version, 'line_count': new_content.count('\n') + 1}
        )

    registry.register(
        ToolDef(
            name='update_code_file',
            description='Update the content of a file in the code project. Returns the new version number.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Relative file path to update'},
                    'new_content': {'type': 'string', 'description': 'Complete new file content'},
                    'reason': {'type': 'string', 'description': 'Brief reason for the change'},
                },
                'required': ['file_path', 'new_content'],
            },
            handler=update_code_file,
        )
    )

    def navigate_to_file(file_path, line_start=None, line_end=None):
        """Signal the frontend to navigate to a specific file and line range."""
        return json.dumps({'file_path': file_path, 'line_start': line_start, 'line_end': line_end})

    registry.register(
        ToolDef(
            name='navigate_to_file',
            description='Navigate the code viewer to display a specific file, optionally highlighting a line range.',
            input_schema={
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Relative file path to open'},
                    'line_start': {'type': 'integer', 'description': 'Optional start line to highlight'},
                    'line_end': {'type': 'integer', 'description': 'Optional end line to highlight'},
                },
                'required': ['file_path'],
            },
            handler=navigate_to_file,
        )
    )

    def start_coding_agent():
        """Signal that code generation should be started.

        This does not run the coding agent inline — it checks preconditions and
        returns a signal that the frontend uses to trigger the SSE-based coding
        agent stream.
        """
        db = get_db()
        pdd = db.query(PddVersion).filter_by(process_id=process_id).order_by(PddVersion.version_number.desc()).first()
        if not pdd or not pdd.content:
            return json.dumps({'error': 'No SOP/PDD content found. Please create one first.'})
        return json.dumps(
            {
                'success': True,
                'action': 'start_coding_agent',
                'pdd_version': pdd.version_number,
                'message': 'Code generation initiated. The coding agent will now generate/update the codebase based on the current PDD.',
            }
        )

    registry.register(
        ToolDef(
            name='start_coding_agent',
            description='Start the coding agent to generate or regenerate the codebase from the current PDD. '
            'Call this when the user asks to generate code, update the code, or regenerate the engine. '
            'Returns a signal that triggers the actual coding agent run.',
            input_schema={'type': 'object', 'properties': {}},
            handler=start_coding_agent,
        )
    )

    # ── Test tools ───────────────────────────────────────────────────

    def list_test_cases():
        """List all active test cases for the process."""
        db = get_db()
        cases = db.query(TestCase).filter_by(process_id=process_id, is_active=True).all()
        return json.dumps([c.to_dict() for c in cases])

    registry.register(
        ToolDef(
            name='list_test_cases',
            description='List all active test cases for this process.',
            input_schema={'type': 'object', 'properties': {}},
            handler=list_test_cases,
        )
    )

    def read_test_case(test_name_or_id):
        """Read a specific test case by name or ID."""
        db = get_db()
        tc = db.query(TestCase).filter_by(process_id=process_id, test_name=test_name_or_id, is_active=True).first()
        if not tc:
            tc = db.query(TestCase).filter_by(id=test_name_or_id, process_id=process_id).first()
        if not tc:
            return json.dumps({'error': f'Test case not found: {test_name_or_id}'})
        return json.dumps(tc.to_dict())

    registry.register(
        ToolDef(
            name='read_test_case',
            description='Read a specific test case by its name or ID.',
            input_schema={
                'type': 'object',
                'properties': {'test_name_or_id': {'type': 'string'}},
                'required': ['test_name_or_id'],
            },
            handler=read_test_case,
        )
    )

    def create_test_case(name, input_data, description='', expected_assertions=None):
        """Create a new test case."""
        db = get_db()
        if isinstance(input_data, str):
            input_data = json.loads(input_data)
        if isinstance(expected_assertions, str):
            expected_assertions = json.loads(expected_assertions)
        tc = TestCase(
            process_id=process_id,
            test_name=name,
            description=description,
            input_data=input_data,
            expected_assertions=expected_assertions or [],
        )
        db.add(tc)
        db.commit()
        return json.dumps({'success': True, 'id': str(tc.id), 'test_name': tc.test_name})

    registry.register(
        ToolDef(
            name='create_test_case',
            description='Create a new test case with input data and optional expected assertions.',
            input_schema={
                'type': 'object',
                'properties': {
                    'name': {'type': 'string', 'description': 'Test case name'},
                    'description': {'type': 'string', 'description': 'Brief description'},
                    'input_data': {'type': 'object', 'description': 'Input data as JSON object'},
                    'expected_assertions': {
                        'type': 'array',
                        'description': 'List of assertion objects',
                        'items': {'type': 'object'},
                    },
                },
                'required': ['name', 'input_data'],
            },
            handler=create_test_case,
        )
    )

    def update_test_case(test_name_or_id, input_data=None, expected_assertions=None, description=None):
        """Update an existing test case."""
        db = get_db()
        tc = db.query(TestCase).filter_by(process_id=process_id, test_name=test_name_or_id, is_active=True).first()
        if not tc:
            tc = db.query(TestCase).filter_by(id=test_name_or_id, process_id=process_id).first()
        if not tc:
            return json.dumps({'error': f'Test case not found: {test_name_or_id}'})
        if input_data is not None:
            tc.input_data = json.loads(input_data) if isinstance(input_data, str) else input_data
        if expected_assertions is not None:
            tc.expected_assertions = (
                json.loads(expected_assertions) if isinstance(expected_assertions, str) else expected_assertions
            )
        if description is not None:
            tc.description = description
        db.commit()
        return json.dumps({'success': True, 'id': str(tc.id), 'test_name': tc.test_name})

    registry.register(
        ToolDef(
            name='update_test_case',
            description='Update an existing test case\'s input data, assertions, or description.',
            input_schema={
                'type': 'object',
                'properties': {
                    'test_name_or_id': {'type': 'string'},
                    'input_data': {'type': 'object', 'description': 'New input data'},
                    'expected_assertions': {'type': 'array', 'items': {'type': 'object'}},
                    'description': {'type': 'string'},
                },
                'required': ['test_name_or_id'],
            },
            handler=update_test_case,
        )
    )

    def delete_test_case(test_name_or_id):
        """Soft-delete a test case."""
        db = get_db()
        tc = db.query(TestCase).filter_by(process_id=process_id, test_name=test_name_or_id, is_active=True).first()
        if not tc:
            tc = db.query(TestCase).filter_by(id=test_name_or_id, process_id=process_id).first()
        if not tc:
            return json.dumps({'error': f'Test case not found: {test_name_or_id}'})
        tc.is_active = False
        db.commit()
        return json.dumps({'success': True, 'test_name': tc.test_name})

    registry.register(
        ToolDef(
            name='delete_test_case',
            description='Soft-delete a test case by name or ID.',
            input_schema={
                'type': 'object',
                'properties': {'test_name_or_id': {'type': 'string'}},
                'required': ['test_name_or_id'],
            },
            handler=delete_test_case,
        )
    )

    def bulk_create_tests(tests):
        """Create multiple test cases at once."""
        db = get_db()
        created = []
        for t in tests:
            inp = t.get('input_data', {})
            if isinstance(inp, str):
                inp = json.loads(inp)
            assertions = t.get('expected_assertions', [])
            if isinstance(assertions, str):
                assertions = json.loads(assertions)
            tc = TestCase(
                process_id=process_id,
                test_name=t['name'],
                description=t.get('description', ''),
                input_data=inp,
                expected_assertions=assertions,
            )
            db.add(tc)
            created.append(t['name'])
        db.commit()
        return json.dumps({'success': True, 'count': len(created), 'names': created})

    registry.register(
        ToolDef(
            name='bulk_create_tests',
            description='Create multiple test cases at once from an array of test definitions.',
            input_schema={
                'type': 'object',
                'properties': {
                    'tests': {
                        'type': 'array',
                        'description': 'Array of test case objects',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string'},
                                'description': {'type': 'string'},
                                'input_data': {'type': 'object'},
                                'expected_assertions': {'type': 'array', 'items': {'type': 'object'}},
                            },
                            'required': ['name', 'input_data'],
                        },
                    },
                },
                'required': ['tests'],
            },
            handler=bulk_create_tests,
        )
    )

    return registry


def _merge_section(full_content, section_path, new_content):
    """Replace or append a section in the PDD. new_content should include its own header."""
    if not full_content.strip():
        return new_content.strip()

    section_key = section_path.lower().replace('_', ' ').replace('-', ' ').strip()

    # Special case: "purpose" replaces everything before the first ## header
    if section_key == 'purpose':
        lines = full_content.split('\n')
        rest = []
        found_h2 = False
        for line in lines:
            if line.startswith('## '):
                found_h2 = True
            if found_h2:
                rest.append(line)
        if rest:
            return new_content.rstrip() + '\n\n' + '\n'.join(rest)
        return new_content.strip()

    # General case: find and replace a section by matching h2 (##) headers only
    lines = full_content.split('\n')
    result = []
    in_section = False
    section_depth = 0
    replaced = False

    for line in lines:
        if not replaced and line.startswith('## ') and not line.startswith('### '):
            stripped = line[3:].strip().lower()
            if section_key in stripped or stripped in section_key:
                section_depth = 2
                # Replace the entire old section (header + content) with new_content
                result.append(new_content.rstrip())
                in_section = True
                replaced = True
                continue

        if in_section:
            if line.startswith('#'):
                depth = len(line) - len(line.lstrip('#'))
                if depth <= section_depth:
                    in_section = False
                    result.append(line)
            continue

        result.append(line)

    if not replaced:
        # Section not found — append at the end
        result.append('')
        result.append(new_content.rstrip())

    return '\n'.join(result)


def _extract_sentences(text):
    """Extract sentences from text for provenance tracking."""
    import re

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
