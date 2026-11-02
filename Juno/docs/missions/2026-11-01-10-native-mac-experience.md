# Mission 10 — make Juno a better native Mac work companion

Drafted November 1, 2026. Status: preview.12 increment delivered; remaining acceptance is explicitly tracked in the linked review.

## Outcome

Make Juno easier to scan, navigate and trust on the work desktop and laptop. A person should be able to identify an issue, inspect its context, clarify one uncertainty and return to work without losing a draft or wading through setup controls. Preserve Juno’s conversational personality and end-of-day diary rather than turning it into another task manager.

This mission authorizes no production replacement merely by being written. Implementation, app installation and installer delivery must be reported separately. Do not claim an older package includes subsequent source changes.

## Evidence and lessons from TaskDock

Reviewed TaskDock’s `docs/beta-4-macos-mission.md`, `docs/interface-and-help.md`, current AppKit entry point and recent interface commits; reviewed Juno’s SwiftUI workspaces, previous usability audit and preview.11 build evidence. The mission began with source review; execution evidence is in [the native review](../reports/native-review-2026-11-01.md).

The maintenance checkout still uses AppKit/WKWebView. The separate `/Users/dmccoy/bin/python/TaskDock-beta4` worktree contains the native implementation at build 52 (`8a97d37`); its stabilization review documents stable editor identity, draft-preserving inspectors, fixed actions, aligned settings and native date controls. Its verification ledger explicitly separates mounted callbacks from physical/native acceptance. Juno already uses SwiftUI/AppKit: apply those concrete interaction and preservation lessons without adopting TaskDock’s task-editing scope.

| Lesson | Application to Juno |
| --- | --- |
| One clear workspace with a focused inspector | Keep issue selection/search visible while one issue’s details are reviewed. Avoid repeating a full editor for every task. |
| Setup belongs in grouped Settings | Move routine connection/model/computer administration out of the daily work area, preserving discoverability and recovery. |
| Display choices must not change data or permissions | Collapsing a panel or hiding an optional field never clears facts, disconnects a source or expands sharing. |
| Native menus and file panels should work predictably | Add useful keyboard commands, focus/search behavior, Help and standard open/save interactions where supported. |
| Drafts and multiple views need a clear save contract | Preserve drafts across navigation; distinguish draft, saved, queued offline and failed states; prevent stale overwrites. |
| Packaging and preservation are part of the feature | Use consistent release metadata and verify existing records, pairing and offline state before calling an update ready. |

The TaskDock screenshot sent to the wrong chat on October 30 is not treated as a Juno change request.

## Product boundaries

- TaskDock remains the task system of record. Juno reads approved task/evidence fields; this mission adds no task writes, provider refreshes or credential import.
- Recommendations remain suggestions. No automatic assignments, calendar reservations, employee messages or source edits. Employee availability and capability remain separately reviewed; candidate staff and changing/unknown shifts are not confirmed capacity.
- Keep real work data on the approved work Mac and paired laptop cache. No external cloud/model fallback or broader provider grants.
- Preserve memories and their message links, conversations, diaries, planning facts, schedules, holds, queued operations, conflicts, owner/workspace IDs, pinned certificates, device trust and existing credentials.
- Keep offline entries/edits, manual meeting-mode switching, reviewed memory correction/deletion and the approximately 15-minute end-of-day interview.
- Do not replace Juno’s backend, database or LAN protocol solely for visual consistency. A future XPC/private-worker change would need its own proven benefit and compatibility work.

## Priorities

### P0 — responsive interaction and safe drafts

1. Audit blocking calls on the UI thread, beginning with TaskDock and provider Keychain access. An earlier live refresh was sampled waiting inside macOS Security on the main thread. Run potentially blocking work away from that thread; show an honest waiting state and keep navigation/window controls usable. Never weaken Keychain authorization or certificate checks to avoid a wait.
2. Define cancellation precisely: cancel a request where supported, or ignore a late result safely. Do not claim cancellation stopped an OS authorization prompt or a completed write. Late refresh/model results must not replace a newer selection or draft.
3. Audit Plan, Chat, Memories, check-in and setup forms for navigation/reload draft loss. Preserve recoverable edits when switching sections, selecting another item or encountering an error. Use explicit Save/Apply/Cancel behavior. Dirty drafts must survive stale-save conflicts; Discard must be deliberate.
4. Protect an existing chat draft when actions such as Discuss this detail or Discuss estimate prepare another prompt. Offer a separate draft or an explicit replacement choice; never silently overwrite it.
5. Show local save, offline queue acknowledgement, failed sync and conflict states in ordinary language. A generated reply is never proof that something was saved.

