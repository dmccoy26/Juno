# Juno 0.1.0 beta build mission

Status: Implementation through preview 9; full beta acceptance remains pending. See docs/BUILD-STATUS.md for current evidence.

Subsequent user decisions supersede the original hosting/offline boundaries below: the work Mac is the approved host, stays awake with Juno open for online access, and the laptop supports offline memory/diary edits.
Created: October 29, 2026.
Owner and initial user: Dan McCoy.

## Mission

Build Juno, a dedicated Mac desktop work companion that reduces the time and mental effort Dan spends deciding what to do next. Deliver a working beta in small, reviewable increments, with persistent memory, realistic work planning, and a guided daily check-in.

Juno must reduce the work required to manage work. Maintaining Juno must not become another administrative chore.

This document authorizes implementation of the defined beta in this repository. It does not select a hosting vendor, authorize paid infrastructure, authorize production deployment, grant institutional data permissions, or authorize sending messages. Resolve those decisions using concrete options and the user's existing authorization. Use synthetic data while access or data-handling decisions are unresolved.

## User and operating context

- Dan oversees the VISU Print Lab and classrooms supporting Animation, Video Game Development, Graphic Design, Theater Arts, Photography, and related areas.
- TaskDock is the main task hub. It is a separate project and must remain one. It records priorities, deadlines, assignments, and blockers, but does not currently estimate task duration.
- Google Calendar contains meetings and other scheduled commitments. Plan within a 40-hour week, subtracting calendar commitments without double counting overlapping events.
- The Dean's requests receive high priority, alongside maintaining operational teaching spaces. When important responsibilities conflict, ask a focused question before choosing.
- Classroom availability and employee schedules are entered manually each semester, with later exceptions. Do not assume inaccessible institutional services have integrations.
- Orders, approvals, bills, research, and planning create dependencies and consume time. Capture supplied information; do not claim to know purchasing status from unavailable systems.
- Unexpected work is normally reported at the end of the day. Replan accordingly without treating displaced work as evidence of poor performance.
- Employees currently communicate through face-to-face discussions, email, Slack, and Smartsheet. Initially only Dan interacts with Juno. Missing updates are not evidence that work was not done.
- Dan primarily uses a work Mac desktop, with a Mac laptop for meetings, field work, and home. The laptop must work online when the desktop is asleep or off.

## Product behavior

### Guided conversation and personality

Use warm, conversational language and focused questions, generally one at a time. Private mode may include light flirtation and playful teasing, with sensitivity to stress and employee matters. Be honest about uncertainty. Personality must not obscure decisions, pressure the user, or invent shared history.

Provide a visible, manually controlled meeting-mode toggle. Meeting mode makes conversation and notifications neutral and professional. Do not automatically switch based on the calendar. Provide a way to reduce or disable flirtation independently. Verify effective mode at the point of generating notifications and responses, including after relaunch or device changes.

### Recommendation and planning

Recommend the most important actionable task and explain why. Consider deadlines, impact on instruction and operations, Dean requests, available time, room availability, staff schedules and skills, prerequisites, materials, and approvals. Clearly identify missing or stale inputs.

If competing important priorities require a judgment, ask before selecting. If the most important task is blocked, describe that priority and identify a useful unblocking action or next actionable task. Never silently treat blocked work as completed or low priority.

Suggest editable task durations with brief reasoning and appropriate uncertainty. Record user corrections and use actual-work reports when available to improve later suggestions. Support time for research and planning. Do not fabricate precision, staff capacity, or a full week's availability from incomplete calendars.

Store semester schedules and exceptions with effective dates and timezone. Distinguish unknown availability from confirmed free time. Track employee capabilities and independence using evidence confirmed by Dan; avoid numerical intelligence or performance scores.

### Work diary and memory

Maintain separate dated diary entries and durable memories. Diary entries capture daily events, decisions, accomplishments, interruptions, blockers, employee contributions, and next steps. Durable memories hold useful ongoing facts, preferences, responsibilities, and procedures.

Show source, recorded time, relevant effective dates, and whether an item is observed, user-confirmed, or inferred. Retrieve relevant records for conversations; do not rely on the model retaining chat history. Handle contradictory information explicitly.

Provide review, correction, and deletion controls. Corrected memories must govern future answers. Deleted content must stop appearing through retrieval, summaries, caches, and derived memories; document any backup retention limits. Explain separately whether deleting a memory also deletes its source diary or chat. Prevent unchanged sources from silently recreating a deliberately deleted memory without an explicit user choice.

