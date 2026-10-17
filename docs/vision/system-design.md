# OpenKnowledgeWorker System Design

> Architecture review diagrams: [`README.md`](README.md)

## 1. Purpose

OpenKnowledgeWorker is an enterprise process discovery, specification, and automation engineering platform. It converts fragmented organizational knowledge into an approved process definition, generates a maintainable hybrid automation codebase, verifies that code offline, and keeps the process and implementation synchronized as organizational knowledge changes.

OpenKnowledgeWorker owns three workflows:

- **Workflow A — Discover and formalize:** ingest sources, elicit knowledge from subject-matter experts, reconcile conflicts, and publish an evidence-backed process definition.
- **Workflow B — Generate and verify automation:** transform an approved process definition into deterministic code, bounded LLM calls, tests, and an exportable release.
- **Workflow D — Maintain knowledge and automation:** identify changes, assess their impact, approve a new process version, update the implementation, rerun regression verification, and export a new release.

OpenKnowledgeWorker does **not** deploy, serve, or monitor generated automation against live production data. The customer owns production deployment and execution.

```text
Enterprise sources + SMEs
          |
          v
Evidence and proposed claims
          |
          v
Reconciliation and approval
          |
          v
Versioned Process IR + PDD projection
          |
          v
Generated hybrid automation
          |
          v
Offline verification and release export
```

## 2. Design principles

1. **Evidence before assertion.** Every material process claim must be traceable to source evidence, an expert response, or an explicitly recorded manual decision.
2. **Process IR is canonical.** The typed Process Intermediate Representation is the source of truth. PDD, PDL, and diagrams are projections.
3. **Agents propose; domain services decide.** Agents never receive direct database access and cannot approve their own output.
4. **Published objects are immutable.** Source versions, published process versions, build candidates, verification reports, and releases are append-only.
5. **Stable identity across versions.** Process steps, rules, schemas, and semantic contracts use stable identifiers rather than headings, line numbers, or filenames.
6. **Govern every boundary.** Reads, mutations, tool calls, approvals, model use, and exports are authorized and audited.
7. **Asynchronous work is durable.** Ingestion, research, generation, verification, repair, and export run as checkpointed operations outside HTTP request threads.
8. **Provider and cloud portability.** Model providers, source systems, and exported runtimes are accessed through contracts rather than embedded vendor assumptions.
9. **Modular monolith first.** Logical and data-ownership boundaries are enforced before introducing unnecessary network services.
10. **Production execution is an export boundary.** OpenKnowledgeWorker verifies artifacts offline and hands them to the customer's production platform.

## 3. Users and responsibilities

### 3.1 Process Owner

- Creates and scopes a use case.
- Assigns process ownership, architects, and SMEs.
- Defines completion and approval requirements.
- Reviews material gaps and conflicts.
- Approves process versions and major maintenance changes.

### 3.2 Process Architect / Business Analyst

- Adds and classifies sources.
- Reviews extracted evidence and proposed claims.
- Reconciles conflicts and manages questions.
- Builds and maintains the Process IR.
- Reviews PDD and diagram projections.
- Performs change-impact analysis and prepares versions for approval.

### 3.3 Subject-Matter Expert

- Answers focused questions with applicability, exceptions, and confidence.
- Supplies examples and supporting evidence.
- Reviews assigned process sections.
- Reports outdated or incorrect organizational knowledge.

### 3.4 Automation Engineer

- Defines implementation targets and integration contracts.
- Reviews the proposed execution design.
- Reviews generated code and traceability mappings.
- Manages offline tests and verifier findings.
- Produces and exports approved releases.

### 3.5 Governance / Review Approver

- Reviews provenance, source authority, scope, and effective dates.
- Reviews unresolved assumptions and accepted exceptions.
- Approves process publication.
- Reviews semantic LLM use, verification results, and release contents.
- Approves release export according to tenant policy.

### 3.6 Platform Administrator

- Configures tenants, identity, access policies, model providers, secrets, retention, and source connectors.
- Monitors platform operations, quotas, audit events, and failed jobs.

## 4. Use-case aggregate and lifecycle

A business use case is represented by one long-lived `Process` aggregate.

```text
Tenant
└── Process
    ├── Source associations
    ├── Knowledge claims and conflicts
    ├── Questions and expert responses
    ├── Process change sets
    ├── Published process versions
    ├── Automation projects
    └── Exported releases
```

The principal identifiers are:

- `ProcessId`: stable identity of the business process.
- `ProcessVersionId`: immutable approved understanding of the process.
- `AutomationProjectId`: implementation of a process for a particular target.
- `BuildCandidateId`: immutable candidate implementation.
- `ReleaseId`: verified, approved, exportable artifact.

One process version may have multiple automation projects and targets.

### 4.1 Process lifecycle

```text
DRAFT -> DISCOVERING -> ELICITING -> REVIEW -> APPROVED
                                                   |
                                                   v
                                              SUPERSEDED -> RETIRED
```

Review may return a process to discovery or elicitation.

### 4.2 Change-set lifecycle

