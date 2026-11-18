"""Owner-scoped routine definitions and reviewed TaskDock activation."""
import calendar
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from pydantic import Field, model_validator
from sqlalchemy import select
from .models import RecurringRoutine, RoutineRuleVersion, RoutineOccurrenceRecord, now
from .planning import Strict


class RoutineInput(Strict):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default='', max_length=10000)
    frequency: Literal['daily', 'weekly', 'monthly', 'ordinal'] = 'weekly'
    interval: int = Field(default=1, ge=1, le=52)
    weekdays: list[int] = Field(default_factory=lambda: [0], max_length=7)
    month_day: int = Field(default=1, ge=1, le=31)
    ordinal: int = Field(default=1, ge=-1, le=5)
    weekday: int = Field(default=0, ge=0, le=6)
    month_end: Literal['skip', 'last_day'] = 'skip'
    start_date: date
    end_date: date | None = None
    creation_time: str = '09:00'
    timezone: Literal['America/Chicago'] = 'America/Chicago'
    due_offset_days: int = Field(default=0, ge=0, le=365)
    missed_policy: Literal['latest', 'all', 'skip'] = 'latest'
    overlap_policy: Literal['wait', 'allow'] = 'wait'

    @model_validator(mode='after')
    def valid(self):
        if any(not 0 <= n <= 6 for n in self.weekdays):
            raise ValueError('Use weekdays Monday through Sunday.')
        self.weekdays = sorted(set(self.weekdays))
        if self.frequency == 'weekly' and not self.weekdays:
            raise ValueError('Choose at least one weekday.')
        if self.ordinal == 0:
            raise ValueError('Choose first through fifth, or last.')
        try:
            parsed = time.fromisoformat(self.creation_time)
        except ValueError:
            raise ValueError('Use HH:MM for creation time.') from None
        if parsed.tzinfo or parsed.strftime('%H:%M') != self.creation_time:
            raise ValueError('Use HH:MM for creation time.')
        if not date(2000, 1, 1) <= self.start_date <= date(2098, 12, 31):
            raise ValueError('Use a start between 2000 and 2098.')
        if self.end_date and not self.start_date <= self.end_date <= date(2098, 12, 31):
            raise ValueError('End must follow start and be no later than 2098.')
        return self


class RoutineEdit(RoutineInput):
    expected_revision: int = Field(ge=1)


class RoutineCreate(RoutineInput):
    request_id: UUID


def matches(rule, day):
    delta = (day - rule.start_date).days
    if delta < 0 or rule.end_date and day > rule.end_date:
        return False
    if rule.frequency == 'daily':
        return delta % rule.interval == 0
    if rule.frequency == 'weekly':
        anchor = rule.start_date - timedelta(days=rule.start_date.weekday())
        return (day - anchor).days // 7 % rule.interval == 0 and day.weekday() in rule.weekdays
    months = (day.year - rule.start_date.year) * 12 + day.month - rule.start_date.month
    if months % rule.interval:
        return False
    last = calendar.monthrange(day.year, day.month)[1]
    if rule.frequency == 'monthly':
        wanted = min(rule.month_day, last) if rule.month_end == 'last_day' else rule.month_day
        return day.day == wanted
    if day.weekday() != rule.weekday:
        return False
    return day.day + 7 > last if rule.ordinal == -1 else (day.day - 1) // 7 + 1 == rule.ordinal


def creation_at(rule, day):
    zone = ZoneInfo(rule.timezone)
    local = datetime.combine(day, time.fromisoformat(rule.creation_time))
    for shift in range(181):
        candidate = (local + timedelta(minutes=shift)).replace(tzinfo=zone, fold=0)
        if candidate.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == candidate.replace(tzinfo=None):
            return candidate
    raise ValueError('Creation time could not be resolved.')


def preview(rule, after=None, count=5):
    cutoff = now() if after is None else None
    day = max(rule.start_date, after or cutoff.astimezone(ZoneInfo(rule.timezone)).date())
    result = []
    for _ in range(366 * 25):
        if day > date(2098, 12, 31) or rule.end_date and day > rule.end_date:
            break
        if matches(rule, day) and (cutoff is None or creation_at(rule, day) >= cutoff):
            result.append({'occurrence_date': str(day), 'creation_at': creation_at(rule, day).isoformat(),
                           'due_date': str(day + timedelta(days=rule.due_offset_days))})
            if len(result) == count:
                break
        day += timedelta(days=1)
    return result



def retain_rule(session, row, action):
    session.flush()
    key = (row.owner_id, row.id, row.revision)
    if session.get(RoutineRuleVersion, key) is None:
        session.add(RoutineRuleVersion(owner_id=row.owner_id, routine_id=row.id, revision=row.revision,
            definition=row.definition, status=row.status, action=action, recorded_at=row.updated_at))


class RoutineLifecycle(Strict):
    expected_revision: int = Field(ge=1)
    action: Literal['retire', 'restore']

def view(row):
    rule = RoutineInput.model_validate(row.definition)
    return {'id': row.id, 'revision': row.revision, 'status': row.status,
            'definition': rule.model_dump(mode='json'), 'next_occurrences': preview(rule) if row.status != 'retired' else [], 'updated_at': row.updated_at.astimezone(timezone.utc)}


