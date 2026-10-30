# Build status

Updated: October 30, 2026.

## Staged usability increment — mission 6

The native source now has a grouped collapsible sidebar and Today landing screen with dated unfinished/due/recorded-blocker counts, issue search/filter, today's local holds, and direct chat/check-in/schedule/memory actions. Daily work is separate from source review and setup. No assignments, external messages, new permissions or model/cloud connections are created.

The planning sheet has a pinned Cancel/Apply footer, grouped fields and in-sheet validation. Unknown estimates can remain blank while recording other context. Invalid inputs no longer dismiss an editor just because another planning draft was already dirty. Estimation is cancelable. Plan filters and collapsed missing-detail/source sections reduce list noise. Schedule notes and planning context are expandable; comparison view selection is remembered, stale overlap responses are hidden, TaskDock setup is collapsible with a visible refresh action, and misleading laptop-model/empty-memory copy is corrected.

Validation: optimized native build; 103 real isolated-PostgreSQL backend tests (zero skips); exact native planning/schedule API decoding; native offline cache/queue and actual JunoStore regression; Today deadline/completion/blocker helpers; planning optional-estimate/bounds/date validation; existing room-alias and weekly projection checks. The staged development app is `.local/usability-final/Juno.app`. The running work-Mac app and published preview 10 installer have **not** yet been replaced by this increment. Native inspection repeatedly lost its pipe before a fresh visual sweep; full screen-by-screen and laptop-width visual acceptance remain pending. The user was asked to quit/reopen Juno when convenient after finishing any unsaved edits. No forced app termination was performed.

See [mission 6](missions/2026-10-30-06-usability.md) and [audit findings](reports/usability-audit-2026-10-30.md).

## Desktop follow-up — weekly person and room views

Schedules provides **By person**, **By room**, **Room + person**, and **List & edit** views. Room + person compares the selected room and person for one shared date with synchronized day navigation. Schedule times and time editors use AM/PM; new schedule dates and view entry default to today. Comparison panels have compact fixed widths rather than expanding across the window. A third Possible work times column uses the authenticated availability engine for the selected room/person/date, with same-day filtering, source warnings, offline/draft gating and explicit independent-work assumptions. Native live checks verified selection/date updates, weekend exclusions and Sammy’s November 2 ARTS 121 opening (10:45 AM–12:00 PM); 12 PostgreSQL scheduling tests and native projection checks pass. Weekly day columns show work/building hours, occupied classes, local planning holds and daily exceptions, with dated navigation and staff status/limits. This is an overview of saved facts; Plan remains responsible for repair feasibility. No assignments or schedule records were changed by adding these views.

The development app on the work Mac is updated. Native optimized compilation and synthetic projection checks pass (person/room isolation, supervised holds, candidates without shifts, daily overrides, semester boundaries and the daylight-saving week). Actual native controls were checked for person/room selection; Sammy's revised shifts and room occupancy were observed, and the room layout was visually inspected. Side-by-side room/person controls and synchronized previous-day navigation were checked in the running native app, and its layout was visually inspected. Host owner, record counts, certificate/key and existing paired-device states are preserved. The published preview 10 installer remains the earlier build; this desktop follow-up is not yet included in a new laptop installer.

Room-and-person comparison also shows unfinished TaskDock issues below the calendars: room-filtered title, status, priority, due date, recorded estimate/person/capability, planning and TaskDock blockers, and expandable original record fields. Saved room links take precedence over clearly labeled title-based matches; an all-rooms/unlinked toggle and search expose unmapped issues. Existing planning facts are joined only within the matching TaskDock workspace. Missing details stay unknown. No automatic task placement was added. Optimized native build and synthetic room-alias/isolation checks pass; the work Mac is updated with host records/pairing preserved. UI automation lost its native connection when opening the comparison, so the new issue cards’ hands-on visual check remains pending.

## Current installer — preview 10 schedules and repair windows

