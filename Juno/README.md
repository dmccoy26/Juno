# Juno

A Mac AI work companion that helps Dan decide what to do next, retain work context, and complete a guided daily check-in.

The agreed product direction and first beta build mission are in [MISSION-0.1.0.md](MISSION-0.1.0.md).

Current state: a native Mac development application with a working memory interface, a PostgreSQL-backed memory API, and a read-only TaskDock connector. Persistent local-model chat, guided daily check-ins, offline conflict recovery, dated operational evidence and native read-only connection setup for seven providers are implemented. Preview 10 adds recurring schedules, staff status and weekly limits, possible repair windows and local planning holds. Preview 9 introduced constrained next-task planning, editable estimates, confirmed room/staff availability, blocker follow-up and a weekly Dean draft.

The latest self-contained installer is `dist/Juno-0.1.0-preview.10-macOS-arm64.pkg`. Install it, then open `/Applications/Juno.app` in Finder. Python and PostgreSQL are included; no terminal, Homebrew, checkout, or browser tab is required on the recipient Mac. This Mac is approved as the work host. A paired laptop uses encrypted local-network access and keeps an offline copy with queued memory/diary edits. The host must be awake with Juno open. Chat runs through the host’s local model; no cloud fallback is enabled. Independent standalone data is not automatically merged.

Start with [preview 10 setup](docs/PREVIEW-10-SETUP.md), [schedules and repair planning](docs/SCHEDULES-AND-REPAIR-PLANNING.md), [work planning](docs/PLANNING.md), [preview 8 connection setup](docs/PREVIEW-8-SETUP.md) and [direct provider/TaskDock connection setup](docs/CONNECTIONS.md).

See [work Mac hosting, laptop pairing and offline edits](docs/SHARED-HOST.md) and [new evidence integrations and setup](docs/INTEGRATIONS.md).

The native TaskDock tab supports read-only task pairing with TaskDock build 14; the separate build 15 candidate adds opt-in stored notes/events/work evidence. It uses Keychain credentials, dated task snapshots, source freshness and cached history. See [TaskDock pairing and verification](docs/TASKDOCK-CONNECTION.md).

See [chat, LM Studio setup and check-ins](docs/CHAT-AND-CHECKINS.md), plus [latest installer verification](docs/reports/installer-preview-10.json). This internal preview is not Developer ID signed or notarized. Dan confirmed real laptop synchronization; actual laptop offline-edit/reconnect acceptance remains pending.

Rebuild the source-dependent development app after quitting Juno:

```sh
python3 scripts/build_macos.py
```

- [Architecture decisions](docs/DECISIONS.md)
- [Discovery evidence](docs/DISCOVERY.md)
- [Build status and next steps](docs/BUILD-STATUS.md)
- [Local service setup and testing](docs/LOCAL-DEVELOPMENT.md)
- [Native development preview](docs/NATIVE-PREVIEW.md)
- [First laptop installer](docs/INSTALLER-PREVIEW.md)

Run the complete suite after setting up the local environment (see the service setup link above):

```sh
python3 scripts/dev_database.py start
JUNO_TEST_ADMIN_URL="$(python3 scripts/dev_database.py url)" .venv/bin/python -m unittest discover -s backend/tests -v
```
