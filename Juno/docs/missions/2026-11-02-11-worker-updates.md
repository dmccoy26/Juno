# Mission 11 — worker updates through the work Mac

Created November 2, 2026. Status: preview.13 software increment implemented and verified; real worker access remains disabled pending approved HTTPS/network and pilot.

## Outcome

Let Daniel's workers report progress, completed work, interruptions and blockers without installing Juno or filling out its supervisor planning form. Juno remains the native Mac application. A small browser portal served by the approved work Mac provides a deliberately limited worker interface. Submissions arrive in a native review inbox and inform planning only through explicit review.

The first release supports three paths in the same portal: update a shared task, submit an end-of-shift check-in, and report unexpected work that has no existing task. Daniel copies links himself; this mission does not authorize sending email/Slack messages, exposing the Mac publicly or granting access to actual workers during development.

## Product boundaries

- TaskDock remains the task system of record. Its existing Juno connector remains read-only. A worker's submission or an accepted Juno planning change never silently updates TaskDock, Smartsheet or a calendar.
- Juno's desktop application remains native. The worker portal is a small companion form, not a browser replacement for Juno or a full shared workspace.
- Use the approved work Mac for storage and processing. No cloud form service, external model, public tunnel, automatic router configuration or unapproved hosting fallback.
- Workers can see only task information Daniel explicitly shares with their worker identity. A name selector is not authentication. No access to private chats, memories, diary, source credentials, other workers' updates, employee assessments or the complete plan.
- Student reports are evidence, not confirmed skill, verified completion or an intelligence/performance score. Daniel retains priority, assignment, capability, supervision and schedule approval.
- No automatic task assignment, reservation, source refresh, calendar entry or staff communication.

## Worker experience

### Enrollment and access

Daniel opens **Workers & updates** in Juno, selects an existing schedule person and creates a separate portal identity. Linking a person does not create shifts or change active/candidate status. He creates an expiring invitation for that person and shares it manually. Enrollment establishes a revocable worker-only browser session. Later task links still require that worker's session and task authorization; knowing a task ID never grants access.

Use one-time enrollment invitations, hashed server-side invitation secrets, cryptographically random sessions and per-worker revocation. Default to a short enrollment lifetime (24 hours) and a bounded browser session (7 days), configurable downward. Explain that an invitation authenticates its holder, not independently verified institutional identity. Daniel verifies the recipient before sharing; institutional sign-in can be a later integration. Provide Sign out and a shared-device warning.

The worker can bookmark the portal address. Its landing page shows only currently shared tasks and three clear actions: **Update a task**, **End my shift**, **Report other work**. Display worker identity and the saved/submitted state. No worker can switch identity through an unauthenticated picker.

### Task update

Show a reviewed task excerpt: title, room, short issue/requested outcome and relevant instructions. Show due date or selected supporting facts only if explicitly shared. Never expose the raw TaskDock payload or entire planning record. Preview exactly what the worker will see before sharing; contact information, troubleshooting comments and source history are excluded by default.

Ask short questions:

1. What did you do or try?
2. What is the current state: not started, in progress, blocked, or reported complete?
3. How many minutes did you spend? Is remaining effort known? Unknown is a valid answer.
4. Is anything preventing the next step? Distinguish explicitly no blocker from not supplied. Capture parts/access/approval/instructions/help and the next action if known.
5. What should the next person know? Optional handoff note.

Use the task's saved context, not the full supervisor form. Do not ask the worker to confirm their own independent capability or change priority. Permit **I need help** without requiring a precise technical explanation. Completion reports can describe verification performed without forcing a false claim that the issue is verified fixed.

### End-of-shift check-in and unexpected work

Aim for a two-to-three-minute check-in: work completed, time by task if known, unplanned work, unresolved blockers and handoff. Link entries to authorized shared tasks; allow unlinked notes without revealing other tasks. Report shift date explicitly in America/Chicago, default today, allow correction. An entered shift report does not replace the official timekeeping system or silently change scheduled hours.

Unexpected work asks what happened, room/equipment if known, action taken, current state, time and whether follow-up is needed. Store it as an unlinked worker report until Daniel links it to a task or records a next action. Do not create a TaskDock task automatically.

### Submission and failure behavior

Preserve typed text while navigating within the current page. Show a review step and clear **Submit update** action, then a receipt with date/time and submission reference. A spinner, model response or button click is not proof of receipt. Validate reasonable text/minute limits and allow unknown duration. Prevent duplicate creation on double-click, timeout and retry through idempotency keys.

When Juno is unreachable, state that nothing has been submitted. Keep the draft in the open page for retry. First release does not promise offline browser reopening, background synchronization or persistent sensitive drafts on shared devices. Document tab-close loss clearly. After receipt, a worker may add a linked correction/follow-up; retain attribution and superseded history rather than silently rewriting an already-reviewed report.

## Native supervisor experience

