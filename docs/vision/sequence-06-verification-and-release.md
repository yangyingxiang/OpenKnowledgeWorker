# Sequence Diagram: Offline Verification, Repair, and Release

## Purpose

This flow independently verifies an immutable candidate, performs controlled repair if necessary, obtains release approval, and creates an export bundle. It never processes live production cases.

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Automation Engineer
    actor Reviewer as Governance Reviewer
    participant UI as OpenKnowledgeWorker Web / BFF
    participant Gov as Governance Control
    participant AE as Automation Engineering
    participant VR as Verification and Release
    participant Sandbox as Isolated Verification Worker
    participant AR as Agent Runtime
    participant Model as Approved LLM Provider
    participant Store as Artifact Store

    Engineer->>UI: Start release verification
    UI->>Gov: authorize(StartVerification, candidate, fixture classification)
    Gov-->>UI: ALLOW_WITH_CONSTRAINTS(no egress, resource limits, model policy)
    UI->>VR: startVerification(candidateId, suiteId, modes, policy)
    VR->>AE: getCandidatePackage(candidateId)
    AE-->>VR: Immutable CandidatePackage + digest
    VR->>Sandbox: Create ephemeral no-egress sandbox
    VR-->>UI: 202 Accepted + verificationRunId + eventsUrl

    par Deterministic verification
        Sandbox->>Sandbox: Build from locked dependencies
        Sandbox->>Sandbox: Unit, integration and contract tests
        Sandbox->>Sandbox: Type, lint, secret, dependency and license scans
        Sandbox->>Sandbox: Rule-code-test mapping and stale mapping checks
        Sandbox-->>VR: Structured test and scan results
    and Optional LLM-guided reference comparison
        VR->>AR: startRun(VERIFICATION, ProcessVersion + golden cases)
        AR->>Model: Execute approved Process IR as reference
        Model-->>AR: Structured reference outputs and trace
        AR-->>VR: Reference results with model and prompt versions
    end

    VR->>VR: Compare outputs, calculate coverage, create immutable findings
    VR-->>UI: Stream results and VerificationReport

    alt Verification has blocking findings
        Engineer->>UI: Select findings and request repair
        UI->>AE: createRepair(baseCandidateId, findingIds)
        AE->>AR: startRun(REPAIR, scoped files + rules + tests + findings)
        AR->>AE: Governed workspace mutations and mappings
        AE->>AE: Create new workspace version and new BuildCandidate
        AE-->>UI: New candidate and diff
        Note over Engineer,VR: New candidate repeats complete verification before release
    else Candidate satisfies release policy
        VR->>Gov: createApprovalCase(resource=VerifiedCandidate)
        Gov-->>Reviewer: Assign release review
        Reviewer->>UI: Review reports, mappings, semantic contracts, limitations
        UI->>Gov: recordApproval(APPROVE or REJECT)

        alt Release rejected
            Gov-->>VR: ApprovalRejected with rationale
            VR-->>UI: Candidate remains VERIFIED but not releasable
        else Release approved
            Gov->>VR: ApprovalRequirementsSatisfied
            VR->>VR: Create immutable Release
            Engineer->>UI: Request export format and contents
            UI->>VR: exportRelease(releaseId, export options)
            VR->>Store: Package source, tests, schemas, provenance, reports, SBOM
            Store-->>VR: Export URI + digest
            VR->>VR: Sign release manifest
            VR-->>UI: Short-lived governed download reference
        end
    end
```

## Release gates

- Candidate digest matches the verified CandidatePackage.
- Required suites and scans passed.
- Traceability coverage meets tenant policy.
- Accepted findings have recorded owners and rationale.
- Semantic contracts declare schemas, model policy, confidence thresholds, and fallback behavior.
- Required release approvals are satisfied.
