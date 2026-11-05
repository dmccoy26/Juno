# TaskDock mission — Give Juno planning facts and reviewed task actions

**Outcome**

Juno can read the TaskDock repair task associated with a Beacon issue, build proposals from authorized staffing and project facts, and apply a reviewed task change with a verifiable receipt.

## 1. Ship the read contract for the printer pilot

- Extend the scoped Juno interface with a persisted, permission-checked reference to the Beacon instance, asset and issue. Include the alert ID when available. Expose the TaskDock workspace ID, task ID, revision, status, assignment, due date and source link. Preserve the relationship through task edits, renames and closure.
- Expose the work TaskDock can confirm, including task closure and any task-side acknowledgement. Keep Beacon’s equipment condition and recovery evidence separately referenced.
- Identify the authoritative source for people and teams. Supply stable person/team IDs, qualification and supervision rules, and coverage, hours or availability where TaskDock is authoritative. Include effective dates and revisions. Provide stable project and milestone IDs, status, due dates and links for Dean drafts. Identify external owners for inputs TaskDock cannot supply.
- Publish capability discovery, field-level permission behavior, and explicit unavailable or restricted states. Preserve existing read clients and scope. Provide designated procedure references and versions where TaskDock owns them.

## 2. Ship a separate write contract after the read-only pilot

- Provide Juno-specific, user-scoped actions for task creation, assignment or delegation, and deadline changes. Advertise each capability separately. TaskDock must validate the acting user, workspace, target, assignee, action permission and expected revision when applying the action.
- Define a preview and explicit confirmation flow. The preview shows the proposed change and its target. A changed task or expired preview requires a fresh review. Keep equipment, access, purchasing and financial decisions with their respective owners.
- Use a durable idempotency key tied to the action payload and scope. The same key and payload return the same result. A changed payload with the same key returns a conflict. Supply a permission-checked status lookup so Juno can reconcile a lost response before retrying. Return a receipt with the saved task ID/link, resulting revision and audit reference. Document the retention window and outcomes for pending, applied, rejected and unknown requests.

## Acceptance

- Complete the shared printer pilot against authorized live records. Juno can trace Beacon’s issue to the exact TaskDock task, distinguish closure from verification and show the effect of a withdrawn relationship or permission.
- Test duplicate names, cross-workspace IDs, missing or expired qualifications, and unavailable staffing and milestone data. Juno receives enough information to withhold unsupported proposals and report the gap.
- For each write action, test authorized success, denied access, revoked permission after preview, stale revision, concurrent changes, exact retry, changed payload under the same key and a lost response after commit. Confirm the task changes at most once and that lookup recovers the original receipt.
- Return the versioned interface, synthetic fixtures, permissions, test results and live pilot evidence. Keep write capability disabled until the joint write acceptance passes.

[Shared Juno contract](../OPERATIONAL-CONNECTION-CONTRACT.md) · [Mission 13 acceptance ledger](2026-11-04-13-operational-evidence.md)
