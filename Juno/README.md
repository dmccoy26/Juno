# Juno

A Mac AI work companion that helps Dan decide what to do next, retain work context, and complete a guided daily check-in.

The agreed product direction and first beta build mission are in [MISSION-0.1.0.md](MISSION-0.1.0.md).

Current state: a native Mac development application with a working memory interface, a PostgreSQL-backed memory API, and a read-only TaskDock connector. Chat and daily check-ins are not implemented yet.

The first self-contained installer is `dist/Juno-0.1.0-preview.1-macOS-arm64.pkg`. Install it, then open `/Applications/Juno.app` in Finder. Python and PostgreSQL are included; no terminal, Homebrew, checkout, or browser tab is required on the recipient Mac. Use synthetic data only. Each Mac has separate local data; shared memory and chat are not connected yet.

See [laptop installation and verification](docs/INSTALLER-PREVIEW.md). This internal preview is not Developer ID signed or notarized. Actual M5 laptop installation is still pending.

Rebuild after quitting Juno:

```sh
python3 scripts/build_macos.py
```

- [Architecture decisions](docs/DECISIONS.md)
- [Discovery evidence](docs/DISCOVERY.md)
- [Build status and next steps](docs/BUILD-STATUS.md)
- [Local service setup and testing](docs/LOCAL-DEVELOPMENT.md)
- [Native development preview](docs/NATIVE-PREVIEW.md)
- [First laptop installer](docs/INSTALLER-PREVIEW.md)

Run the synthetic connector tests without installing dependencies:

```sh
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -v
```
