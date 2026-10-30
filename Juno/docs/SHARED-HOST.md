# Work Mac host and offline laptop — preview 7

Dan approved this Mac as Juno's shared system and authorized a laptop cache, including offline memory and diary edits. This changes the earlier synthetic-only storage restriction for this specific local deployment. It does not authorize cloud storage, remote model providers or public hosting.

## Current host

The development Juno app on this Mac is configured to start its encrypted host at:

`https://<work-Mac-private-IP>:8443` (the actual IP address is shown in Computers)

Juno must remain open and this Mac must remain awake. Closing the window leaves the Mac app running; quitting Juno or sleeping/shutting down the Mac makes the host unavailable. Hosting starts again when Juno starts. This version does not install an always-running daemon or change sleep, firewall, router or login settings.

The current host uses the existing development data in `/Users/dmccoy/Ai/Juno/.local`. Installing the packaged app on this desktop would use its separate `~/Library/Application Support/Juno` data. Do not switch hosts to an empty packaged database expecting the development data to migrate automatically.

## Pair the laptop

1. Install Juno `0.1.0-preview.7` on the laptop and open it. The laptop needs no separate LM Studio model for shared-host chat.
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
- Existing record edits carry an expected revision. A rejected edit stays queued behind a durable conflict block. In Computers, compare the queued chain with the current host record, then explicitly apply it against that reviewed revision or use the host version for that record. Unrelated queued work is preserved. Deleted-memory text can be recovered as a new record. A freeform field-by-field merge editor is not implemented; export/copy text before discarding any changes you want to keep.
- Cached assistant replies are hidden after offline context edits. The host also invalidates replies and redacts old replay receipts when canonical context is corrected or deleted.

The offline export includes at most 10,000 memories, 1,000 conversations, 50,000 messages total, 10,000 check-ins and the selected TaskDock snapshot/history. The encoded response is limited to 64 MB; an oversized or failed export retains the prior complete copy. It is a cache and edit queue, not a separate canonical task system or backup service.

## Storage and transport

The host keeps PostgreSQL on a private Unix socket. Only the opt-in HTTPS service listens on the LAN, restricted to loopback/private/local addresses and an explicit route allowlist. Remote clients cannot administer hosts/devices, configure model endpoints, supply TaskDock credentials or trigger TaskDock refreshes. TaskDock remains connected locally on the work Mac; its dedicated token is not copied to the laptop.

New pairing files prefer the work Mac’s private IPv4 address, avoiding Bonjour discovery across wired/Wi-Fi networks. The certificate includes that IP, the Mac hostname and localhost as subject alternative names. Existing certificates are preserved on normal restarts; this repair replaced the unused initial localhost-only certificate after confirming no laptop had paired and invalidated unused invitations.

A browser still treats this private self-signed certificate as untrusted unless separately trusted; Juno uses the pairing-file pin and does not install system-wide trust. The root HTTPS route contains only a connection-status message, not a web interface.

A pairing file supplies the exact host certificate fingerprint as the out-of-band trust anchor. Native requests use an ephemeral pinned TLS session, reject another certificate and reject redirects. No certificate is installed into system-wide trust. Host private keys/settings are in the private `shared-host` state directory; invitation/device credentials are hashed in PostgreSQL. Keychain credentials and invitation codes are excluded from the offline export and model context.

A laptop copy and queued edits are stored in its application-support directory, scoped by pinned host certificate and owner (legacy address-scoped files migrate on successful decoding), with private directory/file permissions. Queues and full-copy replacement use atomic writes. A different owner or host identity does not merge into an existing copy. Keep normal Mac account/device protections enabled; application-specific at-rest encryption is not added in this preview.

## Verification and remaining acceptance

