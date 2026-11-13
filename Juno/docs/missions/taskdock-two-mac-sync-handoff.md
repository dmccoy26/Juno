# TaskDock mission — Pair and sync two Macs as simply as Juno

## Outcome

I use TaskDock on a wired work Mac Studio and an M5 MacBook Air on Wi-Fi. The work Mac should host my TaskDock workspace and keep its provider connections. I should be able to open the laptop away from work, see the last complete copy, make supported edits, and have them sync when the work Mac is reachable again. I should be able to tell at a glance whether an edit is saved on the laptop, synced to the work Mac, or waiting for my decision.

Apply this workflow to the supported Beta 3 and Beta 4 builds. Start by mapping each build’s current Settings, device sync, and team hub to the flow below. Use the existing device protocol, journal, snapshot, recovery, and provider execution code where compatible. If a protocol change is necessary, version it and keep supported existing pairings working.

## How Juno did it

1. **One host.** In Juno → Settings → Computers & sync, the work Mac opts into hosting. Juno starts a dedicated HTTPS listener and advertises its private network address. The laptop initiates the connection. It needs no listener or provider setup.
2. **One invitation file.** The work Mac exports a small `.junopair` file. It contains a format version, HTTPS address, SHA-256 fingerprint of the host’s certificate, and a high-entropy invitation that expires after 15 minutes and works once. A fresh export invalidates older unused invitations. Transfer the file directly between the two Macs. Creating it on the work Mac is the owner’s authorization to pair a device that has the file.
3. **Import and authenticate.** The Air imports the file and contacts the address in it. Juno checks the exact TLS certificate fingerprint before sending the invitation. The host consumes the invitation and provisions a revocable device credential for the same workspace. The laptop stores that credential in its device-only Keychain and saves the address, certificate fingerprint, and workspace and device identifiers in its profile. Certificate trust is scoped to Juno’s connection.
4. **Keep a complete offline copy.** Juno validates the workspace and format of the downloaded snapshot and saves it atomically in the user’s Application Support folder. It shows the time of the last complete copy. The cache is keyed by owner and host certificate fingerprint, so an address change alone does not give it a different cache identity. Supported diary and memory edits update the laptop view and are saved to a durable queue with operation IDs. The work Mac still handles services such as AI replies.
5. **Reconnect and synchronize.** The laptop checks in automatically while Juno is running, and the user can also click **Reconnect and synchronize**. The laptop sends queued edits first. It clears each edit only after acknowledging the host result locally. Stable operation IDs let the host return the prior result if a response was lost. A conflict pauses the affected queue for review. Once the queue is clear, Juno fetches and validates a fresh snapshot and replaces the previous copy. An interrupted connection keeps the last usable copy and outstanding edits.
6. **Keep troubleshooting specific.** Juno initially advertised a `.local` hostname, and the original certificate covered localhost only. We repaired the certificate coverage, preferred the work Mac’s reachable private IPv4 address in the invitation, and retained certificate pinning. The Air reached the wired Studio on TCP 8443 and then synced. The host address in a pairing file must be reachable from the laptop. Having both devices on campus does not establish that the Wi-Fi segment can reach the wired Mac.

The M5 Air walkthrough on Juno preview.35 confirmed a successful manual reconnect, no queued edits, and a spoken “Offline copy synced” result in VoiceOver. A separate disposable test covered a real host outage, app restart, and replay of queued diary and memory changes. The physical Air result did not exercise replay of a pending edit.

## Build the TaskDock experience

### 1. Use one Settings entry for my two Macs

Use **Settings → Sync my Macs** as the entry point. On an unpaired installation offer **Host this workspace** and **Connect to my work Mac**. Hosting should detect and show a suitable private address and the computer’s name. Keep network interface, address and port selection under **Connection details** for cases where the detected address is unreachable. The laptop should get the port and address from the invitation. Use TaskDock’s own port and show the actual endpoint in diagnostics.

On the work Mac, **Create pairing file…** should explain where to send it and when it expires. On the laptop, **Open pairing file…** should show the work Mac’s name and workspace and then prepare the join. Use one short-lived, single-use file carrying the endpoint and pinned certificate fingerprint, with the existing pairing proof inside the file where compatible. Preserve TaskDock’s authentication, request signing, revocation, and replay protections. If TaskDock’s existing security model still requires approval on the host, show one named pending device with an **Approve** button. Keep manual fingerprint and code entry available only for a workflow that actually needs it.

Show progress for reaching the work Mac, verifying the connection, and downloading the workspace. Name failures separately. Give the user a fresh-invitation action for expiry, network details for an unreachable host, and a verified re-pair path for a changed certificate. Address repair on the same workspace should retain the cache and queue. Treat host identity changes as an explicit recovery step with the old workspace and queued edits preserved.

### 2. Preserve the laptop’s existing work

