# Domain packs

A **domain pack** is a self-contained example process. Packs are how OpenKnowledgeWorker
learns a new domain without changes to the core: the agents' prompts are domain-neutral,
and everything domain-specific comes from the pack.

| Pack | Domain |
|---|---|
| [`mortgage-income-verification`](mortgage-income-verification/) | Mortgage underwriting: qualifying income from W-2s, paystubs, tax returns |

Load packs into a running database with `python backend/seed.py` (Docker does this on
first start). The UI's **Load example** button calls the `POST /api/domain-packs/<id>/install` endpoint.

## Pack layout

```text
examples/<pack-id>/
├── pack.json              manifest (validated by domain-pack.schema.json)
├── README.md              what the process is, where the sources come from
├── sources/               documents you are allowed to redistribute (synthetic or your own)
├── sample_input.json      one realistic case
├── test_cases.jsonl       golden test cases
├── agent_guidance.md      domain hints for the agents (optional)
├── sample_outputs/        pre-generated PDD / knowledge / questions (optional)
└── reference_engine/      hand-written engine/ package (optional)
```

## `pack.json`

| Field | Purpose |
|---|---|
| `id`, `name`, `domain`, `description` | Required. `id` must equal the folder name. |
| `key_inputs`, `key_outputs` | Shown on the process and given to the agents. |
| `sources` | `{title, path}` for bundled files, `{title, url}` for third-party documents. **Never bundle third-party documents** — link to them. |
| `sample_input` | An example case (file path or inline object). It tells the coding agent what input to expect. |
| `test_cases` | JSONL with `test_name`, `description`, `input_data`, `expected_assertions`, `mock_llm_judge`. |
| `output_contract.summary` | Keys the engine's `summary` must contain, with descriptions. Golden tests assert on them. |
| `agent_guidance` | Domain rules and conventions the generic prompts can't know (Markdown). |
| `reference_code` | Folder with an `engine/` package exposing `engine/engine.py:run_engine(case)`. Installed as a completed code project, so code-mode tests work without an API key. |
| `sample_outputs` | `pdd`, `knowledge`, `questions` Markdown files (same formats as the mortgage pack). |

## Golden test assertions

`expected_assertions` maps keys of the engine result's `summary` to expected values:

- numbers match within ±1, other scalars match exactly;
- objects match as a subset, e.g. `{"step_decisions": {"2.1": "PASS"}}` checks only step 2.1;
- `min_flag_count` is built in: `len(summary.flags) >= n`.

Prefer assertions on **outputs** (totals, decisions, flags). Step-numbered assertions
such as `step_decisions` only hold for one particular PDD. A regenerated or edited PDD can
number its steps differently and fail them even when every result is right. Keep
step-level checks for a reference engine's own tests.

If a step needs semantic judgment (an "LLM judge"), record the expected judgment per
step in `mock_llm_judge` so tests stay deterministic. Engines receive it when their
`run_engine` accepts a `mock_llm_judge` argument.

## Contributing a pack

1. Copy `mortgage-income-verification/` as a starting point and edit `pack.json`.
2. Use synthetic data only: no real people, customers, or organizations.
3. Run `cd backend && pytest tests/test_domain_packs.py`; the bundled packs are validated in CI.
4. Open a pull request using the **Domain pack** issue/PR template.
