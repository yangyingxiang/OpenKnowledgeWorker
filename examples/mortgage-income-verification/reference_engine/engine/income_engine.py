"""
income_engine.py — Code Engine (Mode B) for PDD execution.

Implements each PDD step as a deterministic Python function.
Data-driven: handles varying application structures (single/dual borrower,
variable income present/absent, deposits, gaps, etc.).
Calls llm_judge() only where semantic NLU is genuinely required.
"""

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Optional

from .llm_judge import llm_judge

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXAMPLE_DIR = os.path.dirname(os.path.dirname(BASE_DIR))


@dataclass
class TraceStep:
    step_id: str
    title: str
    decision: str  # PASS | FLAG | EXCLUDE | INFO
    result_value: Optional[float] = None
    result_label: str = ""
    rule_citation: str = ""
    rationale: str = ""
    method: str = "deterministic"  # deterministic | llm_judge
    inputs: dict = field(default_factory=dict)
    llm_judgment: Optional[dict] = None
    duration_ms: int = 0


@dataclass
class EngineState:
    trace: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    income: dict = field(default_factory=dict)
    total_annual: float = 0
    total_monthly: float = 0
    # SE intermediate results
    se_tenure_months: int = 0
    se_same_field_pass: bool = False
    # Mock LLM judge responses (keyed by step_id)
    mock_llm_judge: dict = field(default_factory=dict)


def load_sample_application() -> dict:
    path = os.path.join(EXAMPLE_DIR, "sample_application.json")
    with open(path) as f:
        return json.load(f)


def _borrower(app, role):
    for b in app.get("borrowers", []):
        if b["role"] == role:
            return b
    return None


def _name(borrower):
    if not borrower:
        return "Unknown"
    return borrower.get("name", {}).get("first", "Borrower")


def _call_llm_judge(state, step_id, question, evidence, rule_citation):
    """Call llm_judge or return mock if available."""
    mock = state.mock_llm_judge.get(step_id)
    if mock:
        return mock
    return llm_judge(question, evidence, rule_citation)


# ============================================================
# STEP FUNCTIONS
# ============================================================


