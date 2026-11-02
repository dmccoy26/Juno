# Worker assignments and searchable sharing — November 2, 2026

Preview.15 addresses three owner requests: find tasks among similar titles, include TaskDock information without repeated field entry, and use TaskDock assignment without reassigning in Juno.

## Result

TaskDock remains read-only and authoritative for assignment. Enabled worker portals derive access for uniquely matched active registered workers from the current saved snapshot's assignment channel. Name-only assignees match exact normalized names; email/stable identifiers and different names have an explicit one-time identity selector. Explicit matches are workspace-bound and cannot be claimed by two active workers. Ambiguous names fail closed. No worker identities, invitations or outbound messages are created automatically.

Assigned access lasts while assigned, with current source identity/policy/assignment rechecked on worker reads and report submission. Refresh reconciles derived grants under the owner lock. Reassignment/task removal/worker revocation/source withdrawal removes access; old reports remain retained. Worker browser sessions retain their seven-day maximum. Manual collaboration shares remain separate and expiring; changing those never writes an assignment to TaskDock.

New shares include supported permitted business fields automatically and render against the latest saved authorized snapshot. Old limited grants remain limited. Optional instructions and same-workspace confirmed room supplement the source. Known fields only are forwarded; arbitrary unknown record keys and private Juno chats/memory/diary/reviews are excluded. Already-cached permitted history is included without upstream calls. Source details not shared/fetched cannot be invented.

Native sharing searches title, room aliases, equipment, parent, description, status, assignee and reference using all query terms. Distinguishing row context and stable IDs avoid similarly named-task mistakes. Selection survives filtering and is visibly identified when hidden. Preview/Cancel are pinned. Assigned tasks reached from Plan/TaskDock offer existing worker links directly; manual sharing is labeled requesting help.

## Verification

- 144 full backend tests passed without skips against isolated PostgreSQL databases.
- 20 focused worker tests passed after final display formatting, covering owner/worker isolation, source scope, full versus legacy excerpts, live detail changes, stable/workspace-bound identity matching, ambiguous names, reassignment, stale report rejection, task removal and report retention.
- Exact Swift task-filter fixture passed with 60 similar titles plus accent, aliases, all-word equipment/parent queries, stable ID, confirmed-room and empty-result cases.
- Optimized native builds passed. Native isolated lab observed 60 similar titles, initial disabled Preview, unique equipment/parent filtering, correct LIBR 115/task 042 selection, selection retained through a no-match query, exact preview, automatic full details with no field checkboxes, one-time identity choices, Cancel without creating a share, and the existing-assignment panel reached through TaskDock's task action. Visually inspected the task chooser and assigned-task panel. Lab HTTPS was unavailable, so link creation stayed disabled; actual grant/auth behavior is covered separately by integration tests.
- Actual extracted/relocated preview.15 package passed 106 bundled-runtime fixtures, 239 Mach-O checks, migration from schema 1 with readable backup, persistence/restart, pinned pairing/offline and resource integrity checks. See installer-preview-15.json.
- Installed preview.15 development app at ~/Applications/Juno.app. Before/after guards preserved owner, memory/diary/chat/source/report/worker counts, planning/schedule content, existing paired-device revocation states and paired certificate/key. Existing grant IDs were preserved. Only the temporary local app credential rotated; temporary verification credentials were revoked. Previous bundle is privately preserved under .local/host-app-before-worker-assignments.
- Schema 0011 upgrade created a readable private pre-migration dump. Work app was observed connected with preview.15. Existing worker HTTPS at https://10.3.66.50:8444 passed certificate-chain/hostname validation and worker-page/owner-overview checks. Listener settings and pairing remain unchanged.

## Remaining operator actions and limits

The work snapshot exposes seven TaskDock identity choices, with one active Juno worker and no exact-name/explicit match yet. The owner must choose that worker's TaskDock identity once in Worker access. No match was guessed and no real task assignment was edited for testing. Refresh Juno's TaskDock copy after upstream changes; workers reload/reconnect to see the list. This is not an upstream live subscription or automatic scheduling.

The reported student Wi-Fi issue remains pending the device's exact error/IP. App source filtering still permits actual 10/8 peers, and each browser needs approved CA trust. No trust, firewall/router, provider permissions, public exposure or real worker invitation/message was changed during these tests. Existing explicit manual shares retain their independent expiry/access even if a TaskDock assignment changes. Physical laptop installation and Developer ID notarization remain outside this verification.