```text
OPEN -> ANALYZING -> READY_FOR_REVIEW -> APPROVED -> PUBLISHED
                                      \-> REJECTED
```

### 4.3 Automation lifecycle

```text
DESIGNING -> DESIGN_REVIEW -> GENERATING -> VERIFYING
                                              |
                               RELEASE_READY <-+
                                      |
                                      v
                                  EXPORTED
```

### 4.4 Release lifecycle

```text
CANDIDATE -> VERIFICATION_FAILED
         \-> VERIFIED -> APPROVED -> EXPORTED -> SUPERSEDED
```

State transitions are enforced by domain services rather than inferred from agent messages or UI state.

## 5. Logical architecture

OpenKnowledgeWorker consists of six major components.

```text
                          +---------------------------+
                          | Governance & Platform     |
                          | Control                   |
                          +-------------+-------------+
                                        |
              authorization, policy, approval, audit
                                        |
+--------------------+       +----------v-----------+
| Source & Evidence  +------>| Process Knowledge    |
| Fabric             |       | Studio               |
+--------------------+       +----------+-----------+
                                        |
                              immutable AutomationPackage
                                        |
                             +----------v-----------+
                             | Automation           |
                             | Engineering          |
                             +----------+-----------+
                                        |
                                immutable candidate
                                        |
                             +----------v-----------+
                             | Offline Verification |
                             | & Release             |
                             +----------------------+

           Agent Runtime supports the four lifecycle components
           through governed application APIs and scoped tools.
```

The frontend and public API are presentation/application layers over these components and do not own domain data.

## 6. Component design

## 6.1 Source and Evidence Fabric

### Responsibilities

- Register uploads and enterprise source connections.
- Synchronize source systems incrementally.
- Store immutable raw artifacts and source versions.
- Extract text using parsers, OCR, and transcription.
- Divide content into addressable chunks and evidence spans.
- Preserve source metadata, effective dates, authority hints, and ACL snapshots.
- Propagate deletion, revocation, and supersession events.
- Search evidence subject to actor permissions.

This component records what sources say. It does not decide which claims are correct.

### Owned data

- `SourceConnection`
- `SourceArtifact`
- `ArtifactVersion`
- `ContentRendition`
- `DocumentChunk`
- `EvidenceSpan`
- `SourceAclSnapshot`
- `SyncCursor`
- `IngestionAttempt`

### Application interface

```python
class SourceService:
    def register_source(self, command: RegisterSource) -> SourceConnection: ...
    def ingest_artifact(self, command: IngestArtifact) -> IngestionOperation: ...
    def synchronize(self, source_id: SourceId) -> SyncOperation: ...
    def get_artifact_version(self, version_id: ArtifactVersionId) -> ArtifactVersion: ...
    def get_evidence_span(self, span_id: EvidenceSpanId) -> EvidenceSpan: ...
    def search_evidence(self, query: EvidenceQuery, context: ActorContext) -> list[EvidenceResult]: ...
```

### Events

- `ArtifactVersionCreated`
- `ArtifactRemoved`
- `EvidenceExtracted`
- `SourceAccessChanged`
- `SourceSynchronizationFailed`

## 6.2 Process Knowledge Studio

### Responsibilities

- Manage processes, scope, ownership, and lifecycle.
- Convert evidence and expert responses into proposed claims.
- Represent supporting, contradicting, and elaborating evidence.
- Detect and manage conflicts, gaps, assumptions, and questions.
- Assign questions and record expert responses.
- Represent source and expert authority by domain and scope.
- Maintain change sets and structured Process IR edits.
- Generate PDD, PDL, rule catalog, and diagram projections.
- Validate process completeness and consistency.
- Coordinate process approval and publish immutable process versions.
- Determine which claims, rules, steps, releases, and tests are affected by change.

This is OpenKnowledgeWorker's central domain component.

### Owned data

- `Process`
- `ProcessMember`
- `ProcessSourceRef`
- `KnowledgeClaim`
- `ClaimEvidenceLink`
- `AuthorityAssessment`
- `ConflictCase`
- `Question`
- `QuestionAssignment`
- `ExpertResponse`
- `DecisionRecord`
- `ProcessChangeSet`
- `ProcessOperation`
- `ProcessVersion`
- `ProcessIR`
- `ProcessStatement`
- `ImpactAssessment`
- `ProjectionSnapshot`

### Application interface

