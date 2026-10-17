from app.services.assertions import evaluate, values_match


def test_scalar_numeric_tolerance():
    assert values_match(13120.83, 13120.5)
    assert not values_match(13120.83, 13000)
    assert values_match('PASS', 'PASS')
    assert not values_match(None, 0)


def test_dict_assertions_match_as_subset():
    actual = {'1.1': 'PASS', '2.1': 'PASS', '2.2': 'FLAG'}
    assert values_match(actual, {'2.1': 'PASS'})
    assert not values_match(actual, {'2.2': 'PASS'})
    assert not values_match('not a dict', {'2.1': 'PASS'})


def test_min_flag_count_is_builtin():
    results = evaluate({'flags': ['a', 'b']}, {'min_flag_count': 2})
    assert results == [{'name': 'min_flag_count', 'expected': 2, 'actual': 2, 'passed': True}]
    assert not evaluate({'flags': []}, {'min_flag_count': 1})[0]['passed']


def test_missing_summary_key_fails():
    result = evaluate({}, {'total_annual': 100})[0]
    assert result['actual'] is None and not result['passed']
