# Juno development mission

Extend Juno’s existing connectors, planning, briefing, repair-history and weekly-draft capabilities. Do not rebuild these foundations. Resolve installed schedule configuration first, then join one printer issue across Beacon and TaskDock and deliver an evidence-linked read-only briefing. Keep TaskDock writes in a separate later release.

Baseline: the user supplied Juno’s code and existing-test-evidence review. It did not change code or rerun tests. The coverage below is reported evidence, not a new independent audit. Verify current behavior and run appropriate checks for changes; do not describe historical test results as current validation.

Juno owns planning preferences and proposed plans. TaskDock owns assignments/approvals; Beacon owns equipment facts. Preserve existing sharing controls, identity/freshness checks, planning constraints, reviewed facts, repair estimates, persistent weekly drafts and recovery behavior.

## Prioritized tickets

### JUN-00 — Recover installed schedule configuration

**Priority:** P0 first

**Existing coverage reported:** Scheduling capability exists, but the installed data root lacks previously entered schedules.

**Acceptance criteria for remaining work:**

- Identify installed/runtime data roots and the intended authoritative schedule configuration; diagnose missing data without assuming a new scheduling feature is needed.
- Back up affected data before recovery; reconnect or recover schedules without overwriting existing records. Surface conflicts for review.
- Confirm schedules load in the installed app, persist after restart and affect a representative availability prediction.
- Clearly report unresolved missing configuration; do not infer unrestricted availability.

**Dependencies:** Installed app configuration and authorized access to relevant schedule stores.

### JUN-01 — Extend existing connectors and record relationships

**Priority:** P0

**Existing coverage reported:** TaskDock read-only snapshots, sharing/version/identity/freshness checks; limited Beacon alert connector with failure retention.

**Acceptance criteria for remaining work:**

- Agree cross-app identities and stable asset–alert–issue–task references; use explicit IDs, not name matching.
- Reuse existing connectors. Preserve source links, versions, update/retrieval times and permission boundaries.
- Handle unmatched and conflicting relationships explicitly; distinguish unavailable data from empty results.
- Consume current alerts read-only initially; add durable issue relationships when Beacon supplies them.

**Dependencies:** Existing TaskDock snapshots and Beacon feed; shared contract. BCN-03/11 and verified TD-05/read capabilities gate linked-pilot completion, not all connector work.

### JUN-02 — Combined evidence-linked operational briefing

**Priority:** P0

**Existing coverage reported:** Saved daily evidence, dated completions, blockers, next-workday suggestions, stale/missing TaskDock warnings. Current daily briefing excludes Beacon alerts.

**Acceptance criteria for remaining work:**

- Incorporate Beacon observations and linked TaskDock work into the daily briefing with evidence links for every operational claim.
- For one printer, explain alert/issue, assigned work, teaching impact, next action and whether a department-lead decision is required.
- Distinguish observation, acknowledged issue, completed work and verified recovery; do not infer recovery from task closure.
- Show stale/missing sources and unresolved joins. Include coverage gaps only when schedule data is available and authoritative.

**Dependencies:** JUN-01; BCN-03/04/11 and TaskDock linkage for full pilot; JUN-00 for schedule-dependent claims.

### JUN-03 — Extend prioritization and contradiction handling

**Priority:** P0

**Existing coverage reported:** Dean/operations importance, dates, TaskDock priorities, blockers, explained suggestions, dated override; conflicting important priorities prompt a question.

**Acceptance criteria for remaining work:**

- Preserve existing ranking and overrides; add structured service impact and approval-authority reasoning.
- Explain source-backed priority and distinguish service disruption from a decision requiring the department lead.
- Surface cross-source contradictions rather than silently select a convenient value; do not invent authority, deadlines or availability.

**Dependencies:** JUN-01–02; agreed service-impact and authority fields/policies.

### JUN-04 — Extend capacity planning and allocation

**Priority:** P1

**Existing coverage reported:** Hours, occupancy, building access, staff schedules, supervision, capability checks, commitments, interruption reserve and feasible repair windows. Suggestions are alternatives, not a committed weekly schedule.

**Acceptance criteria for remaining work:**

- Preserve existing constraints and validate recovered schedules. Designate authoritative coverage and qualification sources.
- Integrate TaskDock qualifications where available; explicitly show missing/stale inputs.
- Coordinate allocation across tasks so the same person/time is not promised repeatedly. Clearly label alternatives versus committed plans.
- Changes requiring TaskDock assignment remain proposals until JUN-05 succeeds.

**Dependencies:** JUN-00; JUN-03; verified TD-07 and authorized scheduling inputs. Calendar integration is needed only if the existing source does not cover the requirement.

### JUN-06 — Enrich existing weekly drafts

**Priority:** P1