### P1 — daily work layout

**Today:** keep a short orientation to the day: due work, recorded blockers, next continuity item and a clear entry into check-in. Place source freshness in a compact status area; expose detailed coverage/errors on demand. Unknown deadlines/blockers must not look clear or complete. Do not choose a priority without the required clarification.

**Plan:** replace the growing wall of expanded issue cards with a searchable/selectable issue list and one consistent detail inspector. In the list show title, room, priority/due date and a compact blocked/needs-information indicator. In the inspector show shared request facts, source time, Juno-confirmed context, duration review, person/support and next action in that order. Keep one focused question visible, with additional questions available without overwhelming the user. Retain existing filters, scope notices, draft review and the room/person window workflow. Explicitly-none, unknown, withheld, title inference and confirmed facts must remain distinct. Request completeness is not scheduling readiness.

**Schedules:** retain room/person/work-opening comparison, but use aligned day/time headings and a common visual scale where a timeline is useful. Keep the selected date, room and person visible. Show usable overlap windows alongside occupied/working intervals, and keep linked issues close to those windows. Distinguish a possible window from a saved hold. Preserve class exclusions, closures, supervision constraints, staffing status, caps and uncertainty. Support narrow-window stacking or horizontal scrolling without clipped selectors or duplicate scrollbars.

**Chat and memories:** keep conversation navigation, composer and review actions predictable. Saved-memory status must continue to survive edits/restarts/sync and clear appropriately after deletion. Make source/review links available without filling each message with controls. Keep neutral meeting mode visibly identifiable without exposing private-mode replies.

**Connections and evidence:** summarize connection health, last successful read and next required action. Put credentials, selected resources, raw metadata and troubleshooting behind purposeful detail sections. Preserve explicit account/resource/permission review. Add evidence filters/paging if the measured volume warrants it; never silently truncate and describe the result as complete.

### P1 — Mac application conventions

- Provide a native Settings window with grouped Connections, Local model, Computers & sync, Appearance/accessibility and About/help. Keep one shared state/service authority; a Settings window must not launch another backend or silently write independently.
- Keep My workday navigation focused on Today, Chat, Plan, Schedules, Check-in and Memories. Saved sources remain easy to reach. Provide migration links so existing setup destinations remain discoverable.
- Use consistent toolbar positions and primary-action labels. Keep Save/Cancel visible in long forms and sheets. Put short checkbox labels beside controls; constrain form widths and avoid fields stretching across the whole desktop without benefit.
- Support standard Command-comma Settings, Command-F search in the current workspace, Escape cancellation and useful existing edit/Undo/Redo actions. Only advertise shortcuts that work. Define behavior in text editors so commands do not unexpectedly submit messages or discard text.
- Provide accessible labels, predictable tab order, visible keyboard focus, selectable content and status conveyed by more than color. Test light/dark appearance and increased text size.
- Keep work dates grounded in America/Chicago, default date selections to today when first opening a workflow, and honor an intentional selected date while it remains open. Use 12-hour AM/PM times throughout visible schedules and forms. Do not convert date-only due dates through UTC or overwrite an active selection at midnight.
- Centralize release/build metadata used by development and packaged About/footer/installer labels. Keep existing bundle identities and data locations stable; version cleanup is not permission to move user storage.

## Execution milestones

