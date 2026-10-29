# Juno

A Mac AI work companion that helps Dan decide what to do next, retain work context, and complete a guided daily check-in.

The agreed product direction and first beta build mission are in [MISSION-0.1.0.md](MISSION-0.1.0.md).

Current state: a native Mac development application with a working memory interface, a PostgreSQL-backed memory API, and a read-only TaskDock connector. Chat and daily check-ins are not implemented yet.

Open `~/Applications/Juno.app` in Finder. Juno opens her own native window and starts the local service automatically; no terminal or browser tab is required. Use synthetic data only. This development app depends on this checkout and its installed dependencies and is not a portable laptop release yet.

Rebuild after quitting Juno:

```sh
python3 scripts/build_macos.py
```

- [Architecture decisions](docs/DECISIONS.md)
- [Discovery evidence](docs/DISCOVERY.md)
- [Build status and next steps](docs/BUILD-STATUS.md)
- [Local service setup and testing](docs/LOCAL-DEVELOPMENT.md)
- [Native development preview](docs/NATIVE-PREVIEW.md)

Run the synthetic connector tests without installing dependencies:

```sh
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -v
```
