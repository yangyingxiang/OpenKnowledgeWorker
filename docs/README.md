# Documentation

## Using and contributing

- [Architecture: how it works today](architecture.md) — request flow, agent loops, SSE,
  data model, and where to add endpoints, tools, models, and migrations.
- [Glossary](glossary.md) — PDD, PDL, knowledge items, open questions, overlays, golden test
  cases, LLM judge, provenance, domain packs, SMEs.
- [Good first issues](good-first-issues.md) — well-scoped starter tasks.
- [Contributing guide](../CONTRIBUTING.md)
- [Mortgage income verification example](../examples/mortgage-income-verification/README.md)

## Project

- [Roadmap](../ROADMAP.md)
- [Changelog](../CHANGELOG.md)
- [Security policy](../SECURITY.md)
- [Code of conduct](../CODE_OF_CONDUCT.md)

## Vision: target architecture

These documents describe the long-term target design. Much of it — tenants, governance
approvals, immutable releases, the Process IR — is **not implemented yet**.

- [Vision overview](vision/README.md)
- [System design](vision/system-design.md)
- [Component diagram](vision/component-diagram.md)
- [Memory and collaboration-state design](vision/memory-and-collaboration-design.md)
- Sequence diagrams:
  - [Use-case intake and source ingestion](vision/sequence-01-use-case-intake.md)
  - [Research and claim review](vision/sequence-02-research-and-claim-review.md)
  - [SME elicitation](vision/sequence-03-sme-elicitation.md)
  - [Process review and publication](vision/sequence-04-process-approval.md)
  - [Automation design and code generation](vision/sequence-05-automation-generation.md)
  - [Offline verification, repair, and release](vision/sequence-06-verification-and-release.md)
  - [Long-term process and automation maintenance](vision/sequence-07-maintenance.md)