**Existing coverage reported:** Persistent editable Dean drafts from confirmed diaries/task context, missing diary coverage, source-change comparison and recovery; no automatic sending.

**Acceptance criteria for remaining work:**

- Preserve draft editing/recovery and coverage warnings; add decisions, milestones, unresolved issues and agenda structure.
- Link operational evidence throughout and identify incomplete or changed source coverage.
- Do not automatically send drafts. Validate that refreshing sources does not silently overwrite user edits.

**Dependencies:** JUN-01–03; TD-09 only for enhanced milestone data, not existing weekly drafting.

### JUN-09 — Recommendation lifecycle and evaluation

**Priority:** P1 read feedback first

**Existing coverage reported:** Correctable preferences/estimates, reviewed history and existing tests for stale sources, staff availability, conflicts and repeated saves.

**Acceptance criteria for remaining work:**

- Record accepted, dismissed and rescheduled recommendations with rationale where supplied; retain preference corrections.
- Extend existing tests for cross-source contradictions, permission restrictions, missing schedules, unmatched issues and stale feeds.
- Run relevant checks and distinguish current results from historical evidence. Add write retry/version/duplicate tests when JUN-05 ships.

**Dependencies:** JUN-02–03 for read-only feedback; JUN-05 only for action-execution checks.

### JUN-05 — Reviewed TaskDock writes

**Priority:** P1 after read-only pilot

**Existing coverage reported:** Reviewed changes to Juno planning facts already have revision checks, provenance and duplicate protection. No TaskDock task creation/delegation/deadline writes exist.

**Acceptance criteria for remaining work:**

- Keep planning-fact review distinct from operational writes. Preview task creation, delegation and deadline changes with target and effect.
- Apply accepted actions through supported TaskDock endpoints with user-scoped permission and revision checks.
- Prevent repeated execution; show saved links or explicit failure/conflict. Reconcile uncertain delivery before retrying.
- Exclude direct equipment, building access, purchasing and financial decisions from this release.

**Dependencies:** Validated JUN-01–03 read-only pilot; verified TD-10 write contract and identity mappings. Existing Juno reviewed saves are a foundation, not proof of TaskDock writes.

### JUN-07 — Incremental semester and lifecycle planning

**Priority:** P2

**Existing coverage reported:** Semester schedules, reviewed repair patterns and duration ranges from verified completed repairs.

**Acceptance criteria for remaining work:**

- Preserve semester and repair-estimate capabilities; add lifecycle/condition/usage/cost evidence as available.
- Explain replacement suggestions, missing inputs and estimates without making purchase decisions.
- Save accepted work to TaskDock only through JUN-05; read-only recommendations can ship first.

**Dependencies:** JUN-00 and JUN-03; BCN-10/current authorized lifecycle data for analysis; JUN-05 and TD-03 only for task/recurrence creation.

### JUN-08 — Authorized procedure retrieval

**Priority:** P2

**Existing coverage reported:** Saved evidence can provide reference text to the local model; no dedicated procedure retrieval/version workflow.

**Acceptance criteria for remaining work:**

- Retrieve authorized procedures from designated linked sources and preserve source/version/retrieval metadata.
- Identify stale or missing instructions for review; distinguish reference text from verified current procedures.
- Treat document content as reference, not authority to execute instructions or broaden permissions.

**Dependencies:** JUN-01; authorized document connectors and agreed procedure locations.

## Release and completion gates

1. Recover schedule configuration and validate persistence; connector/contract work can proceed independently.
2. Join one Beacon printer issue and TaskDock task using stable references.
3. Deliver the combined briefing and priority explanation; retain read-only behavior.
4. Extend allocation, weekly drafts and recommendation feedback.
5. Add reviewed TaskDock writes only after the read-only pilot and write contract are validated.
6. Add lifecycle and procedure assistance incrementally.

**Configuration gate:** Installed app loads intended schedules after restart and demonstrates their effect on availability.

**Read-only pilot gate:** Juno traces a printer observation/issue to assigned work and verified condition, links evidence, explains the next action and decision authority, and clearly shows stale/unavailable/unmatched records. Test failed verification and task completion without recovery.

**Write release gate:** An accepted TaskDock action is applied once with correct permissions/version checks, returns its saved link, and handles retries/conflicts without silent duplication.

## Shared connection contract

Include this contract in all three applications. Agree on the details before implementing cross-app connections.