**Request worker update…** on a Plan/TaskDock issue opens a native sharing preview. Select a worker, choose a minimal excerpt, provide optional instructions and expiration, then create/copy the link. Creating a link is distinct from sending it. A shared-task row shows active/expired/revoked state and a revoke control. Re-sharing requires explicit review; do not automatically include newly imported TaskDock fields.

A native **Worker updates** inbox shows worker, task/room, reported state, age and blocker indicator, with unread/reviewed filters. A detail inspector shows what was shared, the original report, later corrections and proposed effects. Use **Worker reports complete** until Daniel verifies; allow **Reviewed**, **Needs follow-up**, **Completion verified** and **Dismissed** as distinct review outcomes. Inbox review is not an employment evaluation.

Daniel can accept selected facts into a Juno planning draft: actual minutes, revised remaining estimate, blocker/waiting-on/next action and handoff continuity. Show before/after values, source attribution and the saved task/planning revision. Existing unsaved drafts or concurrent edits require comparison; never overwrite an entire plan with a worker's stale form. Reuse the explicit Apply-to-draft then Save contract where appropriate. Mark a submission applied only after the save succeeds. Reapplying a reviewed report must not add time twice.

Worker completion and Daniel's verified completion remain local annotations; imported TaskDock status is displayed separately. TaskDock may still show open until changed there. Provide a copyable summary for manual TaskDock entry, explicitly labeled not synchronized. Duplicate/overlapping minutes across a task update and shift summary need reconciliation, not automatic addition.

Worker statements may inform the existing local planning/check-in context after review, with provenance and bounded excerpts. No LLM is necessary to submit, receive or review an update. Optional summaries use only the configured approved model and treat worker text as untrusted data, never instructions to run tools or expand sharing.

## Architecture and local hosting

Build on Juno's Python/FastAPI backend and PostgreSQL with a separate worker authentication dependency, worker routes and minimal locally bundled HTML/CSS/JavaScript. Keep the native supervisor inbox in SwiftUI. No external CDN, analytics or remotely loaded assets. Inspect `api.py`, `shared_host.py`, `planning.py`, `schedules.py`, `offline_cache.py` and the native task/plan workspaces before implementation.

Add owner-scoped worker identities, invitations/sessions, task-share grants, immutable submissions/corrections and review/application records. Use stable workspace/task identifiers and revisions, not task titles or free-text worker names. Store only the approved excerpt needed for the grant, with its source and sharing revision; do not copy whole provider records into the portal. All reads/writes enforce owner, authenticated worker and active grant in the database, including individual record endpoints.

The portal may reuse the approved work-host lifecycle/listener only after checking its trust boundary. It must never reuse owner-device pairing tokens, accept a worker session at owner APIs, or expose pairing/admin routes as worker functions. Test both authorization directions. Do not enable a second host accidentally on the paired laptop. Initial administration and application of reports are host-only; any laptop cache support must explicitly preserve the existing owner-only sync rules and invalidate revoked shared material. No silent new portal-data export to other devices.

Browser security includes HTTPS, Secure/HttpOnly/SameSite cookies, CSRF/origin checks for mutations, no credential-bearing query URLs, strict output escaping/CSP, bounded requests and rate limits. Enrollment secrets can use a fragment exchanged for a session and immediately removed from browser history; never log raw secrets or put them in analytics/referrers. Check grant/session expiration and revocation on every request. Disable shared caching and disclose that already-viewed information/screenshots cannot be remotely erased.

If TaskDock sharing is reduced/revoked, or task/workspace identity changes, fail closed for affected grants and remove withdrawn task excerpts from future portal responses. Preserve independent worker reports under the retention policy without re-exposing withdrawn source text. Ordinary network outages should be distinguished from authorization withdrawal. A copied old page must not remain an authorized submission channel after revocation. A worker losing task access may retain only their own submission receipt, not the withdrawn task excerpt.

### Network and certificates

Juno and the Mac must remain awake and reachable while receiving updates. Portal Settings shows actual enabled state, local address, certificate readiness and a connection test. Start development loopback-only with synthetic data. Do not assume campus wired/Wi-Fi routes or a fixed IP are stable.

Mac-to-Mac pinned-certificate pairing is not browser trust. Before real worker use, establish an institution-approved hostname and browser-trusted certificate or an IT-approved managed trust arrangement. Never instruct workers to bypass browser security warnings or distribute Juno's private key. If this cannot be provisioned, report the blocker and keep the portal disabled for real data; prepare the complete feature and local tests meanwhile. Do not expose port 8443 or another port publicly, request firewall/security changes or create a tunnel automatically. Off-campus use requires an approved network path such as institutional VPN, outside the first local-only release.

Hosting is opt-in with a reviewable field/access summary. Revoking a worker invalidates sessions and invitations. Turning off the portal stops worker access without destroying retained submissions or affecting the existing paired laptop service. Existing real-data and institutional approval boundaries remain in force.

## Phased implementation and gates

