"""Durable recurrence ledger with leases, retained receipts and reviewed TaskDock delivery.

The native work host supplies a separate scoped credential for each bounded tick.
Remote lookups precede retries; known tasks are never silently recreated.
"""
from dataclasses import dataclass
from copy import deepcopy
from datetime import date, timedelta, timezone
import hashlib
import json
from uuid import NAMESPACE_URL, uuid4, uuid5
from zoneinfo import ZoneInfo
from sqlalchemy import select
from .models import RecurringRoutine, RoutineRuleVersion, RoutineOccurrenceRecord as Occurrence
from .recurring import RoutineInput, creation_at, matches


OPEN = {'planned', 'in_flight', 'unknown', 'created', 'deferred'}
TARGET_KEYS = {'owner_id', 'instance_id', 'workspace_id', 'column_id'}


def checked_scope(owner, value):
    if not isinstance(value, dict) or set(value) != TARGET_KEYS or value.get('owner_id') != owner:
        raise ValueError('An approved exact owner/instance/workspace/column target is required.')
    if not all(isinstance(v, str) and 0 < len(v) <= 500 and not any(ord(c)<32 or ord(c)==127 for c in v) for v in value.values()):
        raise ValueError('Invalid delivery target.')
    return dict(value)


def period_key(rule, day):
    # Monthly date/ordinal edits cannot create a second task for an already
    # represented month. Daily/selected-weekday occurrences retain their date.
    return day.strftime('month:%Y-%m') if rule.frequency in {'monthly','ordinal'} else 'day:' + str(day)


def occurrence_id(owner, routine, scope, period):
    # Exclude rule revision, grant rotation and column changes from identity.
    return str(uuid5(NAMESPACE_URL, json.dumps([owner, routine, scope['instance_id'], scope['workspace_id'], period])))


def plan_due(factory, owner, identity, at, *, limit=1000):
    if at.tzinfo is None or not 1 <= limit <= 1000: raise ValueError('Use an aware clock and bounded batch.')
    at=at.astimezone(timezone.utc)
    if not 2000 <= at.astimezone(ZoneInfo('America/Chicago')).year <= 2098: raise ValueError('Clock is outside the supported scheduling range.')
    with factory() as session:
        routine = session.scalar(select(RecurringRoutine).where(RecurringRoutine.owner_id == owner,
            RecurringRoutine.id == identity).with_for_update())
        if routine is None or routine.status != 'active': return {'planned':0,'more_due':False,'state':'not_active'}
        if routine.activated_at is None: raise ValueError('An explicitly reviewed activation boundary is required.')
        scope = checked_scope(owner, routine.target_scope)
        from .recurring import retain_rule
        retain_rule(session,routine,'planning_boundary')
        rule = RoutineInput.model_validate(routine.definition)
        today = at.astimezone(ZoneInfo(rule.timezone)).date()
        first = max(rule.start_date, routine.activated_at.astimezone(ZoneInfo(rule.timezone)).date())
        if routine.last_planned_date: first = max(first, routine.last_planned_date + timedelta(days=1))
        last = min(today, rule.end_date or date(2098,12,31))
        due = []
        day = first
        while day <= last:
            if matches(rule, day) and creation_at(rule, day).astimezone(timezone.utc) <= at: due.append(day)
            day += timedelta(days=1)
        if not due: return {'planned':0,'more_due':False,'state':'current'}
        existing = session.scalars(select(Occurrence).where(Occurrence.owner_id == owner,
            Occurrence.routine_id == identity)).all()
        known = {row.id for row in existing}
        prior_open = any(row.status in OPEN for row in existing)
        count = 0
        for day in due[:limit]:
            period = period_key(rule, day)
            key = occurrence_id(owner, identity, scope, period)
            if key not in known:
                status, reason = 'planned', 'Due occurrence; awaiting scoped delivery.'
                if rule.missed_policy == 'latest' and day != due[-1]:
                    status, reason = 'skipped', 'Reviewed latest-missed policy coalesced this occurrence.'
                elif rule.missed_policy == 'skip' and day < today:
                    status, reason = 'skipped', 'Reviewed skip-missed policy excluded an earlier local date.'
                elif rule.overlap_policy == 'wait' and prior_open:
                    status, reason = 'deferred', 'Previous work remains open or its delivery outcome is unknown.'
                payload = {'routine_id':identity, 'rule_revision':routine.revision, 'occurrence_key':period,
                           'title':rule.title, 'description':rule.description, 'rule':rule.model_dump(mode='json'), 'occurrence_date':str(day),
                           'due_date':str(day + timedelta(days=rule.due_offset_days)), 'target':scope}
                fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
                session.add(Occurrence(id=key, owner_id=owner, routine_id=identity, rule_revision=routine.revision,
                    local_date=day, period_key=period, scheduled_at=creation_at(rule,day), due_date=day+timedelta(days=rule.due_offset_days),
                    target_scope=scope, payload=payload, payload_hash=fingerprint, operation_id=str(uuid5(NAMESPACE_URL,key)),
                    status=status, reason=reason, updated_at=at))
                known.add(key); count += 1
                if status in OPEN: prior_open = True
            routine.last_planned_date = day
        session.commit()
        return {'planned':count,'more_due':len(due)>limit,'state':'recorded'}


