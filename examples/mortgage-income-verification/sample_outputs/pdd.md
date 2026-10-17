# Income Verification for Mortgage Underwriting — Process Definition Document

## Purpose

Determine qualifying monthly income for mortgage loan applicants by analyzing W-2s, paystubs, tax returns, and other income documentation per FNMA Selling Guide (B3-3 series, March 2026) and AHL institutional overlay (v4.2, January 2026). This process covers all employment-related income types including fixed base, variable base, bonus/overtime/commission, self-employment, and RSU income.

## Key Concepts

| Term | Definition |
|---|---|
| Qualifying Monthly Income | The total monthly income amount approved for use in DTI calculation |
| Fixed Base Income | Salary or hourly income that does not vary — requires only most recent paystub and W-2 |
| Variable Base Income | Hourly income with fluctuating hours — requires 12-month history minimum |
| Variable Income | Bonus, overtime, commission, or tip income — requires 24-month history per AHL |
| Income Trending | Analysis of whether income is stable, increasing, or declining year-over-year |
| Continuance | Expectation that income will continue for at least 36 months from note date (AHL) |
| Provenance | Source attribution for each rule — FNMA section number or AHL overlay reference |
| TENTATIVE | Knowledge inferred from documents but not yet confirmed by SME |
| CONFIRMED | Knowledge verified by SME or explicitly stated in authoritative source |

## Variable Reference

| Variable | Type | Source |
|---|---|---|
| `paystubs` | input | Borrower-provided |
| `w2_forms` | input | Borrower-provided (most recent + prior year) |
| `tax_returns` | input | Borrower-provided (2 years for self-employment) |
| `voe_forms` | input | Employer verification |
| `bank_statements` | input | Borrower-provided (2 months) |
| `employer_info` | input | Verbal VOE + written verification |
| `income_type` | intermediate | Determined in Phase 1 |
| `base_monthly_income` | intermediate | Calculated in Phase 2 |
| `variable_monthly_income` | intermediate | Calculated in Phase 3 |
| `self_employment_income` | intermediate | Calculated in Phase 4 |
| `qualifying_monthly_income` | output | Final sum from Phase 5 |
| `income_component_breakdown` | output | Itemized list per income type |
| `flags_and_conditions` | output | Issues requiring attention |
| `audit_trail` | output | Provenance chain for each calculation |

## Outputs

| Output | Type | Description |
|---|---|---|
| `qualifying_monthly_income` | currency | Total monthly income approved for DTI |
| `income_component_breakdown` | list | Per-type breakdown with calculation method |
| `flags_and_conditions` | list | Conditions, LOE requirements, sign-offs needed |
| `audit_trail` | list | Rule citations and calculation provenance |

## Process

### Phase 1: Document Collection and Income Classification

Collect all required income documentation from the borrower and classify each income source by type. This phase determines which calculation rules apply to each component and ensures documentation completeness before calculation begins.

#### Step 1.1: Collect and Inventory Income Documents

Gather all borrower-provided income documentation including paystubs, W-2 forms, 1099 forms, tax returns, bank statements, and any additional documentation such as employer letters, award letters, or verification of employment forms. Cross-reference the document set against the loan application (1003) to ensure all declared income sources have supporting documentation. Per FNMA B3-3.1-01, all income used for qualification must be documented, verified, and likely to continue.

<!-- pdl
GIVEN borrower_docs, loan_application
FOR EACH income_source IN loan_application.declared_income:
  IF income_source.supporting_docs IS EMPTY:
    SET flags += "Missing documentation for {income_source.type}"
  ELSE:
    SET doc_inventory += income_source
RETURN doc_inventory, flags
-->

#### Step 1.2: Classify Income by Type

For each documented income source, determine the income classification: fixed base (salaried, non-varying), variable base (hourly with fluctuating hours), bonus, overtime, commission, tip, self-employment, or RSU/restricted stock. The classification determines which calculation rules and history requirements apply. Per FNMA B3-3.1-01, the lender must identify the income type to apply the correct verification and calculation methodology.

<!-- pdl
GIVEN doc_inventory
FOR EACH source IN doc_inventory:
  DECIDE income_type:
    IF source.pay_type = "salary" AND source.has_no_variable_components:
      SET income_type = "fixed_base"
    ELSE IF source.pay_type = "hourly":
      SET income_type = "variable_base"
    ELSE IF source.category IN ["bonus", "overtime", "commission", "tips"]:
      SET income_type = "variable_income"
    ELSE IF source.has_schedule_c OR source.has_1099_income:
      SET income_type = "self_employment"
    ELSE IF source.category = "RSU":
      SET income_type = "rsu"
  SET source.classification = income_type
RETURN classified_sources
-->

#### Step 1.3: Verify Employment Continuance