def step_1_1_classify_income(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    co = _borrower(app, "co-borrower")

    streams = []
    if primary:
        pname = _name(primary)
        inc = primary.get("income", {})
        if inc.get("paystub") or inc.get("w2"):
            streams.append(f"{pname}: Fixed base (W-2 salaried)")
        if inc.get("overtime"):
            streams.append(f"{pname}: Overtime (variable)")
        if inc.get("bonus"):
            streams.append(f"{pname}: Bonus (discretionary)")
        if inc.get("rsu"):
            streams.append(f"{pname}: RSU (restricted stock)")
    if co:
        cname = _name(co)
        co_type = co.get("employment", {}).get("current", {}).get("type", "")
        if co_type in ("1099-NEC", "1099", "Self-Employed"):
            streams.append(f"{cname}: Self-employment (1099/Schedule C)")
        elif co.get("income", {}).get("paystub") or co.get("income", {}).get("w2"):
            streams.append(f"{cname}: Fixed base (W-2 salaried)")

    borrower_count = (1 if primary else 0) + (1 if co else 0)
    step = TraceStep(
        step_id="1.1",
        title="Classify Income Types",
        decision="PASS",
        rationale=f"Identified {len(streams)} income streams across {borrower_count} borrower(s): {'; '.join(streams)}",
        rule_citation="FNMA B3-3.1-01: General Income Information",
        inputs={"borrower_count": borrower_count, "streams": streams},
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_1_2_verify_employment(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    emp = primary.get("employment", {})
    current = emp.get("current", {})
    gap = emp.get("gap")
    pname = _name(primary)

    if gap and gap.get("days", 0) > 0:
        step = TraceStep(
            step_id="1.2",
            title=f"Verify Employment Status ({pname})",
            decision="FLAG",
            rationale=(
                f"{pname} employed at {current.get('employer', 'N/A')} since {current.get('start_date', 'N/A')}. "
                f"Employment gap of {gap['days']} days. "
                f"Gap documented — flagged but not disqualifying."
            ),
            rule_citation="FNMA B3-3.1-02: Standards for Employment Documentation; AHL 4.2.1 gap > 30 days requires documentation",
            inputs={
                "employer": current.get("employer"),
                "start_date": current.get("start_date"),
                "gap_days": gap["days"],
            },
            duration_ms=int((time.time() - start) * 1000),
        )
        state.flags.append(f"Employment gap: {gap['days']} days (documented)")
    else:
        step = TraceStep(
            step_id="1.2",
            title=f"Verify Employment Status ({pname})",
            decision="PASS",
            rationale=f"{pname} employed at {current.get('employer', 'N/A')} since {current.get('start_date', 'N/A')}. No employment gaps.",
            rule_citation="FNMA B3-3.1-02: Standards for Employment Documentation",
            inputs={"employer": current.get("employer"), "start_date": current.get("start_date")},
            duration_ms=int((time.time() - start) * 1000),
        )

    state.trace.append(step)
    return step


def step_1_3_assess_continuance(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    pname = _name(primary)
    current = primary.get("employment", {}).get("current", {})
    w2_data = primary.get("income", {}).get("w2", [])
    w2_evidence = ""
    if len(w2_data) >= 2:
        w2_evidence = f"W-2 wages: ${w2_data[0].get('wages', 0):,.0f} ({w2_data[0].get('year')}), ${w2_data[1].get('wages', 0):,.0f} ({w2_data[1].get('year')}). "

    judgment = _call_llm_judge(
        state,
        "1.3",
        question=f"Is {pname}'s income at {current.get('employer', 'their employer')} likely to continue for at least 36 months?",
        evidence=(
            f"Employer: {current.get('employer', 'N/A')}, "
            f"Title: {current.get('title', 'N/A')}, "
            f"Start date: {current.get('start_date', 'N/A')}. "
            f"{w2_evidence}"
            f"Employment type: {current.get('type', 'W-2')}."
        ),
        rule_citation="FNMA B3-3.1-01: Income must be reasonably expected to continue for 3+ years",
    )

    step = TraceStep(
        step_id="1.3",
        title=f"Assess Income Continuance ({pname})",
        decision="PASS" if judgment["decision"] else "FLAG",
        rationale=f"LLM judgment: {judgment['reasoning']} (confidence: {judgment['confidence']:.0%})",
        rule_citation="FNMA B3-3.1-01: Income continuance requirement (36 months)",
        method="llm_judge",
        inputs={"borrower": pname, "employer": current.get("employer")},
        llm_judgment=judgment,
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_2_1_fixed_base(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    pname = _name(primary)
    inc = primary.get("income", {})
    paystub_annual = inc.get("paystub", {}).get("base_rate_annual", 0)

    w2_base = inc.get("w2_base")
    if w2_base is None:
        w2_list = inc.get("w2", [])
        w2_base = w2_list[0].get("wages", paystub_annual) if w2_list else paystub_annual

    variance = abs(paystub_annual - w2_base) / w2_base * 100 if w2_base > 0 else 0

    if variance < 10:
        base = paystub_annual
        rationale = (
            f"Paystub annual rate ${paystub_annual:,.0f} vs W-2 base ${w2_base:,.0f} — "
            f"variance {variance:.2f}% < 10% threshold. Using paystub rate."
        )
    else:
        base = min(paystub_annual, w2_base)
        rationale = (
            f"Paystub annual rate ${paystub_annual:,.0f} vs W-2 base ${w2_base:,.0f} — "
            f"variance {variance:.2f}% >= 10% threshold. Using lower value."
        )

    state.income["primary_base"] = base

    step = TraceStep(
        step_id="2.1",
        title=f"Fixed Base Income ({pname})",
        decision="PASS",
        result_value=base,
        result_label=f"${base:,.0f}/yr",
        rationale=rationale,
        rule_citation="FNMA B3-3.1-03: Base Pay — paystub vs W-2 variance < 10%",
        inputs={"paystub_annual": paystub_annual, "w2_base": w2_base, "variance_pct": round(variance, 2)},
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_2_2_overtime(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    ot = primary.get("income", {}).get("overtime")
    if not ot:
        return None

    pname = _name(primary)
    ot_2025 = ot.get("2025", 0)
    ot_2024 = ot.get("2024", 0)
    avg_24mo = (ot_2025 + ot_2024) / 2

    state.income["primary_overtime"] = avg_24mo

    step = TraceStep(
        step_id="2.2",
        title=f"Overtime Income ({pname})",
        decision="PASS",
        result_value=avg_24mo,
        result_label=f"${avg_24mo:,.0f}/yr",
        rationale=(
            f"OT 2025: ${ot_2025:,.0f}, OT 2024: ${ot_2024:,.0f}. "
            f"24-month average = ${avg_24mo:,.0f}. History requirement met."
        ),
        rule_citation="FNMA B3-3.1-04: Variable income requires 24-month history; use average",
        inputs={"ot_2025": ot_2025, "ot_2024": ot_2024, "avg_24mo": avg_24mo},
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_2_3_bonus(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    bonus = primary.get("income", {}).get("bonus")
    if not bonus:
        return None

    pname = _name(primary)
    bonus_2025 = bonus.get("2025", 0) or 0
    bonus_2024 = bonus.get("2024")

    if bonus_2024 is not None:
        avg = (bonus_2025 + bonus_2024) / 2
        state.income["primary_bonus"] = avg
        step = TraceStep(
            step_id="2.3",
            title=f"Bonus Income ({pname})",
            decision="PASS",
            result_value=avg,
            result_label=f"${avg:,.0f}/yr",
            rationale=(
                f"Bonus 2025: ${bonus_2025:,.0f}, 2024: ${bonus_2024:,.0f}. "
                f"24-month history present — average = ${avg:,.0f}."
            ),
            rule_citation="FNMA B3-3.1-04: Bonus income requires 24-month documented history",
            inputs={"bonus_2025": bonus_2025, "bonus_2024": bonus_2024, "avg": avg},
            duration_ms=int((time.time() - start) * 1000),
        )
    else:
        state.income["primary_bonus"] = 0
        step = TraceStep(
            step_id="2.3",
            title=f"Bonus Income ({pname})",
            decision="EXCLUDE",
            result_value=0,
            result_label="$0/yr (excluded)",
            rationale=(
                f"Bonus 2025: ${bonus_2025:,.0f}, 2024: none. "
                f"Only 1 year of history — requires 24 months per FNMA. Excluded."
            ),
            rule_citation="FNMA B3-3.1-04: Bonus income requires 24-month documented history",
            inputs={"bonus_2025": bonus_2025, "bonus_2024": bonus_2024, "history_months": 12},
            duration_ms=int((time.time() - start) * 1000),
        )

    state.trace.append(step)
    return step


def step_3_1_rsu(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    rsu = primary.get("income", {}).get("rsu")
    if not rsu:
        return None

    pname = _name(primary)
    vested_2025 = rsu.get("2025_vested", 0)
    has_3yr_forward = rsu.get("three_year_forward_continuance", False)

    if has_3yr_forward:
        state.income["primary_rsu"] = vested_2025
        step = TraceStep(
            step_id="3.1",
            title=f"RSU / Restricted Stock ({pname})",
            decision="PASS",
            result_value=vested_2025,
            result_label=f"${vested_2025:,.0f}/yr",
            rationale=(
                f"RSU vested 2025: ${vested_2025:,.0f}. "
                f"3-year forward continuance documented. Included in qualifying income."
            ),
            rule_citation="FNMA B3-3.3-07: RSU requires documented 3-year receipt history or forward continuance",
            inputs={"vested_2025": vested_2025, "three_year_forward": True},
            duration_ms=int((time.time() - start) * 1000),
        )
    else:
        state.income["primary_rsu"] = 0
        step = TraceStep(
            step_id="3.1",
            title=f"RSU / Restricted Stock ({pname})",
            decision="EXCLUDE",
            result_value=0,
            result_label="$0/yr (excluded)",
            rationale=(
                f"RSU vested 2025: ${vested_2025:,.0f}. "
                f"Grant date {rsu.get('grant_date', 'N/A')}, {rsu.get('vesting_schedule', 'N/A')}. "
                f"No 3-year forward continuance. Excluded."
            ),
            rule_citation="FNMA B3-3.3-07: RSU requires documented 3-year receipt history or forward continuance",
            inputs={"vested_2025": vested_2025, "three_year_forward": False},
            duration_ms=int((time.time() - start) * 1000),
        )

    state.trace.append(step)
    return step


def step_3_2_employment_gap(app, state):
    start = time.time()
    primary = _borrower(app, "primary")
    if not primary:
        return None

    gap = primary.get("employment", {}).get("gap")
    if not gap or gap.get("days", 0) == 0:
        return None

    history = primary.get("employment", {}).get("history", [])
    prior_employer = history[0].get("employer", "prior employer") if history else "prior employer"
    current_employer = primary.get("employment", {}).get("current", {}).get("employer", "current employer")

    step = TraceStep(
        step_id="3.2",
        title="Employment Gap Assessment",
        decision="FLAG",
        rationale=(
            f"{gap['days']}-day gap between {prior_employer} and {current_employer}. "
            f"Documentation provided. Flagged for audit trail, not income-affecting."
        ),
        rule_citation="AHL Overlay 4.2.1: Employment gaps > 30 days require written explanation + documentation",
        inputs={"gap_days": gap["days"], "documentation": gap.get("documentation", [])},
        duration_ms=int((time.time() - start) * 1000),
    )
    state.conditions.append(f"Employment gap documented ({gap['days']} days)")
    state.trace.append(step)
    return step


def step_4_1_se_tenure(app, state):
    start = time.time()
    co = _borrower(app, "co-borrower")
    if not co:
        return None

    emp = co.get("employment", {}).get("current", {})
    months_se = emp.get("months_self_employed", 0)
    state.se_tenure_months = months_se

    cname = _name(co)
    meets_standard = months_se >= 24
    meets_exception = months_se >= 12

    if meets_standard:
        suffix = "Meets standard tenure requirement."
    elif meets_exception:
        suffix = "Proceeding to same-field evaluation."
    else:
        suffix = "Below minimum threshold — SE income will be excluded."

    step = TraceStep(
        step_id="4.1",
        title=f"Self-Employment Tenure ({cname})",
        decision="PASS" if meets_standard else "FLAG",
        rationale=(
            f"{cname} self-employed {months_se} months (since {emp.get('start_date', 'N/A')}). "
            f"Standard requirement: 24 months — {'met' if meets_standard else 'NOT met'}. "
            f"Same-field exception threshold: 12 months — {'met' if meets_exception else 'NOT met'}. "
            f"{suffix}"
        ),
        rule_citation="FNMA B3-3.1-05: SE income; AHL 5.1: 24-mo requirement with same-field exception at 12-mo",
        inputs={
            "months_self_employed": months_se,
            "meets_24mo": meets_standard,
            "meets_12mo_exception": meets_exception,
        },
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_4_2_same_field(app, state):
    start = time.time()
    co = _borrower(app, "co-borrower")
    if not co:
        return None

    # Only relevant if tenure 12-24 months
    if state.se_tenure_months >= 24 or state.se_tenure_months < 12:
        return None

    same_field = co.get("income", {}).get("same_field_exception")
    if not same_field:
        return None

    cname = _name(co)
    prior_field = same_field.get("prior_field", "N/A")
    current_field = same_field.get("current_field", "N/A")
    prior = co.get("employment", {}).get("prior", {})
    prior_title = prior.get("title", "prior role")
    prior_employer = prior.get("employer", "prior employer")
    prior_salary = prior.get("final_annual_salary", 0)
    current_title = co.get("employment", {}).get("current", {}).get("title", "current role")

    judgment = _call_llm_judge(
        state,
        "4.2",
        question=(
            f"Is '{current_field}' ({current_title}) the same professional field as '{prior_field}' ({prior_title})?"
        ),
        evidence=(
            f"Prior role: {prior_title} at {prior_employer}, "
            f"W-2 employee, salary ${prior_salary:,.0f}. "
            f"Current role: {current_title}, 1099 self-employed {state.se_tenure_months} months. "
            f"Prior field: {prior_field}. Current field: {current_field}."
        ),
        rule_citation=(
            "FNMA B3-3.1-05: SE borrowers with < 24 months history may qualify if "
            "transitioning from same field of work."
        ),
    )

    state.se_same_field_pass = judgment["decision"] and judgment.get("meets_threshold", True)
    decision = "PASS" if state.se_same_field_pass else "FLAG"

    step = TraceStep(
        step_id="4.2",
        title=f"Same-Field Exception ({cname})",
        decision=decision,
        rationale=(
            f"LLM judgment: {judgment['reasoning']} "
            f"(confidence: {judgment['confidence']:.0%}). "
            f"Prior: {prior_field} -> Current: {current_field}. "
            f"Same-field exception {'applies' if decision == 'PASS' else 'does not apply'}."
        ),
        rule_citation="FNMA B3-3.1-05 + AHL 5.1.2: Same-field exception for SE tenure",
        method="llm_judge",
        inputs={"prior_field": prior_field, "current_field": current_field},
        llm_judgment=judgment,
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


def step_4_3_se_income(app, state):
    start = time.time()
    co = _borrower(app, "co-borrower")
    if not co:
        return None

    cname = _name(co)
    schedule_c = co.get("income", {}).get("schedule_c", {})
    sc_2025 = schedule_c.get("2025", {})
    form_1099 = co.get("income", {}).get("form_1099", {})

    net_profit = sc_2025.get("net_profit", 0)
    gross_1099 = form_1099.get("annualized_amount", 0)

    tenure = state.se_tenure_months
    qualifies = False
    exclude_reason = ""

    if tenure >= 24:
        qualifies = True
    elif tenure >= 12 and state.se_same_field_pass:
        qualifies = True
    elif tenure >= 12:
        exclude_reason = f"Same-field exception denied — {tenure} months tenure with different field"
    else:
        exclude_reason = f"Self-employed only {tenure} months — below 12-month minimum"

    if qualifies:
        state.income["co_borrower_se"] = net_profit
        step = TraceStep(
            step_id="4.3",
            title=f"Self-Employment Income Calculation ({cname})",
            decision="PASS",
            result_value=net_profit,
            result_label=f"${net_profit:,.0f}/yr",
            rationale=(
                f"1099 gross: ${gross_1099:,.0f}. Schedule C net profit: ${net_profit:,.0f}. "
                f"Per FNMA, use Schedule C net profit. "
                f"Tenure {tenure} months — {'standard requirement met' if tenure >= 24 else 'same-field exception applies'}."
            ),
            rule_citation="FNMA B3-3.1-05: SE income = Schedule C net profit",
            inputs={"gross_1099": gross_1099, "schedule_c_net": net_profit, "tenure_months": tenure},
            duration_ms=int((time.time() - start) * 1000),
        )
    else:
        state.income["co_borrower_se"] = 0
        step = TraceStep(
            step_id="4.3",
            title=f"Self-Employment Income Calculation ({cname})",
            decision="EXCLUDE",
            result_value=0,
            result_label="$0/yr (excluded)",
            rationale=(
                f"1099 gross: ${gross_1099:,.0f}. Schedule C net profit: ${net_profit:,.0f}. "
                f"{exclude_reason}. Excluded from qualifying income."
            ),
            rule_citation="FNMA B3-3.1-05: SE income tenure requirements not met",
            inputs={"gross_1099": gross_1099, "schedule_c_net": net_profit, "tenure_months": tenure},
            duration_ms=int((time.time() - start) * 1000),
        )

    state.trace.append(step)
    return step


def step_5_1_large_deposits(app, state):
    start = time.time()
    deposits = app.get("bank_deposits", {}).get("large_deposits", [])
    if not deposits:
        return None

    for i, dep in enumerate(deposits):
        docs = dep.get("documentation", {})
        fully_documented = (
            docs.get("gift_letter", False)
            and docs.get("donor_bank_statement", False)
            and docs.get("transfer_evidence", False)
        )

        if fully_documented:
            decision = "PASS"
            rationale = (
                f"${dep['amount']:,.0f} deposit on {dep.get('date', 'N/A')}. "
                f"Source: {dep.get('source_claimed', 'N/A')}. Fully documented."
            )
        else:
            decision = "FLAG"
            missing = []
            if not docs.get("gift_letter"):
                missing.append("gift letter")
            if not docs.get("donor_bank_statement"):
                missing.append("donor bank statement")
            if not docs.get("transfer_evidence"):
                missing.append("transfer evidence")
            rationale = (
                f"${dep['amount']:,.0f} deposit on {dep.get('date', 'N/A')}. "
                f"Source: {dep.get('source_claimed', 'N/A')}. "
                f"Missing: {', '.join(missing)}. "
                f"Exceeds AHL ${dep.get('overlay_threshold', 3000):,.0f} threshold."
            )
            state.flags.append(f"Large deposit ${dep['amount']:,.0f} — incomplete documentation")

        step = TraceStep(
            step_id=f"5.{i + 1}",
            title=f"Large Deposit Review #{i + 1}",
            decision=decision,
            result_value=dep["amount"],
            result_label=f"${dep['amount']:,.0f} {'documented' if fully_documented else 'flagged'}",
            rationale=rationale,
            rule_citation="AHL Overlay 6.1: Deposits > $3,000 require source documentation",
            inputs={
                "amount": dep["amount"],
                "threshold": dep.get("overlay_threshold", 3000),
                "documented": fully_documented,
            },
            duration_ms=int((time.time() - start) * 1000),
        )
        state.trace.append(step)

    return None  # multiple entries appended directly


def step_6_1_aggregate(app, state):
    start = time.time()
    inc = state.income
    total = sum(inc.values())
    monthly = round(total / 12, 2)

    state.total_annual = total
    state.total_monthly = monthly

    parts = [f"{k.replace('_', ' ').title()}: ${v:,.0f}" for k, v in inc.items()]

    step = TraceStep(
        step_id="6.1",
        title="Aggregate Qualifying Income",
        decision="PASS",
        result_value=monthly,
        result_label=f"${monthly:,.2f}/mo",
        rationale=(
            f"{' + '.join(parts)} = "
            f"${total:,.0f}/yr = ${monthly:,.2f}/mo. "
            f"Flags: {len(state.flags)}, Conditions: {len(state.conditions)}."
        ),
        rule_citation="FNMA B3-3.1-01: Total qualifying income aggregation",
        inputs={
            "components": inc,
            "total_annual": total,
            "total_monthly": monthly,
            "flag_count": len(state.flags),
        },
        duration_ms=int((time.time() - start) * 1000),
    )
    state.trace.append(step)
    return step


# ============================================================
# ORCHESTRATOR
# ============================================================

ALL_STEPS = [
    step_1_1_classify_income,
    step_1_2_verify_employment,
    step_1_3_assess_continuance,
    step_2_1_fixed_base,
    step_2_2_overtime,
    step_2_3_bonus,
    step_3_1_rsu,
    step_3_2_employment_gap,
    step_4_1_se_tenure,
    step_4_2_same_field,
    step_4_3_se_income,
    step_5_1_large_deposits,
    step_6_1_aggregate,
]


def run_engine(app: dict = None, on_step=None, mock_llm_judge=None) -> dict:
    """
    Run the full income verification engine.

    Args:
        app: Application JSON. Loads sample_application.json if None.
        on_step: Optional callback(TraceStep) called after each step completes.
        mock_llm_judge: Optional dict of step_id -> judgment for deterministic test runs.

    Returns:
        dict with trace, summary, income, flags, conditions, and optionally naive_comparison.
    """
    if app is None:
        app = load_sample_application()

    state = EngineState()
    if mock_llm_judge:
        state.mock_llm_judge = mock_llm_judge

    engine_start = time.time()

    for step_fn in ALL_STEPS:
        trace_before = len(state.trace)
        step_fn(app, state)
        # Call on_step for any new trace entries
        if on_step:
            for s in state.trace[trace_before:]:
                on_step(s)

    total_duration = int((time.time() - engine_start) * 1000)

    # Build naive comparison from application expected_results if available
    expected = app.get("expected_results", {})
    naive = expected.get("naive_extraction", {})
    naive_annual = naive.get("total_annual", 0)
    naive_monthly = naive.get("total_monthly", 0)

    result = {
        "trace": [asdict(s) for s in state.trace],
        "summary": {
            "total_annual": state.total_annual,
            "total_monthly": state.total_monthly,
            "qualifying_monthly_income": state.total_monthly,
            "flag_count": len(state.flags),
            "condition_count": len(state.conditions),
            "step_count": len(state.trace),
            "duration_ms": total_duration,
        },
        "income": state.income,
        "flags": state.flags,
        "conditions": state.conditions,
    }

    if naive_annual > 0:
        result["naive_comparison"] = {
            "naive_annual": naive_annual,
            "naive_monthly": naive_monthly,
            "rule_applied_annual": state.total_annual,
            "rule_applied_monthly": state.total_monthly,
            "gap_annual": naive_annual - state.total_annual,
            "gap_monthly": round(naive_monthly - state.total_monthly, 2),
        }

    return result


if __name__ == "__main__":
    result = run_engine()
    print(json.dumps(result, indent=2))
    print(f"\nMonthly qualifying income: ${result['summary']['total_monthly']:,.2f}")