| Milestone | Deliverable | Gate |
| --- | --- | --- |
| 0 — fresh baseline | Current native captures, navigation/action inventory and retained-feature checklist; record source/package baseline and known limits. Measure startup, issue search and selection with representative data. | Separate source findings from observed behavior. Identify minimum supported laptop layout and any unresolved native inspection limitation. |
| 1 — responsiveness and drafts | Keychain/background-work handling, safe late-result behavior, draft-preserving navigation and prompt handoff. | Artificially delayed reads/auth and stale saves do not freeze the UI, lose edits, apply a late result to another issue or bypass authorization. Test backend crash/reconnect as relevant. |
| 2 — native shell and focused workspaces | Grouped Settings, working menu commands, Plan list/inspector, compact Today and consistent forms. | Main workflows remain reachable; selection/search context survives inspection; no removed feature, hidden-field data loss or duplicate service owner. Native checks at agreed laptop and desktop sizes. |
| 3 — schedules and evidence | Better room/person/overlap presentation; source health and evidence browsing improvements. | Known class/shift/closure/hold cases retain identical constraints. Unknown schedules/candidate staff are never offered as confirmed capacity. Large evidence sets remain navigable and truthful. |
| 4 — human acceptance and delivery | HumanLab scenarios, native review, preservation report, release notes and a fresh self-contained installer. | Automated results, actual native observations and physical two-Mac results labeled separately. No acceptance-by-compilation alone. |

Deliver a usable increment after each milestone rather than bundling every redesign into one replacement. Start with responsiveness/draft safety, then the Plan list/inspector and Settings. Preserve a reversible app candidate and verified data backup before an authorized installed update.

## Verification and acceptance

Use synthetic records and isolated services for mutation/failure tests. Do not create test tasks, memories, holds or employee communications in production merely for screenshots.

Required scenarios:

1. Select a classroom issue, understand its recorded context, inspect the source timestamp and start one focused clarification without losing list position or an existing chat draft.
2. Review an estimate/room/person draft, switch views, return, encounter a revision conflict, correct it and explicitly save; Cancel leaves canonical data untouched.
3. Compare a room and person at a chosen date, identify an overlap excluding classes and holds, and understand why another interval is unavailable. No suggested interval becomes a reservation automatically.
4. Interrupt and resume the end-of-day interview; distinguish a diary draft from a confirmed saved entry.
5. Save/review/correct a memory, verify the message badge, and exercise deletion only with disposable data. Preserve independently saved memories when a conversation is deleted.
6. Delay or deny Keychain access, lose the network or stop a disposable backend: the UI remains responsive, explains the actual state and offers a safe recovery path.
7. Restart offline, create/edit diary and memory records, reconnect with pending/conflicting operations, and verify no lost/duplicate edits. A laptop view change must not alter host identity or sharing.
8. Use keyboard-only navigation and perform the same primary flows at laptop and desktop sizes, with larger text and light/dark appearances. Record exact tested dimensions, not a generic “responsive” claim.
9. Expand and relocate the installer, verify bundled dependencies/private-data exclusion, upgrade a disposable earlier database with readable backup, and check release-label consistency. Keep the production work host intact.

At baseline, establish measured performance budgets for representative task/evidence volumes. At minimum, no synchronous credential/network work may block ordinary navigation; search and inspector rendering must avoid an unbounded full-detail view per record. Report measured latency and volume limits rather than inventing a pass threshold after seeing results.

Use the existing native/backend/installer checks where they provide real coverage. Add focused tests for draft preservation, main-thread blocking prevention, late responses, inspector selection and unchanged scheduling/privacy semantics. Avoid brittle tests that only search for UI label strings. HumanLab should test these workflows through supported interactions; its availability does not substitute for actual Mac screenshots, keyboard use or physical laptop sync acceptance.

## Outputs and definition of done

Outputs: updated native UI, retained-feature checklist, before/after visual evidence, HumanLab findings, targeted automated reports, preservation/rollback notes, updated build status, source pushed to GitHub and a versioned installer with checksum. Keep private work content, screenshots containing sensitive information, credentials and pairing material out of committed reports.

The mission is complete when everyday work takes fewer navigation steps, one issue can be understood without an expanded-card wall, forms/drafts have reliable exits and recovery, and authorization/network waits do not freeze Juno. Existing task-sharing limits, schedules, memories, diaries, pairing and offline edits must continue to work. Record any untested physical-device behavior or release-signing limit explicitly. No automatic task writes or employee actions are part of completion.

## Execution result

Preview.12 implements the responsiveness, draft safety, focused Plan and native Settings increment. The actual work app is updated with preservation checks; the fresh installer passed extracted-payload verification. See [coverage, discovered defects and remaining acceptance](../reports/native-review-2026-11-01.md). Common-scale timeline refinement, high-volume latency budgets, actual VoiceOver/larger-text acceptance and physical M5/two-Mac checks remain follow-up work. The complete aspirational mission is not certified as exhaustive or perfect.