| Phase | Deliverable | Gate |
| --- | --- | --- |
| 1 — isolated foundation | Schema/migration, role separation, grant lifecycle, submission API and bundled portal with synthetic data | Owner/worker/task isolation, expiry/revocation, CSRF/XSS, replay and retry tests pass; default remains disabled |
| 2 — worker forms | Shared task update, shift check-in, unexpected work, review and receipts; mobile layout | A worker completes each flow without access to supervisor fields; errors retain text and never falsely claim submission |
| 3 — native review | Share preview/copy/revoke, update inbox, corrections, selective planning draft application | No stale overwrite, duplicate minutes or automatic TaskDock write; provenance and reported/verified states remain visible |
| 4 — deployment readiness | Certificate/network diagnostics, indefinite retention, package and preservation checks | Bundled portal works without external assets; host/laptop identity and existing records/pairing preserved |
| 5 — supervised pilot | Daniel reviews readiness, enrolls a real worker and observes one update | Approved browser trust/network available; no security-warning bypass; actual pilot results reported separately from synthetic tests |

Attachments/photos, Slack/email ingestion, institutional SSO, automatic TaskDock write-back, full worker-facing scheduling and offline browser sync are later missions. Exclude them from the first release rather than leaving apparently functional buttons. Draft a short TaskDock API proposal only if write-back is separately requested.

## Verification and acceptance

Use an isolated host and at least two synthetic workers, two owners and overlapping room/task names. Test:

- One worker cannot enumerate another's tasks, grants, reports or receipt IDs. Tampered IDs, expired/revoked sessions/invitations and changed workspace identities fail closed. Worker credentials cannot access any owner API, pairing, credentials or private model context.
- Share only selected fields; newly refreshed TaskDock details do not expand a prior grant. Revoked sharing withdraws excerpts and blocks stale-form submissions. Source withdrawal never recreates withdrawn fields from a cached grant.
- Actual browser enrollment, task update, shift check-in, unexpected work, receipts, sign-out and resubmission after timeout; duplicate request returns the same receipt. No real invitation is sent during testing.
- Keyboard and screen-reader labels, phone-width forms and Mac browser layouts, 12-hour times and Chicago date boundaries. Required fields and unknown/explicitly-none meanings are understandable.
- Native sharing preview, Copy link, cancellation, inbox filtering/detail, follow-up, correction, apply selected changes, save failure, concurrent revision and repeated application. Completion verified never implies TaskDock closed.
- Host sleep/outage/restart, expired form mid-edit, network disconnect before/after server commit and worker revocation while a form is open. An offline paired laptop never becomes a worker host accidentally.
- Text injection/HTML, prompt injection, CSRF, cross-origin reads, oversized/rapid requests, token leakage in logs/referrers/history and unauthorized attachments. No unsafe uploaded-content path is introduced in version one.
- Database backup/migration/restart, preservation of chat/memories/diary/planning/schedules/pairing, packaged asset inclusion and no development secrets/private work data in the installer.

Retain reports indefinitely, with explicit supervisor deletion semantics and a clear distinction between revoking access and deleting history. Expire worker-session secrets independently; report retention has no age-based deletion. Do not silently retain raw browser drafts indefinitely. Backups follow existing approved retention; no claim that deleting a live record erases old backups.

## Outputs and completion

Deliver native supervisor controls, locally hosted worker forms, schema/auth/grant/review implementation, automated and actual UI coverage, operator setup/certificate/network guide, worker-facing instructions, limitations, updated build status and a verified installer. Push reviewed source changes to GitHub at the end of implementation; keep secrets and work data out of the repository.

The software increment is complete when a synthetic worker can submit each kind of report through their own limited session and Daniel can review/apply selected planning changes without exposing private context, losing drafts, double-counting work or writing to TaskDock. Real-world readiness additionally requires approved browser trust/network and an observed worker pilot. Keep those statuses separate; do not enable real access merely because the isolated tests pass.

## Execution result

Implemented the isolated identity/grant/report foundation, bundled worker forms, native sharing/review inbox and selected planning application. See the [verification report](../reports/worker-updates-2026-11-02.md), [operator guide](../WORKER-UPDATES.md) and [actual installer verification](../reports/installer-preview-13.json). Work-host records/pairing were preserved and default worker access stays disabled. Phase 5 (real approved-network/browser pilot) remains outstanding; no worker invitations were sent.

## Accepted scope updates — November 2

The owner explicitly requested reports be kept forever and used to help predict repairs. Remove automatic report-age pruning and migrate any finite settings to indefinite retention. Invitation/session expiry remains separate. Add independently reviewed repair context, an evidence-linked patterns view, calibrated effort comparisons using verified complete-repair times, and approved local-model chat/estimate context. Exclude partial/unknown effort, duplicate linked repairs, the current task itself and superseded corrections. Preserve uncertainty and source references; do not claim exact future failure dates, automatically order parts, schedule staff or evaluate employee intelligence. The original report remains durable independently of generated summaries.