Native **Schedules** adds recurring semester rules, classroom occupancy, building access, personal/staff hours, dated exceptions and explicit active/tentative/candidate status with funded/agreed weekly limits. **Plan → When could we work on this?** intersects those inputs, distinguishes independent from supervised work and shows possible windows. Reviewed local planning holds reject room/person conflicts and excess weekly hours. TaskDock remains read-only and authoritative.

The user approved enabling TaskDock Juno access and saving its dedicated credential in Juno Keychain. Actual native pairing/import succeeded; real payloads remain on the work Mac. TaskDock tasks can open their planning details, suggest a room from the title for review, and request a duration range from the local model. A local-model call against an authorized saved task returned a valid suggestion without changing a task or hold. No upstream providers were refreshed or granted broader access.

The work Mac is updated, and its existing approved schedule inputs were migrated privately to recurring rules and staff-status records. The five room/employee intersections match the previously verified possible work windows. The host owner, existing record counts, certificate/key and paired-device states are preserved. New schedule data joins the laptop cache. No real planning holds were created automatically.

See [schedules and repair planning](SCHEDULES-AND-REPAIR-PLANNING.md), [preview 10 setup](PREVIEW-10-SETUP.md) and [mission 5](missions/2026-10-30-05-schedules.md). 103 backend tests pass without skips. The extracted/relocated installer passed 44 bundled planning/schedule/provider contract tests with external networking disabled, 239 Mach-O dependency checks, migrations/backups, restart and TLS checks. Native Swift decoding, offline regression and pinned-TLS outage/reconnect checks passed. See [schedule verification](reports/schedules-preview-10.json) and [installer verification](reports/installer-preview-10.json). Installer: `dist/Juno-0.1.0-preview.10-macOS-arm64.pkg`; a verified copy and setup guide are in `~/Downloads/Juno-0.1.0-preview.10`. Reopen the development app once for the final helper compatibility guard. Native pairing/import and the new root navigation were observed; interaction tests for the new schedule/window controls remain pending because the native tool repeatedly returned closed-pipe errors/timeouts. Real calendar consent/coverage and physical laptop offline-edit/reconnect acceptance also remain pending. This is not a whole-week optimizer or full beta signoff.