```python
class ProcessKnowledgeService:
    def create_process(self, command: CreateProcess) -> Process: ...
    def associate_source(self, command: AssociateSource) -> ProcessSourceRef: ...
    def propose_claim(self, command: ProposeClaim) -> KnowledgeClaim: ...
    def review_claim(self, command: ReviewClaim) -> KnowledgeClaim: ...
    def detect_conflicts(self, process_id: ProcessId) -> list[ConflictCase]: ...
    def create_question(self, command: CreateQuestion) -> Question: ...
    def assign_question(self, command: AssignQuestion) -> QuestionAssignment: ...
    def record_expert_response(self, command: RecordExpertResponse) -> ExpertResponse: ...
    def resolve_conflict(self, command: ResolveConflict) -> DecisionRecord: ...
    def apply_operation(self, command: ApplyProcessOperation) -> ProcessChangeSet: ...
    def validate_change_set(self, change_set_id: ChangeSetId) -> ValidationReport: ...
    def submit_for_approval(self, change_set_id: ChangeSetId) -> ApprovalCaseRef: ...
    def publish_version(self, change_set_id: ChangeSetId) -> ProcessVersion: ...
    def get_automation_package(self, version_id: ProcessVersionId) -> AutomationPackage: ...
    def assess_impact(self, trigger: ChangeTrigger) -> ImpactAssessment: ...
```

### Events

- `ClaimProposed`
- `ClaimConfirmed`
- `ConflictDetected`
- `QuestionAssigned`
- `ExpertResponseReceived`
- `ProcessChangeSetSubmitted`
- `ProcessVersionPublished`
- `ProcessImpactDetected`

## 6.3 Agent Runtime

### Responsibilities

- Run research, elicitation, process architecture, implementation, verification, and maintenance agents.
- Provide one streaming, checkpointed tool-use state machine.
- Assemble permission-filtered context under explicit token budgets.
- Manage working memory, session summaries, and narrowly scoped durable memory.
- Abstract model providers and apply tenant model policies.
- Validate and schedule typed tools.
- Enforce maximum turns, tokens, cost, duration, and failures.
- Support retries, continuation, cancellation, approval pauses, and resumption.
- Persist model requests, responses, tool calls, tool results, transitions, and usage.

The Agent Runtime owns execution state, not business artifacts. Agent tools invoke the same application interfaces used by human actions.

### Agent definitions

- `PROCESS_RESEARCH`
- `SME_ELICITATION`
- `PROCESS_ARCHITECT`
- `IMPLEMENTATION_PLANNER`
- `IMPLEMENTATION`
- `VERIFICATION`
- `REPAIR`
- `MAINTENANCE`

### Owned data

- `AgentDefinition`
- `AgentRun`
- `RunCheckpoint`
- `RunEvent`
- `ModelInvocation`
- `ToolInvocation`
- `ToolResultRecord`
- `ContextSnapshot`
- `MemoryRecord`
- `BudgetState`

### Application interface

```python
class AgentRuntime:
    def start_run(self, request: StartAgentRun) -> AgentRun: ...
    def resume_run(self, run_id: RunId, input: RunInput) -> AgentRun: ...
    def cancel_run(self, run_id: RunId) -> None: ...
    def get_run(self, run_id: RunId) -> AgentRunSnapshot: ...
    def stream_events(self, run_id: RunId, cursor: EventCursor | None) -> Iterator[AgentEvent]: ...
```

### Tool contract

```python
class ToolDescriptor:
    name: str
    version: str
    input_schema: JsonSchema
    output_schema: JsonSchema
    access_mode: Literal["READ", "WRITE", "EXECUTE", "EXTERNAL"]
    side_effect: Literal["NONE", "REVERSIBLE", "IRREVERSIBLE"]
    concurrency: Literal["SAFE", "RESOURCE_EXCLUSIVE"]
    approval_policy: ApprovalPolicyRef | None
    timeout_seconds: int
    retry_policy: RetryPolicy
    idempotency: IdempotencyPolicy
    maximum_result_bytes: int


class Tool:
    descriptor: ToolDescriptor

    def authorize(self, invocation: ToolInvocation, context: ExecutionContext) -> PolicyDecision: ...
    def execute(self, invocation: ToolInvocation, context: ExecutionContext) -> ToolResult: ...
```

Each agent definition receives only the tools required for its task. For example, a research agent can search evidence and propose claims but cannot write code or approve a process version.

## 6.4 Automation Engineering

### Responsibilities

- Create automation projects from immutable approved process versions.
- Define target language, package type, input/output schemas, and deployment assumptions.
- Produce an explicit execution design before code generation.
- Classify steps as deterministic code, semantic LLM call, external-system port, or human-review output.
- Manage versioned code workspaces and file history.
- Generate multi-file code, tests, configuration, integration adapters, and documentation.
- Maintain stable rule-to-code and rule-to-test mappings.
- Package immutable build candidates.
- Analyze implementation impact between process versions and produce targeted upgrades.
- Store artifact manifests and digests.

The component generates deployable artifacts but does not deploy them.

### Owned data

- `AutomationProject`
- `BuildTarget`
- `ExecutionDesign`
- `StepImplementationPlan`
- `SemanticContract`
- `IntegrationContract`
- `CodeWorkspace`
- `WorkspaceVersion`
- `CodeFile`
- `CodeFileVersion`
- `TraceabilityMapping`
- `GenerationRunRef`
- `RepairRunRef`
- `BuildCandidate`
- `UpgradePlan`
- `AutomationImpactReport`

### Application interface

