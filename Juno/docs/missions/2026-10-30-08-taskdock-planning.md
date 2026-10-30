# Mission 8 — TaskDock Beta 3.17 request facts

Support TaskDock’s optional controlled-sharing API v1 extension without expanding existing grants. TaskDock remains the read-only task authority. No provider credentials, upstream refreshes or task writes are introduced.

## Behavior

- Validate discovery sharing metadata and pin the sharing version on every task/history page. Check response versions, task-page policy and final discovery. Discard incomplete or changed collections; restart a conflicting collection up to three times.
- Import only explicitly selected structured request fields. Preserve provided, unknown and explicitly-none states, provenance, observation timestamps and blocker conflicts. Strip new request fields from legacy connections.
- Show shared request facts in task details and room issue cards. Prefer provided room hints over title inference; room access still needs confirmation. Include shared blockers/dependencies in planning, reservation checks and Today counts. Share bounded dated comment samples with the configured local model as untrusted evidence; completeness does not confirm staffing or scheduling readiness.
- Expose the sharing selection/version and direct permission changes to TaskDock Settings → Juno. Existing permissions remain unchanged.
- Detected policy changes or denied/revoked access clear Juno’s task snapshots, source copies and task histories for that owner/origin, including archived snapshots, and invalidate derived chat replies. Independent confirmed memories, diaries and planning facts remain. Ordinary network failures retain the last good copy. Offline devices receive changes on reconnection; existing backups are not retroactively erased.

## Verification and limits

119 PostgreSQL/backend tests pass with zero skips. Synthetic tests cover first/subsequent-page pins, changed versions and policies, history mismatch rejection, legacy non-expansion, field quality, comment scope, readiness checks, archive withdrawal and revocation. Native room matching and Today helper checks pass, including structured blockers and conflicting TaskDock flags. Optimized macOS development build succeeds.

Real optional-field sharing still requires the user to select fields in TaskDock and refresh Juno. Synthetic contract checks do not establish that those live grants have been enabled. The portable laptop installer remains a separate follow-up.

## Desktop acceptance

Installed on the work Mac; native inspection confirmed connected state and the legacy-scope notice. Private checks preserved host identity, work-record counts, certificate/key and prior paired-device states. Native exact planning API decoder checks also passed. Attempting a live refresh then blocked in macOS Security’s Keychain read on the UI thread, confirmed by a private process sample; CUA inspection timed out. No credential or permission changes were attempted. Live refresh and controlled-field visual acceptance remain pending resolution of that Keychain wait.
