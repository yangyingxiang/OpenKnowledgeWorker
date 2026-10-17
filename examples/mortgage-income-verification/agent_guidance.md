- **Per-borrower processing:** iterate over every borrower in `borrowers` and process each
  income component separately. Sum qualifying income across all borrowers.
- **Income type detection** (from the data, not from a field called `income_type`):
  - `employment.current.type == "1099-NEC"` or an `income.schedule_c` entry → self-employment
  - `income.overtime` or `income.bonus` present → base plus variable income
  - otherwise → fixed base (W-2 salaried)
- **Fixed base salary:** use `income.paystub.base_rate_annual` as the annual amount (the
  current rate), not W-2 wages.
- **Overtime** (separately from bonus): with `months_documented >= 24`, average the two
  years; with 12–23 months, use the single year; with fewer than 12 months, EXCLUDE.
- **Bonus** (separately from overtime): requires two years of history. A null prior year
  means less than two years → EXCLUDE. Otherwise average the two years.
- **RSU / restricted stock:** requires `three_year_forward_continuance == true` and at least
  two years of vesting history; otherwise EXCLUDE (result_value 0).
- **Self-employment:** use Schedule C `net_profit`; average two years when available,
  otherwise use the one year (the same-field exception still uses Schedule C net profit).
- **Semantic judgments** (income continuance, same-field exception): these need judgment;
  in generated code use a simple, documented heuristic and set `method` to `"llm_judge"`.
- **Worked example:** primary (W-2) base $87,500 + overtime average $11,550 + bonus
  excluded + RSU excluded = $99,050/yr; co-borrower (self-employed) Schedule C $58,400/yr;
  total $157,450/yr → $13,120.83/mo.
