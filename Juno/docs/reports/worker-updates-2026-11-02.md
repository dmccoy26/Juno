# Mission 11 verification — worker updates

November 2, 2026. Software increment delivered as preview.13, build 13. Real worker enrollment remains disabled pending approved HTTPS/network and a supervised pilot. This is not a claim that every state, browser or physical device has been tested.

## Delivered behavior

- Native Worker updates inbox (Command-9), person-linked portal identities, explicit field-sharing previews, invitation/task link creation and copying, revocation, report review and selective planning changes.
- Locally bundled worker forms for task updates, end-of-shift check-ins and unexpected work, with review, attributed receipts, linked corrections, sign-out and draft-preserving reconnect.
- Separate worker identity/session/grant authorization and dedicated HTTPS surface. Worker sessions never authenticate as owner devices; worker routes are not exposed through the paired-laptop listener.
- 24-hour one-use enrollment invitations, bounded seven-day sessions, expiring task grants, per-request revocation checks and permanent grant withdrawal on TaskDock sharing restriction. Re-sharing replaces that worker's old grant for the same task.
- Minimal selected excerpts. A selected room prefers confirmed Juno facts from the matching workspace, otherwise shared TaskDock room facts. No contact/employee assessments/credential/chat/memory fields are offered.
- Immutable attributed report contents, private supervisor review notes, optimistic revision checks, explicit reported-versus-verified completion and selected-field application through existing planning validation. Time replaces a reviewed value, never automatically accumulates. Already-applied fields cannot be applied twice.
- Indefinite report retention, explicit reviewed repair context/patterns and calibrated estimates, explicit deletion semantics, no offline worker draft persistence or attachments. No LLM is required, no worker message is sent automatically, and no TaskDock/provider write is added.

## Automated checks

The full isolated PostgreSQL/backend suite passes **138 tests, zero skips**. The worker-specific subset contains 15 tests covering role/owner/task isolation, minimal excerpts, room provenance/workspace fences, one-use/expired/revoked sessions, CSRF, request size/rate bounds, safe assets, duplicate/retry payload checks, linked corrections, all three report types, sharing withdrawal/replacement, unknown/zero values, stale planning/report edits, repeated application, private notes, deletion and retention.

The actual HTTPS listener test uses a temporary certificate/CA trusted only by the test client; it installs no system/browser trust. It verifies certificate chain/hostname/key permissions, rejection by an untrusted client, secure/HttpOnly/SameSite cookies, actual enrollment and report receipt through HTTPS, blocked owner/pairing/docs routes and listener shutdown on disable. Certificate preflight uses an in-memory TLS handshake because macOS's bundled LibreSSL CLI lacks hostname verification. No outbound certificate probe or trust bypass is used.

Existing native offline memory/diary/queue/conflict tests, planning model/editor validation, schedule projection/DST/limits, room aliases, Today helpers, memory intent, credential responsiveness/Keychain isolation and pinned-TLS host outage/reconnect checks pass. Schema/model comparison passes at `0010_repair_history`.

The [actual installer report](installer-preview-13.json) passes extracted/relocated startup and 100 bundled-runtime fixture tests with external networking disabled, 239 Mach-O dependency checks, private-data exclusion, bundled portal assets, migration/backup, restart/persistence, existing laptop TLS/pairing and owned-service shutdown checks. This tests the built artifact, not just the source checkout. The installer remains an ad-hoc-signed internal preview, without Developer ID notarization.

## Actual browser/native observations

Mutation work used a separately identified Juno Lab, isolated database and fictional Student Test records. No actual worker was enrolled, contacted or evaluated.

| Surface | Observation | Boundary |
| --- | --- | --- |
| Browser task update | Selected a shared task, entered work/time/completion, reviewed and submitted; dated receipt appeared | Synthetic loopback fixture, not an actual campus HTTPS browser session |
| Browser shift/unexpected work | Both submitted successfully; blocker/help text retained | Official payroll and automatic task creation are excluded |
| Reconnect | Text and blocker choices remained in the open form; current tasks refreshed | Expired sessions still need a new authorized invitation |
| Timeout/retry | Paused the isolated host, waited for the 20-second request timeout, observed honest unconfirmed state with reviewed report intact, resumed host and retried | Database assertion found exactly one matching report, not two |
| Phone-width layout | Inspected at a 390×844 viewport override; document/content width fit inside viewport; controls stack and receipt wraps | Instrument screenshot scaling differs from a physical phone; no physical-device/VoiceOver verdict |
| Consecutive reports | Found and fixed a hidden required blocker field left behind after reset; submitted a blocked report followed by an update with no blocker, receiving both receipts | Actual browser regression sequence |
| Sign-out | Returned to Signed out and hid/cleared shared form content | Browser/system memory and screenshots cannot be remotely erased |
| Native inbox | Actual browser report arrived attributed to Student Test Alex; selected only actual minutes and saved | TaskDock copy stayed unchanged |
| Native review | Saved private note and Completion verified by me; local verification displayed separately | No real employee record or external task modified |
| Native share preview | Defaults title/room, optional fields off, explicit instructions and source time; final preview puts task title first and explains disabled link creation | Native invitation creation with real approved hosting not clicked; API/actual-TLS tests cover creation/enrollment |
| Native layout | Long forms/management groups scroll; inspector actions stack; Cancel remains visible; final release footer observed | No exhaustive keyboard/VoiceOver/large-volume usability claim |

