"""
test_runner.py — Test suite runner for income verification engine.

Loads test cases from test_cases/, runs income engine with mock LLM judge,
and compares results against expected assertions.
"""

import json
import os
import time

from engine.income_engine import run_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.dirname(BASE_DIR)
TEST_CASES_DIR = os.path.join(EXAMPLE_DIR, "test_cases")


def load_test_cases():
    """Load all test case files from test_cases/."""
    cases = []
    if not os.path.isdir(TEST_CASES_DIR):
        return cases
    for fname in sorted(os.listdir(TEST_CASES_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(TEST_CASES_DIR, fname)
        with open(path) as f:
            case = json.load(f)
        # Resolve application_ref if present
        if "application_ref" in case and "application" not in case:
            ref_path = os.path.join(EXAMPLE_DIR, case["application_ref"])
            with open(ref_path) as f:
                case["application"] = json.load(f)
        case["_filename"] = fname
        cases.append(case)
    return cases


def run_single_test(test_case, on_step=None):
    """Run a single test case and return results with pass/fail assertions."""
    app = test_case["application"]
    assertions = test_case.get("assertions", {})
    mock_judge = test_case.get("mock_llm_judge", {})

    start = time.time()
    result = run_engine(app, on_step=on_step, mock_llm_judge=mock_judge)
    duration = time.time() - start

    # Run assertions
    assertion_results = []

    # Total annual
    if "total_annual" in assertions:
        expected = assertions["total_annual"]
        actual = result["summary"]["total_annual"]
        assertion_results.append(
            {
                "name": "Total Annual Income",
                "expected": expected,
                "actual": actual,
                "passed": abs(expected - actual) < 1,
            }
        )

    # Total monthly
    if "total_monthly" in assertions:
        expected = assertions["total_monthly"]
        actual = result["summary"]["total_monthly"]
        assertion_results.append(
            {
                "name": "Total Monthly Income",
                "expected": expected,
                "actual": actual,
                "passed": abs(expected - actual) < 1,
            }
        )

    # Step decisions
    for step_id, expected_decision in assertions.get("step_decisions", {}).items():
        trace_step = next((s for s in result["trace"] if s["step_id"] == step_id), None)
        actual_decision = trace_step["decision"] if trace_step else "MISSING"
        assertion_results.append(
            {
                "name": f"Step {step_id} Decision",
                "expected": expected_decision,
                "actual": actual_decision,
                "passed": actual_decision == expected_decision,
            }
        )

    # Step values
    for step_id, expected_value in assertions.get("step_values", {}).items():
        trace_step = next((s for s in result["trace"] if s["step_id"] == step_id), None)
        actual_value = trace_step.get("result_value") if trace_step else None
        passed = actual_value is not None and abs(expected_value - actual_value) < 1
        assertion_results.append(
            {
                "name": f"Step {step_id} Value",
                "expected": expected_value,
                "actual": actual_value,
                "passed": passed,
            }
        )

    # Min flag count
    if "min_flag_count" in assertions:
        expected_min = assertions["min_flag_count"]
        actual_count = result["summary"]["flag_count"]
        assertion_results.append(
            {
                "name": "Minimum Flag Count",
                "expected": f">= {expected_min}",
                "actual": actual_count,
                "passed": actual_count >= expected_min,
            }
        )

    all_passed = all(a["passed"] for a in assertion_results)

    return {
        "test_id": test_case["test_id"],
        "test_name": test_case["test_name"],
        "description": test_case.get("description", ""),
        "passed": all_passed,
        "assertions": assertion_results,
        "passed_count": sum(1 for a in assertion_results if a["passed"]),
        "total_count": len(assertion_results),
        "trace": result["trace"],
        "summary": result["summary"],
        "income": result["income"],
        "flags": result["flags"],
        "duration_ms": int(duration * 1000),
    }


def run_all_tests(on_test=None):
    """Run all test cases. Calls on_test(result) after each."""
    cases = load_test_cases()
    results = []
    for case in cases:
        result = run_single_test(case)
        results.append(result)
        if on_test:
            on_test(result)
    return results


if __name__ == "__main__":
    results = run_all_tests()
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"Test Suite Results: {passed}/{total} passed")
    print(f"{'=' * 60}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['test_name']} — ${r['summary']['total_monthly']:,.2f}/mo ({r['duration_ms']}ms)")
        for a in r["assertions"]:
            mark = "  +" if a["passed"] else "  X"
            print(f"    {mark} {a['name']}: expected={a['expected']}, actual={a['actual']}")
