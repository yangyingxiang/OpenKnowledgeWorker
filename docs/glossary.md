# Glossary

Terms used throughout OpenKnowledgeWorker's code, UI, and documentation.

### PDD — Process Definition Document

The central artifact: a structured Markdown document describing how a process works,
written by the research agent and refined through SME chat. It has fixed sections — purpose,
key concepts, variable reference, outputs, process (phases and steps), business rules, and
decision priority summary. The required format is defined in `RESEARCH_SYSTEM_PROMPT` in
`backend/app/agent/prompts.py`. Every edit creates a new, append-only `PddVersion`.
The UI presents the PDD in the **SOP Studio**.

### PDL — Process Description Language

Structured pseudo-code embedded in each PDD step inside an HTML comment
(`<!-- pdl ... -->`), so it is invisible in rendered Markdown but machine-readable. PDL uses
the keywords `GIVEN`, `DECIDE`, `IF` / `ELSE IF` / `ELSE`, `SET`, `RETURN`, `FOR EACH`,
`IN`, `AND`, `OR`, and `NOT`. Every `DECIDE` must end with an `ELSE` default, and variable
names must match the PDD's Variable Reference table exactly. The coding agent and the
LLM execution mode follow PDL literally.

```text
<!-- pdl
GIVEN months_documented, overtime
DECIDE overtime_treatment:
  IF months_documented >= 24:
    SET overtime_annual = average(overtime)
  ELSE:
    SET overtime_annual = 0
RETURN overtime_annual
-->
```

### Knowledge item

A discrete fact the agent has learned about the process (`KnowledgeItem`), grouped by
section and linked to its source (document, conversation, research, or test case). Each has
a confidence of:

- **TENTATIVE** — inferred or uncertain; needs SME confirmation.
- **CONFIRMED** — stated explicitly by a source or confirmed by an SME.

### Open question

A question the agent raises for an SME when sources are ambiguous, conflict, or are silent
(`Question`). Questions have a display ID, priority, target roles, and the related PDD
section, and move from `OPEN` to `ANSWERED` (or `DISMISSED`). Answering one in chat
typically triggers a PDD edit.

### Overlay

An organization's internal policy that adds to, tightens, or overrides a public or
regulatory source — for example, a lender's overlay on top of the Fannie Mae Selling Guide.
Overlays are a main source of conflicts and open questions. The mortgage example ships a
fictional one at `examples/mortgage-income-verification/sources/lender_overlay.html`.

### Golden test case

A curated input with expected outcomes (`TestCase`): `input_data`, `expected_assertions`
(totals, per-step decisions and values), and optional `mock_llm_judge` responses so the case
can run offline. Golden cases are imported as CSV or JSONL and run against the generated code,
the LLM-only execution, or both.

### LLM judge

A bounded LLM call used inside otherwise deterministic generated code, only for steps that
require semantic judgement (for example, whether a borrower's prior and current jobs are in
the "same field"). Trace steps record `method: "llm_judge"` versus `"deterministic"`.
Tests can supply mock judge responses. See
`examples/mortgage-income-verification/reference_engine/engine/llm_judge.py`.

### Provenance / evidence span

How a PDD statement is traced to where it came from.

- **Provenance** (`Provenance`): a sentence-level record, written on every PDD edit, of the
  source type (research, conversation, document, test case) and detail behind each new
  sentence.
- **Evidence span** (`EvidenceSpan`): an exact excerpt of a source document chunk (text,
  offset, heading path, page). `EvidenceLink` connects a `PddStatement` to spans as
  `supports`, `contradicts`, or `elaborates`, forming the evidence graph.

### Domain pack

A self-contained bundle for applying OpenKnowledgeWorker to one domain: public source
documents (or links to them), synthetic sample inputs, golden test cases, expected outputs,
and any domain-specific prompt guidance. The mortgage income verification example is the
reference. Propose a new one with the domain pack issue template.

### SME — Subject-Matter Expert

The person who knows how the process really works — a loan underwriter, compliance analyst, or
compliance analyst. SMEs answer open questions in chat; their answers become knowledge items,
PDD edits, and provenance records.

### Trace step

One entry in the step-by-step output of generated code or LLM execution: step ID, decision
(`PASS`, `FLAG`, `EXCLUDE`, `SKIP`), result value, rule citation, rationale, and method.
The test suite compares trace steps between code and LLM modes and against assertions.

### Code unit

A function in a generated project mapped to a PDD step ID and business-rule IDs (`CodeUnit`).
Code units are marked stale when the PDD steps they implement change.
