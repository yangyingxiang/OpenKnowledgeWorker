# Roadmap

This roadmap describes where OpenKnowledgeWorker is headed. It is a statement of direction,
not a commitment to dates. Priorities shift with user feedback and contributions.

Items marked **help wanted** are good places to contribute. Comment on the linked issue (or
open one) before starting larger work so we can agree on the approach. Smaller starter tasks
are listed in [docs/good-first-issues.md](docs/good-first-issues.md).

For how the system works today, see [docs/architecture.md](docs/architecture.md). For the
long-term target design, see [docs/vision/](docs/vision/README.md).

## Near term — v0.2

Goal: make OpenKnowledgeWorker usable beyond the mortgage example and safe to run for a small
team.

- **More domain packs.** The prompts are domain-neutral and domain specifics live in
  [domain packs](examples/README.md). Each new pack (see mid-term ideas) proves the design and
  surfaces remaining domain assumptions. *help wanted.*
- **Local and alternative models.** OpenAI-compatible endpoints (OpenAI, Ollama, vLLM,
  LiteLLM) are supported through `backend/app/llm/`. Test and document which models work well
  for research, chat and coding. *help wanted: test and document local models.*
- **Container sandbox for generated code.** Run coding-agent tests and test-suite executions
  in an isolated container (no network, read-only base, resource limits) instead of a
  same-user subprocess. *help wanted.*
- **Authentication and roles.** OIDC sign-in and basic roles (owner, SME, engineer, viewer)
  so the app can run on a shared network. Actor identity recorded in the audit log.
- **Durable job queue.** Research, coding and test runs already run as background jobs with
  resumable event streams (in-process). Next: persist events, survive server restarts,
  support cancellation and multiple backend workers (e.g. Redis-backed). *help wanted.*

## Mid term

Goal: close the loop from an approved process to a reviewable, exportable release.

- **Approval workflow and release export.** Explicit review and approval of PDD versions;
  immutable, exportable release bundles (PDD, generated code, test cases, verification report,
  evidence links).
- **Evidence graph UI.** A viewer for the statement-to-evidence links, change history, and
  document-removal impact already exposed by the experimental `/evidence` API.
  *help wanted: frontend.*
- **Transcript and meeting ingestion UI.** Ingest SME interview and meeting transcripts as
  first-class evidence, and expose agent-run transcripts (the experimental `/transcripts` API)
  for debugging. *help wanted: frontend.*
- **More domain packs**, each with public sources, synthetic inputs, and golden test cases.
  *help wanted — propose one with the
  [domain pack template](.github/ISSUE_TEMPLATE/domain_pack.yml):*
  - KYC/AML customer onboarding
  - Accounts payable invoice matching (two- and three-way match)
  - Procurement purchase-request approvals (approval limits, segregation of duties)

## Long term

Goal: the target architecture described in [docs/vision/](docs/vision/README.md).

- **Process IR as the canonical model.** A typed Process Intermediate Representation with
  stable step and rule identifiers; the PDD, PDL, and diagrams become projections of it.
- **Claims, conflicts, and decisions.** Source evidence produces proposed claims; conflicts are
  reconciled and recorded as decisions with effective dates, rather than edited directly into
  the PDD.
- **Maintenance workflow.** When a source changes, compute the impact on process rules, code,
  and tests; generate a targeted upgrade; rerun full regression against the prior release.
- **Governance and multi-tenancy.** Tenant isolation, fine-grained authorization on every read,
  mutation, tool call, and export, and a tamper-evident audit trail.
- **Durable, checkpointed agent runtime.** Agents propose and domain services decide; agent runs
  are checkpointed, budgeted, and resumable.
- **Provider and source-system portability.** Connectors to document stores and ticketing
  systems; model providers accessed only through contracts.
