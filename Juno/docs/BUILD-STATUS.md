# Build status

Updated: October 29, 2026.

## Completed

- Product mission and beta acceptance criteria captured.
- User delegated routine technology choices.
- User specified real data must remain on approved systems until external processing/storage is confirmed.
- Inspected installed TaskDock metadata and relevant API source; verified key checkout files against the installed manifest.
- Documented architecture, local bridge requirement, storage model, deployment restrictions, and HumanLab boundaries.
- Added the first read-only TaskDock workspace connector and automated tests against synthetic responses. It does not access production credentials or data.
- Installed isolated project dependencies and PostgreSQL 17 tooling; created a Juno-only developer cluster using a private Unix socket without a network listener or login service.
- Added an explicit Alembic schema migration, hashed/revocable per-device credentials, owner-scoped memory APIs, literal search, provenance/confidence, revision-checked corrections/deletions, reimport suppression, and metadata-only audit events.
- Verified schema/model consistency, two-client/service-recreation persistence, authorization isolation, revocation, deletion, and concurrent edits against real PostgreSQL. All 13 tests pass (8 memory/database tests and 5 connector tests).
- Added a dependency lockfile and `LOCAL-DEVELOPMENT.md` with reproducible setup, provisioning, API, verification, and shutdown instructions.
- A live loopback HTTP smoke check passed for service startup, authentication, creation/read/deletion, and credential revocation. Dependency checks and whitespace checks passed. The development database and temporary API process were stopped after verification.
- Built a native SwiftUI/AppKit development application at `~/Applications/Juno.app`, with its own window, Dock presence, menus, memory listing/search/add/correction/deletion confirmation, revision-conflict errors, and a manual meeting-mode setting saved on this Mac.
- Native interaction checks verified adding and correcting one explicitly fictional demo memory (revision 2), search results, meeting-mode switching, and canceling the deletion confirmation. Actual destructive deletion remains covered by backend tests; the native confirmation was canceled.
- Changed the interface decision from React/Tauri to SwiftUI to prioritize the user's standalone Mac workflow. No browser tab is needed to use the preview.
- Final bundle compiled and passed strict signature verification. Reopening the native app retained the corrected demo memory and meeting-mode setting. A helper lifecycle check verified authenticated startup and clean shutdown of its owned database. All 13 backend tests passed after the native implementation. The app was reopened and left running for the user.

## In progress / incomplete

- Discovery architecture recommendation written. Live integrations, shared infrastructure and real calendar access are not established.
- Local PostgreSQL memory service exists; approved shared deployment and actual two-Mac access do not.
- The native development app depends on this checkout, its virtual environment, and Homebrew PostgreSQL. It is not yet a self-contained installer that can be copied to the laptop.
- No chat/model integration, semantic retrieval/embeddings, diary/check-in UI, approved shared-service connection, or deployed beta yet.
- Meeting mode currently changes the neutral welcome copy and saves a local preference; chat tone, notifications, and cross-device preference synchronization do not exist yet.
- No Juno HumanLab runs or actual two-Mac tests yet.

## Verification

Run all tests from the Juno directory with the developer PostgreSQL cluster started:

```sh
JUNO_TEST_ADMIN_URL="$(python3 scripts/dev_database.py url)" .venv/bin/python -m unittest discover -s backend/tests -v
```

Evidence covers the memory/database behaviors above and synthetic connector responses. It does not establish a live TaskDock connection, semantic recall, or actual two-Mac operation. Integration tests are skipped when the test database URL is absent; do not report that as a full pass.

## Next implementation step

Extend the service and native app with conversations/diary/check-ins and a configurable approved model endpoint. Add Keychain-backed remote-service credentials and package independent runtimes before claiming portable installation or two-Mac support. HumanLab needs native interaction capability before it can test the actual SwiftUI interface; do not substitute a different web interface and call that equivalent coverage. Use synthetic records throughout until approved hosting/model access exists.

Refer to `DECISIONS.md` for unresolved environment facts. Institutional deployment details can remain pending while synthetic local implementation continues.
