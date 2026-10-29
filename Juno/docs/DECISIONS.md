# Architecture decisions

Date: October 29, 2026. These decisions guide implementation; they do not claim a deployed service.

## Adopted direction

| Area | Choice | Reason |
| --- | --- | --- |
| Interface | SwiftUI with AppKit window/menu integration | A standalone native Mac app with its own Dock presence, direct native editing controls and no browser requirement. |
| Mac application | Compiled Swift `.app` bundle | Replaces the proposed Tauri/Rust/React stack after the user emphasized a standalone app like TaskDock. Keep work data and business rules in the Python service. |
| Service | Python 3.12+, FastAPI, Pydantic, HTTPX | Fits the existing application ecosystem, typed boundary validation, and explicit integration adapters. |
| Primary storage | PostgreSQL | Shared transactional records and access controls independent of either Mac. |
| Semantic retrieval | pgvector within PostgreSQL | Keep embeddings adjacent to canonical memory records so updates and deletion can be coordinated transactionally. No separate ChromaDB service. |
| Database access/migrations | SQLAlchemy 2 and Alembic | Explicit schema evolution and a stable relational layer. |
| Model boundary | Provider adapter with configurable approved endpoint | No vendor dependency in memory or planning logic. No external model calls with real data until approved. |
| Model operation | Retrieval with traceable sources; structured outputs validated by code | Generated prose cannot authorize an action or replace canonical task/calendar state. |
| Testing | Python behavior/integration tests and native Mac interaction checks; HumanLab coverage to be extended | HumanLab's existing browser instrument cannot test SwiftUI. Do not claim browser testing covers the native interface. |

Python dependencies are locked in `backend/requirements.lock`. PostgreSQL 17 is installed for isolated local development. The available Swift compiler builds the native app; Rust and Node are not needed for this interface. The development bundle uses this checkout's environment. The separate installer builder bundles pinned standalone Python and Postgres.app server runtimes, eliminating the checkout/Homebrew dependency for recipient Macs. Each installed preview uses independent local storage until approved shared hosting is connected.

The development app starts its helper automatically, receives a short-lived credential through a private pipe, and keeps it only in process memory. The helper revokes its previous development credential on restart and its current credential on clean shutdown. Tokens are not persisted by the app. Keychain-backed credentials remain required for a future connection to an approved shared service; they are not implemented in this local preview.

## Data location and deployment

The user explicitly selected: keep real work data on institution-approved systems until permission for external services is confirmed.

Therefore development uses synthetic fixtures in a local-only environment. Do not copy production TaskDock data or credentials into fixtures, HumanLab sessions, model requests, or reports. Select an approved shared host before real-data deployment. Hosting on the desktop alone cannot meet the laptop requirement when the desktop is off.

Recommended production shape: both Mac clients connect over authenticated HTTPS to one institution-approved shared service and PostgreSQL database. A model endpoint must also be approved for the information it receives. A local/approved model endpoint is supported by design; no particular locally installed model has been verified.

For the single-user beta, use independently provisioned device credentials stored in macOS Keychain and only hashed credentials on the service. Map each credential to an owner; never accept an owner ID from the client as authorization. Permit per-device revocation. Require all queries to be scoped to the authenticated owner. Add institutional SSO before a broader rollout if required. Browser test credentials must be separate and ephemeral; no long-lived credentials in browser localStorage.

## TaskDock connectivity and stale data

TaskDock's installed API is loopback-only. A shared server cannot directly call a laptop's or desktop's `127.0.0.1`. Do not expose TaskDock publicly or copy its SQLite database to solve this.

Implement a desktop-side read-only bridge: when Juno runs alongside TaskDock on an authorized Mac, it fetches the workspace API and sends a normalized snapshot to the approved Juno service. Keep the TaskDock bearer token in Keychain, separate from the Juno service credential. The service stores source device, fetch time, source revision, and last error. If both apps are not running, use the last successful snapshot with a visible freshness warning. Never overwrite a successful snapshot with an empty result caused by a connection failure.

Two TaskDock installations may contain different workspaces. Each bridge must have an explicit workspace binding. Do not merge them just because they share a display name. Start with the desktop workspace as the primary source; whether Dan's laptop TaskDock is synchronized with it remains unverified. Juno's own memory synchronization is separate from TaskDock synchronization.

