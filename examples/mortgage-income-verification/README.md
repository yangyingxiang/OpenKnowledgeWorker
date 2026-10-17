# Example: Mortgage Income Verification

Determine a borrower's **qualifying monthly income** for a mortgage application from W-2s,
paystubs, tax returns, and bank statements, following the Fannie Mae Selling Guide plus a
stricter lender overlay.

This is a good showcase for OpenKnowledgeWorker because the rules are detailed, publicly
documented, and produce answers that are provably right or wrong, and because the lender
overlay deliberately conflicts with or leaves gaps in the agency guide. Resolving those
conflicts is the work the SME chat is built for.

> All lender, borrower, and employer names are fictional. This repository does not
> include third-party documents. Download the Fannie Mae sections yourself from the links
> below.

## Contents

| Path | What it is |
|---|---|
| `pack.json` | Domain pack manifest: sources, output contract, test cases, guidance ([format](../README.md)). |
| `agent_guidance.md` | Mortgage-specific calculation rules handed to the coding and execution agents. |
| `sources/lender_overlay.html` | A fictional mortgage lender's internal overlay ("AHL v4.2"), with stricter and intentionally ambiguous rules. |
| `sample_application.json` | A full two-borrower application (W-2 + self-employed co-borrower, RSUs, a large deposit, an employment gap). |
| `test_cases/*.json` | Five golden test cases with expected totals, per-step decisions (numbered for the reference engine), and mock LLM-judge responses. |
| `test_cases.jsonl` | The same cases in the app's import format (**Test Suite → Upload Tests**). These check only PDD-independent outputs (annual and monthly totals, flag count), so they hold for any PDD version. |
| `sample_outputs/` | A PDD, knowledge base, and open-questions list as produced by the research phase. |
| `reference_engine/` | A hand-written engine (`engine/` package) implementing the PDD, with the same `run_engine(case)` contract as generated code. |

## Source documents

The example uses two kinds of sources:

1. **Fannie Mae Selling Guide, income sections (B3-3).** Not included in this repository.
   Open each link below and save the page (for example, *Print → Save as PDF*) into
   `sources/third_party/`. That folder is git-ignored, so the downloads stay local.

   | Section | Title |
   |---|---|
   | B3-3.1-01 | [General Income Information](https://selling-guide.fanniemae.com/sel/b3-3.1-01/general-income-information) |
   | B3-3.1-04 | [Verbal Verification of Employment](https://selling-guide.fanniemae.com/sel/b3-3.1-04/verbal-verification-employment) |
   | B3-3.2-01 | [Standards for Employment and Income Documentation](https://selling-guide.fanniemae.com/sel/b3-3.2-01/standards-employment-and-income-documentation) |
   | B3-3.2-02 | [Standards for Employment-Related Income](https://selling-guide.fanniemae.com/sel/b3-3.2-02/standards-employment-related-income) |
   | B3-3.3-01 | [Base Income](https://selling-guide.fanniemae.com/sel/b3-3.3-01/base-income) |
   | B3-3.3-02 | [Bonus, Commission, Overtime, and Tip Income](https://selling-guide.fanniemae.com/sel/b3-3.3-02/bonus-commission-overtime-and-tip-income) |
   | B3-3.3-03 | [Employment Offers or Contracts](https://selling-guide.fanniemae.com/sel/b3-3.3-03/employment-offers-or-contracts) |
   | B3-3.3-07 | [Restricted Stock Units and Restricted Stock Employment Income](https://selling-guide.fanniemae.com/sel/b3-3.3-07/restricted-stock-units-and-restricted-stock-employment-income) |
   | B3-3.4-01 | [General Requirements for Other Sources of Income](https://selling-guide.fanniemae.com/sel/b3-3.4-01/general-requirements-other-sources-income) |
   | B3-3.5-01 | [Underwriting Factors and Documentation for a Self-Employed Borrower](https://selling-guide.fanniemae.com/sel/b3-3.5-01/underwriting-factors-and-documentation-self-employed-borrower) |

   The section numbers above follow the guide's March 2026 reorganization. The sample
   outputs and test cases cite some sections by their older numbers (for example, B3-3.1-05
   for self-employment, now B3-3.5-01).

2. **`sources/lender_overlay.html`**: a fictional lender's overlay written for this
   example and included in the repository.

## Using it in the app

**Quickest:** click **Load example** on the processes page (or run `python backend/seed.py`).
That creates a fully populated process: the overlay document, a PDD, knowledge, open
questions, the five golden tests, and the reference engine as a completed code project.
Go to **Test Suite**, choose **CODE**, and press **Run All**. No API key is needed.

**From scratch, with an LLM API key:**

1. Create a process (name: *Income Verification*, domain: *Mortgage Underwriting*).
2. On the **Documents** tab, upload the Fannie Mae pages you saved in `sources/third_party/`
   and `sources/lender_overlay.html`.
3. In **SOP Studio**, run research. Compare your result with `sample_outputs/pdd.md`.
4. Answer the open questions in the chat, for example the overlay's undefined
   "significant income variance" threshold.
5. Upload `test_cases.jsonl` in the **Test Suite**, generate code in the **Code Agent** tab,
   and run the tests in CODE, LLM, or side-by-side mode.

## Reference engine

`reference_engine/engine/income_engine.py` implements each PDD step as a plain Python function
(`step_1_1_classify_income` … `step_6_1_aggregate`). It emits a step-by-step decision trace
with a rule citation for each step. Two steps, income continuance (1.3) and the
self-employment same-field exception (4.2), need semantic judgement and call
`engine/llm_judge.py`. The test cases supply mock judge responses, so the suite runs offline:

```bash
cd reference_engine
python test_runner.py        # readable report
pytest                       # same cases as a pytest suite
```

To run the engine against the live judge, set `ANTHROPIC_API_KEY`. You can override the
judge model with `JUDGE_MODEL`.