- 59 automated backend tests in preview 7, including invitation lifetime/replay/replacement, device revocation, LAN administration boundaries, owner isolation, atomic idempotency, revision conflicts, diary chains and receipt redaction.
- `scripts/verify_offline_client.py` compiles the actual native cache/queue code and verifies offline memory/diary edits, restart persistence, dependent-ID mapping, local conflict retention, safe stale-reply handling, search and private file permissions. It also compiles the actual JunoStore and verifies immediate offline reads/create/edit/delete/check-in saves and failure when the pinned session is missing.
- `scripts/verify_shared_host.py` compiles the actual native TLS/cache/queue code and uses a disposable PostgreSQL owner and real HTTPS host. It verifies strict TLS validation for the advertised IP and hostname, wrong-certificate rejection, native pairing using the IP, Keychain storage, an actual stopped-host outage, offline edits, a separate client process restart, host restart, replay-safe sync and final host data.
- The native Computers screen confirmed this Mac's live host address and enabled state. The live TLS endpoint rejected unauthenticated access.
- The packaged installer verifier checks shared-host TLS startup, one-use invitations, owner-scoped export, replay-safe offline operations, forbidden remote administration and revocation, alongside existing migration/runtime tests.

Dan confirmed actual laptop sync and wired/Wi-Fi reachability. Actual laptop offline-edit/reconnect and multi-day use still require acceptance. The app is ad hoc signed and the installer remains unsigned/not notarized. Shared preferences, a background host daemon, formatted TaskDock rich text, automatic TaskDock source refresh, live calendar OAuth and HumanLab native acceptance remain outside this increment.

## Wired/Wi-Fi connection troubleshooting

On the laptop, `nc -vz <work-Mac-IP> 8443` tests TCP access without sending any credentials. Success means the network path is open; timeout/refusal indicates a network/firewall/listener problem rather than a certificate trust problem. Use a fresh pairing file after this certificate repair. Preview 5 reports DNS, TCP reachability, identity verification and expired-invitation failures separately. Network isolation between wired and wireless VLANs cannot be repaired by changing the certificate; have the network administrator allow the intended local connection if it is blocked. No firewall protection is disabled by Juno.

## Preview 6 recovery update

Dan confirmed successful real wired/Wi-Fi laptop synchronization on October 29. Real laptop offline editing/reconnection still needs acceptance; disposable native process/TLS tests cover that path automatically.

Preview 6 stores acknowledged temporary-to-server IDs in the atomic archive and rewrites cached record IDs before requesting the next complete export. This survives a failed export followed by a client restart. Known revocation removes host cache pages but saves unsynchronized edits on disk. A legacy archive upgrades without clearing its queue; unreadable archives are preserved and activation fails visibly.

The cache identity now follows the verified host certificate and owner rather than its address. A fresh invitation for that same identity can move from hostname to IP, or to a changed private IP, without stranding the queue. Different certificates/owners remain separate. Legacy address-scoped files are moved only after successful decoding; existing canonical files take precedence and other legacy files are left intact for manual recovery.

On a 404/409/422 sync rejection, the queue stores a persistent block and automatic sync stops reposting that operation. In **Computers**, compare queued changes with the current host record. Choose to apply the queued chain to the reviewed revision, or explicitly use the host version for that record. Both retain unrelated queued work. Rebased payloads receive new operation IDs and still use host revision checks, so another host edit requires another review. A deleted memory's edited text can be preserved as a new, clearly sourced recovered memory. Deleted check-ins remain exportable; no automatic recreation is claimed. Full-queue export and explicit full-queue discard remain available.

Verification: 49 PostgreSQL/backend tests; native queue/store regressions including durable mappings, revocation, legacy decoding, scoped conflict decisions and recovery; native TLS outage/restart tests; isolated fictional native recovery screen inspection; extracted preview 6 installer verification. See the machine-readable installer report and mission report for final evidence.

## Preview 7 evidence

Beacon alerts, calendar exports and manually supplied semester schedules now join the bounded owner-scoped offline export. The laptop reads them from **Evidence**; imports, refresh and removal are work-Mac-only. See `INTEGRATIONS.md`. Pending conflicts still allow a pinned availability check, without resubmitting the blocked write. Invalidated replay receipts hide known superseded records when no dependent local edits need preservation. Queue exports now contain human-readable bodies, not base64 payloads.
