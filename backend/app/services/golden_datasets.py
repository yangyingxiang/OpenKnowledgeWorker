"""Golden datasets for multi-domain evaluation.

Each dataset contains:
- domain name and description
- sample PDD content
- sample application data
- expected engine behaviors (assertions)
- expected step count and decision patterns
"""

GOLDEN_DATASETS = {
    'income_verification': {
        'domain': 'Mortgage Underwriting',
        'description': 'Verify and calculate qualifying borrower income for mortgage loans.',
        'pdd_summary': 'Income verification across W2, self-employment, overtime, bonus, and asset sources.',
        'sample_application': {
            'borrower': {
                'name': 'John Smith',
                'citizenship': 'US',
                'occupancy': 'primary_residence',
            },
            'income_sources': [
                {
                    'source_type': 'W2',
                    'employer_name': 'Acme Corp',
                    'base_annual_salary': 85000,
                    'pay_frequency': 'biweekly',
                    'ytd_gross': 42500,
                    'pay_period_end_date': '2026-06-30',
                    'hire_date': '2020-01-15',
                    'overtime_history': [
                        {'year': 2025, 'amount': 8000},
                        {'year': 2024, 'amount': 7500},
                    ],
                    'bonus_history': [
                        {'year': 2025, 'amount': 5000},
                        {'year': 2024, 'amount': 6000},
                    ],
                }
            ],
            'loan': {
                'purpose': 'purchase',
                'ltv_ratio': 0.80,
            },
        },
        'expected_behaviors': [
            {'step_pattern': '1.*', 'min_count': 2, 'description': 'At least 2 eligibility/classification steps'},
            {'step_pattern': '4.*', 'min_count': 1, 'description': 'At least 1 income calculation step'},
            {
                'key': 'summary.total_annual',
                'type': 'positive_number',
                'description': 'Total annual income must be positive',
            },
            {
                'key': 'summary.total_monthly',
                'type': 'positive_number',
                'description': 'Total monthly income must be positive',
            },
            {
                'key': 'summary.total_monthly',
                'approx': 7083,
                'tolerance_pct': 50,
                'description': 'Monthly income roughly in expected range',
            },
        ],
        'expected_step_count_range': [10, 25],
    },
    'loan_origination': {
        'domain': 'Commercial Loan Origination',
        'description': 'Evaluate business loan applications based on financials, credit, and collateral.',
        'pdd_summary': 'Business financial analysis, credit scoring, collateral valuation, risk rating, and approval.',
        'sample_application': {
            'business': {
                'name': 'Smith Manufacturing LLC',
                'ein': '12-3456789',
                'years_in_operation': 8,
                'industry': 'manufacturing',
                'annual_revenue': 2500000,
            },
            'financials': {
                'revenue_2025': 2500000,
                'revenue_2024': 2300000,
                'net_income_2025': 375000,
                'net_income_2024': 340000,
                'total_assets': 1800000,
                'total_liabilities': 900000,
                'current_ratio': 1.8,
                'debt_service_coverage': 1.35,
            },
            'loan_request': {
                'amount': 500000,
                'purpose': 'equipment_purchase',
                'term_months': 60,
                'collateral_value': 650000,
            },
        },
        'expected_behaviors': [
            {'key': 'summary.total_annual', 'type': 'number', 'description': 'Loan amount/score is numeric'},
            {'step_pattern': '*', 'min_count': 5, 'description': 'At least 5 evaluation steps'},
        ],
        'expected_step_count_range': [5, 20],
    },
    'kyc_aml': {
        'domain': 'KYC/AML Compliance',
        'description': 'Customer due diligence and anti-money laundering screening for financial services.',
        'pdd_summary': 'Identity verification, sanctions screening, PEP checks, risk scoring, enhanced due diligence.',
        'sample_application': {
            'customer': {
                'name': 'Jane Doe',
                'date_of_birth': '1985-07-22',
                'nationality': 'US',
                'address': '123 Main St, New York, NY 10001',
                'id_document': {'type': 'passport', 'number': 'P12345678', 'expiry': '2030-12-31'},
            },
            'account': {
                'type': 'checking',
                'expected_monthly_volume': 15000,
                'source_of_funds': 'employment',
                'purpose': 'personal_banking',
            },
            'screening_results': {
                'sanctions_match': False,
                'pep_match': False,
                'adverse_media': False,
            },
        },
        'expected_behaviors': [
            {'step_pattern': '1.*', 'min_count': 1, 'description': 'Identity verification steps'},
            {'step_pattern': '*', 'min_count': 3, 'description': 'At least 3 screening steps'},
        ],
        'expected_step_count_range': [3, 15],
    },
}


def list_datasets() -> list[dict]:
    """List available golden datasets."""
    return [
        {
            'name': name,
            'domain': ds['domain'],
            'description': ds['description'],
            'expected_step_range': ds['expected_step_count_range'],
            'behavior_count': len(ds['expected_behaviors']),
        }
        for name, ds in GOLDEN_DATASETS.items()
    ]


def get_dataset(name: str) -> dict | None:
    """Get a specific golden dataset."""
    return GOLDEN_DATASETS.get(name)


def validate_engine_output(dataset_name: str, engine_output: dict) -> dict:
    """Validate engine output against a golden dataset's expected behaviors.

    Returns validation results with pass/fail for each assertion.
    """
    dataset = GOLDEN_DATASETS.get(dataset_name)
    if not dataset:
        return {'error': f'Dataset {dataset_name} not found'}

    results = []
    trace_steps = engine_output.get('trace_steps', [])

    for behavior in dataset['expected_behaviors']:
        result = {'description': behavior['description'], 'passed': False, 'detail': ''}

        if 'step_pattern' in behavior:
            import fnmatch

            matching = [s for s in trace_steps if fnmatch.fnmatch(s.get('step_id', ''), behavior['step_pattern'])]
            min_count = behavior.get('min_count', 1)
            result['passed'] = len(matching) >= min_count
            result['detail'] = f'Found {len(matching)} matching steps (need >= {min_count})'

        elif 'key' in behavior:
            # Navigate dotted key path
            value = engine_output
            for part in behavior['key'].split('.'):
                value = value.get(part, {}) if isinstance(value, dict) else None
                if value is None:
                    break

            if behavior.get('type') == 'positive_number':
                result['passed'] = isinstance(value, (int, float)) and value > 0
                result['detail'] = f'Value: {value}'
            elif behavior.get('type') == 'number':
                result['passed'] = isinstance(value, (int, float))
                result['detail'] = f'Value: {value}'
            elif 'approx' in behavior:
                if isinstance(value, (int, float)):
                    tolerance = behavior.get('tolerance_pct', 20) / 100
                    expected = behavior['approx']
                    lower = expected * (1 - tolerance)
                    upper = expected * (1 + tolerance)
                    result['passed'] = lower <= value <= upper
                    result['detail'] = f'Value: {value}, expected ~{expected} (±{behavior.get("tolerance_pct", 20)}%)'
                else:
                    result['detail'] = f'Value is not numeric: {value}'

        results.append(result)

    # Step count check
    step_range = dataset['expected_step_count_range']
    step_count = len(trace_steps)
    step_check = {
        'description': f'Step count in range [{step_range[0]}, {step_range[1]}]',
        'passed': step_range[0] <= step_count <= step_range[1],
        'detail': f'Actual: {step_count}',
    }
    results.append(step_check)

    passed = sum(1 for r in results if r['passed'])
    return {
        'dataset': dataset_name,
        'total_checks': len(results),
        'passed': passed,
        'failed': len(results) - passed,
        'all_passed': passed == len(results),
        'results': results,
    }