def state(session, owner):
    rows = session.scalars(select(RecurringRoutine).where(RecurringRoutine.owner_id == owner).order_by(RecurringRoutine.updated_at.desc())).all()
    from .routine_api import connection
    conn,_=connection(session,owner)
    return {'owner_id': owner, 'items': [view(row) for row in rows], 'execution_available':bool(conn and conn.get('enabled')),
            'notice': 'Approved routines create due tasks on the work Mac; review each exact rule in TaskDock before enabling it.' if conn and conn.get('enabled') else 'Connect a separate TaskDock managed-write credential, then review and approve exact routines before enabling delivery.',
            'time_policy': 'Central time. Repeated DST times use the first occurrence; nonexistent times move forward to the first valid minute. No holiday calendar is assumed.'}


def install(app, db, device, lock_owner):
    def host(request):
        if request.scope.get('juno_lan'):
            raise HTTPException(403, 'Edit routines on the work Mac.')

    @app.get('/v1/recurring')
    def read(actor=Depends(device), session=Depends(db)):
        return state(session, actor.owner_id)

    @app.post('/v1/recurring/preview')
    def dates(value: RoutineInput, actor=Depends(device)):
        return {'items': preview(value)}

    @app.post('/v1/recurring', status_code=201)
    def create(value: RoutineCreate, request: Request, actor=Depends(device), session=Depends(db)):
        host(request); lock_owner(session, actor.owner_id)
        definition = value.model_dump(mode='json', exclude={'request_id'})
        previous = session.get(RecurringRoutine, str(value.request_id))
        if previous:
            if previous.owner_id != actor.owner_id or previous.definition != definition:
                raise HTTPException(409, 'This save identity is already used. Reload before saving.')
            return view(previous)
        if len(session.scalars(select(RecurringRoutine.id).where(RecurringRoutine.owner_id == actor.owner_id)).all()) >= 200:
            raise HTTPException(409, 'The workspace has reached its 200 routine limit.')
        row = RecurringRoutine(id=str(value.request_id), owner_id=actor.owner_id, definition=definition, status='draft')
        session.add(row); retain_rule(session, row, 'created'); session.commit()
        return view(row)

    @app.put('/v1/recurring/{identity}')
    def edit(identity: str, value: RoutineEdit, request: Request, actor=Depends(device), session=Depends(db)):
        host(request); lock_owner(session, actor.owner_id)
        row = session.scalar(select(RecurringRoutine).where(RecurringRoutine.id == identity, RecurringRoutine.owner_id == actor.owner_id).with_for_update())
        if row is None:
            raise HTTPException(404, 'Routine not found.')
        if row.status == 'retired': raise HTTPException(409, 'Restore this routine before editing its future schedule.')
        if row.revision != value.expected_revision:
            raise HTTPException(409, 'Routine changed; reload before saving.')
        if row.status=='active':row.status='paused'
        row.definition = value.model_dump(mode='json', exclude={'expected_revision'})
        row.revision += 1; row.updated_at = now()
        retain_rule(session, row, 'edited')
        session.commit()
        return view(row)


    @app.get('/v1/recurring/{identity}/history')
    def history(identity: str, offset: int = 0, actor=Depends(device), session=Depends(db)):
        if not 0 <= offset <= 100000: raise HTTPException(422, 'Choose a valid history page.')
        row = session.scalar(select(RecurringRoutine).where(RecurringRoutine.id == identity, RecurringRoutine.owner_id == actor.owner_id).with_for_update())
        if row is None: raise HTTPException(404, 'Routine not found.')
        versions = session.scalars(select(RoutineRuleVersion).where(RoutineRuleVersion.owner_id == actor.owner_id,
            RoutineRuleVersion.routine_id == identity).order_by(RoutineRuleVersion.revision.desc()).offset(offset).limit(21)).all()
        occurrences = session.scalars(select(RoutineOccurrenceRecord).where(RoutineOccurrenceRecord.owner_id == actor.owner_id,
            RoutineOccurrenceRecord.routine_id == identity).order_by(RoutineOccurrenceRecord.scheduled_at.desc()).offset(offset).limit(21)).all()
        return {'versions':[{'revision':v.revision,'definition':v.definition,'status':v.status,'action':v.action,'recorded_at':v.recorded_at} for v in versions[:20]],
                'occurrences':[{'id':v.id,'period_key':v.period_key,'local_date':v.local_date,'status':v.status,'reason':v.reason,'task_id':v.task_id,'updated_at':v.updated_at} for v in occurrences[:20]],
                'has_more':len(versions)>20 or len(occurrences)>20,
                'notice':'Saved rule revisions and durable occurrence records; task creation and physical repair verification are separate.'}

    @app.post('/v1/recurring/{identity}/lifecycle')
    def lifecycle(identity: str, value: RoutineLifecycle, request: Request, actor=Depends(device), session=Depends(db)):
        host(request); lock_owner(session, actor.owner_id)
        row = session.scalar(select(RecurringRoutine).where(RecurringRoutine.id == identity, RecurringRoutine.owner_id == actor.owner_id).with_for_update())
        if row is None: raise HTTPException(404, 'Routine not found.')
        if row.revision != value.expected_revision: raise HTTPException(409, 'Routine changed. Reload before changing its lifecycle.')
        if row.status not in {'draft','paused','retired'}:
            raise HTTPException(409, 'Review active delivery before changing this routine.')
        target = 'retired' if value.action == 'retire' else 'draft'
        if row.status == target: return view(row)
        retain_rule(session,row,'preserved_before_lifecycle')
        row.status = target; row.revision += 1; row.updated_at = now()
        retain_rule(session,row,value.action)
        session.commit()
        return view(row)
