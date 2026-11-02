# Worker updates — preview.15

Juno remains a native Mac application. Workers use a small browser portal hosted by the approved work Mac; they do not install Juno. The portal is disabled by default, and it is separate from laptop pairing.

## What Daniel can do now

Open **Worker updates** in the sidebar (Command-9). Expand **Worker access** to see certificate readiness, indefinite report retention and worker identities. Select an existing saved schedule person and add their portal identity. This does not change shifts, active/candidate status or weekly limits.

TaskDock controls task assignment. With worker access enabled, an active portal worker whose name uniquely matches the TaskDock assignee gets that task automatically after Juno refreshes TaskDock. No second task assignment is needed. Names must match exactly apart from case/spacing. In **Worker access**, use **TaskDock identity** once when the source uses a different name, email or stable identifier. Stable identifiers require this explicit match; duplicate names are never guessed. Matches are workspace-bound. Register and invite each intended worker first; no identity or message is created automatically.

Assigned tasks stay available while assigned, rather than expiring after seven days. Reassignment, task removal, worker revocation or source-permission withdrawal removes derived access when Juno receives that change. Workers reconnect/reload their portal to see the new list; this is Juno’s dated TaskDock copy, not a live upstream subscription. Browser sessions still expire after seven days. Change assignment in TaskDock, or revoke the worker’s entire portal access in Juno.

From a task in **Plan** or **TaskDock**, **Request worker update…** offers the existing assigned-worker link when available. **Request help on a task…** remains for temporary collaboration. Search by title, room/room alias, equipment, parent, description or task reference; rows distinguish similar names with room, status, due date, parent and reference. Preview and Cancel stay at the bottom of the sheet.

New manual shares and automatically assigned tasks include all supported TaskDock business details available under its current sharing policy: description/outcome, location/equipment, requester/contact, impact/priority/status/dates, troubleshooting/blockers/dependencies, assignment, tags/custom values, source references, included updates and already-saved permitted history. Juno never triggers upstream history reads for a worker. Additional information that TaskDock has not shared or Juno has not fetched remains unavailable. Optional worker instructions are separate. Private Juno chat, memory, diary, reviews and employee assessments are excluded. A confirmed same-workspace Juno room can supplement the source room.

The preview shows what the worker will receive. Full-context shares render against the latest permitted saved snapshot; earlier limited-field grants remain limited until replaced. Manual collaboration links retain their selected 1–30-day expiry. Re-sharing manually replaces the earlier manual grant for that worker/task; it does not change TaskDock assignment.

After approved hosting is enabled, create a worker invitation and copy it to the intended recipient yourself. Invitations last 24 hours, are one-use and enroll a worker-only browser session lasting at most seven days. Verify the recipient before sharing: possession of an invitation establishes the session; it is not institutional single sign-on or independent identity verification. No email/Slack message is sent by Juno. A copied task link alone cannot enroll a browser or grant another worker access.

## What workers can do

- Update a shared task: work tried, current state, time spent/remaining, blockers/help and handoff.
- End-of-shift check-in: accomplishments, interruptions and handoff, with optional time.
- Report other work: unexpected or unlinked work needing supervisor attention.

They review the form before submitting and receive a dated receipt. A report of completion is distinct from Daniel verifying completion. Zero remaining time can be reported, but cannot be converted into a zero-length schedulable estimate. Unknown time/blockers remain unknown. Work dates default to today in America/Chicago; visible times use AM/PM.

The open page retains text during a failed request. **Reconnect without losing my draft** renews page/session state when the session is still valid. A new invitation may be needed if access expired; it can be opened in another tab, then reconnect the draft page. Closing/reloading an unsubmitted form loses its draft: there is no persistent offline browser queue in this release. After an uncertain submission, retry the same reviewed payload to recover its receipt; it is not counted twice. Corrections are new attributed reports linked to the original receipt, with the same task and update type. A withdrawn task share cannot be used to submit a correction; ask the supervisor for a new shared task/update instead.

