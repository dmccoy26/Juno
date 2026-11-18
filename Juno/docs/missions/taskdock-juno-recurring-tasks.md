# TaskDock handoff — Juno-managed recurring tasks

November 18, 2026. Proposed contract; these capabilities and operations must be verified in TaskDock before Juno enables recurring writes. Companion to [Juno Mission 16](2026-11-18-16-workspace-redesign-and-recurring-tasks.md).

## Outcome and ownership

Juno schedules approved recurring routines. TaskDock creates and owns the resulting native task cards in one explicitly approved workspace and column named **Juno**. TaskDock remains authoritative for assignments, due dates, progress, closure and task history. Juno stores recurrence definitions and occurrence receipts. TaskDock does not run a competing scheduler for the same routines.

## Required interface

1. Advertise versioned, individually grantable capabilities for column discovery/create, managed native task create/read, operation lookup and any supported update/complete action. Keep current Juno read access read-only. Unsupported actions must remain disabled in Juno.
2. Discover stable TaskDock instance, workspace and column IDs. Show all matching Juno columns. Create a column only after explicit setup approval; do not select an arbitrary duplicate name or alter an existing unrelated column. Column creation itself needs idempotency and permission checks.
3. Issue a separate revocable grant restricted to the acting owner, instance, workspace, exact Juno column and Juno-managed native tasks. Enforce the restriction server-side. Never let caller-supplied metadata turn an arbitrary task into a managed task. A moved managed task remains readable if authorized, but writes outside the grant are denied. No provider credentials, Smartsheet writeback, backup or general administration access.
4. Accept a reviewed task title, description/checklist, occurrence/due dates, optional allowed assignee and exact room references, plus Juno routine ID, rule revision and occurrence key. Validate lengths, timestamps, assignees and scope. Optional fields must not require invented information. Create through TaskDock's normal history/audit path.
5. Enforce durable uniqueness of owner/instance/workspace/routine/occurrence identity. Retry with the same operation ID and payload returns the same receipt. Different payload under the same ID returns conflict. A new transport request ID must not defeat occurrence uniqueness. Persist a payload fingerprint, resulting task ID, revision, target and operation state transactionally.
6. Provide authorized lookup by operation ID and by occurrence identity. Return pending, applied, rejected or unknown explicitly. A timeout does not establish failure. Document retention sufficient for late retries, host backup restoration and recurrence lifetime. Keep minimal deduplication tombstones after deletion; do not purge them while replay remains possible.
7. Return a receipt with task link/ID, actual column, saved revision, saved fields and audit reference. Include occurrence metadata in authorized task reads and history so Juno can reconcile a lost response. Include cancellation/deletion/move state without exposing unauthorized text.
8. For updates or completion, require expected revision and validate the still-current grant and target at commit. Expose field ownership/conflicts. Juno must review changes to an existing occurrence; it cannot silently overwrite human edits or mark task completion from a model inference. Human deletion does not authorize automatic recreation. Physical repair verification is separate from task closure.
9. Revoke grants immediately, including after client profile restoration. Check owner/scope on every direct-ID request. Log the actual acting integration and user without logging credentials or private report content.

Juno's scheduler is host-only and uses durable local claims, but TaskDock's transactional uniqueness is still required. Define exact URLs and JSON schemas in TaskDock's implementation; no endpoint in this document is an assertion of an existing API. Preserve backward compatibility with the current read connector and sharing-version checks.

## Required tests and handback

- Authorized column setup and one managed task; duplicate column names require explicit choice.
- Same operation retry, changed payload conflict, new operation for the same occurrence, simultaneous requests and interrupted commit/reply.
- Operation lookup after service restart and client/host backup restoration; retention and tombstone behavior after task deletion.
- Wrong/revoked grant, read-only credential, owner, instance, workspace, column and direct task IDs. Changing column scope must not widen an existing grant.
- Existing imported task and unrelated native task cannot be edited, tagged as managed, completed or moved through this interface.
- Manual rename, due/assignment edit, column move, completion and deletion remain authoritative; stale-revision updates fail.
- Stable IDs and occurrence receipts survive task rename and normal backup/restore; source sharing controls continue to apply.

Return the versioned schemas, capability names, permission setup path, synthetic fixtures and scoped test results, plus the supported TaskDock versions. Coordinate one explicit live routine pilot with Juno. Never enable a financial action, email send or upstream source refresh as a side effect of this grant.


## November 18 dependency recheck

Installed TaskDock still advertises `write_tasks:False`. Juno 0.2.25 is installed and its physical Air sync check passed; the live Juno-column pilot remains blocked on this contract. This recheck changed only Juno documentation; the owning application was not modified.


## Optional local bridge acceptance

`backend/tests/test_routine_bridge.py` uses disposable databases and a separate TaskDock development checkout. Set `JUNO_TEST_ADMIN_URL` to the isolated PostgreSQL test administrator, `JUNO_TASKDOCK_CHECKOUT` to that checkout and `JUNO_TASKDOCK_PYTHON` to its virtual-environment Python. Without a local TaskDock checkout/runtime these optional tests skip explicitly. They never discover or use an installed production TaskDock workspace.