def release_deferred(factory, owner, identity, at):
    """Apply the reviewed missed policy after prior work is confirmed finished."""
    if at.tzinfo is None: raise ValueError('Use an aware clock.')
    at=at.astimezone(timezone.utc)
    with factory() as session:
        routine = session.scalar(select(RecurringRoutine).where(RecurringRoutine.owner_id==owner,
            RecurringRoutine.id==identity).with_for_update())
        if routine is None or routine.status != 'active': return 0
        rows = session.scalars(select(Occurrence).where(Occurrence.owner_id==owner,
            Occurrence.routine_id==identity).order_by(Occurrence.scheduled_at)).all()
        if any(row.status in OPEN - {'deferred'} for row in rows): return 0
        waiting = [row for row in rows if row.status=='deferred']
        if not waiting: return 0
        latest = {row.rule_revision:row.id for row in waiting}
        selected=[]
        for row in waiting:
            history=session.get(RoutineRuleVersion,(owner,identity,row.rule_revision))
            if history is None: raise ValueError('Original rule revision is unavailable; review deferred work.')
            rule=RoutineInput.model_validate(history.definition)
            today=at.astimezone(ZoneInfo(rule.timezone)).date()
            skip=(rule.missed_policy=='skip' and row.local_date<today or
                  rule.missed_policy=='latest' and row.id!=latest[row.rule_revision])
            if skip:
                row.status='skipped';row.reason='Original reviewed missed-run policy coalesced or skipped deferred work.'
            elif rule.overlap_policy=='allow' or not selected:
                row.status='planned';row.reason='Prior work finished; deferred occurrence released.';selected.append(row)
            row.updated_at=at
        session.commit();return len(selected)


class DeliveryConflict(Exception):pass


@dataclass(frozen=True)
class Lookup:
    state: str  # absent, pending, found, denied
    receipt: dict | None = None


def _owned(session, owner, identity):
    routine_id=session.scalar(select(Occurrence.routine_id).where(Occurrence.id==identity, Occurrence.owner_id==owner))
    if routine_id is None: return None
    # Match planner/lifecycle lock ordering: routine first, occurrence second.
    routine=session.scalar(select(RecurringRoutine).where(RecurringRoutine.id==routine_id,
        RecurringRoutine.owner_id==owner).with_for_update())
    if routine is None: return None
    return session.scalar(select(Occurrence).where(Occurrence.id==identity, Occurrence.owner_id==owner).with_for_update())


