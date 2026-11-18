# Mission 16 — clearer daily work and Juno-managed recurring tasks

November 18, 2026. Status: implementation in progress; **0.2.25 / build 71 is installed and verified**, including live automatic calendar reads. Preview.45 was the first development increment. Historical results below remain as the acceptance ledger; the overall mission is not complete.

## Outcome

Juno opens to a useful account of today's work, makes planning and reporting easy to navigate, and manages explicitly approved recurring routines as real TaskDock tasks in a dedicated **Juno** column. Existing drafts, history, memories, source relationships, worker records and laptop pairing survive every update. TaskDock remains the task system of record; Juno owns recurrence definitions and planning context.

The design input is the November 18 interface recommendations DOCX and nine proposal PNGs supplied by Dan, based on the preview.43 review. The recommendations and pictured records are design references, not proof of implemented features or real events. Keep sample purchases, repairs and dates out of the production workspace. Mission 15 remains the acceptance history; carry relevant unfinished checks into this mission without erasing their results.

## Baseline and scope

At mission creation, release metadata is preview.44. Current source has a Reports destination, department-specific saved drafts, a document-style Dean reader, planning readiness calculations, schedule intersection, host/laptop synchronization, and separate read-only TaskDock access. The staffing editor still allows independent and supervised flags together, and the report overview and preparation notice can disagree. Inline Markdown is not fully rendered. No Juno Purchasing workspace or recurring-task write service is established by this mission document.

Inspect the exact source, installed build, TaskDock capabilities and Concur Helper export before implementation. Record commit, dirty-tree state, database schema, OS and viewport. Do not assume a past handoff was implemented. Proposed TaskDock requirements are in [the companion handoff](taskdock-juno-recurring-tasks.md).

This mission authorizes implementation and testing. A routine approved in the new interface authorizes its future occurrences within the reviewed scope. It does not grant blanket changes to existing TaskDock tasks, upstream Smartsheet records, assignments or financial systems. Keep code and documentation local until Dan requests a GitHub push. Do not send chair emails. Build/install only verified increments using the established data-preservation procedure; administrator prompts still require the user on the Mac.

## Product rules

- Keep a compact Juno logo and visible version by her name. Keep native macOS controls, semantic colors, system typography and both appearances. Preserve the user's appearance preference.
- Use Issues, Schedule, Reports and Sources as jobs the user recognizes. Preserve old deep links and menu routes through explicit redirects.
- Offer one next question where competing priorities need Dan's decision. Never label incomplete facts as ready or select an unapproved tradeoff silently.
- A possible work window, Juno hold, TaskDock assignment, worker report, and verified repair are different states. Say which occurred and where it was saved.
- Generated, edited, reviewed, saved locally, queued, synchronized, stale and unavailable have distinct meanings. Opening a document does not mark it reviewed. A cleared alert does not verify a repair.
- Display all times in 12-hour form. Use America/Chicago for work schedules and reporting boundaries, with the zone explicit where a device could differ.
- Keep sensitive work data and model processing on approved systems. Keep credentials in the owning app's Keychain scope. Redact test evidence committed to the repository.

## Phase 1 — trustworthy controls and state

1. Replace the two staffing checkboxes in guided and full planning editors with one choice: Me, Worker independently, Worker with me. Store the existing booleans consistently for compatibility. Preserve an old ambiguous combination until reviewed, explaining how it affects planning. Do not silently turn an old supervised task into independent work. Independent work requires the existing capability review; supervised work requires Dan's availability too.
2. Give every input a visible label that survives entry. Eliminate nested Apply-to-draft then Save puzzles. Each editor has a pinned Save/Revert or Save/Cancel footer, a clear unsaved state, and Command-S. Preserve validation, async estimate cancellation and revision checks. Closing, changing selection or leaving with unsaved changes offers Save, Discard or Keep editing. Count changed fields accurately when displaying a count.
3. Derive report availability from one selected-week/time state shared by the overview and reader. Distinguish scheduled, preparing, saved, edited, reviewed, failed and unavailable. Before Friday preparation, show the next scheduled run and links to prior drafts. A previously saved draft remains accessible at any time. Do not add Thursday early generation without aligning the backend's period rules and tests.
4. Schedule opens on today on a fresh visit, with an explicit Today command. Preserve deliberate date exploration and unsaved work within a visit. Reports show their reporting week and actual meeting boundary rather than resetting a saved historical document to today's date.
5. Render supported Markdown in Dean documents without visible syntax for formatting. Preserve original stored text. Provide plain-text and rich-text copy, verifying actual paste output. Literal hashes/asterisks in content must remain valid text.
6. Group consecutive invalidated chat replies into a concise notice with the known source/reason and retry action. Reuse the user's question only through an explicit action. Do not invent changed fields or timestamps. Never restore content purged for revoked sharing, deletion or privacy. Old text is viewable only if retained and currently authorized.
7. Put a compact source-health control in the header, with per-source last successful read, provider freshness, current failure and refresh action in its detail. A successful Juno read does not make an upstream source current. Move general explanations to contextual help while keeping actionable warnings visible.
8. Make manual Meeting mode prominent and accessible, with a text label and unobtrusive band. Do not imply full privacy protection before phase 5 is implemented.

## Phase 2 — navigation and daily workflows

Use the proposal's hierarchy as the starting point: Day (Today, Chat), Work (Issues, Schedule, Purchasing, Team), Write and recall (Reports, Memories, Sources), and Settings. Show Purchasing only when useful connection/setup content exists; never show invented counts. Recurring routines live under Issues in a clearly labeled Recurring view, with navigation from Today and TaskDock connection setup.

### Today

Use a readable main column for one pending decision, Ready to work, and Waiting or missing details. A secondary column contains today's timeline, Where you stopped, report readiness, purchasing when connected, and source health. Counts act as filters. Each suggested action gives its evidence-based reason and its actual effect. Show the confirmed diary's restart cue with a direct open/resume action. Surface due or failed recurring routines without making a technical job log the main screen.

### Issues

Provide a searchable list and selected-item inspector. Search title, room, person and exact asset references using authorized fields. Distinguish read-only TaskDock facts from Juno planning details. Show a readiness checklist for room, duration, capability/supervision, blockers, prerequisites and desired outcome. Use explicit unknown/none states. Ask the single next relevant question inline and save reviewed answers to the correct task with source/date. Preserve list selection, filters and scroll position. Find time carries exact task/workspace IDs, reviewed room, person, length and supervision to Schedule.

### Schedule

Combine the existing comparison and planning search. Use one aligned time axis for room, worker, Dan and possible windows; show Dan only when relevant or requested. Distinguish classes, closures, shifts, meetings and holds. Show short intervals without claiming they fit the selected task. Explain best fit, alternatives and limiting coverage. Reserve creates a Juno-only hold, and Copy note does not notify anyone. Retain all current weekly caps, candidates/active status, semester boundaries, exceptions and overlap checks.

### Daily check-in

Launch from Today and the reminder into a focused flow with five steps, one question, saved progress and an optional today's-records pane. Source hints require Add to answer; they do not become diary facts automatically. Debounce local recovery safely, distinguish it from canonical saves, handle navigation during save, and show queue state offline. Review and explicit confirmation precede report inclusion. Keep source labels and manual correction/carry-forward.

### Reports

Use a week-grouped document list, reader/editor and collapsible evidence pane. Show To and Subject for chair emails. Dean notes remain concise talking points grouped by decisions, progress, blockers and relevant purchasing; chair drafts remain complete emails. Provide Present with larger type, Copy, Edit and explicit Mark reviewed. Preserve every existing edit. New generation and selected-evidence redrafts create a new version with inspectable history; never overwrite the user's version.

Implement per-item include/exclude only after the backend can record exact authorized evidence IDs and generation basis. Show included and omitted items and reasons, rather than guessing them from prose. Keep Smartsheet Modified labeled last update, never completion. A Use current style action previews a greeting/signature-only change and preserves the body.

Retain weekly routing: Alex/VISU includes GDES, VGAM, ANIM, Flextight and Ali Rex; Amy/LWR covers Sorin; Kathryn/Performing Arts covers ARTS 140 and Music. Holy Cross 203 and 326 go only to the Dean. Use Howdy [name], and -Dan for chair emails. Financial additions are recipient scoped: VISU amounts to Alex; full AHMX/VISU totals to the Dean. A successful Concur submission remains pending validation until evidence changes it.

### Sources, Memories and Team

Unify source health and browsing while preserving TaskDock, Beacon and direct-provider setup, exact grants, archive mappings, freshness and reviewed relationships. Memories retain review/correction/deletion and provenance. Team opens to people and a report inbox, with invitations and shares attached to exact identities. Show invitation lifetime, link/QR, access preview and revocation; keep technical hosting details secondary. Worker claims and supervisor verification remain separate, with before/after review for applying details. Preserve the browser portal's keyboard/mobile access and recovery.

## Phase 3 — Juno-managed recurring tasks in TaskDock

### Ownership and user journey

Juno owns a versioned routine definition and occurrence ledger. TaskDock owns each resulting task, its assignment, due date, progress and completion history. Only the approved work-Mac host executes recurrence. A paired Air can inspect synchronized definitions/history; offline routine mutation and execution wait for the host in the first release. Existing offline memory/diary edits keep working.

In Issues → Recurring, offer New routine, active/paused/error filters, next run, latest occurrence and Open in TaskDock. A creation sheet contains a title, optional task description/checklist, recurrence, work timezone, start/end, creation time, due rule, optional reviewed person/room, missed-run policy and overlap policy. Do not require every task to have a room. Show the next five occurrences and exact target workspace/column before Enable routine. Templates such as printer checks are examples only; do not enable any automatically.

During setup, inspect TaskDock capabilities, select the intended workspace and create or explicitly select its **Juno** column. Bind to stable workspace and column IDs. Duplicate names require a choice. Never rename or repurpose an existing column based on its name alone. Show the chosen target and scope in Settings. If the column is removed or its permissions change, pause creation with a repair action; do not silently create a substitute. An approved rename preserves the stable-ID relationship and is shown to the user.

