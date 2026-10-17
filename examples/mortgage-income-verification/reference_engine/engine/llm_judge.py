"""
llm_judge.py — Semantic judgment helper using Claude Haiku for cost efficiency.

Used where deterministic rules can't resolve a decision and NLU is needed:
- Same-field exception evaluation (Step 4.2)
- Income continuance assessment (Step 1.3)
"""

import json
import os
import time
from datetime import datetime

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-4-5-20251001")

_client = None


def _get_client():
    """Create the Anthropic client lazily so offline test runs never need a key."""
    global _client
    if _client is None:
        import anthropic  # only needed when no mock judgment is supplied

        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


JUDGE_SYSTEM = """\
You are a mortgage underwriting judgment engine. You evaluate evidence against regulatory rules and return a structured decision.

CRITICAL: Respond with ONLY a JSON object. No markdown, no explanation outside JSON.

Response format:
{"decision": true/false, "confidence": 0.0-1.0, "reasoning": "one sentence"}
"""


def llm_judge(question: str, evidence: str, rule_citation: str, confidence_threshold: float = 0.85) -> dict:
    """
    Ask a semantic yes/no question with supporting evidence.

    Returns:
        {
            "decision": bool,
            "confidence": float,
            "reasoning": str,
            "question": str,
            "evidence": str,
            "rule_citation": str,
            "model": str,
            "duration_ms": int,
            "timestamp": str,
            "meets_threshold": bool,
        }
    """
    user_prompt = (
        f"Question: {question}\n\n"
        f"Evidence:\n{evidence}\n\n"
        f"Applicable rule: {rule_citation}\n\n"
        "Evaluate the evidence and return your JSON decision."
    )

    start = time.time()
    try:
        resp = _get_client().messages.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = resp.content[0].text.strip()
        # Parse JSON — handle possible markdown wrapping
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        parsed = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        parsed = {
            "decision": False,
            "confidence": 0.0,
            "reasoning": f"Judge error: {e}",
        }

    duration_ms = int((time.time() - start) * 1000)

    return {
        "decision": parsed.get("decision", False),
        "confidence": parsed.get("confidence", 0.0),
        "reasoning": parsed.get("reasoning", ""),
        "question": question,
        "evidence": evidence,
        "rule_citation": rule_citation,
        "model": JUDGE_MODEL,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat(),
        "meets_threshold": parsed.get("confidence", 0.0) >= confidence_threshold,
    }
