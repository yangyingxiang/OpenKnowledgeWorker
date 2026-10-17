"""Code mapping service — extracts function definitions and maps them to PDD sections.

Also detects stale code units when the PDD changes.
"""

import re

from ..extensions import get_db
from ..models import PddVersion
from ..models.code_project import CodeFile, CodeProject, CodeUnit

# Pattern for Python function definitions
_FUNC_DEF_RE = re.compile(r'^(def\s+(\w+)\s*\()', re.MULTILINE)
# Pattern for step ID in function name or docstring (e.g., step_1_1, Step 1.1)
_STEP_ID_RE = re.compile(r'step[_\s]*(\d+)[_.\s](\d+)', re.IGNORECASE)
# Pattern for rule IDs (e.g., BR-101, BR_201)
_RULE_ID_RE = re.compile(r'BR[-_](\d{3})', re.IGNORECASE)


def extract_code_units(project_id: str) -> int:
    """Parse all source files in a project and extract function-level code units.

    Returns count of units extracted.
    """
    db = get_db()
    project = db.query(CodeProject).filter_by(id=project_id).first()
    if not project:
        return 0

    # Clear existing units
    db.query(CodeUnit).filter_by(project_id=project_id).delete()

    files = db.query(CodeFile).filter_by(project_id=project_id, file_type='source').all()

    units_created = 0
    for cf in files:
        if not cf.content:
            continue

        lines = cf.content.split('\n')
        functions = _extract_functions(lines)

        for func in functions:
            # Try to detect PDD step ID from function name or body
            func_body = '\n'.join(lines[func['start_line'] - 1 : func['end_line']])
            step_id = _detect_step_id(func['name'], func_body)
            rule_ids = _detect_rule_ids(func_body)
            pdd_section = cf.pdd_section_ref

            unit = CodeUnit(
                project_id=project_id,
                file_id=cf.id,
                function_name=func['name'],
                start_line=func['start_line'],
                end_line=func['end_line'],
                pdd_step_id=step_id,
                pdd_section=pdd_section,
                pdd_rule_ids=rule_ids,
                is_stale='fresh',
            )
            db.add(unit)
            units_created += 1

    db.commit()
    return units_created


def detect_stale_units(project_id: str) -> dict:
    """Compare code units against the current PDD to detect stale mappings.

    A code unit is stale if:
    - Its referenced PDD section no longer exists
    - Its referenced business rules have changed
    - The PDD version has been updated since the code was last generated

    Returns dict with stale_count and details.
    """
    db = get_db()
    project = db.query(CodeProject).filter_by(id=project_id).first()
    if not project:
        return {'stale_count': 0, 'units': []}

    # Get current PDD
    current_pdd = (
        db.query(PddVersion).filter_by(process_id=project.process_id).order_by(PddVersion.version_number.desc()).first()
    )

    if not current_pdd:
        return {'stale_count': 0, 'units': []}

    # Check if PDD has been updated since code was generated
    pdd_updated = current_pdd.id != project.pdd_version_id

    units = db.query(CodeUnit).filter_by(project_id=project_id).all()
    pdd_content = current_pdd.content.lower() if current_pdd.content else ''

    stale_units = []
    for unit in units:
        stale_reason = None

        if pdd_updated:
            # Check if the referenced section still exists in the new PDD
            if unit.pdd_section:
                section_key = unit.pdd_section.lower()
                if section_key not in pdd_content:
                    stale_reason = (
                        f'PDD section "{unit.pdd_section}" not found in current PDD v{current_pdd.version_number}'
                    )

            # Check if referenced step still exists
            if unit.pdd_step_id:
                step_patterns = [
                    f'step {unit.pdd_step_id}',
                    f'step_{unit.pdd_step_id.replace(".", "_")}',
                    unit.pdd_step_id,
                ]
                if not any(p.lower() in pdd_content for p in step_patterns):
                    stale_reason = f'PDD step {unit.pdd_step_id} not found in current PDD'

            # If PDD changed but section/step still exist, mark as potentially stale
            if not stale_reason and pdd_updated:
                stale_reason = f'PDD updated from v{project.pdd_version_id} to v{current_pdd.version_number}'

        if stale_reason:
            unit.is_stale = 'stale'
            unit.stale_reason = stale_reason
            stale_units.append(unit.to_dict())
        else:
            unit.is_stale = 'fresh'
            unit.stale_reason = None

    db.commit()

    return {
        'pdd_updated': pdd_updated,
        'current_pdd_version': current_pdd.version_number,
        'project_pdd_version_id': str(project.pdd_version_id) if project.pdd_version_id else None,
        'total_units': len(units),
        'stale_count': len(stale_units),
        'stale_units': stale_units,
    }


def get_code_mapping_summary(project_id: str) -> dict:
    """Get a summary of code-to-PDD mapping for a project."""
    db = get_db()
    units = db.query(CodeUnit).filter_by(project_id=project_id).all()

    step_map = {}
    for u in units:
        if u.pdd_step_id:
            step_map.setdefault(u.pdd_step_id, []).append(
                {
                    'function': u.function_name,
                    'file': u.file.file_path if u.file else None,
                    'lines': f'{u.start_line}-{u.end_line}',
                    'is_stale': u.is_stale,
                }
            )

    rule_map = {}
    for u in units:
        for rule_id in u.pdd_rule_ids or []:
            rule_map.setdefault(rule_id, []).append(u.function_name)

    return {
        'total_units': len(units),
        'mapped_to_steps': len(step_map),
        'mapped_to_rules': len(rule_map),
        'step_mapping': step_map,
        'rule_mapping': rule_map,
        'stale_count': sum(1 for u in units if u.is_stale == 'stale'),
    }


# ── Internal helpers ────────────────────────────────────


def _extract_functions(lines: list[str]) -> list[dict]:
    """Extract function definitions with start/end lines."""
    functions = []
    i = 0
    while i < len(lines):
        m = _FUNC_DEF_RE.match(lines[i])
        if m:
            func_name = m.group(2)
            start_line = i + 1  # 1-indexed
            # Find end of function: next def at same or lower indent, or end of file
            indent = len(lines[i]) - len(lines[i].lstrip())
            end_line = start_line
            j = i + 1
            while j < len(lines):
                line = lines[j]
                if line.strip() and not line.startswith(' ' * (indent + 1)) and not line.startswith('\t'):
                    # Check if it's a new top-level def/class at same indent
                    if line.strip().startswith(('def ', 'class ')) and (len(line) - len(line.lstrip())) <= indent:
                        break
                end_line = j + 1
                j += 1
            functions.append(
                {
                    'name': func_name,
                    'start_line': start_line,
                    'end_line': end_line,
                }
            )
            i = j
        else:
            i += 1
    return functions


def _detect_step_id(func_name: str, func_body: str) -> str | None:
    """Try to detect a PDD step ID from function name or body."""
    # Check function name first (e.g., step_1_1_classify_income)
    m = _STEP_ID_RE.search(func_name)
    if m:
        return f'{m.group(1)}.{m.group(2)}'
    # Check docstring/body
    m = _STEP_ID_RE.search(func_body[:500])
    if m:
        return f'{m.group(1)}.{m.group(2)}'
    return None


def _detect_rule_ids(func_body: str) -> list[str]:
    """Extract business rule IDs from function body."""
    matches = _RULE_ID_RE.findall(func_body)
    return [f'BR-{m}' for m in sorted(set(matches))]