### Recurrence semantics

- Support daily, selected weekdays, every N weeks, monthly by day or ordinal weekday, and an explicit end date/count. Add complete-after-previous recurrence only as a separate clearly named mode with tested semantics. Annual rules may be deferred and visibly unavailable.
- Separate occurrence date, creation/lead time, due date and proposed work window. Creating a task does not reserve a room or employee. A due date is not a claim that the task can be completed then.
- Show weekend/holiday handling, month-end behavior and DST policy in the preview. Do not invent an institutional holiday calendar. For monthly dates that do not exist, require an explicit skip or last-day policy. Test ambiguous/nonexistent local times and ensure one occurrence per rule-defined local period.
- Require a reviewed missed-run policy: create missed occurrences, create only the latest missed occurrence, or skip missed occurrences. Default the setup preview to latest missed and one outstanding task, with the resulting dates visible before approval. Record every skipped/coalesced occurrence and its reason.
- Require an overlap policy: allow distinct occurrences or wait while the previous one remains open. Never claim duplicate suppression if it silently drops a required inspection. Show overdue prior work and the deferred next occurrence.
- Rule edits affect future occurrences unless the user separately approves a task change. Keep rule revision, effective date and prior history. Pause stops new creation; resume previews missed work. Ending/deleting a routine leaves created tasks and audit history intact. Retiring a routine is recoverable; permanent purge is separate.

### Safe TaskDock writes and synchronization

Use a separate least-privilege write grant for native tasks in the approved Juno column. Keep the existing read-only credential unchanged. Obtain TaskDock's enforced contract before enabling the button. See the companion handoff for required behavior; suggested capabilities are requirements, not existing endpoint names.

Persist a stable routine ID, rule revision and occurrence identity before attempting delivery. Use durable idempotency scoped to owner, TaskDock instance, workspace and occurrence. A lost response is reconciled through TaskDock's operation/occurrence lookup before retry. Restarts, multiple scheduler ticks and two host processes cannot create two cards. Use transactional claims/leases plus TaskDock-enforced uniqueness; a local in-memory flag is insufficient. Retain occurrence mappings and cancellation tombstones through backup/restore.

Track pending, in flight, created, completed, deferred, skipped, conflict and failed states with safe retry times and a visible explanation. Unknown remote outcome remains unknown until reconciled. Network failure never counts as completion. Revocation stops further writes immediately.

Read back actual TaskDock status/history. Respect human edits; expected-revision checks are mandatory for approved updates. Never reset completion, delete a task, rewrite a title/due date/assignment, or move a manually moved task back merely to match a template. A human-deleted occurrence is not recreated automatically. Require review to replace it. Links retain their exact IDs after renames and task moves.

Initial management includes creation, pause/resume, future schedule editing, reconciliation, history and explicit changes to Juno-owned task fields where TaskDock permits them. Completion is normally recorded by workers/supervisor in TaskDock; Juno may mark complete only through a separately reviewed task action if supported. Recurring tasks use the same planning, worker and reporting paths as other tasks. Routine completion is not physical repair verification. Reporting deduplicates native TaskDock records and archive copies by stable references and never counts future occurrences as accomplished work.

## Phase 4 — Purchasing and Concur Helper

Inspect the helper's actual output and write a versioned read contract for charges, expense reports, orders and helper runs. Prefer an explicit dated export import first; watch-folder behavior requires secure file validation, atomic publication, size limits and clear opt-in. A local authenticated API is an alternative. Keep Gmail, vendor and Concur credentials in the helper. Juno must distinguish not searched, no match and sign-in required.

Build Purchasing with Needs you, charges, reports, orders and run history using real imported fields only. Show source/observation date, currency, amounts and credits with decimal arithmetic. Review exact purchase-to-task/asset links; similar vendor/title matches are suggestions. A delivery estimate cannot verify receipt. Purchasing can inform prerequisites, check-in hints, approved memories and audience-scoped reports. A submitted report pending validation is not approved or paid. Keep detailed financial information out of worker views and unrelated chair drafts. No Juno control submits, approves or pays in Concur.

## Phase 5 — privacy, accessibility and laptop behavior

Meeting mode must hide private conversation titles and content, private memory/diary excerpts, Today recall, search results and notification previews while enabled. Introduce compatible privacy metadata and context filtering; do not assume old records are public. Use separate meeting conversation context. Switching back restores private navigation without mixing messages. Test UI, backend generation, saved-source inspection and search. Screen-sharing/calendar suggestions are optional future prompts; keep automatic switching off and never claim detection without a working implementation.

Use native resizable split views, collapsible inspectors and readable text. Test the actual M5 Air at its normal display scaling; do not copy the mockup's fixed canvas dimensions. Preserve labeled navigation, with an optional accessible compact sidebar. Check full keyboard navigation, search, Command-S, Command-Return, Escape, focus restoration and VoiceOver announcements. Avoid shortcut conflicts with native menus. Keep Reduce Motion, Increase Contrast and larger text usable. Validate light/dark contrast and do not rely on color alone.

Offline UI states the copy time and queued edits by type. Actions requiring the work Mac explain why, without appearing to succeed locally. On reconnect, show acknowledged counts; conflicts preserve both versions and offer reviewed resolution. No laptop scheduler creates TaskDock occurrences. Retest pairing, certificate pinning, revoked devices, scope isolation and a physical offline memory/diary round trip.

## Increment and release plan

1. **Preview.45:** baseline/mission, exclusive staffing choice, honest report availability and focused regression coverage. Record remaining phase-1 work explicitly.
2. **Subsequent previews:** finish phase 1, then navigation and daily workflows in reviewable increments. Advance release version, build and package version together at each delivered preview; never reuse a published version for a different payload. Do not bump once per file edit or invent predetermined final preview numbers.
3. **Recurrence increment:** implement local definition/ledger and fixture scheduler, then scoped TaskDock write acceptance, then one explicitly approved live routine. Show a clear unavailable state until the external contract passes. Continue independent UI work while waiting.
4. **Purchasing/privacy increments:** use verified contracts and migrations, then final cross-surface and laptop acceptance. Keep dependency-blocked capabilities visible in the ledger.

Before each install, make and verify a restorable private backup, capture workspace fingerprints and pairing/HTTPS identity, and avoid competing source/app database processes. Run the relevant native/backend checks and relocated installer validation. After install, verify /Applications/Juno.app version/signature, saved records, existing report text, source configuration and sync identity/listener. A failed preservation check blocks delivery and triggers recovery review. No installers, private exports or screenshots containing live work data are committed.

## Acceptance matrix

| Area | Required observable evidence |
| --- | --- |
| Navigation | Every old destination remains reachable through the new structure; selection survives; commands work at desktop and Air sizes. |
| Save | Change two fields, save once with Command-S, restart and read them back; cancelling preserves original values; stale revision cannot overwrite another edit. |
| Staffing | Both edit modes cannot save conflicting choices; supervised availability includes Dan; legacy ambiguous records remain safe. |
| Today/readiness | A viewer can identify a useful next action and its reason within ten seconds; blocked/unknown work is not called ready. Record Dan's feedback and distinguish preference from measured performance. |
| Check-in | Five-step recovery, hint insertion, confirmation, carry-forward, notification open and offline sync pass without unconfirmed text entering reports. |
| Reports | Tuesday without current drafts shows the schedule consistently; saved earlier drafts remain available; generated/edited/reviewed states agree; old edits survive refresh and a new version. |
| Audience | Fresh fixture and authorized live-source drafts route Alex, Amy, Kathryn correctly; Holy Cross 203/326 and full AHMX figures appear only in Dean notes; archive claims require actual included records. |
| Recurrence | Preview dates, weekday/month-end/DST/end rules, missed-run/overlap policies and pause/resume produce the reviewed occurrences. Use a controllable clock. |
| Exactly-once task creation | Duplicate ticks, concurrent hosts, timeout after remote commit, restart, laptop reconnect and backup restoration produce one TaskDock task per occurrence with a recoverable receipt. |
| Human authority | Manual TaskDock edit/move/delete/completion is respected; no automatic reopening or recreation; stale revisions and revoked/wrong-scope grants fail closed. |
| Isolation | Wrong owner, TaskDock instance, workspace, column or occurrence ID cannot read/update another user's data; read-only grant cannot write; upstream tasks remain protected. |
| Purchasing | Import validation, precision/credits, exact linking, unavailable sources and private routing pass; no submit/approve/pay control exists. |
| Privacy/accessibility | Meeting-mode screen-share fixture contains no private titles/quotes/search hits; full keyboard and physical VoiceOver, contrast, larger text and narrow layouts pass. |
| Preservation | Before/after work-record and paired-device checks pass; older client compatibility is tested or a clear minimum version blocks unsupported mutations. |

## Deliverables and completion gate

Maintain a control/workflow ledger with pass, fail, blocked and not-run states, commands, build IDs and evidence paths. Deliver source, migrations, focused tests, TaskDock and Concur contracts, synthetic before/after captures, current Help and build status, an install preservation report, and a final remaining-dependencies list. Record physical Mac/Air tests separately from automated fixtures. Do not equate a simulated Friday or recurrence run with an observed live scheduler run.

Mission completion requires all shipping features passing acceptance, a verified native installation with preserved data, and the approved live recurring-task pilot reconciled in TaskDock's Juno column. External dependencies remain blocked with a named owner and contract; placeholders do not count as implemented features. Push only when Dan asks.

## Preview.45 implementation ledger

November 18, 2026. Source increment only; not installed and not visually accepted yet.

