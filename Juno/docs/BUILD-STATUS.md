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
- Pushed the initial implementation to `https://github.com/dmccoy26/Juno` (`32c9403`).
- Built the first self-contained Apple Silicon installer: `dist/Juno-0.1.0-preview.1-macOS-arm64.pkg` (approximately 147 MB), with checksum sidecar. Python 3.14.10 and PostgreSQL 17.11 are bundled from pinned vendor downloads; no Homebrew, checkout, or runtime downloads are needed on the recipient Mac.
- Verified the actual installer payload after extraction and relocation on macOS 26.6.2: 239 Mach-O dependency checks, bundle integrity, clean-data startup, authentication, memory create/edit/conflict, restart persistence, credential rotation, deletion/suppression, clean shutdown and parent-loss cleanup. The packaged native window connected successfully. See `reports/installer-preview-1.json`.
- Target laptop identified by the user: M5 MacBook Air, macOS 26.5. Actual laptop installation remains to be tested. The temporary packaged verification app was quit after inspection.

## Preview 2 additions

- Added schema `0002_companion`: owner-scoped conversations/messages, local model settings and resumable dated check-ins.
- Added native Chat, Daily check-in and Model connection sections alongside Memories.
- Local-only model adapter supports LM Studio, bounded responses, final-answer parsing and explicit failure states. No cloud fallback or model weights are bundled.
- Live desktop smoke test with `qwen3.6-35b-a3b` answered from a synthetic canonical memory. Native chat answered the fictional classroom availability question and survived an application restart.
- Native check-in resumed at question three after a full restart and produced an editable five-section diary draft. The synthetic native diary was left unconfirmed.
- Corrections/deletions invalidate derived assistant history; in-flight replies validate context revisions before publishing. Idempotent retry records and pending-turn recovery prevent silent duplicate turns.
- Automatic pre-migration PostgreSQL backup and readability check added. Preview-1 schema upgrade, backup and preserved memory passed in the package verifier.
- All 24 automated tests pass, including real PostgreSQL behavior and local model-adapter checks. Native interaction verification and a real local-model call supplement those tests.

## In progress / incomplete

- Discovery architecture recommendation written. Live integrations, shared infrastructure and real calendar access are not established.
- Local PostgreSQL memory service exists; approved shared deployment and actual two-Mac access do not.
- The earlier development app still depends on the checkout. The new installer is self-contained and stores fresh per-user data in `~/Library/Application Support/Juno`; it does not import the development data.
- No Developer ID signing identity is available. The app is ad hoc signed; the package is unsigned and not notarized. Institutional/macOS approval may be needed on the laptop.
- Chat and check-ins are implemented locally. Semantic retrieval/embeddings, approved shared-service connection, live task/calendar reads and the full beta mission remain incomplete.
- Meeting mode now controls the chat prompt and hides private-mode assistant replies. Notifications and cross-device preference synchronization do not exist yet.
- No Juno HumanLab runs or actual two-Mac tests yet.

## Verification

Run all tests from the Juno directory with the developer PostgreSQL cluster started:

```sh
JUNO_TEST_ADMIN_URL="$(python3 scripts/dev_database.py url)" .venv/bin/python -m unittest discover -s backend/tests -v
```

Evidence covers the memory/database behaviors above and synthetic connector responses. It does not establish a live TaskDock connection, semantic recall, or actual two-Mac operation. Integration tests are skipped when the test database URL is absent; do not report that as a full pass.

## Next implementation step

Obtain the actual M5 laptop installation result for preview 2 and the local-model setup experience. Then implement the read-only TaskDock bridge and calendar planning context using synthetic fixtures until live access is explicitly connected. Shared hosting, remote-model approvals, Keychain credentials, semantic retrieval and native HumanLab instrumentation remain later requirements.
