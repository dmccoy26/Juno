# TaskDock → Juno: read-only integration handoff

Historical request sent to TaskDock. Its API v1 handoff has now been implemented in Juno preview 3; see [current connection instructions](TASKDOCK-CONNECTION.md).

Build a supported, locally paired, read-only integration for Juno. TaskDock remains the task system of record. Juno supplies conversation, memory, estimates and planning. Do not add an LLM to TaskDock for this integration.

## Start from the existing API

The current TaskDock source already exposes:

- `GET /workspace/tasks` — combined local/imported tasks, subtasks, filters, pagination and consistent snapshot checking.
- `GET /workspace/tasks/{id}` — task details, child pagination and initial update/activity pages.
- `GET /workspace/tasks/{id}/timeline` — paginated updates or activity.

Do not build a second task database or duplicate these task endpoints. `/tasks` alone is insufficient because it excludes native workspace tasks. Juno already has a tested reader for `/workspace/tasks` in its `backend/src/juno/taskdock.py`.

## Add explicit read-only pairing

Add a Juno integration section in TaskDock Settings. The user should be able to enable the integration, create a dedicated token, copy the loopback API address/token, and revoke the token. A reveal/copy action should be deliberate; never put credentials in logs or URLs.

The new credential must be separate from `UNIFIED_API_TOKEN` and provider credentials. Enforce its limited scope on the server, even if the existing general API gate is optional. Store only a secure token hash, persist it across restarts, support revocation, and compare securely.

Allow only the supported task-read endpoints, sanitized integration metadata and sanitized source-freshness metadata. Deny writes and access to configuration, credentials, OAuth operations, backups/restores, exports containing unrelated data, sync controls, and admin endpoints. A task read must not trigger upstream synchronization or source writeback. Preserve the existing dashboard/general-API behavior.

## Add a small discovery endpoint

Proposed endpoint: `GET /integrations/juno/v1/info`.

Return an integration API version, TaskDock release/build, stable workspace identity, installation/device identity, and capabilities. Advertise `read_tasks=true`, supported history reads, and `write_tasks=false`.

Use an existing persistent workspace/sync identity if suitable. Otherwise add a persistent workspace UUID; do not derive it from a hostname, account email or filesystem path. Distinguish a workspace from a device so Juno can recognize separate installations and avoid merging unrelated workspaces. Document how identities behave through backup/restore and TaskDock's own synchronization.

Provide sanitized definitions for statuses, categories and custom fields: IDs, labels, types, relevant choices and status behaviors. Include the actual priority-number meanings. Juno must not guess what opaque custom-field IDs or numeric priority values mean. Definitions can be in this response or a documented, separately scoped read endpoint.

## Freeze and document the task-read contract

Preserve existing native/imported IDs and parent links. Include available fields already exposed by the workspace:

- ID, parent ID/title, native/imported source identity and source link.
- Title, description, owner, priority and start/due dates.
- Status ID/name, normalized behavior, source completion and completion timestamp when known.
- Category, tags and custom values with field definitions.
- `blocked_reason`, `blocked_since`, latest update and update/activity history.
- Created/updated/change timestamps and record version.

Document null/unknown meanings, date-only versus timestamp semantics, and whether timestamps include an offset. Preserve source completion authority. Do not invent room locations, employees, approval status, completion dates or estimates when the source does not record them. Estimates can remain entirely in Juno for this phase.

Existing pagination contract to preserve: `items`, `total`, `limit`, `offset`, `has_more`, `snapshot`. Juno requests completed tasks, excludes archived tasks, includes subtasks, and fetches every page. Later pages pass the first page's `expected_snapshot`. Return HTTP 409 if that snapshot changed; never silently return a mixed revision. Document history cursor semantics and task-removal/archive behavior. A successful complete snapshot is authoritative for its documented scope; Juno will not treat a failed refresh as an empty task list.

Include source last-success/last-attempt times and health without leaking credentials or raw sensitive error payloads. A recent API read is not proof that TaskDock recently refreshed the original email/Slack/Smartsheet source.

## Networking and scope

Keep the API on loopback for this phase. The Mac running both applications can read TaskDock locally. Do not expose TaskDock publicly, weaken origin/host checks, copy its database to Juno, or reuse another application's OAuth tokens.

Juno owns its connector UI, Keychain storage for the integration token, normalized snapshots, stale-data indicators and model context. If TaskDock is unavailable or its computer is off, Juno uses a clearly dated last successful snapshot. Neither a local API nor this handoff provides cross-device synchronization; no cloud deployment is requested here.

## Acceptance and delivery

Use a disposable database and synthetic records for tests. Verify local/imported tasks, subtasks, completed/archived cases, blockers, custom-field definitions, pagination, snapshot conflicts, stable identities, source freshness, and missing values. Verify missing/invalid/revoked credentials are rejected and the integration credential cannot read secrets or perform any mutation.

Deliver the TaskDock changes, API documentation/sample JSON, synthetic fixtures and passing tests. Provide a new TaskDock app/installer build if required; editing its source checkout alone does not update `/Applications/TaskDock.app`. Report the exact installed release/build to test against.

Keep task writes, email sending, webhooks, incremental feeds and remote hosting out of this first integration. Future writes will require a separate scope and explicit approval workflow in Juno.
