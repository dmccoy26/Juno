# Worker updates — preview.13

Juno remains a native Mac application. Workers use a small browser portal hosted by the approved work Mac; they do not install Juno. The portal is disabled by default, and it is separate from laptop pairing.

## What Daniel can do now

Open **Worker updates** in the sidebar (Command-9). Expand **Worker access** to see certificate readiness, indefinite report retention and worker identities. Select an existing saved schedule person and add their portal identity. This does not change shifts, active/candidate status or weekly limits.

From a task in **Plan** or **TaskDock**, choose **Request worker update…**. Select the worker and the fields to share, add optional instructions and preview the exact excerpt. The minimal defaults are title and room (preferring the room you confirmed in Juno for that workspace); contact details, raw TaskDock records, chats, memories and private employee notes are excluded. Creating the link requires approved HTTPS to be running. Re-sharing a task with the same worker replaces the old grant; it never silently broadens an earlier grant.

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

Revoke a worker to invalidate all their sessions, invitations and task shares. Revoke one task to withdraw that excerpt. Reports remain reviewable indefinitely; already-viewed information cannot be erased from screenshots or another person's memory. TaskDock sharing withdrawal permanently revokes affected worker grants and clears their cached excerpts. Reports independently written by workers remain under the report-retention policy.

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

On reopening Juno, Worker updates checks certificate chain, validity, hostname and key compatibility entirely in memory. It still stays disabled until Daniel explicitly enables worker access. Changed HTTPS configuration/certificate material requires disabling and re-enabling the portal. Test an actual worker browser/network before sharing real tasks. The dedicated listener permits only worker pages/API routes and local-network client addresses; it exposes no owner APIs, pairing, credentials or documentation. Disabling access invalidates sessions/invitations and stops its listener when no enabled owner remains, without changing paired-laptop hosting.

## Retention and limitations

Reports are kept indefinitely. There is no age-based report pruning or expiry setting; even older saved settings are migrated to indefinite retention. Worker invitations/sessions and task access still expire independently. Deleting a report is an explicit, permanent live-storage action. Previously applied planning facts, minimal audit events and old backups remain under their existing policies. Revoking worker access does not delete reports.

### Repair history and predictions

In **Review update**, use **Use this report for repair history and future estimates** to confirm room/equipment, repair type and symptom summary. This is independently reviewed history, retained even after a task share expires. Turn it off to exclude a report from prediction evidence without deleting the report. Shift totals are not individual repair samples.

**Repair history & patterns** groups included reports by normalized room, equipment and repair type, with links to supporting records. Repeated reports suggest investigation/preventive checks; they do not establish separate hardware failures or predict a failure date. A calibrated effort range needs at least three **Completion verified by me** reports whose minutes you explicitly confirmed cover the complete repair. Partial/unknown time is excluded; multiple reports linked to the same task count once. The current task is excluded from its own future estimate. Reviewed corrections supersede prior evidence; unreviewed corrections suspend the earlier record from comparisons until reviewed.

Plan's duration suggestion uses comparable verified repair effort when enough evidence exists, with source/sample counts. Comparisons are broad category hints and need equipment/scope review. The approved local model can also read bounded reviewed repair excerpts in chat and estimates: what was tried, blockers, next action and handoff. No external model or model training/upload is introduced. The original report stays authoritative; a model summary is advice. Corrected/deleted/excluded evidence invalidates derived replies rather than preserving stale claims. Reports and private supervisor notes are not employee intelligence/performance scores.

Analysis currently scans at most the latest 2,000 included repair reports; chat receives at most six relevant excerpts and estimates at most six comparable examples. The UI labels a partial analysis when that limit is reached. Older reports remain stored and can be paged in the native inbox. No age limit is applied to retained records.

Portal administration/review is host-only in this release. Worker reports are not added to the laptop cache; accepted planning facts use the existing owner-only synchronization behavior. Existing laptop memory/diary offline edits and pairing remain unchanged.

Not included: photos/attachments, Slack/email ingestion, institutional SSO, payroll, automatic assignments/scheduling, automatic TaskDock updates or persistent offline worker forms. The portal is functional without an LLM. Juno does not assess intelligence or turn missing reports into evidence of poor performance.

## Verification boundaries

See the [mission report](reports/worker-updates-2026-11-02.md) for actual test results. Synthetic browser fixtures deliberately use a loopback-only adapter with fake hosting; they are not HTTPS browser-trust acceptance and are not bundled in the app. Separate tests exercise the actual HTTPS listener/cookies with a temporary CA trusted only by the test client. Real campus certificate/network readiness and a supervised worker pilot remain outstanding.
