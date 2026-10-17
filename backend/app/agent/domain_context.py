"""Domain-specific context for the execution and coding agents.

Core prompts are domain-neutral. Everything domain-specific is assembled here from:

* the process's domain pack (``process.metadata['domain_pack']``, set when a pack is
  loaded — see ``examples/*/pack.json`` and ``backend/seed.py``), and
* the process's golden test cases (input shape and the summary keys they assert on).
"""

import json

from ..extensions import get_db
from ..models import Process, TestCase
from ..services.assertions import BUILTIN_ASSERTIONS

MAX_SAMPLE_CHARS = 6000
STANDARD_SUMMARY_KEYS = ('flags', 'step_decisions', 'step_values')


def get_domain_pack(process_id) -> dict:
    process = get_db().query(Process).filter_by(id=process_id).first()
    if not process:
        return {}
    return (process.metadata_ or {}).get('domain_pack') or {}


def build_domain_context(process_id) -> str:
    """Markdown block describing the input format, output contract, and domain guidance."""
    db = get_db()
    process = db.query(Process).filter_by(id=process_id).first()
    if not process:
        return ''
    pack = (process.metadata_ or {}).get('domain_pack') or {}
    cases = db.query(TestCase).filter_by(process_id=process_id, is_active=True).order_by(TestCase.created_at).all()

    parts = [
        f'## Domain context\n\nProcess: **{process.name}**' + (f' (domain: {process.domain})' if process.domain else '')
    ]
    if process.key_inputs:
        parts.append('Key inputs: ' + ', '.join(map(str, process.key_inputs)))
    if process.key_outputs:
        parts.append('Key outputs: ' + ', '.join(map(str, process.key_outputs)))

    sample = pack.get('sample_input') or next((c.input_data for c in cases if c.input_data), None)
    if sample:
        sample_json = json.dumps(sample, indent=2, default=str)
        if len(sample_json) > MAX_SAMPLE_CHARS:
            sample_json = sample_json[:MAX_SAMPLE_CHARS] + '\n... (truncated)'
        parts.append(
            '### Input format\n\nThe engine receives one case as a JSON object shaped like '
            f'this example:\n\n```json\n{sample_json}\n```'
        )

    contract = summary_contract(pack, cases)
    if contract:
        lines = '\n'.join(f'- `{key}`' + (f': {desc}' if desc else '') for key, desc in contract.items())
        parts.append(
            '### Output contract\n\nThe result\'s `summary` object MUST contain these keys '
            '(golden test cases assert on them):\n\n' + lines
        )

    guidance = pack.get('agent_guidance')
    if guidance:
        parts.append('### Domain guidance\n\n' + guidance.strip())
    return '\n\n'.join(parts)


def summary_contract(pack: dict, cases: list) -> dict:
    """Required summary keys -> description, from the pack and the test assertions."""
    contract = dict((pack.get('output_contract') or {}).get('summary') or {})
    for case in cases:
        for key in case.expected_assertions or {}:
            if key not in BUILTIN_ASSERTIONS:
                contract.setdefault(key, '')
    for key in STANDARD_SUMMARY_KEYS:
        contract.setdefault(key, '')
    return contract