```python
class AutomationEngineeringService:
    def create_project(self, command: CreateAutomationProject) -> AutomationProject: ...
    def create_execution_design(self, project_id: AutomationProjectId) -> ExecutionDesign: ...
    def approve_execution_design(self, command: ApproveExecutionDesign) -> None: ...
    def start_generation(self, command: StartGeneration) -> GenerationOperation: ...
    def read_file(self, workspace_id: WorkspaceId, path: str) -> CodeFileVersion: ...
    def write_file(self, command: WriteWorkspaceFile) -> CodeFileVersion: ...
    def delete_file(self, command: DeleteWorkspaceFile) -> WorkspaceVersion: ...
    def record_mapping(self, command: RecordTraceabilityMapping) -> TraceabilityMapping: ...
    def create_candidate(self, project_id: AutomationProjectId) -> BuildCandidate: ...
    def create_repair(self, command: CreateRepair) -> RepairOperation: ...
    def create_upgrade_plan(self, command: CreateUpgradePlan) -> UpgradePlan: ...
    def get_candidate_package(self, candidate_id: BuildCandidateId) -> CandidatePackage: ...
```

### Events

- `ExecutionDesignApproved`
- `WorkspaceVersionCreated`
- `BuildCandidateCreated`
- `AutomationImpactAnalyzed`
- `RepairCandidateCreated`

## 6.5 Offline Verification and Release

### Responsibilities

- Manage business-readable test cases, test suites, fixtures, and golden datasets.
- Generate synthetic test data where appropriate.
- Run generated code only in isolated offline sandboxes.
- Run unit, integration, contract, acceptance, static, dependency, license, secret, and security checks.
- Compare LLM-guided reference execution with generated-code execution.
- Verify process-to-code and process-to-test traceability.
- Detect stale mappings and behavior changes between candidates or releases.
- Produce immutable verification reports and findings.
- Coordinate release approval.
- Produce signed, versioned export bundles.

### Owned data

- `TestCase`
- `TestCaseVersion`
- `TestSuite`
- `FixtureSet`
- `GoldenDataset`
- `VerificationPolicy`
- `VerificationRun`
- `VerificationResult`
- `VerificationFinding`
- `RegressionReport`
- `Release`
- `ReleaseApprovalRef`
- `ExportBundle`
- `ExportManifest`

### Application interface

```python
class VerificationService:
    def create_test_suite(self, command: CreateTestSuite) -> TestSuite: ...
    def add_test_case(self, command: AddTestCase) -> TestCaseVersion: ...
    def import_fixtures(self, command: ImportFixtures) -> FixtureSet: ...
    def start_verification(self, command: StartVerification) -> VerificationOperation: ...
    def get_findings(self, run_id: VerificationRunId) -> list[VerificationFinding]: ...
    def compare_with_release(self, command: CompareWithRelease) -> RegressionReport: ...
    def request_release(self, command: RequestRelease) -> Release: ...
    def approve_release(self, command: ApproveRelease) -> Release: ...
    def export_release(self, command: ExportRelease) -> ExportOperation: ...
```

### Events

- `VerificationStarted`
- `VerificationCompleted`
- `VerificationFailed`
- `ReleaseApprovalRequested`
- `ReleaseApproved`
- `ReleaseExported`

## 6.6 Governance and Platform Control

### Responsibilities

- Manage tenants, environments, users, groups, roles, and service identities.
- Enforce RBAC and contextual ABAC.
- Evaluate access, tool, model, data-movement, and export policies.
- Manage approval definitions, cases, assignments, and decisions.
- Enforce separation of duties.
- Store secret references and approved model/provider configurations.
- Enforce data classification, residency, retention, legal hold, and deletion policy.
- Maintain immutable, queryable audit events.
- Apply per-tenant token, cost, storage, and concurrency quotas.

### Owned data

- `Tenant`
- `Environment`
- `Subject`
- `Group`
- `Role`
- `RoleBinding`
- `Policy`
- `PolicyDecisionRecord`
- `ApprovalPolicy`
- `ApprovalCase`
- `ApprovalAssignment`
- `ApprovalDecision`
- `ModelProviderConfiguration`
- `SecretReference`
- `DataClassificationPolicy`
- `RetentionPolicy`
- `Quota`
- `AuditEvent`

### Application interface

```python
class GovernanceService:
    def authorize(
        self, subject: SubjectRef, action: Action, resource: ResourceRef, context: PolicyContext
    ) -> PolicyDecision: ...
    def evaluate_tool_invocation(self, invocation: ToolInvocation) -> PolicyDecision: ...
    def resolve_model_policy(
        self, tenant_id: TenantId, classification: DataClassification, task_type: TaskType
    ) -> ModelPolicy: ...
    def create_approval_case(self, request: ApprovalRequest) -> ApprovalCase: ...
    def record_approval(self, command: RecordApproval) -> ApprovalDecision: ...
    def append_audit_event(self, event: AuditEvent) -> None: ...
```

