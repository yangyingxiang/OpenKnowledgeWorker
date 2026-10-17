"""Evaluate a golden test case's expected assertions against an engine result.

``expected_assertions`` maps keys of the result's ``summary`` to expected values:

* scalars match exactly, or numerically within ``tolerance``;
* dicts match as a subset: every expected key must match (e.g. only the step
  decisions you care about);
* ``min_flag_count`` is a built-in check: ``len(summary["flags"]) >= n``.
"""

BUILTIN_ASSERTIONS = {'min_flag_count'}


def evaluate(summary: dict, assertions: dict, tolerance: float = 1.0) -> list:
    """Return ``[{'name', 'expected', 'actual', 'passed'}, ...]`` for each assertion."""
    summary = summary or {}
    results = []
    for key, expected in (assertions or {}).items():
        if key == 'min_flag_count':
            actual = len(summary.get('flags') or [])
            passed = _number(expected) is not None and actual >= _number(expected)
        else:
            actual = summary.get(key)
            passed = values_match(actual, expected, tolerance)
        results.append({'name': key, 'expected': expected, 'actual': actual, 'passed': passed})
    return results


def values_match(actual, expected, tolerance: float = 1.0) -> bool:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        return all(values_match(actual.get(k), v, tolerance) for k, v in expected.items())
    if actual == expected or (actual is not None and str(actual) == str(expected)):
        return True
    a, e = _number(actual), _number(expected)
    return a is not None and e is not None and abs(a - e) <= tolerance


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
