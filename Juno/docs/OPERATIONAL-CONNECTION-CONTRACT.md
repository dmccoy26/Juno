# Cross-app operational contract — proposed extensions and verified boundaries

Status: consumer implementation/fixtures available in Juno; producer agreement and joint validation are pending. This document does not grant access or claim another app implemented these fields.

Inspected read-only on November 4, 2026:

- TaskDock checkout `/Users/dmccoy/bin/python/TaskDock`, HEAD `ebf8345`, `api/unified_tasks/juno.py`: dedicated Juno task-read scope; advertised `write_tasks: false`. The middleware restricts that token to the existing read routes. General workspace endpoints and owner credentials are not substitutes for a Juno write contract.
- Beacon checkout `/Users/dmccoy/bin/python/MacLabInventoryServer`, HEAD `611c61b`, `beacon/reporting/alerts.py`: authenticated complete schema-1 `/api/alerts`; failure returns 503 rather than an empty success. Alert hashes and relative app links exist. Stable asset/issue IDs, durable issue lifecycle, structured service impact/authority and verified recovery are not emitted by this producer function.

The TaskDock TD-05/06/07/09/10 labels in the mission do not establish completed APIs. Exact qualifications, milestone, acknowledged-issue relationship and Juno write endpoints could not be verified in the inspected Juno contract. Producer repository edits and live institutional key/consent configuration are outside this Juno code change.

## Shared ownership and identity contract

1. TaskDock owns tasks, assignments, checklist completion, approvals, projects and handoffs. Beacon owns physical resources, condition, stock, maintenance, reservations and loans. Juno owns preferences/proposed plans/accepted planning history. Copies are dated evidence or references, not independently editable operational records.
2. Stable source-scoped person, team, room, asset, issue, task and reservation IDs must be supplied. TaskDock must designate the authoritative person/team source. Names/email/room aliases are display context, never cross-app join keys. Current Juno reviewed links use `(Beacon alert ID, TaskDock workspace ID, TaskDock task ID)`; a live durable asset/issue pilot still needs producer references.
3. Future events require event ID/type, source app, record ID/version, occurrence time and correlation ID. Repeated events must be idempotent; older versions cannot replace newer materialized facts. No event subscriber is introduced by this change; current complete snapshots and revision fences remain authoritative.
4. Delivery requires acknowledgement, bounded retries, visible terminal/uncertain failures and periodic reconciliation against an authorized complete snapshot. Current readers retain the last good copy on failed/partial reads. Future write/event retry semantics require joint producer tests; Juno does not invent an endpoint or replay an uncertain operational action.
5. Each owning app enforces user-scoped permissions including Juno-originated requests. Dedicated read credentials are not upgraded. Student access stays scoped to operationally necessary records; new owner briefing routes are not worker routes.
6. Audit evidence retains actor/time/source/reference versions, material reviewed changes and source timestamps. Local feedback is distinct from task action audit. Saved draft source changes never replace user edits.
7. Reuse existing authenticated interfaces and deployment constraints. No direct cross-app database writes, provider-secret imports, unapproved cloud fallback or new network infrastructure.

## Beacon consumer extension proposal

Schema-1 alert fields remain required and compatible. The consumer can additionally retain bounded strings `asset_id`, `issue_id`, `record_version`, `updated_at`, and these strict optional states:

- `issue_state`: unknown / acknowledged / open / resolved.
- `verification_state`: unknown / pending / failed / verified_recovered.
- `service_impact`: unknown / none / degraded / unavailable.
- `decision_authority`: unknown / none / department_lead.

These are proposed vocabulary, not agreed institutional policy. Unknown is the default; issue resolution is not recovery verification. A production verified-recovery claim also needs a producer verification record ID, scope, observed time, responsible actor and method; this consumer's optional state alone does **not** satisfy the final printer-pilot gate. Producers must agree how permission/version changes withdraw those facts. Relative app paths may be preserved, but arbitrary URLs, attachments and document instructions are never fetched automatically.

## TaskDock write release — intentionally unavailable

Do not enable writes until a supported Juno-specific contract supplies:

- user-scoped create/delegate/deadline permissions and stable person/team identity mapping;
- target record/version and a preview of material effect;
- durable idempotency/correlation key and a status/receipt lookup for uncertain delivery;
- conflict/revocation responses, saved record ID/link and bounded reconciliation semantics;
- producer fixtures for replay, changed payload, stale revision, lost response and permission withdrawal.

Then build a separate write release after validating the read-only printer pilot. Never use a general admin token or a direct database update as a workaround. Equipment/access/purchasing/financial decisions remain excluded.
