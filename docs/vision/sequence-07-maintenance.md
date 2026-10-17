# Sequence Diagram: Long-Term Process and Automation Maintenance

## Purpose

This flow begins when organizational evidence or requirements change and ends with a newly verified export. It reuses the governed discovery and release lifecycle instead of editing a published process or release in place.

```mermaid
sequenceDiagram
    autonumber
    actor Architect as Process Architect
    actor SME as Subject-Matter Expert
    actor Engineer as Automation Engineer
    participant UI as OpenKnowledgeWorker Web / BFF
    participant SF as Source Fabric
    participant Bus as Domain Event Bus
    participant PK as Process Knowledge
    participant AR as Agent Runtime
    participant Gov as Governance Control
    participant AE as Automation Engineering
    participant VR as Verification and Release

    alt New or changed source
        SF->>SF: Ingest immutable new ArtifactVersion
        SF->>Bus: ArtifactVersionCreated(oldVersion, newVersion)
        Bus->>PK: ArtifactVersionCreated
    else SME correction or reported issue
        Architect->>UI: Record correction or import sanitized issue evidence
        UI->>PK: createChangeTrigger(type, evidenceRefs, rationale)
    end

    PK->>PK: Traverse evidence -> claims -> rules -> steps dependencies
    PK->>PK: Create ImpactAssessment
    PK->>Bus: ProcessImpactDetected(changedClaimIds, ruleIds, stepIds)
    PK-->>UI: Business impact summary

    Bus->>AE: ProcessImpactDetected
    AE->>AE: Resolve stable IDs through traceability mappings
    AE->>AE: Create AutomationImpactReport(files, symbols, tests, contracts, releases)
    AE-->>UI: Automation impact and compatibility summary

    Architect->>UI: Create change set from last approved ProcessVersion
    UI->>PK: createChangeSet(baseVersionId, impactAssessmentId)
    PK-->>UI: ChangeSet(OPEN)

    Architect->>UI: Start maintenance analysis
    UI->>AR: startRun(MAINTENANCE, changed evidence + impacted knowledge)
    AR->>PK: Propose claim revisions, conflicts and questions
    PK-->>UI: Review queue

    opt Additional expert clarification is required
        Architect->>PK: assignQuestion(questionId, SME)
        SME->>UI: Submit answer, scope, exceptions and evidence
        UI->>PK: recordExpertResponse(response)
        PK->>PK: Reevaluate impacted claims and Process IR
    end

    Architect->>PK: Apply structured Process IR changes
    PK->>PK: Validate change set and compute semantic diff
    PK->>Gov: Request process-version approval
    Gov-->>PK: ApprovalRequirementsSatisfied
    PK->>PK: Publish immutable new ProcessVersion
    PK->>Bus: ProcessVersionPublished(newVersionId, packageDigest)

    Engineer->>UI: Request automation upgrade plan
    UI->>AE: createUpgradePlan(oldVersion, newVersion, baseRelease)
    AE->>AE: Compare packages and mappings
    AE-->>UI: UpgradePlan with breaking changes and affected artifacts

    Engineer->>UI: Approve targeted implementation update
    UI->>AE: startUpgrade(upgradePlanId)
    AE->>AR: startRun(MAINTENANCE/REPAIR, impacted scope only)
    AR->>AE: Versioned code, test and mapping updates
    AE->>AE: Freeze new BuildCandidate
    AE-->>VR: Candidate available for verification

    VR->>VR: Run full regression against previous Release
    VR-->>UI: Verification and behavioral diff report
    Gov->>VR: Approve new release after required review
    VR->>VR: Create and export new immutable Release
    VR-->>Engineer: New release bundle; prior release remains auditable
```

## Maintenance invariants

- Published ProcessVersions and Releases are never edited in place.
- New evidence does not automatically invalidate or rewrite an approved process.
- Impact analysis uses stable claim, rule, step, code-symbol, and test identifiers.
- Targeted generation is followed by complete release regression.
- A customer-reported production issue is imported as evidence or a sanitized test fixture; OpenKnowledgeWorker does not reach into the production runtime.
