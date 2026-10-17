# Good First Issues

Well-scoped starter tasks, grounded in the current code. Each one is meant to be filed as a
GitHub issue; maintainers should copy the title, context, acceptance criteria, and labels.
If you want to pick one up, comment on its issue first so work is not duplicated.

Before starting, read [architecture.md](architecture.md) and
[CONTRIBUTING.md](../CONTRIBUTING.md). Backend tests run on in-memory SQLite with no API key:
`cd backend && pytest`.

---

## Backend tests

### 1. Unit tests for document chunking

- **Context:** `backend/app/services/document_ingestion.py` extracts text and splits it into
  heading-aware chunks (`extract_chunks`, `_chunk_structured_text`, `_split_by_headings`,
  `_split_paragraphs`, `_chunk_pdf_text`). None of these are covered in `backend/tests/`.
- **Acceptance criteria:**
  - New `backend/tests/test_document_ingestion.py` covering Markdown and HTML inputs with nested
    headings, a document with no headings, and a very long paragraph.
  - Asserts heading paths and that chunk text concatenates back to the source content (modulo
    whitespace).
  - Uses small inline fixtures or files under `backend/tests/fixtures/`; no network.
- **Labels:** `good first issue`, `backend`, `tests`

### 2. Unit tests for code-to-PDD mapping

- **Context:** `backend/app/services/code_mapping.py` parses generated Python into `CodeUnit`s
  (`_extract_functions`, `_detect_step_id`, `_detect_rule_ids`) and flags stale units
  (`detect_stale_units`). These heuristics have no tests.
- **Acceptance criteria:**
  - New `backend/tests/test_code_mapping.py`.
  - Covers step IDs in function names (`step_1_1_...`) and docstrings, rule IDs such as
    `BR-101`, nested functions, and a function at end of file.
  - At least one test for `detect_stale_units` using the SQLite fixtures in
    `backend/tests/conftest.py`.
- **Labels:** `good first issue`, `backend`, `tests`

### 3. Unit tests for the evidence service

- **Context:** `backend/app/services/evidence.py` extracts PDD statements, builds evidence spans
  from chunks, auto-links them by keyword overlap (`_extract_keywords`, `auto_link_evidence`),
  and computes document-removal impact.
- **Acceptance criteria:**
  - New `backend/tests/test_evidence_service.py` covering `hash_statement`,
    `_extract_keywords`, `extract_pdd_statements`, and `get_impact_of_document_removal` on a
    small seeded process.
  - Tests run on SQLite with no API key.
- **Labels:** `good first issue`, `backend`, `tests`

### 4. Unit tests for the golden-dataset validator

- **Context:** `validate_engine_output()` in `backend/app/services/golden_datasets.py` checks an
  engine's `trace_steps` against `expected_behaviors` (step patterns and minimum counts) and
  `expected_step_count_range`.
- **Acceptance criteria:**
  - New `backend/tests/test_golden_datasets.py` with passing and failing outputs for at least
    two datasets, plus an unknown dataset name.
  - Covers wildcard step patterns (`'1.*'`, `'*'`).
- **Labels:** `good first issue`, `backend`, `tests`

## Frontend features for existing APIs

### 5. Agent-run transcript viewer

- **Context:** Coding-agent runs are recorded by `TranscriptRecorder`
  (`backend/app/services/transcript.py`) and exposed by `backend/app/api/transcripts.py`
  (`GET /transcripts`, `/transcripts/<session_key>`, `/transcripts/<session_key>/summary`).
  There is no UI. The session key for a coding run is the code project ID.
- **Acceptance criteria:**
  - Client functions in `frontend/src/lib/api.ts`.
  - A "Transcript" panel or tab on `frontend/src/app/processes/[id]/code/page.tsx` listing model
    requests, responses, tool calls, and tool results in order, with the summary (token
    counts, tool counts) at the top.
  - Large tool outputs are collapsed by default.
- **Labels:** `good first issue`, `frontend`

### 6. PDD version diff view

- **Context:** `GET /pdd/diff/<v1_id>/<v2_id>` in `backend/app/api/pdd.py` returns a unified diff
  between two PDD versions, and `api.listPddVersions` already exists in
  `frontend/src/lib/api.ts`, but no page shows diffs.
- **Acceptance criteria:**
  - In the SOP Studio (`frontend/src/app/processes/[id]/pdd/page.tsx`), the user can pick two
    versions and see the diff with added and removed lines highlighted.
  - Each version shows its `change_source` and `change_summary`.
- **Labels:** `good first issue`, `frontend`

### 7. Warn before deleting a document that the PDD depends on

- **Context:** `GET /evidence/impact/<document_id>` (`backend/app/api/evidence.py`) returns the
  PDD statements that would lose evidence if a document is removed. The delete action in
  `frontend/src/app/processes/[id]/documents/page.tsx` does not use it.
- **Acceptance criteria:**
  - The delete confirmation dialog fetches the impact and lists affected statements (or says
    none are affected).
  - If the evidence graph has not been built, the dialog still works.
