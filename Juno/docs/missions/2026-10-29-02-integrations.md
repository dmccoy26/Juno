# Overnight mission 2: operational evidence integrations

Status: complete (preview 7). Created after mission 1 passed its exit checks. Dan authorized creating and running another mission and pushing all completed work.

## Outcome

Give the native application more of the evidence needed to reduce daily planning decisions, while keeping TaskDock authoritative for tasks and keeping all work data on the approved Mac.

## Scope and acceptance

1. Beacon read-only alert connector, using its existing schema-1 complete GET /api/alerts contract. Accept a user-supplied dedicated key through the native app/Keychain; do not provision, discover or extract credentials. Loopback-only HTTP, no redirects/proxies. Validate completeness, IDs/counts and bounds before promotion; failures retain the last good snapshot and show freshness/error. Also allow a manually supplied complete alert-feed JSON file.
2. Local calendar .ics import with an explicit finite date window and timezone, recurring event instances/exceptions, cancelled/transparent events and overlap-aware busy-time summaries. Refuse ambiguous or unsupported content rather than inventing free time. No OAuth, subscriptions, URL fetching or calendar writes.
3. Semester schedule CSV import for classroom occupancy, employee scheduled availability and meetings. Explicit timezone, date range and weekly times; validate the entire import before replacement. No inferred employee capability or performance.
4. Owner-scoped dated source snapshots, replacement/deletion, provenance, sanitized local-model evidence and cache export to paired laptops. Imports/configuration remain work-Mac-only; laptops read the shared cache. Imported text is untrusted evidence, never instructions.
5. Native Integrations screen, useful empty/error states and templates; meaningful backend/source-boundary/context tests and native/packaged verification. Build a new standalone Apple Silicon installer, document actual unconnected sources and push both missions to GitHub.

## Boundaries

Read other projects' contracts only. No changes to Beacon/TaskDock, credentials, institutional systems, cloud approval, host certificate or existing paired devices. Test with fictional data and disposable databases. No claim of live Beacon/calendar connectivity without an actual user-supplied feed/key. Keep the running approved host's workspace intact. Do not add email/Slack/Google OAuth using guessed permissions.

## Result

All three source inputs, owner/cache/model boundaries and native UI are implemented. 59 backend tests, native queue/store/TLS outage checks, native fictional-data file-picker acceptance and final extracted-installer verification passed. The existing work host was updated without replacing its owner, work data or paired-device/certificate identity. See `docs/reports/overnight-2026-10-29.md`, `docs/INTEGRATIONS.md` and `docs/PREVIEW-7-SETUP.md`. Live Beacon/calendar credentials/data and real laptop offline-edit acceptance remain explicit user setup/acceptance, not a claimed live connection.
