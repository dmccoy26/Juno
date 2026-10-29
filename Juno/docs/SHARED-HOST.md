# Work Mac host and offline laptop — preview 4

Dan approved this Mac as Juno's shared system and authorized a laptop cache, including offline memory and diary edits. This changes the earlier synthetic-only storage restriction for this specific local deployment. It does not authorize cloud storage, remote model providers or public hosting.

## Current host

The development Juno app on this Mac is configured to start its encrypted host at:

`https://<this-Mac-local-name>.local:8443` (the actual address is shown in Computers)

Juno must remain open and this Mac must remain awake. Closing the window leaves the Mac app running; quitting Juno or sleeping/shutting down the Mac makes the host unavailable. Hosting starts again when Juno starts. This version does not install an always-running daemon or change sleep, firewall, router or login settings.

The current host uses the existing development data in `/Users/dmccoy/Ai/Juno/.local`. Installing the packaged app on this desktop would use its separate `~/Library/Application Support/Juno` data. Do not switch hosts to an empty packaged database expecting the development data to migrate automatically.

## Pair the laptop

1. Install Juno `0.1.0-preview.4` on the laptop and open it. The laptop needs no separate LM Studio model for shared-host chat.
2. On this work Mac, choose **Computers → Create laptop pairing file…**.
3. Transfer the `.junopair` file directly to your own laptop, for example with AirDrop. It contains an invitation secret: do not paste it into chat, email it to others, publish it, or put it in a support report.
4. Within 15 minutes, choose **Computers → Import work Mac pairing file…** on the laptop. Both Macs must be reachable on the local network.
5. Juno validates the host's pinned certificate, redeems the invitation once, stores the laptop's separate credential in Keychain, and downloads an owner-scoped offline copy.

A new invitation invalidates prior unused invitations. Reusing or redeeming an expired invitation fails. Each paired device can be revoked from the host's Computers screen. After a known revocation, the laptop clears cached record pages while retaining unsynchronized edits for recovery. A laptop that remains offline cannot receive a remote revocation or remote erase; local device/account protection still applies.

Standalone laptop records remain separate and are not automatically uploaded or merged. **Use standalone Juno on this Mac** switches back to that independent workspace. Existing shared queues remain separately saved; importing a new invitation for the same host identity/owner can recover them. Pending edits block switching to a different host identity until they are exported or synchronized.

## Offline behavior and reconnection

- Previously downloaded conversations, memories, dated check-ins and the work Mac's active TaskDock snapshot can be read offline.
- New memories, memory corrections/deletions, new daily check-ins, answers and diary edits are saved to a durable local queue. An incomplete save or local revision mismatch does not claim success.
- AI replies need the work Mac and its local model. Juno does not substitute a cloud model or claim an offline reply was generated.
- The header shows connection state, the last complete offline-copy time and queued edit count. The client checks availability about every 30 seconds, refreshes a complete copy at most every five minutes while normally connected, and synchronizes queued edits when it reconnects. **Reconnect / sync** requests this immediately.
- Edits use stable operation IDs. The host commits each operation and its replay receipt together, so a dropped response can be retried without creating another memory or duplicating a diary action. IDs for offline-created records are mapped before dependent operations run.
- Existing record edits carry an expected revision. If the desktop changed or deleted a record, that synchronization attempt stops and the queued payload stays on the laptop. Later reconnect checks may retry the unchanged operation, but cannot overwrite the desktop version. It does not silently overwrite the desktop. The Computers screen lets you inspect/export queued edits and explicitly discard the queue to reload host versions. An inline merge editor is not implemented; resolve the conflict using the exported contents and current host records, then reapply the desired changes.
- Cached assistant replies are hidden after offline context edits. The host also invalidates replies and redacts old replay receipts when canonical context is corrected or deleted.

The offline export includes at most 10,000 memories, 1,000 conversations, 50,000 messages total, 10,000 check-ins and the selected TaskDock snapshot/history. The encoded response is limited to 64 MB; an oversized or failed export retains the prior complete copy. It is a cache and edit queue, not a separate canonical task system or backup service.

## Storage and transport

The host keeps PostgreSQL on a private Unix socket. Only the opt-in HTTPS service listens on the LAN, restricted to loopback/private/local addresses and an explicit route allowlist. Remote clients cannot administer hosts/devices, configure model endpoints, supply TaskDock credentials or trigger TaskDock refreshes. TaskDock remains connected locally on the work Mac; its dedicated token is not copied to the laptop.

A pairing file supplies the exact host certificate fingerprint as the out-of-band trust anchor. Native requests use an ephemeral pinned TLS session, reject another certificate and reject redirects. No certificate is installed into system-wide trust. Host private keys/settings are in the private `shared-host` state directory; invitation/device credentials are hashed in PostgreSQL. Keychain credentials and invitation codes are excluded from the offline export and model context.

A laptop copy and queued edits are stored in its application-support directory, scoped by host certificate/address and owner, with private directory/file permissions. Queues and full-copy replacement use atomic writes. A different owner or host identity does not merge into an existing copy. Keep normal Mac account/device protections enabled; application-specific at-rest encryption is not added in this preview.

## Verification and remaining acceptance

- 47 automated backend tests, including invitation lifetime/replay/replacement, device revocation, LAN administration boundaries, owner isolation, atomic idempotency, revision conflicts, diary chains and receipt redaction.
- `scripts/verify_offline_client.py` compiles the actual native cache/queue code and verifies offline memory/diary edits, restart persistence, dependent-ID mapping, local conflict retention, safe stale-reply handling, search and private file permissions. It also compiles the actual JunoStore and verifies immediate offline reads/create/edit/delete/check-in saves and failure when the pinned session is missing.
- `scripts/verify_shared_host.py` compiles the actual native TLS/cache/queue code and uses a disposable PostgreSQL owner and real HTTPS host. It verifies wrong-certificate rejection, native pairing, Keychain storage, an actual stopped-host outage, offline edits, a separate client process restart, host restart, replay-safe sync and final host data.
- The native Computers screen confirmed this Mac's live host address and enabled state. The live TLS endpoint rejected unauthenticated access.
- The packaged installer verifier checks shared-host TLS startup, one-use invitations, owner-scoped export, replay-safe offline operations, forbidden remote administration and revocation, alongside existing migration/runtime tests.

Actual M5 laptop installation, campus network reachability, AirDrop/import through both real native apps and multi-day use still require user acceptance. The app is ad hoc signed and the installer remains unsigned/not notarized. Shared preferences, a background host daemon, formatted TaskDock rich text, automatic TaskDock source refresh, calendar integration and HumanLab native acceptance remain outside this increment.