| Item | State and evidence |
| --- | --- |
| Mission and external contract | Written in this document and the linked TaskDock handoff. |
| Version | Release/build/package values advanced together to 0.1.0-preview.45 / 45 / 0.1.0.45. |
| Exclusive support choice | Implemented in guided and full editors using existing wire fields. Legacy contradictory flags remain intact until explicitly corrected; Apply rejects the conflict. Empty worker names cannot accompany worker-only choices. |
| Chair availability | Shared Central-time helper used by scheduler, overview and empty reader. Automatic-off state is explicit. A stale success notice is no longer presented as proof a current-week draft exists; errors are scoped to the attempted week. |
| Functional checks | `python3 scripts/verify_workspace_states.py` passed staffing transitions, legacy conflict round-trip, schema compatibility, Friday midnight/manual and 9 AM/automatic boundaries, summer/winter offsets and week rollover. `python3 scripts/verify_planning_inputs.py` passed existing input validation. |
| Native compile | All nine application Swift sources passed `xcrun swiftc -typecheck -parse-as-library -swift-version 5 -target arm64-apple-macosx13.5`. Private compiler log: `.local/preview45/typecheck.log`. |
| Visual and release acceptance | Not run for preview.45. Full installer, native pointer/keyboard walkthrough and installation preservation remain required before delivery. |
| Remaining phase 1 | One-save flow, persistent field labels, full document formatting/copy, source health, invalidated-chat grouping, date behavior and Meeting-mode presentation remain open. |
| Recurring tasks | Design/contract written; definition store, scheduler, UI and TaskDock write pilot remain open. No live task or column created. |
| Remaining phases | Navigation/workspaces, Purchasing, expanded privacy and complete Air/accessibility acceptance remain open. |


## 0.2 implementation ledger — November 18

The user requested the 0.2.X release line. 0.2.0/build46 introduced the first workspaces, 0.2.1/build47 report review/history, 0.2.2/build48 scheduling handoff, and 0.2.3/build49 the visual alignment/action correction. Earlier preview.45 entries above are historical, not current release status.

| Area | Current evidence / remaining work |
| --- | --- |
| One-save planning | Native lab saved a 45-minute edit directly; cancelling a later 60-minute edit preserved 45. Command-S and unchanged/dirty state are implemented. Backend revision/isolation tests pass. |
| Meeting privacy | Separate conversation context and thread lists; private memory/diary/purchasing/team/evidence views hidden. Backend tests exclude private excerpts. Old records default private. Per-record public metadata and full search coverage remain open. |
| Recurring | Owner-scoped idempotent draft create/edit, strict calendar rules and five-date preview; DST/month-end tests pass. No active runtime or TaskDock writes. Exactly-once delivery/pause/resume/live pilot are blocked on scoped TaskDock support. |
| Purchasing | Reviewed expense import and signed credit visually tested; preview/CAS/isolation/validation tests pass. [Additional helper contract](concur-helper-juno-read-contract.md) documents missing order/report/run fields and future reviewed links. |
| Reports | Immutable versions preserve exact text; current-body review fingerprint invalidates after edits. Native greeting update, review and historical original tested. Markdown/large presentation and actual rich-text paste tested. Item selection/redrafting remains open. |
| Schedule | Exact task/workspace handoff, duration/supervision-aware availability and revalidated Juno-only hold tested in lab. 0.2.3 fixes visual axis alignment and adds the first hold action above the timeline; visual retest pending. |
| Automated checks | 328 backend tests passed (`.local/mission16-backend-tests.log`); `verify_workspace_states.py`, `verify_planning_inputs.py`, `verify_offline_client.py` and `verify_update_projection.py` passed. Full native builds through 0.2.2 passed. |
| Physical / install | Current changes have not been installed in production. Physical Air, VoiceOver, notification, backup/restore and post-install preservation must be checked separately. |

The native sidebar and toolbar guidance informed grouped navigation, an explicit hide/show control, short labels and contextual source details: [Apple sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars), [Apple toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars). This is design guidance, not certification. Screenshots are design references; fictional example data is never imported as work evidence.


### 0.2.4–0.2.5 follow-through

0.2.4/build50 passed native compile and pointer/keyboard tests for check-in save/advance, saved-answer review, Escape dismissal, Command-K, exact task search and private-destination filtering in Meeting mode. Check-in reminders can be explicitly inserted into the draft answer; they do not enter a confirmed diary automatically. 0.2.5/build51 adds an optional/required-by-supervision owner timeline and preserves horizontal alignment at narrow widths. Its visual acceptance is pending.

The final disposable backend suite again passed all 328 tests in 46.450 seconds (`.local/mission16-final-backend-tests.log`). Native weekly projection, daily-brief decoding/12-hour time, staffing/Friday/DST/timeline boundaries, planning-input validation and main-actor responsiveness checks passed. The schedule projection harness was updated to extract the actual projection type after the new timeline type was inserted; no assertions were weakened. An initial daily-brief invocation used system Python without dependencies, then passed under the project virtual environment.


### 0.2.6 model evidence correction

The first live LM Studio synthetic test returned a fluent chair email containing an unsupported department-wide “no other new failures” statement and a generic statement about existing tickets. This is a **failed factual review**, despite valid structure and successful transport. The original log's final transport/structure PASS is not semantic acceptance. No real draft was overwritten or sent.

0.2.6/build52 strengthens the writing instruction and rejects common broad absence/all-ticket claims, retaining the deterministic factual draft through the existing fallback path. This guard is conservative and does not prove every generated sentence is supported; human review remains required. Regression covers the observed wording, variants and a valid narrowly scoped update. All 24 focused chair tests passed. Original and retest logs are private under `.local/mission16-lm-studio*.log`.

Updated native Help describes the single-save flow, Command-K, explicit check-in reminders and the draft-only routine / read-only purchasing boundaries. The source guide is [Juno 0.2 workspaces](../JUNO-0.2-WORKSPACES.md). The package is being built privately; GitHub has not been updated.


### 0.2.7 supervisor-window correction

The four-lane visual test passed alignment but exposed that the optional owner lane initially affected display only. 0.2.7/build53 carries that choice into the availability request and its refresh identity, so checking Include my availability actually intersects the owner’s recorded hours/calendar/holds. Required task supervision continues to include the owner automatically. The fixed owner lane now has a clear “You” heading rather than a disabled selector. A conflicting-owner-hours fixture is required before acceptance.

Live model retest returned an incomplete email and correctly selected the safe fallback (`.local/mission16-lm-studio-scope-retest.log`). This is a usable fallback result, not a claim that live model prose passed semantic review. Existing real drafts were left untouched.

Pre-update encrypted backup succeeded and restore validation passed on November 18 at 10:17 AM Central, schema 0017, before any production migration. Private log: `.local/mission16-preinstall-backup.log`. The protected backup is stored under the existing approved `<approved Juno backup destination>` destination.


### Verified 0.2.7 interaction result

The native conflicting-hours fixture has the worker on shift 9 AM–5 PM and owner hours replaced with 2–5 PM for November 18. With Include my availability off, the opening is 10:45 AM–5 PM. Turning it on refreshes the result to 2–5 PM and renders the owner lane on the same time axis. This verifies the actual UI request/result, not merely a label change. Fixtures remain isolated in `.local/native-lab-mission16v027`.

The final offline native-client check passed: memory saved badges, create/restart/remap/correction/deletion, diary edit chains, conflicts, local search, stale-reply removal and private file permissions. Log: `.local/mission16-offline-final.log`. This is automated offline-client verification; it does not substitute for a physical M5 Air round trip on 0.2.


### 0.2.7 package verification

All 15 relocated installer groups passed. The expanded bundled-runtime suite passed 257 tests in 36.046 seconds, including the new recurring, purchasing, chair history/review/scope and separate chat-mode tests. The existing smoke/security groups passed startup, authentication, stale edits, provider readers, TLS pairing, invitation reuse protection, offline idempotency, device revocation, local-admin isolation, restart persistence, shutdown, old-schema backup and fail-closed missing identity. Evidence: `.local/mission16-release/verification-0.2.7-expanded.json`, `.local/mission16-installer-expanded.log`.

The user will send the scoped recurring-task handoff to TaskDock. Live delivery remains blocked on that owning application's implementation. A paused production baseline and private previous app were captured before Installer ran. No repository push has occurred.


The first production installation attempt was correctly rejected by the preinstall guard because isolated test apps still used the executable name Juno. `/var/log/install.log` reported “Quit Juno before installing this update”; preview.44 remained installed and no migration ran. The test apps were closed and absence of Juno processes was checked before retry. This was an agent cleanup mistake, not a failed database migration or a certificate issue.


### Installed 0.2.7 / build 53

The retry installed successfully; Juno opened and displayed 0.2.7 and Connected · This Mac. Strict/deep bundle verification passed. Production upgraded from schema 0017 to 0018. Every pre-upgrade work-record fingerprint matched the paused baseline; previous device IDs remain. Host certificate/key/settings and worker settings fingerprints matched exactly. The existing <work-mac-ip>:8443 sync listener accepted a TCP connection. The migration preserved three existing report revisions in history. No live task/draft edits were made for testing.

The final source suite passed **329 tests** in 42.747 seconds. Native offline-client and additive-schema preservation checks passed. Private verification: `.local/mission16-installed-verification.log`, `.local/mission16-paused-before027.json`, `.local/mission16-backend-0.2.7.log`. Installer and checksum are also available privately in `~/Downloads/Juno-0.2.7` for the Air. No GitHub push.

Remaining independent objectives include item-level report evidence selection/redraft, reviewed purchasing links/report inclusion, complete adaptive/VoiceOver control acceptance, and source/context details. Physical M5 Air acceptance and the TaskDock live recurring pilot remain required. The mission is **not complete** and these items are not silently waived by this installed increment.


### 0.2.8 report-evidence review

Implemented an owner/recipient-scoped evidence checklist, exact source-record IDs, a fingerprint of current routed facts and coverage, and a preview that leaves saved writing untouched. Reviewed save creates a new revision and records included/left-out facts in review notes. Evidence drift, another recipient’s IDs and stale draft revisions fail closed. Modified dates remain last updates. Existing style/routing and source-attribution tests continue to pass. Structured room values shared as provided now route generic task titles; unknown/suggested room text does not become evidence. Holy Cross 203/326 still route only to the Dean.

