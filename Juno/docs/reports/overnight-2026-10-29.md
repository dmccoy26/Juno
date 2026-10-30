# Juno overnight work — October 29, 2026

## Mission 1: work continuity

Implemented durable acknowledgment mappings and optimistic cached IDs, persisted blocked-sync state, disk-safe revocation, certificate/owner cache identity across address changes, owner-scoped read-only conflict inspection, explicit scoped conflict decisions, and deleted-memory recovery. Existing paired-device rows, host key/certificate and running host were not changed.

49 backend tests passed against isolated PostgreSQL databases (no skips). Native queue/store checks passed. The actual native pinned TLS/Keychain client passed host outage, offline memory/diary writes, independent process restart, retry-idempotent replay and complete synchronization. Advertised IP and hostname passed strict TLS validation. An isolated native SwiftUI app showed the fictional blocked queue and expanded payload; this was not a HumanLab native test or real laptop test.

Preview 6 standalone installer built; final extracted-payload report: `docs/reports/installer-preview-6.json`. The working preview 5 development host remains running to preserve the live paired session. Installing the packaged app on this desktop would use a different data directory; do not replace the host with an empty packaged workspace.

Actual laptop offline-edit acceptance, multi-day usage and HumanLab native interaction remain unverified. The private app/installer remain ad hoc signed/unsigned and not notarized.

## Mission 2

Will be recorded after the reliability exit checks finish.