Policy results are:

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`
- `ALLOW_WITH_CONSTRAINTS`

## 7. Core data model

## 7.1 Source and evidence model

```text
SourceConnection 1 ── * SourceArtifact
SourceArtifact   1 ── * ArtifactVersion
ArtifactVersion  1 ── * ContentRendition
ArtifactVersion  1 ── * DocumentChunk
DocumentChunk    1 ── * EvidenceSpan
ArtifactVersion  1 ── * SourceAclSnapshot
```

Important fields:

```text
ArtifactVersion
- id
- tenant_id
- artifact_id
- source_version
- content_digest
- object_storage_uri
- mime_type
- effective_from / effective_to
- authority_hint
- ingestion_status
- created_at

EvidenceSpan
- id
- artifact_version_id
- chunk_id
- text
- page_number
- heading_path
- character_start / character_end
- source_locator
- content_digest
```

## 7.2 Knowledge model

```text
Process 1 ── * ProcessChangeSet
Process 1 ── * KnowledgeClaim
KnowledgeClaim * ── * EvidenceSpan       through ClaimEvidenceLink
KnowledgeClaim 1 ── * AuthorityAssessment
KnowledgeClaim * ── * ConflictCase
Question 1 ── * QuestionAssignment
Question 1 ── * ExpertResponse
ExpertResponse 1 ── * proposed KnowledgeClaim changes
ProcessChangeSet 1 ── * ProcessOperation
Process 1 ── * ProcessVersion
```

Important claim fields:

```text
KnowledgeClaim
- id
- tenant_id
- process_id
- assertion
- status: PROPOSED | DRAFT | CONFIRMED | DISPUTED | SUPERSEDED
- confidence
- owner_role
- applicability_scope
- effective_from / effective_to
- supersedes_claim_id
- created_by
- aggregate_version
```

`applicability_scope` contains structured dimensions such as jurisdiction, product, business unit, customer segment, employee class, and policy type. It must not be only free text.

## 7.3 Process IR model

```text
ProcessIR
├── metadata
├── participants
├── inputs: DataDefinition[]
├── outputs: DataDefinition[]
├── phases: Phase[]
│   └── steps: ProcessStep[]
│       ├── rules: Rule[]
│       ├── transitions: Transition[]
│       ├── exceptions: ExceptionPath[]
│       └── source_claim_ids[]
├── semantic_requirements: SemanticRequirement[]
├── integration_requirements: IntegrationRequirement[]
└── invariants: ProcessInvariant[]
```

Key step fields:

```text
ProcessStep
- stable_step_id
- name
- purpose
- execution_kind: DETERMINISTIC | SEMANTIC | EXTERNAL | HUMAN
- input_refs
- output_refs
- preconditions
- rules
- transitions
- exception_paths
- source_claim_ids
- control_requirements
```

Every published `ProcessVersion` contains:

- Immutable Process IR.
- PDD/PDL projection snapshot.
- Evidence manifest or evidence snapshot reference.
- Content digest.
- Approval references.
- Parent version and semantic version.
- Known assumptions and accepted exceptions.

## 7.4 Automation model

```text
ProcessVersion 1 ── * AutomationProject
AutomationProject 1 ── * ExecutionDesign
AutomationProject 1 ── * WorkspaceVersion
WorkspaceVersion 1 ── * CodeFileVersion
AutomationProject 1 ── * TraceabilityMapping
AutomationProject 1 ── * BuildCandidate
BuildCandidate 1 ── * VerificationRun
BuildCandidate 1 ── 0..1 Release
```

Mappings use stable identifiers:

```text
TraceabilityMapping
- process_version_id
- rule_id or step_id
- target_type: FILE | FUNCTION | SEMANTIC_CONTRACT | TEST
- target_stable_id
- file_path
- symbol_name
- source_digest
- mapping_status
```

Line ranges may be stored as display metadata but are not the durable identity.

## 7.5 Verification and release model

```text
TestSuite 1 ── * TestCaseVersion
TestCaseVersion * ── * Rule / Step references
VerificationRun 1 ── * VerificationResult
VerificationRun 1 ── * VerificationFinding
Release 1 ── * ExportBundle
```

Test cases include:

- Versioned input fixture.
- Expected structured assertions.
- Referenced rules and process steps.
- Execution modes: generated code, LLM-guided reference, or both.
- Numeric and semantic comparison policies.
- Provenance identifying whether the test came from a document, expert, imported case, or generated boundary analysis.

## 8. Cross-component contracts

## 8.1 Command context

Every mutation carries:

```python
@dataclass(frozen=True)
class CommandContext:
    tenant_id: TenantId
    actor: SubjectRef
    correlation_id: UUID
    causation_id: UUID | None
    idempotency_key: str
    expected_version: int | None
    requested_at: datetime