Confirm that each income source has a reasonable expectation of continuance for at least 36 months from the note date, per AHL overlay requirement. Check for employment gaps exceeding 30 days within the most recent 24 months — AHL extends the FNMA lookback from 12 to 24 months. The borrower must have been continuously employed for at least 6 months at the current position.

<!-- pdl
GIVEN classified_sources, borrower_employment_history
FOR EACH source IN classified_sources:
  IF source.current_tenure_months < 6:
    SET flags += "Less than 6 months at current employer — income may not qualify"
  IF employment_gaps_in_last_24_months(borrower_employment_history) > 30_days:
    SET flags += "Employment gap > 30 days in last 24 months — LOE required"
    SET conditions += "Borrower LOE for employment gap"
  IF NOT income_likely_to_continue(source, months=36):
    SET flags += "Income continuance concern for {source.type}"
RETURN flags, conditions
-->

### Phase 2: Fixed and Variable Base Income Calculation

Calculate qualifying income from base pay sources (both fixed salary and variable hourly). Fixed base income uses the most recent paystub and W-2 per FNMA B3-3.3-01. Variable base income requires a 12-month minimum history.

#### Step 2.1: Calculate Fixed Base (Salaried) Income

For salaried borrowers with non-varying pay, use the current base salary as documented on the most recent paystub. Cross-check against the most recent W-2. Per FNMA B3-3.3-01 (March 2026 update), fixed base income requires only the most recent W-2 — prior year W-2 is no longer mandatory for fixed base. AHL follows FNMA on this with no additional overlay.

<!-- pdl
GIVEN paystub, w2_current
SET base_annual = paystub.base_rate * paystub.pay_periods_per_year
SET w2_annual = w2_current.wages

DECIDE variance_check:
  SET variance_pct = ABS(base_annual - w2_annual) / w2_annual * 100
  IF variance_pct > income_variance_threshold:
    SET flags += "Income variance {variance_pct}% exceeds threshold — LOE required"
    SET conditions += "Borrower LOE for income variance"

SET base_monthly_income = base_annual / 12
RETURN base_monthly_income
-->

#### Step 2.2: Calculate Variable Base (Hourly) Income

For hourly borrowers with fluctuating hours, calculate the qualifying income using a minimum 12-month history per FNMA B3-3.3-01. Both the Average Income method and Average Hours method are acceptable per AHL. The income must demonstrate stability or an upward trend; declining income requires additional analysis.

<!-- pdl
GIVEN paystubs_12_months, w2_current, w2_prior
DECIDE calculation_method:
  SET avg_income_method = SUM(paystubs_12_months.gross) / 12
  SET avg_hours_method = AVG(paystubs_12_months.hours) * paystub.hourly_rate * paystub.pay_periods_per_year / 12
  SET variable_base_monthly = MIN(avg_income_method, avg_hours_method)

DECIDE trending:
  SET current_year_avg = AVG(current_year_paystubs.gross)
  SET prior_year_avg = w2_prior.wages / 12
  IF current_year_avg < prior_year_avg * 0.80:
    SET flags += "Variable base income declining > 20%"
    SET variable_base_monthly = MIN(current_year_total / months_worked, variable_base_monthly)

RETURN variable_base_monthly
-->

### Phase 3: Variable Income Calculation (Bonus, Overtime, Commission)

Calculate qualifying income from variable components. AHL requires a full 24-month history for all variable income — no exceptions for 12-month history with offsetting factors (which FNMA B3-3.3-02 allows). Declining income triggers additional requirements.

#### Step 3.1: Verify Variable Income History Requirement

Confirm that each variable income component (bonus, overtime, commission, tips) has a minimum 24-month documented history per AHL overlay Section 4.1. FNMA allows income with 12+ months of history if positive offsetting factors exist, but AHL does NOT accept this exception — the full 24-month history is required regardless.

<!-- pdl
GIVEN variable_income_sources, w2_current, w2_prior
FOR EACH source IN variable_income_sources:
  SET history_months = source.documented_history_months
  IF history_months < 24:
    SET source.eligible = FALSE
    SET flags += "{source.type} has only {history_months} months history — AHL requires 24 months minimum"
  ELSE:
    SET source.eligible = TRUE
RETURN variable_income_sources
-->

#### Step 3.2: Analyze Variable Income Trending

For each eligible variable income component, perform trending analysis per AHL Section 4.2. When the trend is stable or increasing, use the standard 24-month average. When there is a year-over-year decline exceeding 20%, AHL Section 4.3 requires branch manager sign-off, a borrower LOE, and the use of the lower of the most recent 12-month average or the most recent year's total.