The browser fixture in `scripts/worker_browser_lab.py` adapts synthetic loopback HTTP to exercise the production form/session/CSRF/report code without installing certificate trust. Its cookie transport adaptation is test-only, clearly labeled, loopback-bound and **not bundled**. It is not a deployment switch or production security relaxation. The separate actual-TLS tests above provide protocol evidence. The fixture and lab app were stopped, their sessions invalidated and only the isolated lab database shut down afterward.

## Work-host preservation and delivery

The existing work development app at `~/Applications/Juno.app` is updated to preview.13; its previous bundle remains privately at `.local/host-app-before-mission11` (and the follow-up interface at `.local/host-app-before-mission11-history`). The helper created a readable pre-0010 migration backup. Read-only before/after invariants passed for owner, work-record counts, planning/schedule content hashes, prior paired-device states and certificate/private-key digests. Only the normal temporary local app credential rotated. The separate portable installation/data root was not moved or merged.

Native inspection confirmed Connected · This Mac, preview.13, Worker access · Disabled and an empty real worker inbox. Initial checks confirmed no real worker records were created by the implementation. The owner subsequently added a worker identity through the app; the final update preserved that identity and verified that real worker access remains disabled, with no synthetic reports in the work database. No source provider was refreshed, no broader TaskDock scopes requested and no certificate trust/firewall/router settings changed.

Installer, checksum, report and setup instructions are delivered in `~/Downloads/Juno-0.1.0-preview.13`. Follow [the operator/worker guide](../WORKER-UPDATES.md) for IT configuration and workflow. The actual M5 laptop upgrade, real campus wired/Wi-Fi reachability, browser trust and a supervised worker pilot remain open. Worker administration/review is intentionally host-only; reports are not exported into the laptop cache. Accepted planning facts continue through existing owner-only synchronization.

## Remaining scope

Photos, Slack/email ingestion, institutional SSO, automatic TaskDock write-back, payroll, autonomous assignments/reservations and persistent offline worker forms are not included. At most 500 active shared tasks and the latest 50 receipts appear in the worker portal; the owner inbox pages reports and lists the latest 200 grants with whole-worker revocation available. Reports have no age-based expiry; only expired access secrets are pruned. None of these limits is presented as full production or physical-device acceptance.

## Indefinite history and repair prediction follow-up

At the owner's explicit request, reports are kept indefinitely; a ten-year-old report remains in inbox/receipts during the retention test. Migration 0010 resets finite settings and adds independently reviewed repair context and lookup indexes. Invitation/session expiry and explicit report deletion remain separate.

Native testing observed two included verified complete-effort reports labeled insufficient for calibration, then reviewed a third with confirmed room/equipment, printer category and complete effort. The board updated to three samples and a 30–65-minute suggested range, with repeated-issue guidance and clickable supporting reports. Partial work, duplicate linked tasks, current-task self-comparison and superseded corrections are excluded in automated checks; room aliases normalize consistently. Sources remain independently retained user-reviewed history, not a cached TaskDock grant.

Chat/estimates receive bounded reviewed excerpts from the retained records; no external model is used. An actual LM Studio check with the configured local Qwen model initially returned no complete final answer under the prior 1,536-token bound. Increasing the bounded allowance to 4,096 and rejecting length-truncated output produced a complete synthetic-history answer in 28.9 seconds, grounded in the recorded paper-path checks. Two parser tests cover scratch removal and truncated/unfinished answer rejection. This one smoke check is not a general model-accuracy guarantee or a prediction of hardware failure.

Analysis covers at most the latest 2,000 included repair reports, with at most six relevant excerpts in a model request; older reports remain retained and paginated in the inbox. Enough qualified history is needed for time calibration. No failure date, repair commitment, purchase, calendar reservation or employee score is generated automatically.

The final work-Mac inspection confirmed Connected, Worker access Disabled, indefinite retention text, the repair-history section and removal of the 90-day expiry control. The final preservation guard additionally checks the existing worker identity hash. A changed history during a model estimate is re-read after expiring stale ORM state and returns a conflict instead of an obsolete estimate. That race has an isolated regression test.