The native lab selected one of three VISU facts, previewed only that fact, placed the wording into the editor for review, and saved it explicitly. Review notes correctly recorded one included and two left-out records. No real email was altered. The source suite initially passed 330 tests before the additional structured-room test; the focused 26-test chair suite passed after that addition. A final full suite is required for the combined next increment.

### Physical Air / accessibility scope update

Dan confirmed **0.2.7 installed on the M5 Air and automatically synchronized**. This is physical automatic-sync evidence, separate from simulated client tests. Dan then explicitly waived VoiceOver testing because he does not use it currently. VoiceOver is removed from this mission’s remaining release gate; existing accessibility labels and keyboard behavior remain supported and should not regress. Do not describe unperformed VoiceOver checks as passed.

### 0.2.9 reviewed purchase links — in progress

Adds exact reviewed expense-to-TaskDock references without changing TaskDock or Concur. Links bind the expense’s ID, merchant, date, currency and signed amount, the TaskDock workspace and exact task ID. A changed/reused expense ID or unavailable task copy makes the old link unconfirmed and hides its old task title. Corrections/removal retain link history. Financial details are not automatically sent to chair emails. Actual order/report/run statuses and asset linking still depend on the helper’s extended contract.


0.2.9 native link walkthrough passed with a fictional USD -18.14 credit: exact task and workspace review, explicit save and the linked title displayed on return. Backend tests passed changed-amount invalidation, wrong owner/workspace, safe replay, stale snapshot rejection and retained unlink history. The source suite will be rerun after the combined 0.2.10 UI increment.

### 0.2.10 Sources navigation — in progress

Replaces the separate TaskDock/Sources sidebar entries with a Sources hub: dated status, TaskDock and saved records. Old Open TaskDock actions redirect to the TaskDock tab; Cmd-F still targets its search. Connection setup remains in Settings. Status reload reads saved copies rather than implying an upstream provider refresh. The header exposes a labeled Search action, and chair readers name the actual recipient. Native build/interaction acceptance is pending.


### 0.2.11–0.2.12 final layout pass

The 0.2.10 native test passed Sources status, TaskDock tab, old issue-to-TaskDock redirect and Cmd-F focus. Resizing to approximately 888×632 points exposed repeated source headings reducing the list to one visible row. 0.2.11 removes the repeated embedded heading and groups sharing, freshness details and definitions while retaining active stale/error warnings. Purchase-link buttons get explicit control styling/grouping. Version-specific messages explain unsupported actions on an older host. 0.2.12 bounds large modal heights to the active display’s visible area while keeping scrollable forms/documents and footer actions.

All eight focused native checks passed: staffing/Friday/DST/timeline boundaries, planning inputs, weekly schedule projections, similar-name worker task search, room/device aliases, main-actor credential responsiveness, Concur request URL week/month/leap boundaries, and modal-height clearance. No live Concur job was started. Current Concur Helper source now provides an explicit expenses-only Export for Juno action; it remains compatible with the reviewed import. Extended order/report/run metadata is still absent. Concurrent helper wiring in the working tree was preserved.


### 0.2.13 durable routine history and delivery primitives

Migration 0019 retains the current routine definitions as immutable versions and introduces an occurrence ledger with stable operation IDs, original payload hashes, scoped target identities, transactional leases and a durable planning cursor. History and draft retirement/restoration are available in the native interface. Downgrade refuses to erase retained history, occurrences or target state. Production activation and scheduling remain disabled.

Disposable PostgreSQL/fake-remote checks cover concurrent planners and claims, lost replies after remote commit, restart and replay of a pre-delivery local state, original missed-run policy after rule edits, monthly identity, DST folds, scope/receipt validation, deletion and human moves/renames. These are simulated delivery results, not live TaskDock acceptance. No real task was created. The installed TaskDock API still advertises `write_tasks: false` on the November 18 recheck.

### 0.2.14 unsaved editor recovery — acceptance in progress

Routine and chair-email editors now retain owner-scoped local drafts and register unsaved changes with the application quit guard. A recovered new routine retains its original request UUID so retry cannot change identity after an unknown response. Recovery requires another date preview. A recovered email retains its original base revision and selected-evidence token; a newer saved revision requires an explicit comparison and reviewed choice before Save becomes available. Saved report revisions and TaskDock facts remain unchanged until explicit save. Explicit discard clears local recovery.

Native recovery serialization checks passed restart/round-trip, exact request UUID and base revision, selected evidence, owner and recipient isolation, malformed data and explicit discard. Combined backend, native UI, package and install acceptance are still pending. VoiceOver remains waived at Dan's request; this is not a passed test. No GitHub push.


### 0.2.15 compact controls and native recovery acceptance

The 0.2.14 visual test exposed truncated chair-editor actions at the minimum sheet width and a purchase-link button swallowed by native List row semantics. 0.2.15/build61 separates report tools from Save/Cancel/Close, adds Command-S, and makes expense selection plus an external Review task link action explicit. Purchasing actions use a separate row below the heading so they fit the compact window.

Native 0.2.15 lab acceptance passed: a seeded recovered new routine reopened with Save disabled until re-preview, then Command-S saved the original request UUID; a seeded older chair edit reopened with Save disabled, showed the newer canonical text for comparison, required explicit Keep recovered wording, then Command-S saved revision 3. History displayed both recovered wording and preserved revision 2. These are controlled recovery fixtures, not an actual forced crash. Purchase selection exposed a standalone button and it opened the exact link-review sheet. At approximately 888×632 points the purchasing controls remained visible. The 0.2.14 compact Sources/TaskDock view showed all four task rows with the repeated headings removed. No live work record was edited by these tests.

All 362 backend tests passed in 48.622 seconds after 0.2.14 backend changes. Nine native checks passed, including editor recovery, modal sizing, staffing/Friday/DST/timeline, planning input validation, weekly scheduling, similar worker-task search, room aliases, responsiveness and helper request boundaries. The offline-client and additive preservation tests passed. Private logs: `.local/mission16-backend-0.2.14.log`, `.local/mission16-offline-0215.log`, `.local/mission16-projection-0215.log`. The later 0.2.15 changes are native layout/shortcut only plus version metadata.

A new encrypted backup completed November 18 at 11:34 AM Central, schema0018, and passed restore validation. After quitting the work app, a fresh record/device baseline and TLS/hosting fingerprints were captured. The previous 0.2.7 app is retained privately. Final package/install verification is still in progress. No push.


### Installed 0.2.15 / build61

All 15 relocated package groups passed, including 282 bundled tests in 34.575 seconds. Installer completed successfully. `/Applications/Juno.app` opened connected and displayed 0.2.15; strict/deep signature verification passed. The paused before/after comparison matched every old work-record fingerprint and retained all device IDs after migration to0019. Host certificate, private key, host settings and worker HTTPS configuration hashes matched; TCP access to<work-mac-ip>:8443 succeeded. Private evidence: `.local/mission16-release/verification-0.2.15.json`, `.local/mission16-installed0215-preservation.log`, `.local/mission16-host-identity-before0215.json`. The package/checksum is privately available under `~/Downloads/Juno-0.2.15`. No upload.

### 0.2.16 Today and confirmed recall — in progress

Moves the next question, ready suggestions and a six-item issue preview into the main column, with diary recall, remembered completions, local holds and report/source links in a secondary column. The layout stacks at narrow widths. A new owner-scoped latest-confirmed-diary read excludes unconfirmed and future records and is included in dated offline exports. It shows canonical diary text rather than resurrecting a superseded interview answer. Read diary opens a document; Pick up here prepares an unsent chat draft. Meeting mode hides this private recall. Backend/native/package acceptance is pending.


### 0.2.16 results / 0.2.17 layout refinement

All 363 backend tests passed in46.556 seconds. The isolated native reader displayed the corrected November17 diary while November18 remained unconfirmed, and Meeting mode removed both Where you stopped and today's private recall. No superseded interview text appeared. The first wide visual test showed ViewThatFits selecting the stacked layout despite sufficient usable space; 0.2.16 is not accepted for the intended wide two-column presentation. It was not installed over the work app.

0.2.17/build63 uses the available content width to choose side-by-side or stacked content and changes the report link's copy to avoid implying automatic preparation is enabled or a draft exists. It retains all backend semantics from0.2.16. Native/package acceptance is pending.


0.2.17 native visual acceptance passed: approximately1080×752-point window showed decisions/issues on the left and confirmed recall/holds/report links on the right; approximately888×632 stacked the same content without horizontal clipping. Pick up here opened an unsent private-chat draft containing canonical diary text. It sent no model request and changed no planning/task facts. The latest native offline client checks passed again. Final installer verification is pending.


## Remaining acceptance after the 0.2.17 candidate

This is an explicit incomplete-work list, not a declaration that every recommendation has shipped.

| Objective | Current result / next dependency |
| --- | --- |
| Data, drafts, HTTPS and Air identity |0.2.15 installation verified; repeat paused preservation check for0.2.17.|
| Today and corrected diary recall |Wide/narrow visual and unsent resume walkthrough passed; package283 tests/15groups passed; production install under way.|
| Routine delivery |Draft definitions, immutable history and simulated durable ledger pass. TaskDock still advertises write_tasks:false. No live scheduler/column/pilot accepted.|
| Routine setup/lifecycle |Draft retirement/restore works. Activation, pause/resume with remote readback, grant repair and approved live task actions depend on the TaskDock contract; end-count UI is still open.|
| Purchasing |Reviewed expenses and exact task references work. Orders, expense-report status, helper-run coverage and corresponding report/check-in integration await real helper metadata; asset relationship review remains open.|
| Reports |Readable documents, selected evidence, immutable versions, review badges and recovery pass. A unified week-grouped document list with collapsible evidence inspector remains UI work.|
| Issues / Today refinements |The inspector and guided editor work. Direct inline question-and-answer persistence and a complete personal-calendar agenda on Today remain open; local holds are not presented as the full calendar.|
| Physical Air |Dan confirmed0.2.7 automatic sync.0.2.17 visual behavior and reconnect on the physical Air have not been observed. Existing pairing is preserved on the host; do not claim a new physical round trip.|
| Accessibility |VoiceOver explicitly waived. Keep keyboard/focus and native semantics; final larger-text/contrast sweep remains open.|

