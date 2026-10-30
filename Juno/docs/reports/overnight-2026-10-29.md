# Juno overnight work — October 29, 2026

## Mission 1: work continuity

Implemented durable acknowledgment mappings and optimistic cached IDs, persisted blocked-sync state, disk-safe revocation, certificate/owner cache identity across address changes, owner-scoped read-only conflict inspection, explicit scoped conflict decisions, and deleted-memory recovery. Existing paired-device rows, host key/certificate and running host were not changed.

49 backend tests passed against isolated PostgreSQL databases (no skips). Native queue/store checks passed. The actual native pinned TLS/Keychain client passed host outage, offline memory/diary writes, independent process restart, retry-idempotent replay and complete synchronization. Advertised IP and hostname passed strict TLS validation. An isolated native SwiftUI app showed the fictional blocked queue and expanded payload; this was not a HumanLab native test or real laptop test.

Preview 6 standalone installer built; final extracted-payload report: `docs/reports/installer-preview-6.json`. The preview 5 development host was preserved during mission 1. After mission 2 and final installer checks passed, it was cleanly updated in place to preview 7 (see below). Installing the packaged app on this desktop would use a different data directory; do not replace the host with an empty packaged workspace.

Actual laptop offline-edit acceptance, multi-day usage and HumanLab native interaction remain unverified. The private app/installer remain ad hoc signed/unsigned and not notarized.

## Mission 2

Completed preview 7: read-only Beacon alert API/JSON imports, recurring calendar .ics imports and semester CSV schedules. Added dated owner-scoped evidence, explicit coverage/timezone, overlap-aware daily busy totals per source, source replacement/removal, local-model excerpts and reply invalidation (including in-flight generation), shared offline export, and the native Evidence workspace. TaskDock remains authoritative for tasks.

59 backend tests passed with real isolated PostgreSQL and no skips. Native queue/store checks passed, including invalidated receipt redaction and durable recovery. Exact-certificate native TLS/Keychain host-outage/restart checks passed. The final package passed all 13 extracted-payload groups, including actual fixture HTTP Beacon reads, complete-feed validation/failure retention, calendar recurrence/exceptions/DST/cancellation/transparency/overlaps, semester expansion, source persistence/deletion, TLS pairing/revocation, pre-migration backup and resource-signature integrity.

Native UI acceptance used a separate QA bundle and disposable PostgreSQL owner: all three fictional sources rendered; Beacon details and calendar 1.5-hour overlap totals expanded; the macOS file picker imported a supplied CSV, replacing 12 rows with 9 under the selected smaller date window; removal confirmation was shown and cancelled. Initial QA launch/inspection failures were resolved by configuring the synthetic store before rendering and verifying the optimized fixture; no unresolved UI automation failure remains for this acceptance path. No HumanLab native acceptance is claimed.

The real development host was cleanly quit, rebuilt and relaunched after package verification. Hosting resumed on the same IP/8443; private invariant checks confirmed the existing owner, work-record counts, existing paired-device states and certificate/private-key hashes were preserved. Only its temporary local app credential rotated, as designed. Schema 5 and the readable pre-migration backup were verified. Its native Computers screen still listed the paired MacBook Air; Evidence showed the expected empty state (no fictional sources were imported into live work data).

Final installer: `dist/Juno-0.1.0-preview.7-macOS-arm64.pkg`; report: `docs/reports/installer-preview-7.json`. A laptop-ready copy with checksums, setup notes and templates is under `/Users/dmccoy/Downloads/Juno-0.1.0-preview.7`. See `docs/PREVIEW-7-SETUP.md` before updating the laptop.

No live Beacon key/calendar file was supplied; both are ready for user setup. Manual imports are not live calendar sync. Actual laptop offline-edit/reconnect acceptance and multi-day use remain pending. Cloud services, external messages, employee outreach, firewall/sleep/router changes and existing pairing-secret rotation were not performed. The unrelated pre-existing repository-root README deletion remains untouched.