Use `/workspace/tasks`, not the imported-only `/tasks`. Fetch all pages, include completed records for diary evidence, exclude archived records initially, and use `expected_snapshot` after the first page. Detect HTTP 409, inconsistent counts, duplicate IDs, or revision changes; fail the refresh without publishing a partial snapshot. Preserve stable source IDs and parent links. A connector GET must not trigger a source sync or writeback.

## Calendar

Give Juno its own Google Calendar read-only authorization on the approved service. TaskDock's existing Google connection is not evidence of calendar-read permission for Juno. Do not reuse another app's OAuth tokens. Initially select calendars explicitly; expand recurring events over a bounded planning window and retain timezone, all-day, cancellation, and free/busy semantics. Do not treat an all-day informational event as a full-day commitment automatically. Union overlapping busy intervals before subtracting them from work hours.

## Storage model

All user records carry an owner ID. Proposed tables:

- `devices`: credential hashes, revocation, mode/settings revision.
- `conversations` and `messages`: messages, timestamps, mode at generation, provenance references.
- `memories`: text, category, source references, confirmation state, effective dates, revision, deletion state.
- `memory_embeddings`: embedding model/version and vector linked to the canonical memory revision.
- `diary_entries`: local date/timezone, draft/provisional/confirmed state, narrative, structured events, source references.
- `source_connections`, `source_snapshots`, `source_items`: source/workspace identity, fetch time, revision, availability and normalized records.
- `people` and `capability_evidence`: employee availability context and confirmed examples of independence/skills.
- `semester_schedules` and `schedule_exceptions`: effective ranges, room/staff identity, timezone, intervals and overrides.
- `task_context`: source-task reference, duration estimate/correction, blocker dependencies, next check, resumption note. Does not become a competing task hub.
- `check_ins` and `recommendations`: resumable interview state, evidence, missing information, proposed next steps.
- `audit_events` and `deletion_suppressions`: metadata for changes and protection against silently regenerating deleted memories.

Use optimistic revisions for edits and return a conflict rather than overwriting a newer change. Memory changes and dependent embedding removal happen in one transaction. Deliberate deletion removes active retrieval/derived content; backup expiry and any source deletion choices must be visible in the UI. Audit metadata must not retain deleted text as a hidden copy. Validate retrieval behavior in a new conversation after corrections/deletions.

## Implementation sequence

1. Read-only integration contract and synthetic fixtures; build discovery evidence.
2. Shared service schemas, owner authentication, migrations, and memory APIs with a disposable PostgreSQL test environment.
3. Native SwiftUI interface exercising the real service: memory review/edit/delete and locally persisted meeting-mode setting. Implemented in the development preview.
4. Independently packaged runtimes and native verification delivered for `0.1.0-preview.1`. Delivered in preview 2: persistent conversations, offline-capable diary/check-in, and a local-only LM Studio-compatible model connection. Keychain-backed shared-service credentials and remote endpoints remain future work.
5. Calendar and TaskDock bridge, planning behavior, an appropriate HumanLab native adapter or clearly bounded service-only scenarios, and real two-Mac verification on approved infrastructure.

## Unresolved environment facts

- Approved institution host, database, and model endpoint: needed before real data; does not block synthetic local work.
- Google authorization registration and allowed callback origins: needed before real calendar access.
- Laptop TaskDock workspace relationship: needed before enabling a second task bridge.
- Exact work hours and check-in reminder time: configurable user setup, never invented.
- Signing/notarization identity and actual laptop access: needed before distribution/two-device signoff.

Do not ask the user to choose frameworks or database libraries. Ask only for unavailable institutional access facts or consequential deployment decisions, with a concrete recommendation.

## TaskDock API v1 — October 29, 2026

Preview 3 implements the supplied local read-only integration contract. Dedicated credentials live in native macOS Keychain, are passed transiently to the local service, and are never stored in PostgreSQL or given to a model. Immutable dated snapshots and separately dated history caches retain source data without replacing TaskDock as its system of record. Initial and changed workspace/device identities require review; refresh promotion is atomic and rejects concurrent replacement. No calendar, shared host, cloud fallback or task writes are enabled by this work. See `TASKDOCK-CONNECTION.md` for acceptance evidence and remaining limits.
