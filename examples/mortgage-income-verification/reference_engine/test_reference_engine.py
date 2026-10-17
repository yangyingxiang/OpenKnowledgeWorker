"""Pytest entry point for the mortgage income verification golden test cases.

Runs fully offline: every case supplies mock LLM-judge responses.
"""

import pytest
from test_runner import load_test_cases, run_single_test

CASES = load_test_cases()


@pytest.mark.parametrize("case", CASES, ids=[c["_filename"] for c in CASES])
def test_golden_case(case):
    result = run_single_test(case)
    failed = [a for a in result["assertions"] if not a["passed"]]
    assert not failed, failed


@pytest.mark.parametrize("case", CASES, ids=[c["_filename"] for c in CASES])
def test_platform_contract(case):
    """engine.run_engine follows the contract the platform's test runner expects."""
    from engine import run_engine

    result = run_engine(case["application"], mock_llm_judge=case.get("mock_llm_judge"))
    summary = result["summary"]
    assert result["trace_steps"]
    for key in ("total_annual", "total_monthly", "flags", "step_decisions", "step_values"):
        assert key in summary
    assertions = case.get("assertions", {})
    if "total_annual" in assertions:
        assert abs(summary["total_annual"] - assertions["total_annual"]) < 1
    for step_id, decision in assertions.get("step_decisions", {}).items():
        assert summary["step_decisions"][step_id] == decision
