# Local synthetic-data memory service

This is the backend foundation, not the desktop beta. It contains no model calls or live work integrations. Keep all records synthetic until institutional hosting and model permissions are established.

## Setup

From `/Users/dmccoy/Ai/Juno`, with Homebrew Python and PostgreSQL 17 available:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
.venv/bin/python -m pip install --no-deps -e backend
python3 scripts/dev_database.py start
export JUNO_DATABASE_URL="$(python3 scripts/dev_database.py url)"
.venv/bin/alembic -c backend/alembic.ini upgrade head
```

The database script uses `.local/postgres`, not Homebrew's default cluster. PostgreSQL accepts connections only through a private Unix socket; no database TCP listener is opened. Local authentication trusts the Mac account with access to that protected socket. This is an isolated developer setup, not the production authentication design. No launch-at-login service is installed. `start` preserves an existing database rather than resetting it.

The lockfile captures the tested Python 3.14 macOS environment. Review and regenerate it when updating dependencies or supporting another platform. Python 3.12+ is the project target, but other interpreters have not yet been tested.

## Provision a synthetic device

```sh
.venv/bin/juno-admin provision --label 'Synthetic desktop' --output .local/desktop-credential.json
```

The command saves a new credential file with mode `0600` and refuses to overwrite an existing path. The server stores only the token hash. Use the returned owner ID with `--owner-id` when provisioning a second device for that same synthetic user. Without that option, a separate owner is created. Do not paste credential files into chat or commit them. Credential files are temporary developer tooling; the Mac application will use Keychain.

Revoke a device with:

```sh
.venv/bin/juno-admin revoke DEVICE_ID
```

## Run

```sh
.venv/bin/uvicorn juno.api:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log
```

The API uses `Authorization: Bearer TOKEN`. There is no unauthenticated signup. `/health` reports process identity; it is not a database readiness probe. Interactive endpoint documentation is at `http://127.0.0.1:8765/docs` while running. Credentials and private records must not be placed in URLs.

| Endpoint | Behavior |
| --- | --- |
| `GET /v1/memories` | Owner-scoped listing; literal substring `q`, `limit`, and `offset` |
| `POST /v1/memories` | Create using `text`, `source`, and `confidence` |
| `GET /v1/memories/{id}` | Read an owned record |
| `PUT /v1/memories/{id}` | Replace editable fields with `expected_revision` |
| `DELETE /v1/memories/{id}?expected_revision=N` | Delete a record only if its revision still matches |

Confidence is `confirmed`, `observed`, or `inferred`. Bodies reject extra fields such as client-supplied owner IDs. Missing credentials return 401; another owner's record returns 404; stale revisions, duplicates, and suppressed reimports return 409. API responses use `Cache-Control: no-store`.

Corrections suppress the previous text/source fingerprint. Deletions remove the canonical record and suppress its last fingerprint. Audit rows retain action metadata, not memory text. This prevents identical content from being silently recreated through this API. Explicit restoration is not implemented yet.

Search currently uses canonical PostgreSQL records and literal substring matching. Embeddings, semantic retrieval, diary/chat records and their derived copies are not implemented. Deletion does not erase nonexistent future layers, source applications, or old operating-system backups. Backup expiry and deletion propagation through those future layers remain beta requirements.

## Verify

```sh
JUNO_TEST_ADMIN_URL="$(python3 scripts/dev_database.py url)" .venv/bin/python -m unittest discover -s backend/tests -v
.venv/bin/python -m pip check
```

The integration suite creates a uniquely named `juno_test_*` database, applies the real Alembic migration, runs synthetic scenarios, and drops only that database. It does not clear `juno_dev`. Without `JUNO_TEST_ADMIN_URL`, integration tests are explicitly skipped; a connector-only run is not full verification.

The client/restart tests simulate two clients against the same service/database. They do not establish actual two-Mac networking, credential storage, deployment, or synchronization UI behavior.

After stopping the API, stop the developer database with:

```sh
python3 scripts/dev_database.py stop
```
