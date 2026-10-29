# Local discovery evidence

Inspected October 29, 2026. No production applications were launched, modified, or refreshed; no private configuration or task databases were read.

## TaskDock

- Installed app: `/Applications/TaskDock.app`.
- Installed plist: bundle identifier `com.taskdock.desktop`, version `0.2.0`, build `12`, release `0.2.0-beta.3`, minimum macOS `13.5`.
- Source: `/Users/dmccoy/bin/python/TaskDock`.
- Installed source resides in `Contents/Resources/app`. SHA-256 comparisons against the installed `app-source-manifest.json` confirmed the checkout's `main.py`, `workspace.py`, `models.py`, and `scripts/bundle_launcher.py` match the recorded installed files.
- `scripts/bundle_launcher.py` sets the normal data root to `~/Library/Application Support/TaskDock`, with `.env`, `data`, and `private` beneath it. Actual private values were not inspected.
- API: FastAPI. `/workspace/tasks` provides combined native/imported records, pagination up to 500 items, `snapshot`, `has_more`, `expected_snapshot`, and completion/archive/subtask controls. `/workspace/tasks/{ident}` and its `/timeline` endpoint provide details/history.
- `/tasks` alone is insufficient: its query reads the imported `tasks` table and would miss native workspace work.
- The global dependency accepts an optional configured bearer gate. Juno must use the token when configured; it must not assume the dashboard authenticates remote users.
- Host/startup behavior is loopback-oriented. No remote bridge or Juno-approved connection has been established.
- TaskDock also has calendar-delivery functionality. That is not proof it exposes all of Dan's Google Calendar commitments for read-only planning.

## Beacon

`/Users/dmccoy/bin/python/MacLabInventoryServer` contains the `beacon` package. Its alert router is in `beacon/reporting/alerts.py` with prefix `/api/alerts`. Scoped integration-key route definitions exist in `beacon/supplies/integration_keys.py`. TaskDock documents Beacon ingestion. Deeper Beacon integration is deferred; no live endpoint, credential, or data was inspected.

## HumanLab

- Location: `/Users/dmccoy/bin/python/HumanLab`.
- Python project; browser extra uses Playwright, with synthetic participants constrained to visible interface observations.
- Existing `docs/taskdock/README.md` documents isolated fictional-data testing and explicitly excludes native Mac controls from browser coverage.
- Browser tests can operate Juno's real React interface served locally, separate from the Tauri shell. Native notifications, Keychain, installation, window behavior, and actual two-Mac operation need separate checks.
- Do not provide evaluator success criteria or source code to synthetic participants. Keep synthetic participant feedback separate from verified backend outcomes.
- No HumanLab experiment has been run for Juno yet.

## Tooling observed

Node `v26.8.2`, Python `3.14.7`, and `/usr/bin/swift` are available. `cargo`, `psql`, and `docker` were not on PATH during inspection. These are setup gaps, not reasons to select a different product architecture. Do not borrow another project's private environment or credentials.
