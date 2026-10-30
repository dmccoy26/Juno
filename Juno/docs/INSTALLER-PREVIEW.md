# First laptop installer: 0.1.0-preview.1

Historical first package. The latest package is `0.1.0-preview.7`, adding durable offline recovery and Beacon/calendar/semester-schedule evidence; see `SHARED-HOST.md` and `INTEGRATIONS.md`. The installation and verification approach below remains applicable.

Target: Apple Silicon, including Dan's M5 MacBook Air on macOS 26.5. This is the first installable memory preview, not completion of the entire 0.1.0 beta mission.

## Laptop installation

1. Transfer `dist/Juno-0.1.0-preview.1-macOS-arm64.pkg` to the laptop.
2. Quit any running Juno before installing. Run the package through macOS Installer using your institution's usual software approval process.
3. Open `/Applications/Juno.app` directly in Finder. The application starts its included Python service and PostgreSQL runtime automatically. No Homebrew, Python installation, source checkout, or terminal is required on the laptop.
4. Add a fictional memory, correct it, quit/reopen Juno, and verify that it persists. Try search and the meeting-mode toggle.

There is no Developer ID signing identity on the build Mac. The app has an ad hoc integrity signature, while the installer is unsigned and not notarized. macOS or institutional controls may require approval. The build does not disable or bypass those controls.

## Included and excluded

Working: native window and menus, memory listing/search/add/correct/delete, confirmation/source information, stale-edit protection, persistence, local meeting-mode preference and automatic service lifecycle.

Not yet connected: model/chat, daily check-ins, TaskDock/Calendar live reads, cloud processing, employee interaction or cross-device synchronization. Each Mac has its own local data. The package contains no tasks, memories or credentials from the desktop. It is intended only for synthetic data while institutional data-handling permissions are unresolved.

The database and app state live in `~/Library/Application Support/Juno`, outside the app bundle. Reinstalling the app preserves that folder. Keep this data separate from TaskDock. The desktop source checkout's `.local` development records are not imported automatically.

## Build and verify

From the Juno source directory on the build Mac:

```sh
python3 scripts/build_installer.py
python3 scripts/verify_installer.py \
  dist/Juno-0.1.0-preview.1-macOS-arm64.pkg \
  --report dist/installer-verification.json
```

The builder downloads pinned Python and PostgreSQL vendor runtimes, verifies their published SHA-256 digests, installs locked Python dependencies, and compiles the native application. Runtime download URLs and checksums are in `packaging/runtimes-arm64.json`. Optional PostgreSQL PL/Python extensions are excluded because they depend on an external Python framework that Juno does not use. The included PROJ reference database belongs to the vendor runtime; it is not user data.

The verifier expands the actual package, checks for external symlinks/dynamic libraries/private records, relocates the extracted app, and starts its included service with a restricted PATH and isolated temporary data. It exercises authentication, memory edits, stale conflicts, restart persistence, deletion/suppression and clean shutdown. It checks the application signature again after execution.

A passing desktop verification does not establish that macOS Installer or institutional policy will allow installation on the actual laptop. Record that result after the laptop test. Do not describe this preview as a completed shared-service deployment.