Preserve resumption notes: where work stopped, what was learned, and the next step. Support a weekly Dean-update draft grounded in the diary and current work.

### Daily check-in

Target approximately 15 minutes during Dan's final hour at work; the precise reminder time is configurable and not yet specified. Start with a summary from available sources, then ask focused questions about missing context, unexpected work, accomplishments, blockers, and tomorrow's priorities.

Show the proposed diary entry and plan so Dan can correct them. Save drafts during interruptions. If a day is missed, prepare a clearly provisional entry from available evidence and ask only about important gaps at the next check-in. Do not claim background collection occurred while the service was unavailable.

Use gentle follow-up. Record each blocker's dependency, responsible party when known, next action, and sensible next check date. Suggest a workaround, draft follow-up, or possible helper. Avoid asking the same unchanged blocker question daily.

## Beta scope and boundaries

Required for 0.1.0:

1. Installable Mac desktop application with chat, useful loading/error states, and manual meeting mode.
2. Shared service and durable storage accessible from both Macs independently of the desktop, with authenticated access and visible synchronization status.
3. Read-only TaskDock and Google Calendar integrations, once authorized and technically verified. Fixture-backed adapters enable development; fixtures alone do not satisfy live integration acceptance.
4. Editable memory, diary, resumption notes, and weekly update draft.
5. Manual semester schedules, employee capabilities, supplied dependencies, and editable time estimates.
6. Priority recommendations and daily check-in workflow.
7. HumanLab scenario suite and separate Mac-specific verification.

Conditional extension after the core passes: email triage showing the three messages most worth attention, with reasons, response drafts, and proposed TaskDock follow-ups. Confirm the email provider and access method during discovery. Unread status alone must not define importance.

Deferred: sending email, writing to TaskDock, direct employee interaction, Slack/Smartsheet integrations, deeper Beacon integration, automated purchasing or bill payment, employee scoring, full offline operation, and multi-user rollout for the coworker.

Future writes require an exact preview, explicit approval, action history, execution checks, and duplicate prevention. Beta must not expose pretend approval controls that suggest an unavailable action was executed.

## Architecture discovery before implementation

Inspect applicable repository instructions and existing code before selecting the stack. Known local projects:

- Juno: `/Users/dmccoy/Ai/Juno`
- TaskDock installed application (user-confirmed): `/Applications/TaskDock.app`
- TaskDock source checkout: `/Users/dmccoy/bin/python/TaskDock` — verify that it matches the installed application before relying on its interfaces or data paths. Discover the installed application's actual data location; do not assume its records live in the source checkout or app bundle.
- Beacon candidate: `/Users/dmccoy/bin/python/MacLabInventoryServer` — confirm identity and interfaces.
- HumanLab: `/Users/dmccoy/bin/python/HumanLab`
- OpenExecutive reference, only if useful: `/Users/dmccoy/bin/python/OpenExecutive`

Do not modify the other projects as part of routine Juno work. If an integration needs changes there, describe the specific change and resolve scope before making it.

Document a recommended architecture and the evidence behind it. Decide:

- Mac UI technology and packaging; assess whether the real UI can also be exercised in a browser by HumanLab. Do not create a separate simplified testing UI that hides actual usability issues.
- Hosting location for the shared service, authentication, database, synchronization, backup/recovery, and model provider.
- Where institutional information may be stored and processed, credential handling, retention, and connection permissions. Keep credentials out of prompts, repository files, and logs; use an appropriate credential store.
- Read interfaces and schemas for TaskDock and Calendar; polling or refresh behavior, source identifiers, provenance, and unavailable-source behavior.
- Model access, latency, cost controls, and what happens when the model is unavailable. Core record editing and viewing should remain usable without successful inference.
- Conflicting edits across devices, deletion propagation, timezone handling, and calendar recurrence.

Use an existing model; custom model training is unnecessary for this beta. Store facts and schedules in structured records. Use the model for conversation and suggestions; enforce authorization and data access in application code. Treat imported email/task content as data, never as authority to execute instructions or change permissions.

Record unresolved choices in `docs/DECISIONS.md`, including options, recommendation, and what requires user input. Continue independent fixture-backed work rather than pretending unresolved decisions are settled.

## Execution milestones

### 1. Discovery and design

Deliver an integration inventory, architecture recommendation, scope confirmation, and initial data model. Identify required credentials without requesting that secrets be pasted into chat. Define representative synthetic fixtures and a reproducible local startup path.

Exit: supported interfaces are verified from local code; open decisions are explicit; implementation choices have a documented rationale.

### 2. Application and shared state