1. **Record ownership:** TaskDock owns tasks, assignments, checklist completion, approvals, projects, and handoffs. Beacon owns physical resources, condition, stock, maintenance, reservations, and loans. Juno owns planning preferences, proposed plans, and accepted planning history. Other apps store references rather than independently editable copies.
2. **Identifiers:** Use stable person, team, room, asset, issue, task, and reservation references. Designate a source for people/team identities; do not match records solely by names or email.
3. **Event contract:** Include event ID, event type, source app, record ID, record version, occurrence time, and correlation ID. Receivers handle repeated and out-of-order delivery safely.
4. **Reliability:** Provide acknowledged delivery, bounded retries, visible failures, and a reconciliation mechanism for missed updates.
5. **Authorization:** Enforce permissions in each owning app, including Juno-originated requests. Limit student access to operationally necessary records.
6. **Auditability:** Preserve actor, time, source, and material changes. Show timestamps and links wherever copied summaries appear.
7. **Integration approach:** Inspect existing APIs and deployment constraints before choosing transport or infrastructure. Avoid direct cross-app database writes.

## Cross-app sequencing and dependency rules

Agree on extensions to the existing feed and identity contracts → implement Beacon state/issue foundations and verify TaskDock linkage → complete the printer-repair pilot. Juno schedule recovery and read-only connector work can progress in parallel; its linked briefing depends on usable source relationships. Then expand stock receiving, lending, reporting, and reviewed TaskDock writes.

TaskDock ticket references identify external requirements, not verified implementations. Inspect TD-05/TD-06/TD-07/TD-09/TD-10 before relying on them. Read and write interfaces may ship separately. Develop producer and consumer against agreed fixtures/contracts, then run joint validation; reciprocal references are integration gates, not circular implementation prerequisites. Record missing endpoints or fields explicitly.

**P0:** Reliable operational foundations and the linked pilot. **P1:** Departmental workflows and integration expansion. **P2:** Incremental planning and reporting.

## Implementation ledger — November 4, 2026

This ledger distinguishes Juno source completion from live integration acceptance. The original mission above remains unchanged.

| Ticket | Implemented/verified here | Remaining gate |
| --- | --- | --- |
| JUN-00 | Prior backed-up recovery and preview.21 restart preserved schedules; installed native room/work hours and next-day capacity were observed. | Physical laptop and worker reconnect are separate acceptance; no recovery was repeated for this mission. |
| JUN-01 | Existing readers retained; safe Beacon relative links/optional reference metadata; exact reviewed alert/workspace/task references with revisions, source-origin/instance fencing, owner isolation and explicit unavailable joins. | Beacon stable asset/issue identities and cross-app contract agreement/joint validation. No name-based automatic join. |
| JUN-02 | Combined native/API briefing, source-evidence inspection, assignments/impact when shared, explicit unknowns, stale/unmatched/conflicting sources, completion-versus-recovery distinction; coherent verification metadata required for a recovery claim. | Real printer pilot against verified Beacon issue/condition and TaskDock linkage. Synthetic consumer results do not pass this gate. |
| JUN-03 | Existing ordering/dated overrides retained; source-backed service-impact reasons and explicit decision requirements; contradictions prevent unsupported allocation. | Agreed producer authority/impact semantics and institutional policies. |
| JUN-04 | Non-overlapping proposed person/room/owner blocks with supervision, personal capacity, existing holds and employee weekly limits; questions suppress allocation; alternatives stay distinct. | Authoritative staff coverage and TaskDock qualification records; no committed assignment changes. |
| JUN-06 | Decisions/agenda, unresolved operational issues, evidence references, milestone gaps and source-change basis added; saved writing/recovery retained and tested. | Enhanced TaskDock milestone/project facts; live cross-app evidence acceptance. |
| JUN-09 | Accepted/dismissed/rescheduled feedback, source/revision fences, exact retry receipts, retained reasons, native review/history and regression tests. | Write-action retry/version/reconciliation tests belong to JUN-05, which is not enabled. |
| JUN-05 | Write boundary and exact missing requirements documented; existing reviewed local saves remain separate. | Blocked: inspected TaskDock Juno contract advertises `write_tasks: false`; no supported write/status-reconciliation contract or validated live read-only pilot. No bypass is implemented. |
| JUN-07 | Existing repair estimates retained; recurring-repair evidence shown as investigation candidates with missing lifecycle/cost/identity inputs. | Authorized Beacon lifecycle/cost/policy evidence for replacement analysis; accepted-task creation additionally requires JUN-05. |
| JUN-08 | Designation/retrieval of already-authorized saved procedure references, source/snapshot/account identity, changed/stale/missing text, removal and untrusted-reference-only model context. | Live designated document APIs/locations for linked documents beyond existing saved evidence. No arbitrary URL/attachment reader. |

Current validation and exact scope are in [the mission report](../reports/operational-evidence-2026-11-04.md). The source workflow is documented in [Operational evidence](../OPERATIONAL-EVIDENCE.md); producer handoff requirements are in [the proposed shared contract](../OPERATIONAL-CONNECTION-CONTRACT.md). The complete multi-app mission remains open at its external integration gates. Do not call it fully done or enable operational writes based on the local test suite.
