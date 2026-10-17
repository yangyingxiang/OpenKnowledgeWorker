# Sequence Diagram: Process Review and Publication

## Purpose

This flow validates a Process IR, obtains required human approvals, and publishes an immutable `ProcessVersion` and `AutomationPackage`.

```mermaid
sequenceDiagram
    autonumber
    actor Architect as Process Architect
    actor Owner as Process Owner
    actor Reviewer as Governance Reviewer
    participant UI as OpenKnowledgeWorker Web / BFF
    participant PK as Process Knowledge
    participant Gov as Governance Control
    participant Bus as Domain Event Bus
    participant Store as Object Storage

    Architect->>UI: Validate current process change set
    UI->>PK: validateChangeSet(changeSetId, expectedVersion)
    PK->>PK: Validate schemas, paths, evidence, claims, conflicts, controls
    PK-->>UI: ValidationReport(errors, warnings, readiness metrics)

    alt Blocking errors or unresolved required questions
        UI-->>Architect: Display remediation worklist
        Architect->>UI: Apply structured Process IR operations
        UI->>PK: applyOperation(operation, expectedVersion)
        PK-->>UI: Updated ChangeSet and projections
    else Change set is eligible for review
        Architect->>UI: Submit for approval
        UI->>PK: submitForApproval(changeSetId)
        PK->>Gov: createApprovalCase(resource=ChangeSet, policyRef)
        Gov->>Gov: Resolve approvers and separation-of-duties rules
        Gov-->>PK: ApprovalCaseRef
        PK-->>UI: ChangeSet READY_FOR_REVIEW
    end

    par Business approval
        Owner->>UI: Review scope, material changes, gaps, PDD and diagram
        UI->>Gov: recordApproval(ownerDecision)
    and Governance approval
        Reviewer->>UI: Review evidence, authority, effective dates and controls
        UI->>Gov: recordApproval(reviewerDecision)
    end

    alt Any required approver rejects
        Gov->>PK: ApprovalRejected(reason, remediation)
        PK->>PK: Return ChangeSet to OPEN
        PK-->>UI: Rejection and required revisions
    else All approval requirements satisfied
        Gov->>PK: ApprovalRequirementsSatisfied(approvalCaseId)
        PK->>PK: Freeze Process IR and evidence manifest
        PK->>PK: Create immutable ProcessVersion
        PK->>Store: Store Process IR, projections, AutomationPackage
        Store-->>PK: URIs + content digests
        PK->>Bus: ProcessVersionPublished(versionId, packageDigest)
        PK-->>UI: Published ProcessVersion(APPROVED)
        UI-->>Owner: Publication confirmation
        UI-->>Reviewer: Immutable approval record
    end
```

## Publication invariants

- No blocking validation error exists.
- All required questions and conflicts are resolved or explicitly accepted as exceptions.
- Required business and governance approvals are satisfied.
- The Process IR, evidence manifest, projections, and approvals are content-addressed and immutable.
- The actor who authored a material change cannot satisfy an approval role when separation of duties applies.
