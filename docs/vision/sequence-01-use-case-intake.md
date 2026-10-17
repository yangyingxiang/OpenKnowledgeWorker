# Sequence Diagram: Use-Case Intake and Source Ingestion

## Participants

- Process Owner creates and scopes the use case.
- Process Architect supplies source material.
- Process Knowledge owns the process and initial change set.
- Source Fabric owns source artifacts, versions, and evidence.

```mermaid
sequenceDiagram
    autonumber
    actor Owner as Process Owner
    actor Architect as Process Architect
    participant UI as OpenKnowledgeWorker Web / BFF
    participant Gov as Governance Control
    participant PK as Process Knowledge
    participant SF as Source Fabric
    participant Queue as Durable Queue
    participant Worker as Ingestion Worker
    participant Store as Object Storage
    participant Bus as Domain Event Bus

    Owner->>UI: Enter use-case scope, owner, inputs, outputs, approval policy
    UI->>Gov: authorize(CreateProcess, actor, tenant, scope)
    Gov-->>UI: ALLOW_WITH_CONSTRAINTS
    UI->>PK: createProcess(commandContext, process definition)
    PK->>PK: Validate scope and create Process + initial ChangeSet
    PK-->>UI: Process(DRAFT), ChangeSet(OPEN), aggregateVersion
    UI-->>Owner: Display process workspace

    loop For each upload or source connection
        Architect->>UI: Add source and classification metadata
        UI->>Gov: authorize(RegisterSource, source metadata)
        Gov-->>UI: ALLOW
        UI->>SF: ingestArtifact(idempotencyKey, processRef, metadata, content)
        SF->>Store: Store immutable raw artifact version
        Store-->>SF: objectUri + contentDigest
        SF->>Queue: Enqueue ingestion operation
        SF-->>UI: 202 Accepted + operationId + eventsUrl

        Queue->>Worker: Lease ingestion operation
        Worker->>Store: Read raw artifact version
        Worker->>Worker: Malware scan, parse/OCR, normalize, chunk
        Worker->>SF: persistRenditionAndEvidence(operationId, results)
        SF->>Bus: EvidenceExtracted(eventId, artifactVersionId)
        SF-->>UI: Operation event: INGESTION_COMPLETED
        Bus->>PK: EvidenceExtracted
        PK->>PK: Associate source version with Process
    end

    Architect->>UI: Review source inventory and extraction quality
    UI->>SF: getArtifactVersion + sampled evidence spans
    SF-->>UI: Immutable source version and evidence locators
    UI-->>Architect: Render document preview and extraction status
```

## Key controls

- Upload commands are idempotent.
- Raw source versions are immutable and content-addressed.
- Ingestion runs asynchronously and can resume after worker failure.
- Source metadata and access are evaluated before evidence is returned.
- A failed parse creates a failed ingestion attempt, not a partially ready document.