Workers see only currently authorized excerpts and their own recent receipts, not supervisor review notes or other workers' information. Sign out on shared devices. A worker cannot choose another identity from a name list. Browser forms do not record official payroll/timekeeping.

## Reviewing reports

The native inbox filters unread, follow-up and all updates, with search and older-page loading. Select a report to read the worker's original words and attribution. Review outcomes are Reviewed, Needs follow-up, Completion verified by me, or Dismissed. Save a private note if useful; it is not shown in worker receipts.

**Review planning changes…** displays current versus reported values. Choose fields and explicitly save: actual minutes, a nonzero remaining estimate, blocker, next action or handoff. Minutes **replace** a reviewed value; they are never summed automatically. Reconcile overlap between shift and task reports first. Unknown values cannot clear saved facts. Stale planning/report revisions are rejected; re-open the comparison after reviewing changes. Save/discard an existing Plan draft first. An already-applied field cannot be applied again from the same report; further changes require normal planning review. A superseding correction blocks applying/verifying the old report.

Unexpected/shift reports are unlinked evidence; record follow-up in the review note or copy a summary to TaskDock manually. This release does not create a TaskDock task automatically or offer a new write-back API. TaskDock's original status stays separate, including after local verified completion. **Copy TaskDock summary** explicitly labels the summary as not synchronized.

Revoke a worker to invalidate all their sessions, invitations and task shares. Revoke one manual share to withdraw that excerpt. For an automatically assigned task, change assignment in TaskDock. Reports remain reviewable indefinitely; already-viewed information cannot be erased from screenshots or another person's memory. TaskDock sharing withdrawal permanently revokes affected worker grants and clears their cached excerpts. Reports independently written by workers remain under the report-retention policy.

## Before real worker access: IT setup

The work Mac must remain awake, Juno open and campus wired/Wi-Fi routing permitted. No public tunnel, router change, certificate-trust change or real worker enrollment is performed by this feature automatically. Off-campus access requires an institution-approved network path.

The existing paired-laptop certificate is pinned by Juno, not automatically trusted by browsers. IT must provide an approved hostname, a certificate/full chain for that hostname and a matching private key. Alternatively, IT can provision a managed institutional CA/trust arrangement on all participating browsers/devices. Never bypass a browser certificate warning and never distribute the private key.

With Juno quit, IT places a configuration file at `<Juno data root>/worker-portal/https.json`:

```json
{
  "address": "https://juno-work.example.edu:8444",
  "certificate": "/absolute/approved/location/fullchain.pem",
  "private_key": "/absolute/approved/location/private-key.pem",
  "ca_bundle": "/absolute/approved/location/institution-ca.pem"
}
```

These are examples, not configured addresses. Omit `ca_bundle` when the chain verifies using the bundled Python runtime's default trust roots. For a private institutional CA, provide its approved CA bundle explicitly and have IT provision browser trust separately. This does not install trust in macOS or browsers. Private-key permissions must exclude group/other access (`0600`); the configuration and parent data directory should likewise be private. Use a dedicated unprivileged port (1024–65535), normally 8444, separate from laptop pairing at 8443. The hostname must resolve to this Mac on the approved network.

Data roots remain unchanged: the work development installation uses the checkout's `.local`; the portable app uses `~/Library/Application Support/Juno`. Configure the root belonging to the actual approved host. Do not enable another host on the laptop or move/merge databases to set this up.

On reopening Juno, Worker updates checks certificate chain, validity, hostname and key compatibility entirely in memory. It still stays disabled until Daniel explicitly enables worker access. Changed HTTPS configuration/certificate material requires disabling and re-enabling the portal. Test an actual worker browser/network before sharing real tasks. The dedicated listener permits only worker pages/API routes and remote IPv4 clients in `10.0.0.0/8` (plus loopback diagnostics); it exposes no owner APIs, pairing, credentials or documentation. Disabling access invalidates sessions/invitations and stops its listener when no enabled owner remains, without changing paired-laptop hosting.

