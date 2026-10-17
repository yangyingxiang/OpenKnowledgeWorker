# OpenKnowledgeWorker Vision: Target Architecture

> **Note:** The documents in this directory describe the **target architecture / long-term vision**
> for OpenKnowledgeWorker — including tenants, governance approvals, immutable releases, and a
> durable event bus. Much of this is **not implemented yet**. For how the code works today, see
> [`../architecture.md`](../architecture.md). For what is planned next, see the
> [roadmap](../../ROADMAP.md).

This directory contains architecture-review diagrams for the target design defined in [`system-design.md`](system-design.md).

Each user flow has its own sequence diagram so it can be reviewed, discussed, and revised independently.

## Component view

- [Component Diagram](component-diagram.md)
- [Memory and Collaboration-State Design](memory-and-collaboration-design.md)

## User-flow sequence views

- [Use-Case Intake and Source Ingestion](sequence-01-use-case-intake.md)
- [Research and Claim Review](sequence-02-research-and-claim-review.md)
- [SME Elicitation](sequence-03-sme-elicitation.md)
- [Process Review and Publication](sequence-04-process-approval.md)
- [Automation Design and Code Generation](sequence-05-automation-generation.md)
- [Offline Verification, Repair, and Release](sequence-06-verification-and-release.md)
- [Long-Term Process and Automation Maintenance](sequence-07-maintenance.md)

## Diagram conventions

- Solid calls represent synchronous API or application-interface calls.
- Dashed calls represent responses.
- Events are explicitly labeled and are delivered through the durable event bus/outbox path.
- Published `ProcessVersion`, `AutomationPackage`, `BuildCandidate`, verification reports, and `Release` objects are immutable.
- Every command carries authenticated tenant/actor context, correlation metadata, idempotency metadata, and—where applicable—an expected aggregate version.
- Governance authorization and audit behavior may be implemented as middleware/interceptors, even where shown explicitly for architectural clarity.