- **Labels:** `good first issue`, `frontend`

### 8. Show stale code units after a PDD change

- **Context:** `GET /coding/projects/<project_id>/mapping/stale`
  (`backend/app/api/coding_agent.py`, backed by `detect_stale_units` in
  `backend/app/services/code_mapping.py`) reports functions whose PDD step changed since
  generation. The Code page does not surface this.
- **Acceptance criteria:**
  - Client function in `frontend/src/lib/api.ts`.
  - The Code page shows a badge on stale files and a list of stale functions with the reason.
- **Labels:** `good first issue`, `frontend`

### 9. Evidence graph viewer (first version)

- **Context:** The experimental evidence API (`backend/app/api/evidence.py`) can build the graph
  (`POST /evidence/build`), list statements (`GET /evidence/statements`), return evidence for
  one statement, and report stats. No UI uses it.
- **Acceptance criteria:**
  - A "Build evidence graph" action and a stats summary in the SOP Studio.
  - Selecting a PDD statement shows its linked evidence spans (document, heading path, text)
    and link type (`supports`, `contradicts`, `elaborates`).
  - A simple list view is fine; a graph visualization can come later.
- **Labels:** `good first issue`, `frontend`, `help wanted`

## Frontend platform

### 10. Dark mode using the existing CSS variables

- **Context:** Colors are defined as `--okw-*` variables in `frontend/src/app/globals.css`, but
  there is no dark theme, and some components use hard-coded hex colors or Tailwind gray
  utilities instead of the variables.
- **Acceptance criteria:**
  - A `@media (prefers-color-scheme: dark)` block in `globals.css` redefines the `--okw-*` and
    `--background`/`--foreground` variables.
  - Hard-coded colors in `frontend/src/app/processes/[id]/layout.tsx`,
    `frontend/src/components/shared/ChatSidebar.tsx`, and
    `frontend/src/app/processes/[id]/documents/page.tsx` are replaced with variables (other
    pages, such as the PDD views, can follow in separate PRs).
  - Text contrast meets WCAG AA in both themes.
- **Labels:** `good first issue`, `frontend`, `design`

### 11. Test the stream-resume logic in `useSSE`

- **Context:** `frontend/src/lib/useSSE.ts` re-attaches to a background job
  (`GET /api/jobs/<job_id>/events?after=<n>`) when a stream drops before its terminal event.
  The pure parser in `frontend/src/lib/sse.ts` is unit-tested with Vitest, but the hook's
  resume behaviour is not.
- **Acceptance criteria:**
  - Extract the resume decision (when to retry, which `after` value to send, de-duplication by
    `_seq`) into a pure function, or test the hook with a mocked `fetch`.
  - Cover: stream ends after a terminal event (no resume), stream drops mid-job (resumes
    from the last `_seq`), non-job streams (never resume), duplicate events skipped.
  - `pnpm test` passes.
- **Labels:** `good first issue`, `frontend`, `tests`

### 12. Internationalization scaffolding

- **Context:** All UI strings are hard-coded in English, for example the navigation labels in
  `NAV_ITEMS` in `frontend/src/app/processes/[id]/layout.tsx`.
- **Acceptance criteria:**
  - Add an i18n library compatible with the Next.js App Router (for example `next-intl`) with an
    English message catalog.
  - Migrate the process layout navigation and the processes list page
    (`frontend/src/app/processes/page.tsx`) to use it.
  - Document how to add a locale in a short section of `docs/`.
- **Labels:** `good first issue`, `frontend`, `i18n`

## API and docs

### 13. Generate an OpenAPI spec for the REST API

- **Context:** Routes are spread across blueprints in `backend/app/api/` with no machine-readable
  description. Contributors and integrators have to read the code.
- **Acceptance criteria:**
  - A script (for example `backend/scripts/export_openapi.py`) that walks `app.url_map` and
    emits an OpenAPI 3 document with paths, methods, path parameters, and the route docstring
    as the summary. Request/response schemas can be added incrementally.
  - SSE endpoints are marked as returning `text/event-stream`.
  - A test that the script runs and produces valid JSON.
- **Labels:** `good first issue`, `backend`, `documentation`

### 14. Add a new domain pack

- **Context:** The only end-to-end example is
  `examples/mortgage-income-verification/`. More domains test how general the prompts are
  (see the [roadmap](../ROADMAP.md)). Good candidates: accounts payable invoice matching,
  procurement purchase approvals, KYC/AML onboarding.
- **Acceptance criteria:**
  - Open a proposal with the domain pack issue template
    (`.github/ISSUE_TEMPLATE/domain_pack.yml`) first, including source licensing.
  - A new directory under `examples/` with a README (sources with URLs, how to run), synthetic
    sample input, and at least three golden test cases in JSONL using the same shape as
    `examples/mortgage-income-verification/test_cases.jsonl`.
  - No real personal data; only redistributable sources are committed.
- **Labels:** `good first issue`, `domain-pack`, `help wanted`
