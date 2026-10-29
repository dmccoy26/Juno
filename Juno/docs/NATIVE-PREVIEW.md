# Juno native development preview

Open `/Users/dmccoy/Applications/Juno.app` from Finder or Spotlight. It is a compiled SwiftUI/AppKit application with its own native window and menus. It does not open a web browser or embed a website.

## What works

- Automatic startup of the isolated local PostgreSQL service and Python API.
- Memory list, literal search, sources, confirmation status and updated time.
- Adding and correcting memories, with validation and revision checks.
- Deletion confirmation explaining the scope of deletion.
- A manual meeting-mode toggle saved on this Mac; currently affects welcome text only.
- Reopening the window from the Dock after closing it; standard editing and quit shortcuts.

Use only fictional records. One memory beginning `Synthetic demo:` was created and corrected during native testing; it is sample data, not a fact about Dan's classrooms.

## Local lifecycle and credentials

The app launches `scripts/desktop_service.py` with the project's Python environment. The helper migrates the isolated development database, provisions a temporary owner-scoped device token, and passes an endpoint/token handshake through the app's private pipe. The token stays in memory and is not written to app preferences or the development log. The helper saves only owner/device IDs in `.local/desktop-owner.json` so memories survive relaunches. Previous device credentials are revoked on restart.

The API binds a randomly allocated loopback port, never all network interfaces. It does not reuse or launch TaskDock. Diagnostic output goes to `.local/desktop.log`. On clean quit, the helper revokes its token and stops the database only if it started that database. An already running developer database is left running. Forced termination can bypass cleanup; the next launch revokes the previous token.

Meeting-mode state is local to this Mac. Remote credentials, Keychain storage, notification behavior, and shared settings are future work.

## Build and distribution limits

```sh
python3 scripts/build_macos.py
```

The script compiles Swift for Apple Silicon/macOS 13.5+, generates an app icon, creates a bundle and applies an ad hoc signature. It refuses to overwrite a different Juno installation and asks that the running app be quit before rebuilding.

This preview is tied to `/Users/dmccoy/Ai/Juno`, its `.venv`, and `/opt/homebrew/opt/postgresql@17`. It is a standalone application experience on this Mac, but not yet a self-contained distribution. Do not copy it to the laptop and expect it to work. Developer ID signing/notarization, bundled or approved remotely hosted runtimes, upgrade behavior, and actual two-Mac access remain required for beta delivery.

## Test coverage limits

The backend suite tests deletion, authorization and concurrent edits against PostgreSQL. Native interaction checks exercised add/correct/search and deletion-confirmation cancellation. HumanLab's browser instrument cannot exercise SwiftUI; native support or a documented narrower testing approach is needed before a HumanLab Juno run.