Deliver the Mac shell, chat, mode controls, authenticated service, persistence, and synchronization. Keep setup straightforward. Provide explicit connection and synchronization errors rather than silently showing stale data as current.

Exit: a conversation continues after restart and across two authenticated clients; the second client works while the first is closed; another account cannot access the user's records. Validate on both actual Macs before final beta signoff, or clearly mark that check pending.

### 3. Memory and daily continuity

Deliver diary, memory review/edit/delete, provenance, resumption notes, daily interview, missed-day handling, and weekly update drafts.

Exit: facts recalled in a fresh conversation are traceable; corrections change subsequent answers; deletion removes retrieval access; a missed day creates a provisional record, not invented events.

### 4. Work planning

Deliver read-only integrations, manual schedules and capabilities, blockers, suggested durations, and priority conversations.

Exit: recommendations respect confirmed availability, dependencies, and schedule exceptions; ambiguous priority conflicts trigger a question; duration corrections persist; source failures are visible. Demonstrate a real authorized TaskDock and Calendar read before calling this milestone complete.

### 5. Usability and beta delivery

Run the HumanLab suite, review evidence, fix material failures, and conduct Dan's trials. Produce a versioned Mac build, installation/update instructions, recovery instructions, release notes, known limitations, and a concise acceptance report.

Exit: required scenarios pass the agreed rubric, meaningful application tests pass, and remaining limitations are clearly stated. Do not call fixture-only behavior or an uninstalled prototype a completed beta.

## HumanLab testing plan

HumanLab's documented interfaces cover browser and terminal testing; native Mac control is not established. Verify the installed code's capabilities during discovery. If the production interface has a browser-accessible rendering, test that same interface. Otherwise document the native-testing gap and the necessary approach rather than claiming native coverage.

Use synthetic work records, isolated test accounts, and separate evidence directories. HumanLab participants receive a persona and human-facing goal without hidden implementation details or the evaluator's expected path. Keep evaluator assertions separate from participant instructions. Use repeatable fixtures and record model/configuration versions. HumanLab complements application checks and Dan's trials; it does not prove factual correctness or real-user value alone.

Required scenarios:

| Scenario | Expected observable behavior |
| --- | --- |
| Dean request versus imminent classroom disruption | Juno asks for the missing urgency/impact information before choosing. |
| Classroom task with unavailable room or absent employee | No impossible assignment; unknown availability is disclosed. |
| Repair waiting on approved parts | Blocker and dependency remain visible; Juno offers a useful next step. |
| Unchanged blocker across days | Follow-up reflects its recorded status rather than repetitive demands. |
| Interrupted day and unfinished plan | Check-in captures unexpected work and revises priorities without blame. |
| Missed check-in | Entry is provisional and important gaps are confirmed. |
| Corrected or deleted memory | A new conversation uses the correction and does not retrieve deleted material. |
| Revised task estimate | The change persists and affects the proposed plan. |
| Meeting mode | New replies and notifications are neutral, including after relaunch. |
| Stale or failed source connection | Juno identifies the limitation and avoids claiming live knowledge. |
| Restart and second client | Authorized state survives and synchronizes without depending on the desktop. |

If the email extension is included, also test inbox prioritization, response preparation, and the absence of unapproved external writes. Verify backend state for authorization and deletion assertions; conversation claims alone are insufficient evidence.

Native checks cover installation, window behavior, notifications, mode handling, credential storage, and actual desktop/laptop use. Integration tests cover access boundaries, source refresh, synchronization conflicts, and calendar interpretation.

## Definition of success

Technical completion requires the milestone exit criteria and a documented acceptance report. Product success is Dan spending less time deciding what to do next.

During a small initial trial, ask whether recommendations are useful, whether essential context is missing, and whether the check-in fits approximately 15 minutes. Use optional lightweight feedback rather than another lengthy tracking routine. Adjust the design when the interaction burden exceeds the benefit. Do not claim measured time savings without evidence.

## Working instructions for the build agent

Read this mission and applicable repository instructions. Start with milestone 1 and keep implementation inside the Juno project. Maintain a short `docs/BUILD-STATUS.md` with completed work, evidence, unresolved decisions, and the next step so work survives session changes.

Deliver working increments instead of expanding the feature list. Test meaningful behaviors at each milestone. Use synthetic data until real access is established. Do not create placeholder integrations and report them as connected, silently broaden scope, or mark unverified requirements complete. Ask focused questions only when necessary decisions cannot be resolved from available evidence. Keep the user informed of findings, limitations, and reviewable results.