<!-- pdl
GIVEN eligible_variable_sources, w2_current, w2_prior
FOR EACH source IN eligible_variable_sources:
  SET current_year_amount = source.current_year_total
  SET prior_year_amount = source.prior_year_total
  SET yoy_change_pct = (current_year_amount - prior_year_amount) / prior_year_amount * 100

  DECIDE trending:
    IF yoy_change_pct >= 0:
      SET source.monthly = (current_year_amount + prior_year_amount) / 24
      SET source.trend = "stable_or_increasing"
    ELSE IF yoy_change_pct > -20:
      SET source.monthly = (current_year_amount + prior_year_amount) / 24
      SET source.trend = "slight_decline"
    ELSE:
      SET source.trend = "significant_decline"
      SET recent_12mo_avg = source.recent_12_months_total / 12
      SET current_year_monthly = current_year_amount / source.months_in_current_year
      SET source.monthly = MIN(recent_12mo_avg, current_year_monthly)
      SET conditions += "Branch manager sign-off required for declining {source.type}"
      SET conditions += "Borrower LOE required for {source.type} decline"
      SET flags += "{source.type} declined {ABS(yoy_change_pct)}% YoY — using lower calculation"

RETURN variable_income_sources
-->

#### Step 3.3: Exclude Ineligible Variable Income

Exclude any one-time or irregular bonus income per AHL Section 4.4. Bonus income received only once (single occurrence) is excluded entirely from qualifying income regardless of employer documentation. Also exclude any variable income failing the 24-month history requirement.

<!-- pdl
GIVEN variable_income_sources
FOR EACH source IN variable_income_sources:
  IF source.type = "bonus" AND source.occurrence_count = 1:
    SET source.eligible = FALSE
    SET flags += "One-time bonus excluded per AHL 4.4"
  IF NOT source.eligible:
    SET source.monthly = 0

SET total_variable_monthly = SUM(eligible_sources.monthly)
RETURN total_variable_monthly
-->

### Phase 4: Self-Employment Income Calculation

Calculate qualifying income from self-employment using tax returns and Schedule C analysis. AHL requires 2-year history with limited exceptions. All analysis uses FNMA Form 1084 or equivalent.

#### Step 4.1: Verify Self-Employment History

Confirm at least 2 years of self-employment history per AHL Section 5.1. The one-year alternative permitted by FNMA (for businesses with 5+ consecutive years) is accepted by AHL only with additional documentation: a CPA letter confirming business viability and income consistency, plus a borrower letter explaining the nature of the business.

<!-- pdl
GIVEN self_employment_sources, tax_returns
FOR EACH source IN self_employment_sources:
  SET se_history_years = source.years_in_business
  DECIDE eligibility:
    IF se_history_years >= 2:
      SET source.eligible = TRUE
    ELSE IF se_history_years >= 1 AND source.business_years >= 5:
      SET source.eligible = TRUE
      SET conditions += "CPA letter required for 1-year SE exception"
      SET conditions += "Borrower LOE required explaining business"
    ELSE:
      SET source.eligible = FALSE
      SET flags += "Self-employment < 2 years — not eligible"
RETURN self_employment_sources
-->

#### Step 4.2: Evaluate Same-Field Exception

For borrowers transitioning from W-2 employment to self-employment in the same field with less than 2 years of self-employment history, AHL accepts the FNMA same-field exception per AHL Section 5.2 with additional requirements: CPA letter confirming same field, borrower transition explanation letter, and prior employer verification confirming the borrower's prior role and departure.

<!-- pdl
GIVEN self_employment_source, prior_employment
IF self_employment_source.history_years < 2:
  DECIDE same_field:
    IF prior_employment.field SIMILAR_TO self_employment_source.field:
      SET source.same_field_exception = TRUE
      SET conditions += "CPA letter confirming same field required"
      SET conditions += "Borrower transition LOE required"
      SET conditions += "Prior employer verification required"
    ELSE:
      SET source.same_field_exception = FALSE
      SET flags += "Different field — same-field exception does not apply"
RETURN self_employment_source
-->

#### Step 4.3: Calculate Self-Employment Qualifying Income

Analyze self-employment income using FNMA Form 1084 or equivalent cash flow analysis per AHL Section 5.3. Calculate net income after adding back eligible non-cash expenses (depreciation, amortization) and applying required deductions. Use the 2-year average unless declining, in which case use the more recent year.

<!-- pdl
GIVEN tax_returns_2_years, schedule_c
SET year1_net = schedule_c_year1.net_profit + schedule_c_year1.depreciation + schedule_c_year1.amortization
SET year2_net = schedule_c_year2.net_profit + schedule_c_year2.depreciation + schedule_c_year2.amortization

DECIDE calculation:
  IF year2_net >= year1_net:
    SET se_annual = (year1_net + year2_net) / 2
    SET trend = "stable_or_increasing"
  ELSE:
    SET se_annual = year2_net
    SET trend = "declining"
    SET flags += "Self-employment income declining — using most recent year only"

SET self_employment_monthly = se_annual / 12
RETURN self_employment_monthly
-->