```

- `tenant_id` is derived from authenticated identity and cannot be supplied freely by an untrusted client.
- `idempotency_key` makes retries safe.
- `expected_version` enables optimistic concurrency.
- `correlation_id` connects API calls, agent runs, jobs, events, and audit records.

## 8.2 Immutable handoff packages

Components communicate across lifecycle boundaries through immutable packages.

### AutomationPackage

Produced by Process Knowledge and consumed by Automation Engineering:

```text
- process_version_id
- Process IR
- input and output schemas
- rules and invariants
- semantic requirements
- integration requirements
- evidence manifest
- approval references
- content digest
```

### CandidatePackage

Produced by Automation Engineering and consumed by Verification:

```text
- build_candidate_id
- source tree snapshot
- dependency locks
- build manifest
- traceability mappings
- generated tests
- semantic contracts
- ProcessVersion digest
- candidate digest
```

### ReleasePackage

Produced by Verification for export:

```text
- approved CandidatePackage
- verification report
- regression report
- accepted findings
- SBOM and scan results
- release manifest
- approval references
- export digest and signature
```

## 8.3 Long-running operation contract

Ingestion, synchronization, research, generation, repair, verification, and export return `202 Accepted` with an operation reference.

```json
{
  "operation_id": "op-123",
  "status": "QUEUED",
  "status_url": "/v1/operations/op-123",
  "events_url": "/v1/operations/op-123/events"
}
```

Clients consume resumable server-sent events or WebSocket events using a monotonically increasing cursor.

```json
{
  "event_id": "event-42",
  "sequence": 42,
  "type": "FILE_WRITTEN",
  "occurred_at": "2026-08-21T12:00:00Z",
  "correlation_id": "correlation-1",
  "payload": {}
}
```

Operation state is persisted. Workers acquire leases, checkpoint after meaningful transitions, renew leases while active, and may resume after failure.

## 8.4 Domain event contract

Cross-component events are emitted through a transactional outbox.

```json
{
  "event_id": "event-1",
  "event_type": "ProcessVersionPublished",
  "event_version": 1,
  "tenant_id": "tenant-1",
  "aggregate_id": "process-1",
  "aggregate_version": 12,
  "occurred_at": "2026-08-21T12:00:00Z",
  "correlation_id": "correlation-1",
  "data": {
    "process_version_id": "process-version-3",
    "semantic_version": "3.0.0",
    "automation_package_digest": "sha256:..."
  }
}
```

Delivery is at least once. Consumers deduplicate by `event_id`.

## 8.5 Error contract

All APIs use a consistent error envelope:

```json
{
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "The process change set was modified by another actor.",
    "correlation_id": "correlation-1",
    "retryable": false,
    "details": {
      "expected_version": 7,
      "current_version": 8
    }
  }
}
```

## 9. Primary user flows

## 9.1 Workflow A — discover and formalize

### Create and scope

1. Process Owner calls `ProcessKnowledgeService.create_process`.
2. Governance authorizes the action and assigns the tenant approval policy.
3. Process Knowledge creates the process and initial change set.

### Ingest sources

1. Architect registers or uploads sources through Source Fabric.
2. Source Fabric stores immutable artifact versions and starts ingestion operations.
3. Workers extract text, chunks, and evidence spans.
4. `EvidenceExtracted` is emitted and the source is associated with the process.

### Research

1. Architect starts a `PROCESS_RESEARCH` agent run.
2. Agent Runtime builds context using permission-filtered evidence search.
3. The agent proposes claims, conflicts, questions, and process structure through Process Knowledge commands.
4. Process Knowledge validates and records proposals; it does not automatically confirm them.

### Review and elicitation

1. Architect accepts, edits, merges, rejects, or requests confirmation of claims.
2. Architect assigns questions to appropriate SMEs.
3. SMEs review focused evidence and submit answers, applicability, exceptions, and confidence.
4. Expert responses create proposed knowledge changes.
5. Process Knowledge reevaluates related conflicts and questions. Existing questions may become resolved, obsolete, or require revision.

### Model and approve

1. Architect applies structured operations to the Process IR.
2. Process Knowledge validates evidence coverage, paths, schemas, gaps, and unresolved conflicts.
3. PDD, PDL, and diagrams are generated as projections.
4. Architect submits the change set.
5. Governance creates and evaluates the approval case.
6. Once approvals are satisfied, Process Knowledge publishes an immutable ProcessVersion and AutomationPackage.

## 9.2 Workflow B — generate and verify

### Design

1. Engineer creates an AutomationProject from an approved ProcessVersion.
2. Automation Engineering receives the immutable AutomationPackage.
3. The Implementation Planner proposes an ExecutionDesign.
4. Automation Engineering validates the design.
5. Engineer reviews and approves deterministic, semantic, external, and human-output strategies.

### Generate

1. Engineer starts a generation operation.
2. Automation Engineering creates a new versioned workspace.
3. Agent Runtime runs the Implementation Agent with scoped workspace tools.
4. File mutations go through Automation Engineering APIs and create file versions.
5. Stable process-to-code and process-to-test mappings are recorded.
6. Automation Engineering freezes an immutable BuildCandidate.

### Verify and repair

1. Verification receives the CandidatePackage and ProcessVersion digest.
2. It runs code in a separate no-egress sandbox with resource limits.
3. It executes static checks, tests, security scans, traceability checks, golden cases, and optional LLM-versus-code comparison.
4. Findings are immutable and point to rules, steps, symbols, tests, and evidence.
5. Repair requests create a new workspace version and BuildCandidate.
6. Targeted tests run first, followed by the complete release verification suite.

### Release and export

1. A successfully verified candidate is submitted for release approval.
2. Governance applies separation-of-duties and exception policies.
3. Verification creates an immutable Release.
4. Export packaging produces source, tests, schemas, prompts, configuration templates, integration contracts, provenance, verification reports, SBOM, and manifest.
5. Governance records the export event and issues a short-lived download reference.

## 9.3 Workflow D — maintain

1. A new source version, source deletion, expert correction, imported issue, or changed requirement enters OpenKnowledgeWorker.
2. Process Knowledge creates an ImpactAssessment using evidence and claim dependencies.
3. `ProcessImpactDetected` identifies changed rule and step IDs.
4. Automation Engineering resolves those IDs through traceability mappings and produces an AutomationImpactReport.
5. Architect creates a change set based on the last approved ProcessVersion.
6. Discovery, elicitation, modeling, validation, and approval reuse Workflow A.
7. Engineer creates an UpgradePlan between old and new ProcessVersions.
8. Maintenance Agent applies targeted implementation changes to a new workspace version.
9. Verification compares the candidate with the prior Release and runs full regression.
10. A new approved Release is exported. Prior versions remain immutable and auditable.

## 10. Public API shape

The public API is resource-oriented; specialized agent behavior is exposed as asynchronous operations.

```text
/v1/processes
/v1/processes/{id}/sources
/v1/processes/{id}/claims
/v1/processes/{id}/conflicts
/v1/processes/{id}/questions
/v1/processes/{id}/change-sets
/v1/processes/{id}/versions
/v1/process-versions/{id}/automation-package