def deliver(factory, owner, identity, writer, at):
    """Lookup before retry, durable lease, unchanged operation/payload on replay.

    `writer` is an explicit adapter implementing lookup(scope, operation_id, routine_id,
    occurrence_key) and create(scope, operation_id, payload). The native work host
    supplies the scoped adapter; TaskDock also enforces occurrence uniqueness.
    """
    if writer is None: return 'disabled'
    if at.tzinfo is None: raise ValueError('Use an aware clock.')
    at=at.astimezone(timezone.utc)
    lease = str(uuid4())
    with factory() as session:
        row = _owned(session, owner, identity)
        if row is None: return 'not_found'
        if row.status in {'completed','skipped','cancelled','conflict','deferred'}: return row.status
        if row.lease_expires and row.lease_expires > at: return 'leased'
        routine = session.get(RecurringRoutine,row.routine_id)
        can_create = routine is not None and routine.owner_id==owner and routine.status=='active' and routine.target_scope==row.target_scope and row.task_id is None
        if row.status=='planned' and not can_create: return 'not_active'
        scope=checked_scope(owner,row.target_scope)
        expected_hash=hashlib.sha256(json.dumps(row.payload,sort_keys=True).encode()).hexdigest()
        if row.payload_hash != expected_hash:
            row.status='conflict';row.reason='Stored delivery payload changed; review required.';session.commit();return 'conflict'
        row.status='in_flight'; row.lease_id=lease; row.lease_expires=at+timedelta(seconds=30);row.updated_at=at
        operation, payload, known_task = row.operation_id, dict(row.payload), row.task_id
        session.commit()
    try:
        outcome=writer.lookup(deepcopy(scope),operation,payload['routine_id'],payload['occurrence_key'])
        if outcome.state in {'absent','retryable'} and can_create:
            # Pause/re-target after the claim must stop new create calls.
            with factory() as session:
                routine=session.get(RecurringRoutine,payload['routine_id'])
                can_create=bool(routine and routine.owner_id==owner and routine.status=='active' and routine.target_scope==scope and known_task is None)
            if can_create: outcome=writer.create(deepcopy(scope),operation,deepcopy(payload))
        if outcome.state=='found':
            receipt=outcome.receipt or {}
            valid=(receipt.get('scope')==scope and receipt.get('operation_id')==operation
                   and receipt.get('routine_id')==payload['routine_id'] and receipt.get('occurrence_key')==payload['occurrence_key']
                   and isinstance(receipt.get('task_id'),str) and 0<len(receipt['task_id'])<=500
                   and not any(ord(c)<32 or ord(c)==127 for c in receipt['task_id'])
                   and isinstance(receipt.get('completed',False),bool) and isinstance(receipt.get('deleted',False),bool))
            result='conflict' if not valid else 'cancelled' if receipt.get('deleted') else 'completed' if receipt.get('completed') else 'created'
            reason='Receipt scope or identity mismatch; no retry.' if not valid else 'Human-deleted task will not be recreated.' if result=='cancelled' else 'Scoped task reconciled; human edits and moves are retained.'
        elif outcome.state=='denied': result,reason='failed','Scoped access was denied; delivery requires review.'
        else: result,reason='unknown','Remote outcome is unknown or pending; lookup before any retry.'
    except DeliveryConflict:
        result,reason='conflict','TaskDock occurrence or approval changed; review before any new delivery.';outcome=Lookup('pending')
    except PermissionError:
        result,reason='failed','Scoped access was denied; delivery requires review.';outcome=Lookup('denied')
    except Exception:
        # A timeout after remote commit is not proof the operation failed.
        result,reason='unknown','Delivery receipt unavailable; reconcile the same operation before retry.';outcome=Lookup('pending')
    with factory() as session:
        row=_owned(session,owner,identity)
        if row is None or row.lease_id!=lease: return 'claim_changed'
        row.status=result;row.reason=reason;row.updated_at=at;row.lease_id=None;row.lease_expires=None
        if result in {'created','completed','cancelled'}: row.task_id=outcome.receipt['task_id']
        if outcome.state=='denied' or result=='conflict':
            routine=session.get(RecurringRoutine,row.routine_id)
            if routine and routine.owner_id==owner and routine.status=='active' and routine.target_scope==row.target_scope:
                from .recurring import retain_rule
                retain_rule(session,routine,'preserved_before_access_loss')
                routine.status='paused';routine.revision+=1;routine.updated_at=at
                retain_rule(session,routine,'access_denied')
        session.commit()
    return result
