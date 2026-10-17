# Sequence Diagram: Research and Claim Review

## Purpose

This flow converts source evidence into proposed organizational knowledge. Agent output remains a proposal until reviewed through Process Knowledge.

```mermaid
sequenceDiagram
    autonumber
    actor Architect as Process Architect
    participant UI as OpenKnowledgeWorker Web / BFF
    participant Gov as Governance Control
    participant AR as Agent Runtime
    participant Ctx as Context Builder
    participant SF as Source Fabric
    participant Model as Approved LLM Provider
    participant PK as Process Knowledge
    participant Ops as Operation Store

    Architect->>UI: Start initial process research
    UI->>Gov: authorize(StartAgentRun, process, source scope)
    Gov-->>UI: ALLOW_WITH_CONSTRAINTS(model policy, budget, source scope)
    UI->>AR: startRun(PROCESS_RESEARCH, changeSetId, constraints)
    AR->>Ops: Create durable AgentRun and initial checkpoint
    AR-->>UI: 202 Accepted + runId + eventsUrl

    loop Until completion, cancellation, or budget limit
        AR->>Ctx: buildContext(run state, research policy)
        Ctx->>SF: searchEvidence(query, actorContext, source scope)
        SF->>Gov: authorize(ReadEvidence, evidence ACLs)
        Gov-->>SF: ALLOW filtered evidence set
        SF-->>Ctx: Evidence spans + stable source locators
        Ctx->>PK: readCurrentClaimsAndOpenConflicts(changeSetId)
        PK-->>Ctx: Draft knowledge and process state
        Ctx-->>AR: Budgeted context snapshot
        AR->>Model: Model request with scoped tool catalog
        Model-->>AR: Text + proposed tool calls

        alt Agent proposes a claim
            AR->>Gov: evaluateToolInvocation(propose_claim)
            Gov-->>AR: ALLOW
            AR->>PK: proposeClaim(assertion, scope, evidenceRefs)
            PK->>PK: Validate evidence, deduplicate, enforce domain rules
            PK-->>AR: ClaimProposal or structured rejection
        else Agent reports a conflict
            AR->>PK: reportConflict(claimRefs, evidenceRefs, rationale)
            PK->>PK: Create or merge ConflictCase
            PK-->>AR: ConflictCase reference
        else Agent proposes a question
            AR->>PK: createQuestion(gap, targetRole, relatedClaimRefs)
            PK-->>AR: Draft Question
        end

        AR->>Ops: Append run events, usage, tool results, checkpoint
        AR-->>UI: Stream progress and proposal events
    end

    AR->>Ops: Mark run COMPLETED with terminal reason
    AR-->>UI: Research summary and review queue

    Architect->>UI: Review proposed claim
    UI->>Gov: authorize(ReviewClaim, actor, claim)
    Gov-->>UI: ALLOW
    UI->>PK: reviewClaim(decision, edits, expectedVersion)

    alt No concurrent modification
        PK->>PK: Apply review and recompute conflicts/completeness
        PK-->>UI: Updated claim + aggregateVersion
        UI-->>Architect: Show accepted/rejected/needs-SME status
    else Aggregate version changed
        PK-->>UI: 409 VERSION_CONFLICT + currentVersion
        UI-->>Architect: Show diff and request reconciliation
    end
```

## Key controls

- Context retrieval combines relevance, authority, freshness, applicability, and permission.
- The model cannot confirm claims or publish process knowledge.
- Tool invocations use the same application interfaces and policy checks as human actions.
- Each run is budgeted, checkpointed, cancellable, and completely traceable.
