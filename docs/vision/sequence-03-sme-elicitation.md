# Sequence Diagram: SME Elicitation

## Purpose

This flow captures organizational knowledge that cannot be resolved from documents. An expert response becomes evidence and a proposed knowledge change, not automatic process truth.

```mermaid
sequenceDiagram
    autonumber
    actor Architect as Process Architect
    actor SME as Subject-Matter Expert
    participant UI as OpenKnowledgeWorker Web / BFF
    participant Gov as Governance Control
    participant PK as Process Knowledge
    participant AR as Agent Runtime
    participant SF as Source Fabric
    participant Notify as Notification Adapter

    Architect->>UI: Review and assign an open question
    UI->>Gov: authorize(AssignQuestion, actor, question, assignee)
    Gov-->>UI: ALLOW
    UI->>PK: assignQuestion(questionId, SME, dueDate, expertiseScope)
    PK->>PK: Create QuestionAssignment
    PK-->>UI: Assignment created
    PK->>Notify: QuestionAssigned notification
    Notify-->>SME: Focused review request

    SME->>UI: Open assigned question
    UI->>Gov: authorize(ReadQuestionContext, SME, process scope)
    Gov-->>UI: ALLOW_WITH_CONSTRAINTS(relevant evidence only)
    UI->>PK: getQuestionContext(questionId)
    PK->>SF: getEvidenceSpans(evidenceRefs, SME context)
    SF-->>PK: Authorized evidence excerpts and source locators
    PK-->>UI: Question, rationale, related claims, process section, evidence
    UI-->>SME: Render focused question workspace

    SME->>UI: Submit answer, applicability, exceptions, confidence
    opt SME attaches supporting material
        UI->>SF: ingestArtifact(attachment, sourceType=EXPERT_EVIDENCE)
        SF-->>UI: artifactVersionId + ingestionOperation
    end
    UI->>Gov: authorize(RecordExpertResponse, SME, question)
    Gov-->>UI: ALLOW
    UI->>PK: recordExpertResponse(answer, scope, evidenceRefs)
    PK->>PK: Store immutable response and proposed claim changes
    PK->>PK: Reevaluate related claims, conflicts, and questions

    alt Answer resolves existing question
        PK->>PK: Mark question ANSWERED_PENDING_REVIEW
    else Answer creates contradiction
        PK->>PK: Create or update ConflictCase
    else Answer is incomplete
        PK->>AR: Request bounded SME_ELICITATION follow-up proposal
        AR->>PK: createQuestion(follow-up, relatedResponseId)
    end

    PK-->>UI: Updated response and affected-item summary
    UI-->>SME: Confirm submission

    Architect->>UI: Review expert response and proposed changes
    UI->>PK: accept, modify, or reject proposed claim changes
    PK->>PK: Apply decision to current ChangeSet
    PK-->>UI: Updated claims, conflicts, and question statuses
```

## Key controls

- SME access is limited to assigned process scope and authorized evidence.
- Expertise and authority are contextual; an SME is not globally authoritative.
- Original expert responses are immutable, even when the resulting claim is edited.
- Follow-up questions retain causation links to prior responses and conflicts.