No email was sent, no real recurring task was created, and no GitHub push occurred. TaskDock/Concur implementation belongs in their own projects; the handoffs remain the integration contract.


### Installed 0.2.17 / build63

All15 relocated package groups passed, including283 bundled tests in37.723seconds. The new encrypted pre-install backup passed restore testing at11:48AM Central, schema0019. Installer completed successfully, and Juno reopened connected with0.2.17 in the header. The fresh paused baseline matched all work records and retained device IDs; strict/deep code-signature verification passed; host/TLS/worker fingerprints were identical and the original<work-mac-ip>:8443 listener was reachable. Private logs and fingerprints are `.local/mission16-installed0217-preservation.log`, `.local/mission16-host-identity-before0217.json`, `.local/mission16-release/verification-0.2.17.json`. No push.

### 0.2.18 saved-document library — in progress

Adds a metadata-only, owner-scoped report index paginated by20 distinct weeks, retained in offline exports. Reports opens to a searchable week-grouped document list and a reader with actual recipient/subject, canonical saved text, explicit review, copy and history. Editing opens the existing version-checked editor at that exact week/recipient. The list and reader refresh after saving or marking reviewed. Preparation controls and their schedules remain under a separate named tab. Original reports are read, not regenerated. Legacy combined drafts remain discoverable. Backend and native acceptance pending.


### 0.2.18 report-library results / 0.2.19 refinement

All364 backend tests passed in47.274seconds, including21-week pagination, owner isolation, metadata-only index output, offline index pages and retained legacy combined drafts. The native browser displayed both fixture weeks, opened last week's VISU editor with November9 and Alex selected, saved revision2 only there, refreshed the reader/list, and updated its explicit Reviewed badge. At approximately888×632points the document and controls remained usable.

The search test found a mismatch: narrowing the list to Amy left Alex's reader visible.0.2.18 is not accepted for search-selection consistency and was not installed.0.2.19/build65 synchronizes filtered selection, adds a no-match state and Command-F focus, and keeps the document list/selection alive when switching to preparation controls. Native offline-client checks passed again, including actual JunoStore offline reads and writes without host contact. Final refinement/package/install acceptance is pending.


The final0.2.19 refinement also refreshes the already-loaded week range, deduplicates metadata IDs, preserves older selection across refresh, and refuses to display a reader outside the active filter. Empty-search refresh stays empty rather than switching to an unrelated newest report. Opening the editor or marking reviewed remains disabled during a metadata reload. This is part of the same unreleased0.2.19 increment; earlier private candidate packages are not installation artifacts for the user. Final native acceptance uses the installer build's compiled executable in a disposable development lab.

## Required reassessment before Mission 17 — daily work support

Added at Dan's request on November 18, 2026. This is a product-design and user-review checkpoint before defining Mission 17. It extends the direction of Mission 16; it does not silently add every proposed capability to the current release or mark unbuilt controls complete. Preserve the existing 15-minute guided check-in. A shorter five-minute closing review is a configurable option to assess with Dan.

### Intended experience

Give Dan one clear next action, keep time visible, and make it easy to resume after classroom problems, faculty/staff questions, and other interruptions. Reuse the existing task, calendar, capacity, diary, source-freshness and offline-sync foundations. Keep task ownership in TaskDock and preserve explicit review for factual changes and reports.

| Moment | Proposed support to review |
| --- | --- |
| Morning, about five minutes | Show known fixed commitments and deadlines; choose one essential outcome and up to two additional priorities. Preserve an interruption reserve informed by recorded workload, with unknown coverage explicit. |
| Starting work | Offer a small action with a concrete finish point, linked to the exact task. Distinguish a suggested first step from a confirmed instruction or changed assignment. |
| During work | Offer an optional adjustable focus timer, initially suggesting 15–25 minutes only as a user-adjustable starting range. Provide quick capture for unrelated ideas without losing current work. |
| Meetings and transitions | Separate preparation and leave-now cues. Let Dan set walking, travel and setup time; do not invent location or transit assumptions. |
| After an interruption | Restore a short bookmark: current task, what was being done, where work stopped and the next step. Keep its save/queue/sync state visible. |
| Feeling stuck | Offer three explicit choices: make the step smaller, identify the blocker, or deliberately switch tasks. Keep the user's decision visible. |
| Midday reset | Reassess remaining commitments and capacity. Show what must be deferred when urgent work uses the available time, and obtain a reviewed choice where priorities compete. |
| End of day, about five minutes | Capture progress and loose ends and prepare tomorrow's first action. Keep the existing full check-in available and retain its confirmation rules. |

### Four proposed primary controls

- **Start this:** open the relevant task and offer an optional timer; starting a timer does not complete, assign or reserve the task.
- **Capture this:** save a thought or request quickly and return to the current task. Clarify whether it remains a private inbox item or is reviewed into a TaskDock task.
- **I was interrupted:** save or restore the work bookmark, including any time remaining on an optional timer.
- **Help me restart:** propose a small first step from currently authorized task context and the saved bookmark; make the suggestion editable.

### Notifications, privacy and user control

Let Dan choose reminder frequency, quiet periods, focus duration and transition lead times. Keep notifications selective: genuine teaching disruptions and deadlines must be distinguishable from routine incoming work. An unanswered cue offers a simple reschedule or restart choice; avoid repeated alerts accumulating into another queue. Assess reminder behavior on both Macs so reconnects, sleep/wake and two running apps do not duplicate cues. Keep notification previews appropriate to Meeting mode and the existing privacy rules.

For a campus version, store these as **planning preferences**, such as “short starting steps,” “visible time,” and “transition reminders.” Do not infer or store an ADHD diagnosis, send one in model prompts, or treat work-pattern observations as a diagnosis or employee performance score. Use IET-approved data flows for university tasks. Keep real work data on the approved host and preserve offline edit/reconnect behavior.

Evaluate benefit through Dan's feedback about starting and resuming important tasks and meeting commitments. Any optional measurements need explicit scope, retention and a way to inspect/correct them; timer duration alone does not establish work quality or capability.

### Reassessment gate

Before creating or starting Mission 17:

1. Review Mission 16's actual shipped capabilities, external blockers and remaining UI work against this workflow.
2. Ask Dan where his day most often breaks down: **choosing what matters, getting started, noticing time, or returning after interruptions**. Do not choose that preference on his behalf.
3. Agree on the first useful controls, reminder limits and success criteria. Record the decision before expanding scope.
4. Write a concrete Mission 17 implementation and acceptance plan covering saved/queued/synchronized state, user override, selective notifications, quiet periods, task identity, privacy and recovery.

The supplied NHS workplace and Job Accommodation Network links are retained as design references from Dan's proposal, not as a clinical recommendation or a verified medical claim in this mission:

- [NHS Inform — managing ADHD symptoms in work and education](https://www.nhsinform.scot/illnesses-and-conditions/adhd/managing-adhd-symptoms-in-work-and-education)
- [Job Accommodation Network — managing time](https://askjan.org/limitations/Managing-Time.cfm)


### 0.2.19 acceptance / 0.2.20 menu correction

The final0.2.19 installer executable passed a21-week native fixture: an unloaded June29 search correctly showed no match, Load older weeks revealed that week, Refresh retained its selection, a Kathryn query opened Kathryn rather than a hidden Amy/Alex document, an empty query result stayed empty after Refresh, and preparation-tab switching retained the query. All15 relocated installer groups passed, including284 bundled tests in42.847seconds.

Native Command-F did not focus report search because the application menu still excluded Reports from its Find validator.0.2.19 was not installed over the verified work app.0.2.20/build66 makes the selected Reports tab a shared UI state and enables Find only for its searchable Saved documents view, with the existing primary-window/no-modal guard. Backend semantics remain unchanged. Final native/menu/package/install acceptance is pending. Dan's supplied daily-support workflow is recorded above as a required reassessment gate before Mission17.


The0.2.20 native Find check passed against the installer's executable: Command-F focused report search, typing Amy filtered the list and opened Amy's matching document. All15 relocated installer groups passed. The paused backup completed at12:14PM Central and passed restore validation; schema0019. Fresh record/device and TLS/hosting baselines and the prior0.2.17 app were retained. Installer is awaiting macOS administrator authentication; do not call0.2.20 installed until the success screen and post-update preservation checks are observed. No GitHub push.


### Installed 0.2.20 / build 66 — November 18

After Dan approved macOS authentication, Installer's log recorded Install Succeeded at12:17PM Central. `/Applications/Juno.app` reports0.2.20/build66, strict/deep bundle verification passed, and the native header displayed Connected · This Mac. The fresh paused before/after comparison matched every saved work-record fingerprint and retained all device IDs. Host certificate/private key/settings and worker HTTPS fingerprints matched exactly; the existing<work-mac-ip>:8443 listener accepted a connection. No real draft or task was edited for acceptance.

All364 backend tests passed after the report-library API changes. Final package checks passed all15 groups and284 bundled-runtime tests in47.495seconds. The final paused encrypted backup passed restore validation at12:14PM Central, schema0019. Private evidence: `.local/mission16-final-release/verification-0.2.20.json`, `.local/mission16-installed0220-preservation.log`, `.local/mission16-host-identity-before0220.json`, `.local/mission16-paused-0220-backup.log` and `.local/mission16-final-source-fingerprints-0220.json`. The exact verified package/checksum is available at `~/Downloads/Juno-0.2.20`. No GitHub push. Earlier private0.2.18/19 candidates were not installed; the accepted report browser ships in0.2.20.

### Current remaining work / reassessment boundary (updated November 18)

| Work | State and next concrete step |
| --- | --- |
| Native navigation, reviewed planning/blockers, inline answers, calendar agenda, report history, exact purchase/equipment references | Implemented and locally accepted through 0.2.24. 0.2.25 adds clearer rolling-versus-saved calendar coverage and work-Mac-managed status on the Air; package/native navigation and installed work-Mac acceptance pass. |
| Automatic calendar | Live reads observed at 1:53:18 and 2:08:27 PM Central. Both retain busy/free-only privacy and rolling November 11–February 17 exclusive coverage. The later read is a real second scheduled interval, replacing the earlier not-observed note below. |
| Contrast and reading | On the actual work Mac, Increase Contrast and Differentiate Without Color (which also enabled Reduce Transparency) were checked with Today, Issues, Reports and large Dean Present. Status labels remain explicit; presentation text wraps. All three original switches were restored to off. macOS preferred reading-size settings list supported apps but do not list Juno; no full-app preferred-font scaling pass is claimed. Existing larger document presentation is verified. |
| TaskDock recurring task delivery | **Blocked externally.** Installed TaskDock `api/unified_tasks/juno.py` still advertises `write_tasks:False`. Needs the existing scoped-write handoff implemented, a versioned contract/grant and then the approved live Juno-column pilot. Juno cannot safely manufacture that capability from the read token. |
| Purchasing orders, report status and helper-run coverage | **Blocked externally.** Rechecked Concur Helper source: expense/receipt plans exist; the versioned report/order/run export requested by the handoff is absent. Implement that export in its owning project, then finish the Juno read adapter and reviewed summaries. No financial action is authorized by the import. |
| Physical Air acceptance | **Passed for fresh-copy synchronization.** Dan confirmed 0.2.25 on the Air, last update 2:39 PM and zero queued edits after the desktop host restarted. Existing pairing was retained. This does not claim a new offline-edit/drain test or physical sleep/wake. Verified package/checksum/instructions remain in `~/Downloads/Juno-0.2.25`. VoiceOver is waived. |
| Before Mission 17 | Keep Mission 17 unstarted. Once Mission 16’s external/physical gates are settled, reassess the daily-support workflow below with Dan: one next action, small starting steps, optional timer, quick capture, interruption/resume bookmarks, transition reminders, quiet periods and midday reset. No diagnosis field or health prompt context. |

Mission 16 remains open. The work above distinguishes implemented behavior, actual live observations, platform limits, physical checks and external blockers; there is no whole-mission completion claim.


### 0.2.21 / build 67 — visible source success times and overdue blockers

Requested November 18 after the 12:21/12:22 screenshots. Add visible last-successful-copy dates on Today and Issues, not just a generic stale warning. Show full Central date/year and 12-hour time; retain the successful time when a refresh fails, distinguish an unavailable status from no saved copy, and keep Juno read/import time distinct from provider observation/update time. Reload status reads Juno’s saved metadata; it does not contact providers. The compact panel covers TaskDock, Beacon and the archive; Sources retains every available source.

Issues adds an Overdue filter (due today is not overdue), an aging cue, and a focused Add/Edit blocker sheet: blocker, waiting-on person/dependency, next unblocking action and optional native follow-up date. Explicit Save uses the existing owner/workspace/revision-checked planning API. It copies the current plan and changes only the selected task’s blocker fields; other staffing, room, duration, resume text, task facts, availability, reserve and priority remain. Saving is unavailable offline or while the parent plan has unsaved changes. Cancel confirms discard, and failed saves retain the entered text. Clearing a Juno blocker cannot erase a TaskDock-reported blocker. No TaskDock write is attempted.

Verification: native model tests pass for existing/new/cleared blockers, unrelated-field preservation and strict overdue dates. All365 backend tests pass, including failure-retained TaskDock/integration success instants (timezone offsets normalized as datetime instants). The isolated native lab saved/reopened a blocker and follow-up, changed the status/count on Issues and Today, discarded a subsequent edit without changing the saved value, selected Overdue, and displayed successful-copy/no-copy states. Final package/install and preservation acceptance pending. No push.


### Installed 0.2.21 / build 67 — acceptance and reassessment

Installer visibly completed successfully. `/Applications/Juno.app` reopened with0.2.21 and Connected · This Mac. Strict/deep bundle verification passed. The paused before/after projection matched all saved work records and retained every paired device identity; TLS certificate/private key/settings and worker HTTPS fingerprints matched exactly. The original<work-mac-ip>:8443 listener remains reachable. The paused encrypted backup passed restore validation, schema0019. No real task, report or blocker was edited for acceptance.

All365 backend tests passed in49.703seconds. All15 relocated package verification groups passed, including285 bundled tests in40.404seconds and239 Mach-O dependency checks. Native offline reads/writes, additive update preservation, staffing/date boundaries, planning inputs and draft recovery passed. The final installer executable was exercised in a disposable lab: earlier successful TaskDock/Beacon/archive timestamps remained visible with refresh-failed notices; a concurrent plan change rejected the stale blocker write and retained the typed draft; cancel/discard preserved the saved blocker; waiting-on and next action were visible; compact issue actions remained usable. Tests used only fictional records. Initial test assertions were corrected to compare timezone-aware datetime instants rather than offset-dependent timestamp strings; both represented the same successful instant.

Private evidence: `.local/mission16-final-release/verification-0.2.21.json`, `.local/mission16-backend-0221-corrected.log`, `.local/mission16-installed0221-preservation.log`, `.local/mission16-paused-0221-backup.log`, `.local/mission16-host-identity-before0221.json`, `.local/mission16-offline-0221.log`, `.local/mission16-source-fingerprints-0221.json`. Verified package/checksum: `~/Downloads/Juno-0.2.21`. The private prior0.2.20 app is retained for recovery. No push.

Observed production copy times after the update: TaskDock November16 at9:46AM Central; Beacon November13 at2:10PM; Smartsheet archive November13 at2:11PM. Reading status did not refresh providers or change the source snapshots.

#### Reassessment before Mission17

Mission16 remains open. The following are not represented as completed:

| Item | Current disposition |
| --- | --- |
| Live TaskDock recurring-task delivery, Juno-column reconciliation and approved pilot | Dependency blocked: installed TaskDock discovery source still advertises `write_tasks:False`. Existing handoff remains with TaskDock. Local definitions/history/fixture delivery are implemented; no production writer is inferred. |
| Purchasing orders, report status, helper-run coverage and report integration | Dependency blocked on the Concur Helper read contract. Expenses and reviewed task links work; absent metadata is not fabricated. |
| Reviewed purchase-to-equipment links | Open; requires exact equipment identities and explicit review, not a room/title guess. |
| Inline answers to every planning question | Open. The new blocker editor saves existing reviewed fields directly; it does not turn all chat answers into confirmed request facts. Additional fact persistence and older-client preservation need focused implementation/acceptance. |
| Personal calendar agenda on Today | Open. Today’s local holds remain clearly labeled as holds, not a complete calendar or confirmed free time. |
| Full contrast/larger-text acceptance | Open. This increment checked actual native compact/wide layouts and text/status labels; it does not claim all macOS display settings or physical Air acceptance. |
| Physical Air update | Dan’s0.2.7 auto-sync confirmation remains historical evidence.0.2.21 host pairing preservation and offline-client regression pass; a physical0.2.21 Air round trip is not observed. VoiceOver remains explicitly waived. |

Keep Mission17 unstarted. The daily-support reassessment above remains the proposed direction: one visible next action, short first steps, optional focus periods, quick capture, interruption bookmarks and selective transition/reminder controls. Confirm the most useful starting point with Dan before expanding that workflow. No diagnosis storage or new health-related model context was introduced.


### 0.2.22 / build 68 — remaining independent workflows

- **Calendar agenda:** Today reads every overlapping event from saved manual, Google and Outlook calendar copies, in Central time. All-day, overnight, exclusive day-end and DST boundaries have focused native tests. Cancellations are excluded; events not marked busy are labeled. Source coverage and last successful copy dates remain inspectable. No events is not a claim of free time. Calendar commitments and local planning holds are separate cards. Meeting mode replaces private titles with generic busy/free labels.
- **Reviewed inline answers:** Issues asks its next authorized shared request question inline. Save writes a reviewed answer and source/date; explicit none differs from unknown. The immutable TaskDock snapshot remains unchanged. Answers live in separate owner-scoped operational metadata, so an older client's full planning PUT cannot erase them. Writes compare active source snapshot, workspace, field basis and operational revision under the owner lock. Reads/overlays respect the current field grants and exact TaskDock origin/device/workspace/task identity. Changed source facts retain the reviewed answer with a conflict and require review. User-authored history remains stored; withheld answers are not displayed by the review API. Unsubmitted native text has separate owner/question-scoped local recovery and does not become a report fact automatically.
- **Purchase/equipment review:** An explicit chooser uses exact equipment IDs from a current Beacon feed with stable instance identity, not a guessed room/title match or a claim to the full inventory. Expense content, Beacon instance/snapshot, owner and operational revision are checked on save. Old-client task-link saves preserve equipment links and request answers. Changed expenses, stale/removed equipment and changed instances deactivate references; labels are withheld when no longer current. Reviewed link/unlink history is retained. This cannot submit expenses, establish receipt/compatibility or verify repair.
- **Work Google Calendar:** Dan selected his primary work Google Calendar. The installed direct connection has no OAuth Desktop app configuration; live enrollment is pending Dan's setup/sign-in. Added **Save busy/free times only** in the native calendar connection, default on; the backend strips event titles, descriptions, locations and other content before snapshot/cache/model use when selected. Existing API callers retain backward-compatible full-detail behavior unless they request minimization. Account/calendar/resource selection still requires explicit review. Setup instructions and verified Google documentation are in `docs/GOOGLE-CALENDAR-SETUP.md`. This does not silently create a project, grant permissions or schedule automatic provider refreshes.

All392 backend tests passed in65.746seconds, including actual calendar-busy filtering for Dan/supervision versus independent workers and busy-only exclusion from saved snapshots/cache. Focused native agenda, blocker, staffing, editor validation/recovery and offline checks pass. The disposable native lab verified inline navigation recovery, reviewed save followed by the next question, calendar/all-day/cancellation display, no private calendar title in Meeting mode, and exact equipment link save/display. Light appearance exposed two truncated helper paragraphs; wrapping is corrected for final packaged recheck. Final package/install/preservation acceptance is pending. No push.

External TaskDock write capability remains false. Expanded helper order/report/run metadata is still not provided by the current export. Those integration acceptance gates and the specifically approved live recurrence pilot remain blocked, not simulated as done. No Mission17 workflow has started.


### 0.2.22 installed acceptance — November 18

Installed build 68 on the work Mac. All 392 isolated backend tests, 15 relocated installer groups and 310 bundled-runtime tests passed. The final native executable passed light/dark/compact layouts, reviewed inline answer save/recovery/next-question, exact purchase/equipment linking and Meeting privacy. The encrypted paused backup passed restore validation. The before/after upgrade comparison preserved work rows and paired device IDs; host/worker identity fingerprints match and HTTPS sync is reachable. A verified installer and checksum are in `~/Downloads/Juno-0.2.22`. No GitHub push.

The approved Google Desktop client was created once in project juno-515119 and imported into Keychain. Google sign-in completed; only the primary work calendar was selected. At 1:28 PM Central an explicit read saved 149 busy/free-only records for October 19–December 18 (exclusive). Today displayed five busy commitments with generic labels and the dated coverage. No private event titles/descriptions/locations are saved in this mode. Existing reports were preserved. Provider reads remain explicit, and coverage needs renewal before December 18.

Mission 16 remains open for external TaskDock scoped writes and a live recurring-task pilot, expanded Concur Helper metadata, the remaining OS larger-text/contrast sweep and physical Air acceptance on the newer increment. VoiceOver is waived. Reassess the daily support workflow with Dan before Mission 17; Mission 17 has not started.


### 0.2.23 → 0.2.24 — automatic work-calendar refresh

User requested automatic refresh and a current coverage window. Added an opt-in 15-minute work-Mac scheduler using the existing read-only Google connection. It preserves the reviewed account, calendar IDs, client, timezone and busy/free-only choice, requests seven Central calendar days back and 90 days ahead, renews OAuth through Keychain and uses snapshot compare-and-swap. Cadence/retry state persists across restart. Failed reads retain the last good copy; rate limits defer retry and authorization/account changes pause for review. Nothing runs on a paired remote Air. Today and the room/person calculation reload after successful automatic reads. Scheduling now refuses personal/supervised reservations beyond the saved calendar’s exclusive date range.

393 backend tests passed, including explicit-end coverage and shared-cache day separation. The actual native scheduler method passed a fake-vault/transport harness for Central/DST boundaries, restart cadence, selected-resource/privacy preservation, expired-token renewal, disconnect fencing, failure/backoff, changed accounts and remote/offline/settings/overlap gates. Initial package passed 15 installer groups and 311 bundled tests. Synthetic final-executable settings layout was readable and the unreviewed Enable button stayed disabled.

0.2.23 installed with an encrypted restore-tested backup; work records, paired device identities, host/worker certificates and settings were unchanged and HTTPS sync was reachable. Live acceptance caught a real lifecycle defect: macOS retains the closed Settings view, leaving the view-based editing flag true. No automatic read occurred. Automatic refresh was turned off and the existing 149-record calendar copy retained. 0.2.24 replaces that flag with actual native window visibility and prevents manual refresh overlap. This is an acceptance finding, not a completed automatic-read claim; final evidence follows below.


### 0.2.24 accepted — November 18, 1:53 PM Central

The corrected package passed all 15 installer groups and 311 bundled-runtime tests. Actual JunoStore offline memory/diary behavior and native modal sizing checks passed; the production scheduler harness passed again. Installation succeeded. The encrypted paused backup passed restore validation; before enabling the intended calendar refresh, the work-record/device comparison matched. Host/worker certificate, key and settings fingerprints remain unchanged and the existing HTTPS sync listener is reachable. The verified package/checksum are in `~/Downloads/Juno-0.2.24`. No push.

After Keychain access cleared, the saved work account and primary calendar were reviewed with busy/free-only storage retained. Automatic refresh was enabled and Settings closed. The actual scheduler completed a live read at **1:53:18 PM Central** without using the manual refresh button. The resulting copy contains **193 records** for **2026-11-11 through 2027-02-17 exclusive**. Today automatically showed the successful time and the same five busy commitments for the day. Read-only database inspection confirmed the rolling seven-day-history/90-day-future bounds, no source error, generic event labels and absence of private titles/descriptions/locations/notes. The earlier December-limited coverage was replaced by the intended rolling source update.

Future 15-minute cadence/restart/backoff and DST rollover have production-method fixture coverage. A real physical sleep/wake and a physical Air round trip on this increment have not been observed. Automatic refresh requires the work Mac awake with Juno open and pauses while Settings is visible. Mission 16 remains open for TaskDock’s scoped write API/live recurring pilot (installed API rechecked: write_tasks false), expanded Concur Helper metadata and the remaining physical/accessibility acceptance scope. VoiceOver is waived; Mission 17 remains unstarted pending reassessment.


### 0.2.25 / build 71 — final local polish and dependency audit

Automatic Google Calendar settings now show a live Central rolling range instead of editable obsolete manual dates when the saved automatic selection is approved. The successful source copy separately shows its actual saved coverage. Enabling automatic refresh persists the status immediately, avoiding contradictory status after restart. On a paired Air, Today explains that calendar refresh is managed by the work Mac and asks the user to check the copy’s date/coverage; it no longer reports the Air’s local automatic setting as if it described the host.

The actual scheduler-policy harness passes. The final package passed all 15 relocated installer groups, including 311 bundled-runtime tests. Command-K opened with search focused; native final-executable checks reached Sources, Team, Memories, Daily check-in, Schedule and Chat without changing lab records. A larger batched navigation call was interrupted and reset the UI-control session; only states actually observed after recovery are counted. No new live source enrollment, model call or task/report edit was used for UI acceptance.

The 0.2.24 production display was checked with native Increase Contrast and Differentiate Without Color enabled, including the automatically enabled Reduce Transparency. Today, issue status labels and report presentation remained legible; the large-type Dean sheet wrapped its PCARD contents and closed with Escape. Original switches were restored and observed off. macOS preferred reading-size controls do not include Juno; this is recorded as a platform support limit, not an all-app larger-font test pass.

TaskDock and Concur Helper were re-inspected read-only. The scoped write API remains absent and the richer helper export remains absent; the owning-project handoffs are unchanged. No other project source was edited. The verified package/checksum and physical Air instructions are in `~/Downloads/Juno-0.2.25`. A paused encrypted backup passed restore validation at 2:23 PM Central and a fresh work/device baseline was captured; Installer is waiting for administrator authentication. Do not claim the work Mac updated until post-install verification.


### 0.2.25 installed — desktop sync restored

Installer logged success at **2:26:56 PM Central on November 18**. The bundle reports 0.2.25/build 71 and passes deep/strict signature verification. Dan reported 0.2.25 on the Air and identified the desktop being closed during installation as the sync obstruction. Juno was reopened on the desktop and visibly shows **Connected · This Mac**. The existing <work-mac-ip>:8443 listener is reachable; desktop Juno was left running, with Settings closed.

The initially strict preservation comparison flagged `integration_snapshots` because the enabled calendar monitor completed its expected refresh after restart. A reviewed comparison verified exactly one removed/added row hash in that table; the added hash matches the current Google Calendar row. Every other table/row projection, workspace owner and previously paired device identity matched. Host/worker key, certificate and configuration fingerprints are unchanged. No work records were lost or repaired/reset. Private acceptance: `.local/mission16-0225-preservation-reviewed.json`; the initial strict comparison is retained as evidence rather than represented as an exact all-row pass.

Installed Settings now visibly separates automatic rolling coverage and saved source coverage, both November 11–February 17 exclusive, with busy/free-only privacy retained and 193 records saved at 2:37 PM Central. The Settings window was closed and the desktop host left connected. No re-pairing or Google sign-in on the Air is needed. The final physical Air copy timestamp and queued-edit count after retry were requested; no completed Air sync is claimed yet. No push. Mission 16’s remaining dependency/physical gates above still apply; Mission 17 has not started.


### Physical Air follow-up — November 18, 2:39 PM Central

Dan reported the Air’s last update as **2:39 PM** after the desktop host was restored. With his earlier 0.2.25 installation report, this confirms a fresh physical Air copy following desktop recovery. The queued-edit count was not included; no zero-queue or offline-edit-drain result is inferred. Existing pairing was retained. External TaskDock/Concur gates remain open, and Mission 17 is unstarted.


### Air accepted and final dependency reassessment — November 18

Dan confirmed **zero queued edits**, completing his earlier report of **0.2.25 on the Air with a 2:39 PM update**. Physical fresh-copy synchronization after desktop recovery is passed, retaining the existing pairing. No new offline mutation, sleep/wake or VoiceOver result is inferred. Source/installed version remain 0.2.25/build 71; the existing HTTPS listener is reachable and the verified 15-group package evidence is present. Documentation-only acceptance recording does not require a new binary version.

Rechecked the remaining producers read-only. Installed TaskDock still declares `write_tasks:False` in `/Applications/TaskDock.app/Contents/Resources/app/api/unified_tasks/juno.py`. The Concur Helper source still has no versioned Juno report/order/run export. No source in either owning project was modified. These are the concrete remaining integration blockers:

1. **Owner: TaskDock project.** Implement the existing [scoped-write handoff](taskdock-juno-recurring-tasks.md), return the versioned API/grant/operation-lookup contract and test evidence, and install the supported TaskDock build. Then Juno can wire the real adapter, explicitly select/create the Juno column and run/reconcile the approved live routine pilot. Current draft definitions and synthetic ledger tests do not satisfy that live completion gate.
2. **Owner: Concur Helper project.** Implement the existing [read-export handoff](concur-helper-juno-read-contract.md) with stable report/order/run identities, exact source statuses and coverage. Then Juno can implement the actual producer-compatible reader, populated views and audience-reviewed summaries. Expense import and exact links already work; missing metadata is not invented.

**Reassessment before Mission 17:** the local redesign, source visibility, reviewed blockers/answers, report handling, calendar refresh and physical Air copy/queue check have acceptance evidence. Keep Mission 16 open for the two producer contracts and their live integration acceptance. The preferred-reading-size platform limit remains documented; larger document presentation is tested. Mission 17 remains unstarted. Its proposed daily support workflow should be narrowed with Dan after this integration gate is resolved, starting with one next action and an interruption/resume bookmark rather than enabling all reminder/timer features together. No diagnosis storage, new model-health context or GitHub push.


### 0.2.26 / build 72 — producer integration implementation

Dan authorized changes in TaskDock and Concur Helper. The previous producer audit was incomplete: installed capabilities and the older Python helper missed newer development work. TaskDock’s source already contained v2 per-occurrence approval, and Concur Helper’s Swift app had a versioned export. The running TaskDock was subsequently observed at build 2010. This increment extends the actual contracts rather than inventing replacement formats.

Juno now reads reviewed helper envelopes with instance/export IDs, source completeness, exact report status, run coverage, requested/observed dates and signed credits. Imports are owner-scoped, compare-and-swap protected and idempotent. Failed diagnostics retain earlier expense observations instead of replacing them with an empty scan. The concurrently developed submitted-report/Org allocation reader is preserved. The native summary explicitly chooses Dean/full totals or Alex/verified VISU allocation only; other chair amounts are not inferred.

TaskDock build 2011 adds exact recurring-rule owner approval and independent date/key/due-time validation. Juno has a separate Keychain-managed write connection, reviewed destination selection, approval-preview and activation steps, pause, a bounded work-host monitor, durable occurrence reconciliation and denial-triggered pausing. Existing read credentials gain no writes. New definitions remain inactive until approved. No existing routine was silently enabled.

Source verification: all **432 Juno backend tests passed**. Three focused real-HTTP bridge tests use disposable TaskDock SQLite and Juno PostgreSQL: owner approval, due creation, duplicate readback, early rejection and grant revocation. Actual Swift producer → Juno reader checks passed for credits, exact report status, verified allocation, failed-scan preservation and private-URL exclusion. The actual native audience formatter passed VISU-only versus Dean-total checks. TaskDock’s 15 focused managed-write tests and TypeScript checks passed; the broader suite and both distribution packages are being verified.

Deployment, preservation comparisons and an explicitly reviewed production write grant/routine pilot are still pending. No production task, recurring rule or grant has been created by the integration tests. Existing Juno 0.2.25 remains the connected work-Mac sync host during the build. Mission 16 remains open; Mission 17 and GitHub push remain unstarted.


### Integration acceptance follow-up — November 18

TaskDock’s full source suite passed **698 tests**. Its packaged runtime passed the **15 managed-write tests**, and the bundled v1 read connector retained controlled-sharing, restart and revocation behavior. A real HTTP lost-response test also passed: TaskDock committed, Juno lost the reply, and the next tick recovered one receipt without creating a second task.

Review caught a distinct producer case: **Read Report Status** was exported as a scan, which could make a report-only read look like an empty expense scan. Concur Helper now exports `read_report_status`, with `expenses:null` and receipt sources not searched. Juno accepts that operation and preserves prior expense rows/date. The real Swift encoder round-trip and 21 purchasing-export API tests passed. The requested window remains distinct from the report’s accounting period. Concur Helper 0.1.1/build 2 was rebuilt locally; university SSO, receipt attachment confirmation and submission remain manual. No live Concur session or upload was exercised.

Juno’s initial and intermediate packages passed all 15 installer groups (311, then 323 bundled tests). A final distribution rebuild includes the report-only preservation fix and will be independently verified before install. The 0.2.26 source and package have not been published or installed; candidate payloads are confined to private local build folders.

A verified external TaskDock/Hub backup completed at **3:24 PM Central**. TaskDock was normally quit for its update; the prior build 2010 application, SQLite baseline and private/configuration fingerprints were retained. TaskDock build 2011 Installer is waiting for macOS administrator authentication; Dan has been asked to approve it on the work Mac. Juno 0.2.25 remains running for laptop sync. No production write grant, Juno column or routine pilot has been created. Mission 16 remains open pending the installation/preservation/live-pilot gates.


### Deployment progress — 3:34 PM Central

TaskDock build 2011 installation succeeded and its actual header was observed at build 2011. The preservation audit retained every prior database row/column with integrity and foreign-key checks passing. Only `private/dashboard-owner.json` and `private/desktop.log` differed: the documented launcher rotates the local dashboard session on normal restart, and the log appended. All other private hashes, source configuration and pairing/device identities matched. The strict initial report is retained alongside the reviewed report.

Juno’s final source suite passed **434 tests**, and the final 0.2.26 release package passed all **15 distribution groups**. Its exact SHA-256 matched both the verification report and sidecar. At **3:32 PM**, the paused encrypted work-Mac backup succeeded and passed restore validation at schema 0019. Saved record/device projections and host/worker identity fingerprints were captured, and the old 0.2.25 app retained. macOS Installer is now applying 0.2.26; post-install preservation and reopening the sync host remain required.


### Installed and reviewed connection — November 18

Juno 0.2.26/build 72 installed successfully at **3:34 PM Central**. Before reopening, the strict work-record/device preservation comparison passed with no changed table projection, and the saved HTTPS/worker identity fingerprints matched. Deep/strict signature verification passed. Juno was reopened and visibly returned to **Connected · This Mac**. The verified final package and checksum are in `~/Downloads/Juno-0.2.26`.

The TaskDock preservation audit was expanded after resolving its configured database path: its active database is `data/live-tasks.db`, while the initial paused baseline had audited `data/tasks.db`. The verified 3:24 PM whole-workspace backup contains the live database. Every live business/workspace row from that snapshot remains present; integrity and foreign-key checks pass. Only sources.last_attempt_at/last_success_at and backup_health.checked_at/last_backup_at changed, matching normal source/backup runtime timestamps. Pairing and source-configuration hashes remain unchanged. Both audits and the reviewed timestamp-only difference are retained as private evidence.

Dan explicitly approved a separate write grant to the existing exact Juno column, unassigned tasks only, and one test task named **Juno recurring-task integration check**, due November 18. The native TaskDock review showed the exact column, title/notes, unassigned/unspecified room, revision 1, Wednesday-only schedule starting and ending November 18, and **15:43 Central** creation. This rule was approved in TaskDock and enabled through installed Juno. The one-time key was saved separately in Keychain, hidden in TaskDock and replaced on the clipboard with the public local API address. No other routine was present or enabled. The automatic monitor is now being observed; no manual tick has been used to create the pilot. The routine will be paused after receipt/deduplication acceptance.


### Mission 16 integration completion and reassessment — November 18, 3:45 PM Central

**Accepted shipping integration gates.** The installed Juno work-Mac monitor created the approved test automatically at **15:43:05.699 Central**; no manual due check preceded creation. TaskDock retained one occurrence and task ID, and Juno reconciled that exact task receipt. A subsequent native **Check due routines** call retained exactly one task. Native History showed the created occurrence and TaskDock task ID. The test card was observed in TaskDock’s exact Juno column; that existing hidden column was made visible, expanded and the temporary search cleared. The routine is now **paused**, has a November 18 end date, and the owner has **zero active routines**. Test evidence is retained; no repair, completion or new operational assignment was inferred.

Juno 0.2.26/build 72 and TaskDock build 2011 are installed and running. The encrypted Juno backup passed restore validation; the strict pre-reopen Juno record/device comparison and host/worker identity hashes passed. TaskDock’s correctly selected live database was compared to the verified whole-workspace backup: business rows survived and only named runtime timestamps changed. Pairing/source configuration were retained. Existing Juno HTTPS sync remains reachable. User-approved write access is separate from the prior read key, and only the reviewed one-date rule was enabled for testing.

**Evidence ledger:** `.local/mission16-0226-release-tests.log` (434 Juno tests), `.local/mission16-0226-release-verification.json` (15 installer groups), `.local/mission16-0226-preservation.log` (strict saved records/devices), `.local/mission16-helper-final-contract.log` (actual producer round-trip), `.local/mission16-live-pilot-observed.json` and `.local/mission16-live-pilot-reconciled.json` (automatic creation, repeated check and final pause), TaskDock `work/mission16-build2011-tests.log` (698 tests) and `work/mission16-build2011-managed-bundle.log` (15 bundled write tests). Private paths are local verification artifacts, not commit content.

**Limits retained:** physical Air acceptance is the user’s 0.2.25 fresh copy and zero queued edits; additive 0.2.26 host/API tests do not assert a new physical laptop run. VoiceOver remains waived. Concur’s versioned read/import contract is implemented and exercised with the actual producer encoder, but no live university SSO, receipt upload or report submission was performed. Vendor orders are **not searched**, not zero and not an implemented vendor integration. Earlier report/calendar/source/accessibility acceptance remains documented above. The previously observed system-wide preferred-reading-size support limit is not relabeled as a pass.

**Reassess before Mission 17.** Mission 16’s shipping redesign and scoped TaskDock/helper integration are accepted with these explicit limits. Choose real recurring routines separately; none are active. For Mission 17, confirm whether choosing priorities, getting started, noticing time or returning after interruptions causes the most trouble. Start with one visible next action and an interruption bookmark, then tune focus periods, quiet times, transition cues and midday deferral behavior with Dan. Use planning preferences, not diagnosis data. Mission 17 is unstarted. No GitHub push.