/v1/agent-runs
/v1/agent-runs/{id}
/v1/agent-runs/{id}/events

/v1/automation-projects
/v1/automation-projects/{id}/execution-designs
/v1/automation-projects/{id}/generation-runs
/v1/automation-projects/{id}/repair-runs
/v1/automation-projects/{id}/upgrade-plans
/v1/build-candidates/{id}

/v1/test-suites
/v1/verification-runs
/v1/verification-runs/{id}/events
/v1/releases
/v1/releases/{id}/exports

/v1/approval-cases
/v1/policies
/v1/audit-events
/v1/operations
```

The UI may use a Backend-for-Frontend to combine these APIs into task-oriented views, but it must not bypass domain services.

## 11. Security and governance

### Tenant isolation

- Every owned record contains `tenant_id` or is reachable only through a tenant-owned aggregate.
- Tenant context is derived from authenticated identity.
- Database access applies tenant filtering by construction and, where practical, PostgreSQL row-level security.
- Object-storage paths, encryption keys, job queues, and caches are tenant-scoped.

### Identity and access

- OIDC/SAML SSO and SCIM provisioning.
- RBAC for broad responsibilities and ABAC for process, source, environment, classification, and jurisdiction scope.
- User-delegated credentials where source-system permissions must be preserved.
- Separate service identities for API, ingestion, agent, build, and verification workers.

### Data protection

- TLS in transit and customer-appropriate encryption at rest.
- Secret values remain in a secret manager; OpenKnowledgeWorker stores references.
- Network egress is denied by default in build and verification sandboxes.
- Model policy determines which providers may receive each data classification.
- Retention, deletion, export, legal-hold, and regional-residency policies are explicit.

### Audit

Audit events include:

- Actor and delegated identity.
- Tenant, process, and environment.
- Action and affected resource version.
- Policy decision and constraints.
- Approval decision and rationale.
- Agent/model/tool identifiers.
- Before/after digests for mutations.
- Correlation and causation identifiers.
- Timestamp and result.

Audit persistence failures are operational failures; they must not be silently ignored for governed mutations.

## 12. Deployment architecture

The six logical components initially deploy as a modular monolith with specialized workers.

```text
Web/API deployment
├── application APIs and BFF
├── Source & Evidence module
├── Process Knowledge module
├── Automation Engineering module
├── Verification & Release module
└── Governance module

Agent worker deployment
├── research and elicitation
├── process architecture
├── implementation and repair
└── verification assistance

Ingestion worker deployment
├── parsing
├── OCR/transcription
└── connector synchronization

Isolated build/verification workers
├── generated-code execution
├── static and security scanning
└── reproducible builds

