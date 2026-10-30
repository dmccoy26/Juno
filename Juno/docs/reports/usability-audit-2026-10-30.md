# Juno usability audit — October 30, 2026

Final status: updated native app installed and visual sweep completed after the inspection connection recovered. All eleven main workspaces were viewed in the actual app.

## Evidence

Reviewed source for every current workspace and prior native screenshots of Chat, Schedules, room/person comparison, work openings and the planning sheet. Those images demonstrate the crowding and sheet-exit problems directly. A fresh native sweep was attempted through the supported computer-use tool: path/bundle-ID app bindings repeatedly returned “Sky Computer Use native pipe closed before response,” including after reset; app inventory still worked. Screens not successfully captured this mission must not be described as visually verified. No external screenshot comparison was needed to identify these concrete issues.

## Findings and changes

| Screen | Finding | Implementation / next check |
|---|---|---|
| App shell | Ten equal top tabs overflow and mix work with configuration. | Grouped, collapsible sidebar: My workday, Saved sources, Setup; persistent page/status header. Check keyboard and smaller windows visually. |
| Today (new) | No starting place summarizes what is already saved. | Due/overdue, unfinished and recorded-blocker counts; issue search/filter, current local holds, direct check-in/chat/memory/schedule actions. No automatic priority selection. |
| Chat | Conversations and composer already have a useful split layout. | Retain structure; source/model setup now separated in navigation. Verify composer at laptop widths. |
| Plan | A long issue list repeats warnings; task editor has no explicit cancel and validation can close an invalid editor when another draft was dirty. | Issue filters, collapsible missing details/source limits, pinned Cancel/Apply footer, in-sheet validation, cancelable estimation. |
| Schedules | Comparison repeats long notes/notices and pushes room issues below the fold. | Remember view choice, collapse schedule notes and per-issue planning details; keep core room/shift/opening facts visible. Protect against stale overlap results after selection changes. |
| Check-in | Good guided single-question flow; day used device timezone despite work schedules using Chicago. | Use work timezone for day keys. Keep saved answers/draft behavior. |
| Memories | Good list/detail pattern but empty copy describes a first synthetic prototype. | Replace with normal user-facing memory guidance; retain explicit review/correct/delete. |
| TaskDock | Credential form consumes primary space even after connection. | Collapsible connection settings; retain source-freshness and recorded fields. Verify identity-review prompts remain discoverable. |
| Evidence | Imported records can be numerous; existing item disclosures/search limit visible detail. | Retain source/item disclosures and search; source/coverage truth must remain accessible. Future: source-type filter and pagination rather than an unbounded evidence wall. |
| Connections | Setup is complex because real authorization/coverage decisions matter. | Move under Setup; keep explicit account/resource review rather than hiding consequential choices. Future: provider status cards and guided setup steps. |
| Local model | Copy incorrectly says paired laptop needs its own server. | Correct: paired laptops use the work Mac model while connected. Keep no-cloud-fallback and local setup behavior. |
| Computers | Pairing/offline controls are setup, not daily navigation. | Move under Setup; keep host status, per-device revocation and conflict review semantics. |

## Capability increment

Today uses existing authenticated read endpoints; it needs no model and creates no assignments. Deadline counts use valid recorded due dates; missing/invalid dates are not treated as due today. Source completion flags and completion dates exclude finished tasks. Planning facts join only within the active TaskDock workspace. An error clears unavailable supplementary planning facts and warns that blockers may be incomplete. No cloud access or provider permissions are added.

## Verification

Optimized native development build passes. All 103 backend tests pass against isolated PostgreSQL with zero skips. Native API-model decoding, offline cache/queue and actual JunoStore regressions pass. New helper checks cover deadline/completion/blocker classification and unknown-estimate/numeric/date validation; existing room-matching and weekly-projection checks pass. The staged app is `.local/usability-final/Juno.app`; the running app is unchanged pending a convenient quit/reopen. The user asked whether ordinary computer use or macOS security could be responsible; the precise pipe failure does not establish a permissions denial. No security setting was changed. Physical laptop acceptance, full native screen sweep and a fresh installer are separate from source compilation and synthetic regressions.

## Completed native visual sweep

After the user adjusted/rechecked their computer-use setup, native inspection recovered. The actual app was updated and screenshots were inspected for Today, Chat, Plan, Schedules, Daily check-in, Memories, TaskDock, Evidence, Connections, Local model and Computers. Connections included the TaskDock bridge and direct Gmail setup route; this was not a separate consent/setup test for every provider. Schedules included person week, room week, comparison and List & edit.

A task editor was opened, an invalid four-minute estimate was entered, and Apply kept the sheet open with an in-sheet validation message. Cancel closed the sheet and Save planning remained disabled. No facts were applied or saved. The fixed footer remained visible.

The sweep found comparison overflow after adding the sidebar and imports dominating Evidence. Follow-up changes reduce comparison columns to fit the existing desktop window, collapse import/Beacon controls, and scroll reopened Chat to the latest message. Actual screenshots confirmed all three columns fit and saved Evidence is immediately visible; the Chat scroll position was near the bottom on reopening.

The host preservation checker passed after both app updates: owner, work-record counts, pinned certificate/key and existing paired-device states match the private pre-update baseline. Prior app bundles are retained privately. Existing permissions, credentials and data were not changed by the sweep. Provider authorization/refresh and task/hold creation were not exercised on real work records.

The final optimized native build and weekly/time/date/Today helper checks pass. Earlier 103 PostgreSQL and native offline regressions remain applicable; the follow-up changes only alter view layout and initial scroll position. A physical M5 laptop run and fresh portable installer are still pending.