For a new or empty laptop, joining should be a straightforward continuation of pairing. If the laptop already contains independent work, show a short comparison and require a verified backup and explicit confirmation before activating the host workspace. Provide a way to keep or export unique work. Cancel, interruption, or failed validation must leave the prior workspace usable. Resume an interrupted join safely and avoid taking the same backup or replacing the workspace twice.

Use TaskDock’s logical snapshot and local SQLite storage on each Mac. Keep workspace and device IDs stable. Define which existing TaskDock fields can be read or edited offline, including tasks, status changes, notes and other records supported by the current sync schema. Make anything outside that scope clear before a user tries to save it. Keep provider credentials, private attachments, backups, and device preferences outside the shared dataset. Keep provider actions, recurrence, and calendar publication under the work Mac’s authority. Show external actions as pending until their outcome is confirmed.

### 3. Make offline work and sync visible

Show the host name, **Connected** or **Offline**, **Last complete offline copy**, and the queued-edit count in one place. Put **Reconnect and synchronize** beside that information. Announce the result once for manual sync in VoiceOver. A successful network check alone must never update the last-copy timestamp.

Save supported offline edits immediately and durably with the operation or transaction identity and revision information needed by TaskDock’s existing journal. On reconnection, send unacknowledged transactions in dependency order and fetch host changes. Keep the last complete local view usable if the transfer fails. Preserve existing independent-field merge behavior. For a competing edit, show the task, the laptop value, and the work Mac value with a clear review action. Preserve both values until the user resolves the conflict. Use TaskDock’s existing history and deletion protections so retries cannot duplicate updates or revive deleted tasks.

Keep owner laptop pairing separate from worker enrollment. An owner invitation is for another Mac used by the same owner. A worker invitation must use the existing worker permissions and show only the work assigned or shared with that worker. Juno’s TaskDock read-only connection is a separate integration and should continue to work through the change.

### 4. Preserve security and recovery without adding routine setup steps

Keep hosting opt-in on the approved private network. Use HTTPS and verify the pinned host certificate before transmitting the invitation or credentials. Keep the dashboard and host administration local and keep secrets out of logs, snapshots, backups shared with other devices, and source control. Store long-lived credentials using TaskDock’s protected device storage. Treat the invitation like a temporary password.

Put paired-device revocation on the host screen. Document what a revoked laptop can still see before it reconnects and how TaskDock handles previously cached data and unsent work after it learns about revocation. Never promise remote erasure while the laptop is disconnected. Existing pairings, queued edits, conflicts and saved workspace data must survive the supported app upgrades.

## Acceptance

| Test | Pass condition |
| --- | --- |
| New laptop | A user can enable hosting, transfer one file, open it on the Air, and join without typing the address, port, code, or fingerprint. Record the steps and elapsed time against the old flow. |
| Existing workspace on laptop | Cancel preserves the old workspace. A verified backup and review precede replacement. Interrupt the join and verify that resuming preserves both the backup and workspace integrity. |
| Wired Studio and Wi-Fi Air | The Air reaches the advertised private endpoint on the approved network. If discovery fails but the IP works, pairing still succeeds. If routing is blocked, the app identifies reachability as the problem. |
| Offline work and restart | With the host unreachable, create a disposable task, change its status and add a note. Quit and reopen the Air. Verify the local edits and queue survive, then reconnect and verify each change exactly once on the Studio. |
| Lost response and conflicts | Interrupt sync after the host commits but before the Air receives the result. Retry and confirm one effect. Change the same field on both Macs and verify review preserves both values. Also verify an interrupted snapshot retains the previous copy and timestamp. |
| Trust and access | Expired, reused and malformed invitations fail. Wrong certificate fails before any credential is sent. Unpaired and revoked devices cannot fetch records. Worker credentials cannot join the owner workspace. |
| Sleep, upgrade and accessibility | Verify sleep/wake reconnect, an upgrade with pending edits and an existing pairing, and clear results with keyboard navigation and VoiceOver. Test the supported Beta 3 and Beta 4 combinations and document version requirements. |

Use disposable records for destructive cases. Deliver the revised setup guide, before-and-after pairing walkthrough, automated regression results, and a physical two-Mac test record with the builds, outcomes and remaining limits. Keep the physical verification separate from the simulated results.

## References

- Juno desktop pairing, certificate pinning, Keychain, offline archive and queue in `desktop/Shared.swift`.
- Juno host and invitation lifecycle in `backend/src/juno/shared_host.py`. Regression checks in `scripts/verify_shared_host.py` and `scripts/verify_offline_client.py`.
- Juno [HTTPS/IP repair evidence](../reports/https-ip-repair-preview-5.json) and [M5 Air verification](2026-11-12-15-native-design-review.md#preview35-sync-and-reminder-acceptance).
- TaskDock’s existing `docs/device-sync-setup.md`, `docs/direct-device-sync.md`, and `docs/team-hub-protocol-v1.md`.