### Phase 5: Income Aggregation and Final Qualification

Combine all income components, perform cross-document variance checks, and produce the final qualifying monthly income with complete audit trail.

#### Step 5.1: Cross-Document Variance Check

Compare income figures across all document sources (W-2 vs. paystub annualized, year-over-year W-2 comparison) per AHL Section 1.1. Any variance exceeding the significant threshold requires a borrower Letter of Explanation and may require additional documentation at the underwriter's discretion. [TENTATIVE: The specific percentage threshold for "significant variance" is determined by the underwriting team lead and may vary by loan program — needs SME clarification.]

<!-- pdl
GIVEN all_income_docs
FOR EACH income_pair IN cross_document_comparisons:
  SET variance_pct = ABS(income_pair.amount_a - income_pair.amount_b) / income_pair.amount_b * 100
  IF variance_pct > income_variance_threshold:
    SET flags += "Variance {variance_pct}% between {income_pair.source_a} and {income_pair.source_b}"
    SET conditions += "Borrower LOE required for income variance"
RETURN flags, conditions
-->

#### Step 5.2: Large Deposit Review

Review bank statements for any single deposit exceeding $3,000 that is not identifiable as payroll, per AHL Section 8. Each such deposit must be documented with a paper trail including source of funds letter, supporting transfer documentation, or gift letter if applicable. Note: FNMA's standard threshold is 50% of qualifying monthly income, but AHL applies a flat $3,000 threshold.

<!-- pdl
GIVEN bank_statements
FOR EACH deposit IN bank_statements.deposits:
  IF deposit.amount > 3000 AND NOT deposit.is_payroll:
    SET flags += "Large deposit ${deposit.amount} on {deposit.date} — source documentation required"
    SET conditions += "Source of funds documentation for {deposit.date} deposit"
RETURN flags, conditions
-->

#### Step 5.3: Aggregate Qualifying Monthly Income

Sum all eligible income components to produce the final qualifying monthly income. Generate the complete income component breakdown and audit trail with provenance for each calculation. Each income component must cite the FNMA section and/or AHL overlay section that governed its calculation.

<!-- pdl
GIVEN base_monthly_income, variable_base_monthly, total_variable_monthly, self_employment_monthly
SET qualifying_monthly_income = base_monthly_income
  + variable_base_monthly
  + total_variable_monthly
  + self_employment_monthly

SET income_component_breakdown = [
  {type: "fixed_base", amount: base_monthly_income, rule: "FNMA B3-3.3-01"},
  {type: "variable_base", amount: variable_base_monthly, rule: "FNMA B3-3.3-01 + AHL 3"},
  {type: "variable_income", amount: total_variable_monthly, rule: "FNMA B3-3.3-02 + AHL 4"},
  {type: "self_employment", amount: self_employment_monthly, rule: "FNMA B3-3.5-01 + AHL 5"},
]

RETURN qualifying_monthly_income, income_component_breakdown, flags_and_conditions, audit_trail
-->

## Business Rules

| Rule ID | Rule | Source | AHL Override |
|---|---|---|---|
| BR-01 | Fixed base income requires most recent paystub + most recent W-2 only | FNMA B3-3.3-01 (Mar 2026) | No override |
| BR-02 | Variable base income requires 12-month minimum history | FNMA B3-3.3-01 | No override |
| BR-03 | All variable income (bonus/OT/commission) requires 24-month history | AHL 4.1 | Stricter than FNMA 12-month |
| BR-04 | Declining variable income > 20% YoY requires branch manager sign-off | AHL 4.3 | AHL-specific |
| BR-05 | One-time bonus excluded entirely | AHL 4.4 | Aligns with FNMA 2-year req |
| BR-06 | Self-employment requires 2-year history (1-year exception needs CPA letter) | AHL 5.1 | Additional docs vs FNMA |
| BR-07 | Same-field SE exception requires CPA + LOE + prior employer verification | AHL 5.2 | Additional docs vs FNMA |
| BR-08 | Income continuance expectation: 36 months from note date | AHL 1.2 | FNMA says "3 years" |
| BR-09 | Employment gaps: 24-month lookback (vs FNMA 12-month) | AHL 7 | Stricter than FNMA |
| BR-10 | Large deposits: flat $3,000 threshold (vs FNMA 50% of monthly income) | AHL 8 | Stricter for high earners |
| BR-11 | RSU income: time-based 12-month history, performance-based 24-month | FNMA B3-3.3-07 | No override |
| BR-12 | RSU valuation uses 200-day moving average stock price | FNMA B3-3.3-07 | No override |

## Decision Priority Summary

| Priority | Description |
|---|---|
| 1 | AHL overlay rules take precedence over FNMA where stricter |
| 2 | FNMA Selling Guide (March 2026 version) for all non-overridden rules |
| 3 | Underwriter discretion for edge cases with manager approval |
