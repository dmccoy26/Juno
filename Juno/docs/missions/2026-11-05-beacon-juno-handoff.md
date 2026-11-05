# Beacon mission — Give Juno authoritative equipment evidence

**Outcome**

Juno can trace a printer alert to a durable Beacon issue, connect that issue to the correct TaskDock repair task, and report recovery when Beacon records a successful verification.

## 1. Ship the read contract for the printer pilot

- Extend Beacon’s authenticated alert feed while preserving compatibility with existing schema-1 readers. Publish the contract and synthetic fixtures before the joint pilot. Include a stable source `instance_id` and stable alert, asset and issue IDs. Keep IDs stable across renames, room changes, restarts and refreshes. Define what happens when a record is withdrawn, merged or replaced.
- Provide a record revision, update and observation timestamps with timezone, and a permission-checked source link. Make a resolved issue and its verification retrievable by ID after its alert leaves the active feed. Coordinate this lookup or snapshot extension with Juno so a disappearing alert can be reconciled.
- Publish issue state, verification state, service impact and decision authority as separate fields. Confirm the vocabulary and policy with the owning team. Represent missing facts as unknown. For verified recovery, provide the verification record ID, matching asset ID, responsible actor ID, observation time and method. Define what counts as a successful verification for a printer. Juno’s current reader already accepts `verification_record` with `record_id`, `asset_id`, `actor_id`, `observed_at` and `method`.
- Define the reference TaskDock will store for the repair task. Use Beacon instance, asset and issue IDs as the durable identity, with the alert ID as evidence. Keep labels and links as display metadata.

## 2. Add the evidence for lifecycle planning

Expose authorized, dated asset condition, maintenance and repair history, available usage indicators, lifecycle or replacement policy references, and cost evidence with currency and source. Separate estimates from actual costs. Give each fact its own timestamp or revision and distinguish unavailable, restricted and stale inputs. Supply designated procedure references and version metadata where Beacon owns the procedure.

## Acceptance

- A scoped Juno reader can retrieve the same printer issue after an asset rename and after the issue leaves the active alert feed.
- Closing its TaskDock task leaves Beacon’s verification state intact. A failed check leaves recovery unconfirmed. A later successful check supplies proof for the correct asset, and a check on another asset cannot satisfy it.
- Test revoked access, stale revisions, incomplete feeds and producer failure. Juno can identify each condition and retain the last good evidence when appropriate. A failed read cannot appear as a successful empty feed.
- Run the joint pilot with one authorized printer and one linked TaskDock task. Return the contract version, fixture set, pilot evidence and remaining gaps. Separate synthetic results from live acceptance.

[Shared Juno contract](../OPERATIONAL-CONNECTION-CONTRACT.md) · [Mission 13 acceptance ledger](2026-11-04-13-operational-evidence.md)
