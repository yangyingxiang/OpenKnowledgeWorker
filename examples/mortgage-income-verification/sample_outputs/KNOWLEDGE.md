# KNOWLEDGE.md — income_verification

## Data Sources

- FNMA Selling Guide B3-3.1-01: General Income Information — covers income continuity, stability requirements, and documentation standards
  [source: document/B3-3.1-01, general income framework]
- FNMA B3-3.3-01: Base Income (Fixed & Variable Base Pay) — March 2026 update reduced fixed base docs to most recent W-2 only
  [source: document/B3-3.3-01, base pay calculation rules]
- FNMA B3-3.3-02: Bonus, Commission, Overtime, and Tip Income — requires 2-year history (12-month with offsetting factors)
  [source: document/B3-3.3-02, variable income rules]
- FNMA B3-3.5-01: Self-Employment Income — underwriting factors and documentation for self-employed borrowers
  [source: document/B3-3.5-01, self-employment rules]
- FNMA B3-3.3-07: RSU and Restricted Stock Employment Income — time-based (12mo) vs performance-based (24mo) history
  [source: document/B3-3.3-07, RSU income rules]
- AHL Internal Overlay v4.2 (January 2026) — institutional overlay that tightens several FNMA rules
  [source: document/lender_overlay, AHL-specific requirements]

## Decision Rules

- Fixed base income: Use current base salary from paystub, cross-check with most recent W-2. Per March 2026 FNMA update, only 1 W-2 required for fixed base.
  [source: document/B3-3.3-01, fixed base calculation]
- Variable base income: 12-month minimum history required. Both Average Income and Average Hours methods acceptable per AHL.
  [source: document/B3-3.3-01 + lender_overlay/Section 3]
- Variable income (bonus/OT/commission): AHL requires full 24-month history — does NOT accept FNMA's 12-month exception with offsetting factors.
  [source: document/lender_overlay/Section 4.1, AHL override of FNMA B3-3.3-02]
- Declining variable income > 20% YoY: requires branch manager sign-off, borrower LOE, and use of lower of recent 12-month average or most recent year total.
  [source: document/lender_overlay/Section 4.3, declining income rules]
- One-time bonus: excluded entirely from qualifying income regardless of employer documentation.
  [source: document/lender_overlay/Section 4.4, one-time bonus exclusion]
- Self-employment: 2-year history required. 1-year exception only with CPA letter + borrower LOE. Same-field exception requires CPA + LOE + prior employer verification.
  [source: document/lender_overlay/Sections 5.1-5.2, self-employment requirements]
- [TENTATIVE] Income variance threshold: The AHL overlay mentions "significant variance" but the specific percentage threshold is determined by the underwriting team lead and varies by loan program. Needs SME input to determine the actual threshold(s) used.
  [source: document/lender_overlay/Section 1.1, variance threshold ambiguity]
- Large deposit threshold: AHL uses flat $3,000 (vs FNMA's 50% of qualifying monthly income).
  [source: document/lender_overlay/Section 8, large deposit rule]
- Employment gap lookback: AHL extends to 24 months (vs FNMA's 12 months). Gaps > 30 days require written explanation.
  [source: document/lender_overlay/Section 7, employment gap override]

## Data Transformations

- Annualized paystub income: base_rate × pay_periods_per_year (26 for biweekly, 24 for semi-monthly, 52 for weekly, 12 for monthly)
  [source: document/B3-3.3-01, annualization calculation]
- Variable income averaging: sum of 24 months / 24 for standard; for declining use MIN(recent 12mo avg, current year total / months worked)
  [source: document/lender_overlay/Section 4.2-4.3, averaging methodology]
- Self-employment cash flow: Schedule C net profit + depreciation + amortization = adjusted net income
  [source: document/B3-3.5-01, Form 1084 methodology]
- RSU valuation: share count × 200-day moving average stock price per FNMA B3-3.3-07
  [source: document/B3-3.3-07, RSU valuation method]

## Business Context

- AHL (Acme Home Lending) is a mortgage lender that processes conventional, FHA, and VA mortgage originations
  [source: document/lender_overlay, institutional context]
- The overlay supplements FNMA Selling Guide and Freddie Mac Guide — where stricter, AHL takes precedence; where silent, agency guidelines apply
  [source: document/lender_overlay, overlay relationship to agency guides]
- [TENTATIVE] AHL uses "weighted recent performance" methodology for variable income trending — the specific weighting factors are not documented in the overlay and may be at underwriter discretion
  [source: document/lender_overlay/Section 4.2, trending methodology ambiguity]

## Regulatory

- FNMA Selling Guide was reorganized March 4, 2026 (Announcement SEL-2026-02) — old B3-3.1 numbering restructured to B3-3.2/3.3/3.4/3.5 series
  [source: document/INDEX.md, FNMA guide restructuring]
- Key March 2026 change: Fixed base income now requires only 1 W-2 (most recent), down from prior 2-year requirement
  [source: document/B3-3.3-01, March 2026 documentation change]
- AHL overlay v4.2 effective January 2026, supersedes v4.1 (July 2025)
  [source: document/lender_overlay, overlay version info]

## Integration Notes

- All income calculations must cite source FNMA section and/or AHL overlay section per AHL Section 10 audit requirements
  [source: document/lender_overlay/Section 10, audit trail requirement]
- Gift funds: must be on file before appraisal ordered, seasoned 15 days before closing, max 100% of down payment for primary residence
  [source: document/lender_overlay/Section 9, gift fund rules]
