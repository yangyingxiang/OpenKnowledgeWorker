# Sequence Diagram: Automation Design and Code Generation

## Purpose

This flow creates a reviewed execution design and generates a versioned codebase from one immutable, approved process version.

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Automation Engineer
    participant UI as OpenKnowledgeWorker Web / BFF
    participant Gov as Governance Control
    participant PK as Process Knowledge
    participant AE as Automation Engineering
    participant AR as Agent Runtime
    participant Model as Approved LLM Provider
    participant Workspace as Workspace Store

    Engineer->>UI: Create automation project and select target
    UI->>Gov: authorize(CreateAutomationProject, processVersion, target)
    Gov-->>UI: ALLOW_WITH_CONSTRAINTS(build and model policy)
    UI->>AE: createProject(processVersionId, target, constraints)
    AE->>PK: getAutomationPackage(processVersionId)
    PK-->>AE: Immutable AutomationPackage + digest
    AE->>AE: Persist project pinned to package digest
    AE-->>UI: AutomationProject(DESIGNING)

    Engineer->>UI: Generate execution design
    UI->>AE: createExecutionDesign(projectId)
    AE->>AR: startRun(IMPLEMENTATION_PLANNER, AutomationPackage, constraints)
    AR->>Model: Propose step implementation strategies and architecture
    Model-->>AR: Structured ExecutionDesign proposal
    AR->>AE: submitExecutionDesignProposal(projectId, proposal)
    AE->>AE: Validate step coverage, contracts, failure behavior, stable IDs
    AE-->>UI: ExecutionDesign(DRAFT) + findings

    Engineer->>UI: Review/edit deterministic, semantic, external and human steps
    UI->>AE: approveExecutionDesign(designId, expectedVersion)
    AE->>Gov: authorize(ApproveExecutionDesign, actor, design)
    Gov-->>AE: ALLOW
    AE->>AE: Freeze approved ExecutionDesign
    AE-->>UI: ExecutionDesign(APPROVED)

    Engineer->>UI: Start code generation
    UI->>AE: startGeneration(projectId, designId, idempotencyKey)
    AE->>Workspace: Create isolated versioned workspace
    AE->>AR: startRun(IMPLEMENTATION, package + design + workspace tools)
    AE-->>UI: 202 Accepted + generationOperationId

    loop Plan, implement and construct tests
        AR->>Model: Model request with scoped context and tools
        Model-->>AR: Code reasoning + workspace tool calls
        AR->>Gov: evaluateToolInvocation(workspace mutation)
        Gov-->>AR: ALLOW_WITH_CONSTRAINTS(path, size, file type)
        AR->>AE: writeFile/readFile/recordMapping
        AE->>AE: Validate workspace operation
        AE->>Workspace: Store immutable CodeFileVersion
        Workspace-->>AE: file digest + workspace version
        AE-->>AR: Structured ToolResult
        AR-->>UI: Stream file and phase events
    end

    AR->>AE: requestCandidateCreation(generationRunId)
    AE->>AE: Validate completeness and mapping integrity
    AE->>Workspace: Freeze candidate source snapshot
    AE->>AE: Create immutable BuildCandidate and CandidatePackage
    AE-->>UI: BuildCandidate(CANDIDATE) + mapping summary
```

## Key controls

- Generation is pinned to an immutable `AutomationPackage` digest.
- Execution design approval occurs before code generation.
- Agent tools cannot escape the project workspace.
- Agent Runtime does not own or directly persist code files.
- Candidate creation freezes source, dependency, mapping, prompt, and configuration versions.
