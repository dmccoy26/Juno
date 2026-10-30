# Overnight mission 1: reliable two-Mac work continuity

Status: complete (preview 6). Authorized by Dan on October 29, 2026; routine decisions are delegated and no overnight questions are needed.

## Outcome

Make Juno's existing host/laptop workflow dependable when connections fail, the app restarts, access is revoked, or both computers edit the same record. Preserve the working host certificate, the paired laptop credential, existing records and standalone workspaces.

Dan confirmed that TCP access across the wired/Wi-Fi network succeeded and that the laptop synchronized. This is user-reported real-device evidence; offline editing on the actual laptop is still unverified.

## Deliverables

1. Durable offline acknowledgments, record mappings and recovery state. A server save followed by a lost export/response or a restarted client must not strand a laptop record under a temporary ID. Revocation must not remove unsynchronized edits from disk.
2. Conflict review that shows queued laptop contents alongside the current work-Mac record. Explicit actions can rebase the queued version against a reviewed revision, use the work-Mac version, or preserve an edited/deleted memory as a new record where appropriate. Never silently choose a winner; keep unrelated queued work.
3. Persistent conflict/error state and truthful connection status. Distinguish an unreachable host from a reachable host that needs conflict review. Automatic reconnect must not continually resubmit a known conflict. Recovery must remain available after restart and on corrupt/incomplete cache state.
4. Preserve a verified host/owner identity across a changed local IP when importing a fresh invitation. Do not rotate certificates, reset host identities or revoke the paired laptop as routine deployment work.
5. Meaningful regression checks against disposable PostgreSQL owners and the actual native queue/store/TLS code. Verify retry idempotency, dependent edits, deletion, revocation, owner isolation, cache format upgrade and conflict decisions. Native UI verification must use fictional records in an isolated application, not Dan's live workspace.
6. A versioned standalone Apple Silicon installer, extracted-payload verification, recovery/release instructions and a morning report. Push tested changes to the existing GitHub repository.

## Boundaries

Stay inside Juno. Inspect other project contracts read-only if useful. Do not change TaskDock, Beacon, institution systems, firewall/sleep/router policy, certificate trust, existing pairing secrets or external accounts. Use synthetic test data. No external messages, purchases, deployments or new cloud services. Preserve the unrelated pre-existing repo-root README deletion.

Prefer scoped, reviewable fixes over architecture replacement. Never describe a fixture as a real laptop test. Before changing schemas use the existing readable pre-migration backup path. Do not disturb the running host until a verified update is ready; keep local edits and paired-device rows across the update.

## Exit criteria

- Acknowledged creates and subsequent edits recover across a cache-download failure and process restart.
- Pending edits survive known revocation and re-pair recovery; old work records are not shown as current after revocation.
- Conflicts retain laptop contents, show current server data and require an explicit decision. Conflict resolution preserves unrelated queued work and still checks the reviewed revision on the host.
- Automatic recovery remains bounded and does not send tokens to unpinned/redirected destinations.
- Backend, native queue/store/TLS, isolated UI and installer checks pass, with actual-device gaps named.
- Release artifacts, commit, remaining issues and instructions are documented. Then create mission 2 for additional integrations and execute it without asking routine questions.

## Result

Completed both the PostgreSQL/API and native queue/store/TLS regression checks, isolated native UI inspection, and extracted installer verification. See `docs/reports/overnight-2026-10-29.md` and `docs/reports/installer-preview-6.json`. Deleted check-ins stay exportable rather than silently being recreated. Existing paired-device identity and the running host were preserved. The subsequent integration mission is recorded separately.