Infrastructure
├── PostgreSQL
├── object storage
├── durable queue/event bus
├── secret manager and KMS
└── OpenTelemetry-compatible telemetry backend
```

Recommended database schemas:

- `source_fabric`
- `process_knowledge`
- `agent_runtime`
- `automation_engineering`
- `verification_release`
- `governance`
- `platform_operations`

Modules do not access another module's tables. They use application interfaces or versioned events, even while running in one process.

### Extraction criteria

A logical module becomes a separate network service only when justified by:

- A distinct security boundary.
- Independent scaling needs.
- Independent deployment cadence.
- Clear team ownership.
- Customer deployment requirements.

The isolated build/verification worker is a physical boundary from the beginning because it executes generated, untrusted code.

## 13. Reliability and observability

### Reliability

- Transactional outbox for domain events.
- At-least-once event delivery with idempotent consumers.
- Operation leases and heartbeats.
- Persisted checkpoints and resumable agent runs.
- Classified retry policies with exponential backoff.
- Dead-letter handling and administrative replay.
- Optimistic concurrency for mutable aggregates.
- Database backup, point-in-time recovery, and restore testing.
- Object-version retention aligned with tenant policy.

### Observability

OpenTelemetry traces connect:

```text
HTTP request
-> domain command
-> operation/job
-> agent/model/tool calls
-> file/build/test operations
-> audit and domain events
```

Required measurements include:

- API and operation latency/error rates.
- Queue lag and worker saturation.
- Model tokens, cost, latency, and failures by tenant/use case.
- Tool calls and policy denials.
- Context size and compaction.
- Ingestion quality and connector lag.
- Verification duration and failure categories.
- Storage consumption and export volume.

## 14. Export format and customer boundary

An export should contain:

```text
automation-release/
├── src/
├── tests/
├── schemas/
│   ├── input.schema.json
│   └── output.schema.json
├── semantic-contracts/
│   ├── prompts/
│   ├── tool-schemas/
│   └── model-policy.yaml
├── integration-contracts/
├── config/
│   └── example.env
├── deployment/
│   ├── Dockerfile
│   └── runtime-requirements.md
├── provenance/
│   ├── process-version.json
│   ├── rule-code-map.json
│   └── rule-test-map.json
├── reports/
│   ├── verification-report.json
│   ├── regression-report.json
│   └── security-scan.json
├── SBOM.json
├── release-manifest.json
└── README.md
```

The manifest declares:

- Exact process and artifact versions.
- Input/output and error contracts.
- External dependencies and required credentials without secret values.
- LLM provider and model capability requirements.
- Network, resource, timeout, and retry assumptions.
- Audit events emitted by the generated code.
- Human-review outputs expected from the customer runtime.
- Known limitations and accepted verification findings.
- File digests and release signature.

After export, the customer owns deployment, live data processing, scaling, operational monitoring, incident response, and rollback.

## 15. Explicitly out of scope

- Production process-instance state.
- Live case execution.
- Production human-task queues.
- Production business-event ingestion.
- Runtime case escalation.
- Production autoscaling and availability.
- Live deployment orchestration.
- Production canary management.
- Production rollback execution.
- Monitoring customer production business outcomes.

Customer-reported incidents or sanitized cases may be imported as maintenance evidence or offline test fixtures. OpenKnowledgeWorker then produces a new verified release rather than modifying a live deployment.

## 16. Migration from the current implementation

### Phase 1 — domain foundation

1. Add tenant and actor ownership to all entities.
2. Replace generic knowledge rows with claims, evidence relations, authority, scope, and effective periods.
3. Introduce change sets and enforced lifecycle states.
4. Define typed Process IR with stable step and rule identifiers.
5. Make existing Markdown PDD a projection.
6. Introduce transactional outbox and immutable artifact versions.

### Phase 2 — controlled runtime

1. Replace separate chat and coding loops with a shared checkpointed runtime.
2. Introduce typed tool contracts and centralized policy decisions.
3. Route agent mutations through domain application interfaces.
4. Unify context construction across research, elicitation, implementation, and verification.
5. Move long-running work out of Flask request threads.

### Phase 3 — automation supply chain

1. Require approved AutomationPackages as compiler input.
2. Add execution-design review before generation.
3. Store versioned workspaces and stable traceability mappings.
4. Separate implementation and verification agents.
5. Run builds and tests in isolated workers.
6. Add immutable candidates, reports, releases, and export manifests.

### Phase 4 — enterprise controls and integration

1. Add SSO, SCIM, RBAC/ABAC, approval policies, and separation of duties.
2. Add enterprise connectors with ACL inheritance and incremental sync.
3. Add model/data movement policy and secret-manager integration.
4. Add infrastructure as code, telemetry, backup/restore, SLOs, and operational runbooks.

## 17. Architectural decisions

1. **Six logical components are sufficient.** People collaboration and impact analysis belong in Process Knowledge; source adapters belong in Source Fabric; artifact management belongs in Automation Engineering.
2. **No production execution component is required.** Offline execution is contained within Verification.
3. **No general-purpose runtime integration gateway is required initially.** Source adapters live in Source Fabric, exported integration ports live in Automation Engineering, and agent tools call internal application interfaces under Governance policy.
4. **The Agent Runtime is horizontal infrastructure.** It supports the lifecycle but does not own authoritative domain state.
5. **The web UI is not a seventh domain component.** It provides task-oriented views over the six components.
6. **PostgreSQL is the initial system of record.** Explicit relational models and dependency edges are preferred over introducing a graph database prematurely.
7. **Microservices are a deployment choice, not the logical design.** Module boundaries and contracts remain the same whether in-process or remote.