## Retention and limitations

Reports are kept indefinitely. There is no age-based report pruning or expiry setting; even older saved settings are migrated to indefinite retention. Worker invitations/sessions and manual collaboration shares expire independently. Assigned-task access follows TaskDock assignment. Deleting a report is an explicit, permanent live-storage action. Previously applied planning facts, minimal audit events and old backups remain under their existing policies. Revoking worker access does not delete reports.

### Repair history and predictions

In **Review update**, use **Use this report for repair history and future estimates** to confirm room/equipment, repair type and symptom summary. This is independently reviewed history, retained even after a task share expires. Turn it off to exclude a report from prediction evidence without deleting the report. Shift totals are not individual repair samples.

**Repair history & patterns** groups included reports by normalized room, equipment and repair type, with links to supporting records. Repeated reports suggest investigation/preventive checks; they do not establish separate hardware failures or predict a failure date. A calibrated effort range needs at least three **Completion verified by me** reports whose minutes you explicitly confirmed cover the complete repair. Partial/unknown time is excluded; multiple reports linked to the same task count once. The current task is excluded from its own future estimate. Reviewed corrections supersede prior evidence; unreviewed corrections suspend the earlier record from comparisons until reviewed.

Plan's duration suggestion uses comparable verified repair effort when enough evidence exists, with source/sample counts. Comparisons are broad category hints and need equipment/scope review. The approved local model can also read bounded reviewed repair excerpts in chat and estimates: what was tried, blockers, next action and handoff. No external model or model training/upload is introduced. The original report stays authoritative; a model summary is advice. Corrected/deleted/excluded evidence invalidates derived replies rather than preserving stale claims. Reports and private supervisor notes are not employee intelligence/performance scores.

Analysis currently scans at most the latest 2,000 included repair reports; chat receives at most six relevant excerpts and estimates at most six comparable examples. The UI labels a partial analysis when that limit is reached. Older reports remain stored and can be paged in the native inbox. No age limit is applied to retained records.

Portal administration/review is host-only in this release. Worker reports are not added to the laptop cache; accepted planning facts use the existing owner-only synchronization behavior. Existing laptop memory/diary offline edits and pairing remain unchanged.

Not included: photos/attachments, Slack/email ingestion, institutional SSO, payroll, Juno-originated task assignments or automatic scheduling, automatic TaskDock updates or persistent offline worker forms. The portal is functional without an LLM. Juno does not assess intelligence or turn missing reports into evidence of poor performance.

## Verification boundaries

See the [mission report](reports/worker-updates-2026-11-02.md) for actual test results. Synthetic browser fixtures deliberately use a loopback-only adapter with fake hosting; they are not HTTPS browser-trust acceptance and are not bundled in the app. Separate tests exercise the actual HTTPS listener/cookies with a temporary CA trusted only by the test client. Real campus certificate/network readiness and a supervised worker pilot remain outstanding.

## Work-Mac IP configuration — November 2

The owner requested `10.3.66.50` and remote access restricted to `10.*.*.*`. The worker endpoint is `https://10.3.66.50:8444/worker`; laptop pairing remains separate at port 8443. Literal-IP worker listeners bind to that address. The worker HTTP boundary accepts only actual 10/8 peers or local loopback diagnostics, ignores forwarded-IP claims, and rejects other private ranges, public IPs and remote IPv6. This is an application access restriction, not a system-wide firewall rule.

A dedicated private worker CA and exact-IP server certificate can be used for this local setup. This does not make the CA publicly/browser trusted: each participating device needs the public CA certificate installed through its approved trust process. Never bypass a browser warning. The configured CA has an IP name constraint of 10/8 and a reserved `.invalid` DNS constraint; the actual server leaf has only the IP subject alternative name `10.3.66.50`. Root and server private keys stay in the work Mac's private Juno data root and must never be distributed. Public certificate files and the fingerprint are provided separately for device enrollment. This trust setup is independent from Juno's laptop-pairing certificate.