Distribution: implementation `45379a4` is pushed to GitHub. The [preview 10 draft installer release](https://github.com/dmccoy26/Juno/releases/tag/untagged-f95efedce68fc11a1b72) contains the verified package and guides; all six uploaded asset digests and sizes match local files. See [distribution verification](reports/github-preview-10.json).

## Previous increment — preview 9 planning

Native **Plan** adds revision-checked planning facts, editable durations/actual reported minutes, Dean/operations choices, room/staff windows, confirmed capability, blockers/next checks and resumption notes. Deterministic next-task suggestions respect confirmed availability, merged meetings, a 40-hour cap and interruption reserve. Missing scope/availability, stale sources and conflicting important priorities are visible and prevent unsupported choices. Confirmed priority choices expire by planning date.

Daily check-in gains a saved-context starter and avoids repeating unchanged blockers with a future check date. The weekly Dean draft uses confirmed diary text plus dated task/blocker evidence; it is editable for the current screen session and is never sent. Employee workload totals explicitly cover only supplied assignments. Planning corrections invalidate dependent assistant replies. Dated planning facts join the laptop cache; planning edits still need a connection.

See [planning guide](PLANNING.md) and [mission 4](missions/2026-10-30-04-planning.md). 91 backend tests pass with isolated PostgreSQL, including 13 planning acceptance tests. The exact native Swift planning models decode real isolated API responses, and existing native offline memory/diary checks pass. The extracted/relocated standalone installer passed 32 bundled planning/provider contract tests with external networking disabled, 239 Mach-O dependency checks, restart/upgrade/backup checks, TaskDock/evidence fixtures and pinned-TLS pairing boundaries. See [planning verification](reports/planning-preview-9.json) and [installer verification](reports/installer-preview-9.json). Installer: `dist/Juno-0.1.0-preview.9-macOS-arm64.pkg`; [preview 9 setup](PREVIEW-9-SETUP.md). A copy is in `~/Downloads/Juno-0.1.0-preview.9`. The work Mac is running preview 9 on schema 0006; its work-record counts, owner, certificate/key and paired-device states are preserved. Only its temporary local app credential rotated normally. Verified HTTPS at the existing IP reaches the authenticated planning route. Native UI automation is unavailable in this session; the new screen's hands-on interaction check remains pending. Actual live-provider setup and laptop offline-edit/reconnect acceptance also remain pending.

Distribution: source implementation `65c2613` is pushed to GitHub. The [preview 9 draft installer release](https://github.com/dmccoy26/Juno/releases/tag/untagged-a10467c73761a2cab077) contains the verified package and guides; all six asset sizes and SHA-256 digests match local files. See [GitHub distribution verification](reports/github-preview-9.json).

Next product work after acceptance: improve estimate calibration and reduce manual planning setup, then test the 15-minute workflow with Dan. Full weekly allocation, missed-day provisional drafts, reminders and native HumanLab instrumentation are not delivered by this increment.

## Previous release — preview 8 connections

Both connection paths are implemented. Start with [morning setup](PREVIEW-8-SETUP.md), [connection details](CONNECTIONS.md), [connection verification](reports/connections-native-preview-8.json) and [installer verification](reports/installer-preview-8.json).

- Native Connections UI supports a TaskDock source catalog and separately reviewed saved evidence, plus direct Gmail, Google Calendar, Google Tasks, Google Chat, Slack, Smartsheet and Outlook Calendar readers.
- Google/Microsoft use registered desktop clients, loopback state/S256 PKCE and renewable authorization; persistent credentials remain in native Keychain. Slack/Smartsheet accept approved user-supplied tokens. Nothing imports provider secrets from TaskDock.
- Read-only, explicit selection and identity review, bounded complete reads, failure retention, disconnect/removal and local-model/cache integration. An owner-wide 40 MB evidence bound protects export size.
- 78 backend tests passed with isolated PostgreSQL; native offline/store, pinned-TLS outage/restart, Keychain persistence and fictional native UI checks passed. A real local-HTTP two-app bridge test read 501 synthetic notes and exercised permission revocation. Extracted/relocated package verification includes seven-provider fixtures with networking disabled.
- TaskDock source is separately pushed on a draft review branch/PR with a build 15 candidate. Its full isolated gate passed 613 API, 53 JavaScript and 118 browser tests. The installed TaskDock build 14 was left intact with existing grants unchanged.
- The existing development Juno work host is updated without changing its owner, work-record counts, certificate/key or laptop pairing. Only the temporary local app credential rotated normally.
- Actual provider consent/approved credentials and real-account resource policy remain tomorrow's setup. No new live account reads, cloud model approval, background provider polling, automatic task creation or full beta completion is claimed. HumanLab native and actual laptop offline-edit/reconnect acceptance remain manual.
- Package: `dist/Juno-0.1.0-preview.8-macOS-arm64.pkg`, self-contained Apple Silicon, macOS 13.5+, ad hoc app signature, unsigned/not-notarized installer.

## Historical implementation notes (through preview 5)

The entries below describe earlier increments; statements that an integration or two-Mac test had not happened apply to those increments. Use the current verified release and overnight report above for present status.

## Completed

- Product mission and beta acceptance criteria captured.
- User delegated routine technology choices.
- User specified real data must remain on approved systems until external processing/storage is confirmed.
- Inspected installed TaskDock metadata and relevant API source; verified key checkout files against the installed manifest.
- Documented architecture, local bridge requirement, storage model, deployment restrictions, and HumanLab boundaries.
- Added the first read-only TaskDock workspace connector and automated tests against synthetic responses. It does not access production credentials or data.
- Installed isolated project dependencies and PostgreSQL 17 tooling; created a Juno-only developer cluster using a private Unix socket without a network listener or login service.
- Added an explicit Alembic schema migration, hashed/revocable per-device credentials, owner-scoped memory APIs, literal search, provenance/confidence, revision-checked corrections/deletions, reimport suppression, and metadata-only audit events.
- Verified schema/model consistency, two-client/service-recreation persistence, authorization isolation, revocation, deletion, and concurrent edits against real PostgreSQL. All 13 tests pass (8 memory/database tests and 5 connector tests).
- Added a dependency lockfile and `LOCAL-DEVELOPMENT.md` with reproducible setup, provisioning, API, verification, and shutdown instructions.
- A live loopback HTTP smoke check passed for service startup, authentication, creation/read/deletion, and credential revocation. Dependency checks and whitespace checks passed. The development database and temporary API process were stopped after verification.
- Built a native SwiftUI/AppKit development application at `~/Applications/Juno.app`, with its own window, Dock presence, menus, memory listing/search/add/correction/deletion confirmation, revision-conflict errors, and a manual meeting-mode setting saved on this Mac.
- Native interaction checks verified adding and correcting one explicitly fictional demo memory (revision 2), search results, meeting-mode switching, and canceling the deletion confirmation. Actual destructive deletion remains covered by backend tests; the native confirmation was canceled.
- Changed the interface decision from React/Tauri to SwiftUI to prioritize the user's standalone Mac workflow. No browser tab is needed to use the preview.
- Final bundle compiled and passed strict signature verification. Reopening the native app retained the corrected demo memory and meeting-mode setting. A helper lifecycle check verified authenticated startup and clean shutdown of its owned database. All 13 backend tests passed after the native implementation. The app was reopened and left running for the user.
- Pushed the initial implementation to `https://github.com/dmccoy26/Juno` (`32c9403`).
- Built the first self-contained Apple Silicon installer: `dist/Juno-0.1.0-preview.1-macOS-arm64.pkg` (approximately 147 MB), with checksum sidecar. Python 3.14.10 and PostgreSQL 17.11 are bundled from pinned vendor downloads; no Homebrew, checkout, or runtime downloads are needed on the recipient Mac.
- Verified the actual installer payload after extraction and relocation on macOS 26.6.2: 239 Mach-O dependency checks, bundle integrity, clean-data startup, authentication, memory create/edit/conflict, restart persistence, credential rotation, deletion/suppression, clean shutdown and parent-loss cleanup. The packaged native window connected successfully. See `reports/installer-preview-1.json`.
- Target laptop identified by the user: M5 MacBook Air, macOS 26.5. Actual laptop installation remains to be tested. The temporary packaged verification app was quit after inspection.

## Preview 2 additions

- Added schema `0002_companion`: owner-scoped conversations/messages, local model settings and resumable dated check-ins.
- Added native Chat, Daily check-in and Model connection sections alongside Memories.
- Local-only model adapter supports LM Studio, bounded responses, final-answer parsing and explicit failure states. No cloud fallback or model weights are bundled.
- Live desktop smoke test with `qwen3.6-35b-a3b` answered from a synthetic canonical memory. Native chat answered the fictional classroom availability question and survived an application restart.
- Native check-in resumed at question three after a full restart and produced an editable five-section diary draft. The synthetic native diary was left unconfirmed.
- Corrections/deletions invalidate derived assistant history; in-flight replies validate context revisions before publishing. Idempotent retry records and pending-turn recovery prevent silent duplicate turns.
- Automatic pre-migration PostgreSQL backup and readability check added. Preview-1 schema upgrade, backup and preserved memory passed in the package verifier.
- All 24 automated tests pass, including real PostgreSQL behavior and local model-adapter checks. Native interaction verification and a real local-model call supplement those tests.

## TaskDock preview 3

- Added a native read-only TaskDock connection screen, device-only Keychain credentials, identity review, immutable dated snapshots, provider freshness, safe recorded-field display and separately cached update/activity history.
- Added schema `0003_taskdock` and bounded task excerpts for local chat, with invalidation and post-generation context checks.
- All 41 automated tests pass. Juno's reader also passed real HTTP checks against the extracted TaskDock build 13 installer with disposable Student Test data. Existing installed TaskDock and real work data were not used.
- Native screen/missing-token guidance and isolated synthetic Keychain operations were verified. Actual installed TaskDock pairing and laptop installation remain pending. See `TASKDOCK-CONNECTION.md` and the preview 3 installer report for exact evidence.

## Shared work Mac and offline laptop — preview 4

- User approved this Mac as the shared system and authorized offline laptop memory/diary edits. Cloud systems/providers remain unapproved.
- Enabled the encrypted local-network host on this Mac. Added one-use pairing files, pinned native TLS sessions, device revocation and remote administration restrictions.
- Added owner-scoped offline exports, private durable laptop queues, expected-revision conflict handling and atomic idempotent operation replay. The host runs while Juno is open and the Mac is awake; no background daemon or system security/sleep changes were made.
- All 47 backend tests pass. Native-code fixtures verify cache/queue restart behavior and real TLS pairing, stopped-host offline edits, restarted-client replay-safe synchronization and wrong-certificate rejection.
- Actual two-Mac/campus-network acceptance remains pending. See `SHARED-HOST.md` and the preview 4 reports for exact evidence and limits.

## Historical incomplete items (preview 4)

- Discovery architecture recommendation written. The local shared host now exists; installed TaskDock, actual two-Mac network acceptance and real calendar access remain pending.
- Local PostgreSQL memory service exists; the local work Mac host now exists, while actual two-Mac acceptance remains pending.
- The earlier development app still depends on the checkout. The new installer is self-contained and stores fresh per-user data in `~/Library/Application Support/Juno`; it does not import the development data.
- No Developer ID signing identity is available. The app is ad hoc signed; the package is unsigned and not notarized. Institutional/macOS approval may be needed on the laptop.
- Chat and check-ins are implemented locally. Semantic retrieval/embeddings, actual two-Mac acceptance, installed TaskDock acceptance/calendar reads and the full beta mission remain incomplete.
- Meeting mode now controls the chat prompt and hides private-mode assistant replies. Notifications and shared preference synchronization do not exist yet; memories, conversations and diaries now use the work host.
- No Juno HumanLab runs or actual two-Mac tests yet.

## Verification

Run all tests from the Juno directory with the developer PostgreSQL cluster started:

```sh
JUNO_TEST_ADMIN_URL="$(python3 scripts/dev_database.py url)" .venv/bin/python -m unittest discover -s backend/tests -v
```

Evidence covers the memory/database behaviors above and synthetic connector responses. It does not establish a live TaskDock connection, semantic recall, or actual two-Mac operation. Integration tests are skipped when the test database URL is absent; do not report that as a full pass.

## Historical next step (preview 4)

Install preview 4 on the M5 laptop, transfer a fresh invitation from this Mac and verify native pairing, offline editing and reconnection on the actual network. Complete installed TaskDock acceptance separately. Calendar planning, remote-model approvals, semantic retrieval, a background host daemon and native HumanLab instrumentation remain later requirements.


## IP and HTTPS pairing repair — preview 5

The initial certificate named only localhost; the advertised .local address therefore failed ordinary TLS hostname verification. Preview 5 creates certificates with local IP/hostname SANs and exports pairing files using the desktop’s private IP, avoiding Bonjour discovery across wired and Wi-Fi networks. Pairing errors now distinguish DNS, TCP reachability, certificate identity and invalid/expired invitations. No laptop device had successfully paired before the local certificate repair; old unused invitations were invalidated and the prior certificate/key retained privately. 48 backend tests and native strict-TLS/IP-pairing/offline-sync fixtures pass. Actual laptop wired-to-Wi-Fi reachability still requires verification.
