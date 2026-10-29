# TaskDock connection — Juno preview 3

Preview 4 adds the user-approved work-Mac/laptop deployment; see [current shared-host instructions](SHARED-HOST.md). The synthetic-workspace checkbox described below belonged to preview 3 and was removed after that explicit approval. The acceptance evidence below remains historical.

Juno is a standalone native Mac app. TaskDock stays the task system of record. This preview adds local, manually refreshed, read-only TaskDock snapshots to Juno's task view and local-model chat. It is still for synthetic workspaces only.

## Pairing

1. Install TaskDock **0.2.0-beta.3 build 13** (or a compatible later API v1 build). Source changes do not update an installed app. The supplied build 13 installer was inspected and extracted for disposable testing; the existing installed TaskDock was left untouched.
2. In TaskDock, open **Settings → Connections → Juno · read-only task access**. Enable access and create a dedicated token.
3. In Juno's **TaskDock** tab, paste the local API address displayed by TaskDock and the dedicated token. The usual address is `http://127.0.0.1:8100`, not the dashboard's port 3100. Confirm the workspace contains synthetic test data.
4. Choose **Connect / refresh snapshot**, review the workspace and installation identities, then choose **Use this workspace and installation**.
5. Juno saves the token in macOS Keychain. Later refreshes can leave the token field blank. Never paste the token into chat, documentation or a support report.

Each Mac pairs independently. The token uses a non-synchronizing, when-unlocked, device-only Keychain item; development and packaged apps use distinct Keychain services. An ad hoc signing update may cause macOS to request Keychain access again. No global API token, provider credential or TaskDock database is read.

**Forget saved token** removes Juno's local credential, while saved snapshots remain. Revoke access in TaskDock to invalidate the credential. Replacement/revocation never causes an unauthenticated or global-token fallback.

## What is implemented

- API v1 discovery, capability checks, actual definitions, and workspace/device identity checks. First pairing and any changed identity require explicit native review. Identity changes during a read cannot publish a snapshot.
- Full collection scope: completed tasks included, archived tasks excluded, subtasks included, parents-only disabled. The 500-item pages use the same snapshot revision. Conflicts restart the entire staged read up to three times; malformed/duplicate/cyclic/partial results are rejected.
- Atomic, owner-scoped PostgreSQL snapshot promotion. Failed reads keep the last complete snapshot and mark it stale. Prior snapshots remain separately available through the owner-authenticated snapshot API, including after a workspace switch. The native task view shows the active snapshot; an archive browser is not yet implemented.
- Distinct Juno read time and recorded TaskDock provider health/last-success times. A snapshot older than 15 minutes or with a failed refresh is labeled stale. There is no background polling; TaskDock quitting is detected on the next requested read. A recent Juno read does not establish fresh provider data.
- Native task filtering and safe plain-text detail display, including recorded blockers, parent links, dates, source completion flags and custom-field labels. Original task records are retained. Rich content is displayed as text, never executed as HTML or followed as a link. A formatted rich-text renderer remains future work.
- On-demand update/activity history, capability-gated and cursor-paged with duplicate/non-advancing detection. Cursor conflicts restart history up to three times. Complete history reads are dated and cached independently for the selected snapshot/task/kind. Failed reads retain the last cache; updates load from the cache when selecting a task. Activity can be re-read using its button. History is not frozen by the collection snapshot.
- Local chat receives at most eight selected task excerpts, the snapshot date, stale status, source freshness and bounded definition context. Task excerpts use simple keyword matching, not embeddings or a full workload optimizer. No token is included. The prompt treats source text as untrusted evidence and labels estimates as suggestions. Unsupported schedules, employee skills and approvals remain unknown.
- Replies derived from an older task snapshot are invalidated on refresh or a refresh failure. The backend checks context again after model generation so an in-flight answer cannot publish against changed task context.

Only dedicated authenticated GET requests go to TaskDock's supported read paths. The connector rejects remote HTTP **and HTTPS**, credential-bearing URLs and paths; disables environment proxies; blocks redirects; and sends no browser Origin header. Juno's own authenticated service receives the token transiently for a requested read, but has no credential column or credential logging.

## Evidence and limits

The supplied synthetic API JSON is preserved in `backend/tests/fixtures/taskdock-v1.json`. Its example collection uses limit 100; test transport adapts it to the connector's requested limit 500 without changing the recorded task fields.

- 41 automated tests pass, including actual disposable PostgreSQL migrations, owner isolation, concurrent refresh protection, stale context rejection, history persistence, complete pagination, and real HTTP redirect/proxy exclusion.
- `scripts/verify_taskdock_connector.py` exercised Juno's reader over real loopback HTTP against the **extracted build 13 installer**, with its bundled runtime and disposable Student Test data. Discovery, native/subtask hierarchy, updates/activity and revoked-token rejection passed. Report: `docs/reports/taskdock-build13-reader.json`.
- TaskDock candidate SHA-256 matched the handoff: `4802a2a08700c2c1e33f0631a64cf0f80d15ce1e9307fb9062ef1c8477d2e655`.
- Native preview 3 compiled and opened; the TaskDock screen and missing-token guidance were verified through the native UI. Keychain write/read/replace/remove passed with an isolated synthetic credential. This is not a claim of completed native pairing to the installed TaskDock.
- Packaged app checks are recorded separately in `docs/reports/installer-preview-3.json`.

Actual installed-app pairing with TaskDock build 13, real M5 laptop installation, institution-approved real-data use, cross-device synchronization, calendar access, automatic workload planning and native HumanLab acceptance remain unverified or unimplemented.

The installer remains an unsigned internal package containing an ad hoc signed app, without Developer ID signing or notarization. Use the institution's normal software approval process.
