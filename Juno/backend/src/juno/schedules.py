"""Recurring availability and proposed repair windows. No upstream actions."""
from datetime import date,datetime,time,timedelta,timezone
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import re
from fastapi import Depends,HTTPException,Query
from pydantic import Field,model_validator
from sqlalchemy import select
from .models import ScheduleState,IntegrationSnapshot,now
from .planning import Strict,merge,intersect,subtract,stamp,state_view as planning_view
from .integrations import aware,IntegrationError
ZONE=ZoneInfo('America/Chicago')


def room_key(value):
    value=re.sub(r'[^A-Z0-9]','',value.upper())
    for aliases,canonical in [(('A121','ARTS121'),'ARTS 121'),(('A140','ARTS140'),'ARTS 140'),
        (('LIB115','LIBR115','LIBRARY115'),'LIBR 115'),(('MH301','MOOD301','MOODY301'),'MOOD 301'),
        (('TH108','TRUS108','TRUSTEE108'),'TRUS 108')]:
        if value in aliases:return canonical
    return value


def room_hint(text):
    found=[]
    for pattern,room in [(r'\b(?:ARTS\s*|A)121(?=\D|$)','ARTS 121'),(r'\b(?:ARTS\s*|A)140(?=\D|$)','ARTS 140'),
      (r'\b(?:LIBRARY\s*|LIBR?\s*)115(?=\D|$)','LIBR 115'),(r'\b(?:MOODY\s*|MOOD\s*|MH)301(?=\D|$)','MOOD 301'),
      (r'\b(?:TRUSTEE\s*|TRUS\s*|TH)108(?=\D|$)','TRUS 108')]:
        if re.search(pattern,text,re.I):found.append(room)
    return found[0] if len(found)==1 else None


class Rule(Strict):
    id:str=Field(default_factory=lambda:str(uuid4()),min_length=1,max_length=100)
    kind:Literal['work','room','classroom_busy','staff_available']
    name:str=Field(default='',max_length=300)
    location:str=Field(default='',max_length=300)
    start_date:date
    end_date:date
    days:list[int]=Field(min_length=1,max_length=7)
    start_time:str=Field(pattern=r'^\d\d:\d\d$')
    end_time:str=Field(pattern=r'^\d\d:\d\d$')
    timezone:str='America/Chicago'

    @model_validator(mode='after')
    def valid(self):
        try:
            a=time.fromisoformat(self.start_time);b=time.fromisoformat(self.end_time);ZoneInfo(self.timezone)
            assert a<b and 0<=(self.end_date-self.start_date).days<=366
            assert len(set(self.days))==len(self.days) and all(0<=d<=6 for d in self.days)
            assert self.kind=='work' or bool(self.name)
            assert self.kind!='classroom_busy' or bool(self.location)
        except (ValueError,AssertionError,ZoneInfoNotFoundError):raise ValueError('Check dates, weekdays, names, timezone and same-day times.') from None
        return self


class Person(Strict):
    name:str=Field(min_length=1,max_length=300)
    status:Literal['active','tentative','candidate']='tentative'
    weekly_limit_minutes:int=Field(default=1200,ge=0,le=2400)
    desired_minutes:int|None=Field(default=None,ge=0,le=2400)
    notes:str=Field(default='',max_length=2000)

    @model_validator(mode='after')
    def limit(self):
        if self.desired_minutes is not None and self.desired_minutes>self.weekly_limit_minutes:raise ValueError('Agreed hours cannot exceed the weekly limit.')
        return self


class ExceptionInput(Strict):
    id:str=Field(default_factory=lambda:str(uuid4()),max_length=100)
    kind:Literal['work','room','staff_available','classroom_busy']
    name:str=Field(default='',max_length=300)
    day:date
    closed:bool=True
    start_time:str|None=None
    end_time:str|None=None
    note:str=Field(default='',max_length=1000)

    @model_validator(mode='after')
    def valid(self):
        if self.kind!='work' and not self.name:raise ValueError('Select the affected room or person.')
        if not self.closed:
            try:assert time.fromisoformat(self.start_time)<time.fromisoformat(self.end_time)
            except (ValueError,TypeError,AssertionError):raise ValueError('Set valid replacement opening and closing times.') from None
        return self


class ScheduleInput(Strict):
    expected_revision:int=Field(ge=0)
    rules:list[Rule]=Field(default_factory=list,max_length=1000)
    people:list[Person]=Field(default_factory=list,max_length=100)
    exceptions:list[ExceptionInput]=Field(default_factory=list,max_length=1000)

    @model_validator(mode='after')
    def unique(self):
        for values in ([r.id for r in self.rules],[p.name.casefold() for p in self.people],
            [f'{e.kind}:{room_key(e.name) if e.kind in ("room","classroom_busy") else e.name.casefold()}:{e.day}' for e in self.exceptions]):
            if len(values)!=len(set(values)):raise ValueError('Remove duplicate rules, people or daily exceptions.')
        return self


class ReservationInput(Strict):
    expected_revision:int=Field(ge=0)
    task_id:str=Field(min_length=1,max_length=500)
    workspace_id:str=Field(min_length=1,max_length=500)
    room:str=Field(min_length=1,max_length=300)
    employee:str=Field(default='',max_length=300)
    start:datetime
    end:datetime

    @model_validator(mode='after')
    def valid(self):
        if not self.start.tzinfo or not self.end.tzinfo or not 300<=(self.end-self.start).total_seconds()<=28800 or (self.end-self.start).total_seconds()%60:raise ValueError('Use timezone-aware times and 5–480 minutes.')
        return self


def state_view(session,owner):
    row=session.get(ScheduleState,owner)
    return {'revision':row.revision if row else 0,'updated_at':row.updated_at if row else None,
        **(row.data if row else {'rules':[],'people':[],'exceptions':[],'reservations':[]})}


def match(kind,name,other):
    return room_key(name)==room_key(other) if kind in ('room','classroom_busy') else name.casefold()==other.casefold()


def schedule_intervals(session,owner,day):
    if not 2000<=day.year<=2100:raise HTTPException(422,'Choose a date between 2000 and 2100.')
    left=datetime.combine(day,time(),ZONE);right=left+timedelta(days=7)
    state=state_view(session,owner);legacy=planning_view(session,owner)
    spans=[];notices=[]
    overrides={(r['kind'],room_key(r['location'] if r['kind']=='classroom_busy' else r['name']) if r['kind'] in ('room','classroom_busy') else '' if r['kind']=='work' else r['name'].casefold()) for r in state['rules']}
    overrides.update(tuple(value.split('|',1)) for value in state.get('managed',[]))
    def key(kind,name):return (kind,room_key(name) if kind in ('room','classroom_busy') else '' if kind=='work' else name.casefold())
    def add(kind,name,a,b):
        a=max(a,left,now());b=min(b,right)
        if a<b:spans.append((kind,name,a,b))
    for w in legacy['windows']:
        kind='staff_available' if w['kind']=='staff' else w['kind']
        if key(kind,w['name']) not in overrides:add(kind,w['name'],stamp(w['start']),stamp(w['end']))
    sources=session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner)).all()
    for source in sources:
        if source.details.get('active') is False:continue
        if source.kind not in ('schedules','calendar','google_calendar','outlook_calendar'):continue
        notices.append(f'{source.kind}: saved {source.fetched_at.isoformat()}'+('; last refresh failed' if source.error else ''))
        for item in source.items:
            kind=item.get('kind')
            if kind in ('classroom_busy','staff_available'):
                name=str(item.get('location') or item.get('title','')) if kind=='classroom_busy' else str(item.get('title',''))
                if key(kind,name) in overrides:continue
            elif item.get('busy') and item.get('status')!='cancelled':kind='busy';name=''
            else:continue
            try:add(kind,name,stamp(item['start']),stamp(item['end']))
            except (ValueError,KeyError,TypeError):continue
    for raw in state['rules']:
        r=Rule.model_validate(raw);d=max(r.start_date,day-timedelta(days=1))
        while d<=min(r.end_date,day+timedelta(days=7)):
            if d.weekday() in r.days:
                tz=ZoneInfo(r.timezone)
                try:a=aware(datetime.combine(d,time.fromisoformat(r.start_time)),tz);b=aware(datetime.combine(d,time.fromisoformat(r.end_time)),tz)
                except IntegrationError:raise HTTPException(422,'A recurring time is ambiguous at a DST change. Add an explicit exception.') from None
                add(r.kind,r.location if r.kind=='classroom_busy' else r.name,a,b)
            d+=timedelta(days=1)
    for raw in state['exceptions']:
        ex=ExceptionInput.model_validate(raw)
        if not day<=ex.day<day+timedelta(days=7):continue
        a=datetime.combine(ex.day,time(),ZONE);b=a+timedelta(days=1)
        updated=[]
        for kind,name,x,y in spans:
            if kind==ex.kind and (kind=='work' or match(kind,name,ex.name)):
                updated.extend((kind,name,c,d) for c,d in subtract([(x,y)],[(a,b)]))
            else:updated.append((kind,name,x,y))
        spans=updated
        if not ex.closed:
            add(ex.kind,ex.name,aware(datetime.combine(ex.day,time.fromisoformat(ex.start_time)),ZONE),aware(datetime.combine(ex.day,time.fromisoformat(ex.end_time)),ZONE))
    return state,spans,notices


def availability(session,owner,day,room='',employee='',minutes=60,supervision=False,_context=None,_budget_cache=None):
    state,spans,notices=_context or schedule_intervals(session,owner,day)
    rooms=sorted({name for kind,name,_,_ in spans if kind in ('room','classroom_busy')})
    people={p['name'].casefold():p for p in state['people']}
    staff_names={name for kind,name,_,_ in spans if kind=='staff_available'}
    staff_names.update(p['name'] for p in state['people'])
    def intervals(kind,name=''):
        return merge((a,b) for k,n,a,b in spans if k==kind and (kind in ('work','busy') or match(kind,name,n)))
    warnings=[];possible=intervals('room',room) if room else []
    if room and not possible:warnings.append('No confirmed building access for this room in this period.')
    possible=subtract(possible,intervals('classroom_busy',room))
    person=people.get(employee.casefold()) if employee else None
    if employee:
        if state['revision'] and person is None:
            possible=[];warnings.append('Confirm an active staff profile and weekly limit for '+employee+'.')
        elif person and person['status']!='active':
            possible=[];warnings.append(employee+' is '+person['status']+'; no confirmed work capacity.')
        else:
            shift=intervals('staff_available',employee)
            possible=intersect(possible,shift)
            if not shift:warnings.append('No confirmed work shifts for '+employee+'.')
    if not employee or supervision:
        work=subtract(intervals('work'),intervals('busy'))
        possible=intersect(possible,work)
        if not work:warnings.append('No confirmed personal work availability; add your hours or resolve meetings.')
    # Dated local reservations are explicit planning holds, not TaskDock edits.
    relevant=[]
    for r in state['reservations']:
        if (room_key(r['room'])==room_key(room) or (employee and r['employee'].casefold()==employee.casefold()) or ((not employee or supervision) and r.get('uses_owner',True))):
            relevant.append((stamp(r['start']),stamp(r['end'])))
    possible=subtract(possible,relevant)
    if employee and person:
        limit=min(person['weekly_limit_minutes'],person['desired_minutes'] if person['desired_minutes'] is not None else person['weekly_limit_minutes'])
        filtered=[]
        for a,b in possible:
            local=a.astimezone(ZONE);week=local.date()-timedelta(days=local.weekday());weekstart=datetime.combine(week,time(),ZONE);weekend=weekstart+timedelta(days=7)
            used=sum(max(0,(min(stamp(r['end']),weekend)-max(stamp(r['start']),weekstart)).total_seconds()/60) for r in state['reservations'] if r['employee'].casefold()==employee.casefold())
            if used+minutes<=limit:filtered.append((a,b))
        if len(filtered)<len(possible):warnings.append('Some windows exceed the employee’s weekly agreed/funded hour limit after existing reservations.')
        possible=filtered
    budget_cache=_budget_cache if _budget_cache is not None else {}
    calendar_ready=True
    if not employee or supervision:
        if 'calendar_ready' not in budget_cache:
            calendars=session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner,IntegrationSnapshot.kind.in_(['calendar','google_calendar','outlook_calendar']))).all()
            calendar_ready=not any(r.details.get('active') is not False and (r.error or (now()-r.fetched_at).total_seconds()>86400) for r in calendars)
            budget_cache['calendar_ready']=calendar_ready
        calendar_ready=budget_cache['calendar_ready']
        if not calendar_ready:warnings.append('The connected calendar needs refresh before reserving personal/supervised work.')
        filtered=[]
        for a,b in possible:
            local=a.astimezone(ZONE);week=local.date()-timedelta(days=local.weekday());weekstart=datetime.combine(week,time(),ZONE);weekend=weekstart+timedelta(days=7)
            if week not in budget_cache:
                _,weekspans,_=schedule_intervals(session,owner,week)
                owned=merge((x,y) for k,n,x,y in weekspans if k=='work')
                meetings=[(x,y) for k,n,x,y in weekspans if k=='busy']
                owned=subtract(owned,meetings)
                allowance=max(0,min(2400,sum((y-x).total_seconds()/60 for x,y in owned))-planning_view(session,owner)['reserve_minutes'])
                used=sum(max(0,(min(stamp(r['end']),weekend)-max(stamp(r['start']),weekstart,now())).total_seconds()/60) for r in state['reservations'] if r.get('uses_owner',True))
                budget_cache[week]=(allowance,used)
            allowance,used=budget_cache[week]
            if used+minutes<=allowance:filtered.append((a,b))
        if len(filtered)<len(possible):warnings.append('Some windows would consume your weekly interruption reserve or exceed personal capacity.')
        possible=filtered
    slots=[{'start':a.isoformat(),'end':b.isoformat(),'available_minutes':int((b-a).total_seconds()/60),'proposed_end':(a+timedelta(minutes=minutes)).isoformat()} for a,b in possible if (b-a).total_seconds()>=minutes*60]
    return {'day':str(day),'end':str(day+timedelta(days=7)),'generated_at':now(),'revision':state['revision'],
        'rooms':rooms,'people':[{'name':n,'status':people.get(n.casefold(),{}).get('status','active')} for n in sorted(staff_names)],
        'calendar_ready':calendar_ready,'room':room,'employee':employee,'minutes':minutes,'windows':slots[:100],'warnings':warnings,'source_notices':notices,
        'notice':'Possible windows, not assignments. Confirm task scope, parts, permissions and capability. Class times are excluded. Alternatives may overlap; a reservation prevents double booking. Unrecorded holidays and source gaps can reduce availability.'}


def invalidate(session,owner):
    from .companion import invalidate_context
    invalidate_context(session,owner,'schedules:'+owner)
    # The old Plan result also depends on the schedule geometry.
    invalidate_context(session,owner,'planning:'+owner)


def install(app,db,device,lock_owner):
    @app.get('/v1/schedules')
    def read(actor=Depends(device),session=Depends(db)):return state_view(session,actor.owner_id)

    @app.put('/v1/schedules')
    def save(value:ScheduleInput,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=session.get(ScheduleState,actor.owner_id)
        if (row.revision if row else 0)!=value.expected_revision:raise HTTPException(409,'Schedules changed. Reload before saving; keep your draft.')
        data=value.model_dump(mode='json',exclude={'expected_revision'})
        data['reservations']=row.data.get('reservations',[]) if row else []
        managed=set(row.data.get('managed',[])) if row else set()
        for rule in data['rules']:
            kind=rule['kind'];name=rule['location'] if kind=='classroom_busy' else rule['name']
            managed.add(kind+'|'+(room_key(name) if kind in ('room','classroom_busy') else '' if kind=='work' else name.casefold()))
        data['managed']=sorted(managed)
        # Do not silently validate old reservations against a newly changed schedule.
        data['reservation_notice']='Existing holds need review after schedule changes.' if data['reservations'] else ''
        invalidate(session,actor.owner_id)
        if row is None:row=ScheduleState(owner_id=actor.owner_id,data=data,revision=1,updated_at=now());session.add(row)
        else:row.data=data;row.revision+=1;row.updated_at=now()
        session.commit();return state_view(session,actor.owner_id)

    @app.get('/v1/availability')
    def find(day:date=Query(),room:str=Query(default='',max_length=300),employee:str=Query(default='',max_length=300),
        minutes:int=Query(default=60,ge=5,le=480),supervision:bool=False,actor=Depends(device),session=Depends(db)):
        return availability(session,actor.owner_id,day,room,employee,minutes,supervision)

    @app.post('/v1/schedules/reservations')
    def reserve(value:ReservationInput,actor=Depends(device),session=Depends(db)):
        from .taskdock_api import active_snapshot
        from .models import TaskDockState
        lock_owner(session,actor.owner_id);state=state_view(session,actor.owner_id)
        if state['revision']!=value.expected_revision:raise HTTPException(409,'Schedules or holds changed. Refresh the possible windows.')
        snapshot=active_snapshot(session,actor.owner_id)
        if not snapshot or snapshot.info['workspace_id']!=value.workspace_id:raise HTTPException(409,'TaskDock workspace changed.')
        task=next((t for t in snapshot.items if str(t['id'])==value.task_id),None)
        facts=next((f for f in planning_view(session,actor.owner_id)['tasks'] if f['task_id']==value.task_id),{})
        if not task or task.get('source_completed') or task.get('completed_at') or task.get('behavior') in ('completed','archived'):raise HTTPException(409,'This task is not an open saved TaskDock task.')
        tdstate=session.get(TaskDockState,actor.owner_id)
        if task.get('start_date') and str(value.start.astimezone(ZONE).date())<str(task['start_date'])[:10]:raise HTTPException(409,'The task start date is later; review before scheduling early.')
        if (tdstate and tdstate.error) or (now()-snapshot.fetched_at).total_seconds()>86400:raise HTTPException(409,'Refresh the TaskDock copy before reserving work.')
        if task.get('blocked_reason') or task.get('behavior')=='waiting' or facts.get('blocker'):raise HTTPException(409,'Resolve the task blocker before reserving work.')
        if room_key(facts.get('room',''))!=room_key(value.room) or facts.get('employee','').casefold()!=value.employee.casefold():raise HTTPException(409,'Save and review the task’s room and employee first.')
        minutes=int((value.end-value.start).total_seconds()/60)
        if facts.get('minutes')!=minutes:raise HTTPException(409,'Review the task duration before reserving this window.')
        if value.employee and (not facts.get('independent') or not facts.get('capability')) and not facts.get('supervision'):raise HTTPException(409,'Confirm independent capability or choose supervised work.')
        view=availability(session,actor.owner_id,value.start.astimezone(ZONE).date(),value.room,value.employee,minutes,facts.get('supervision',False))
        if not view['calendar_ready']:raise HTTPException(409,'Refresh the calendar before reserving this work.')
        if value.employee:
            person=next((p for p in state['people'] if p['name'].casefold()==value.employee.casefold()),None)
            if not person or person['status']!='active':raise HTTPException(409,'Confirm the employee profile and weekly limit first.')
        if not any(stamp(w['start'])<=value.start and value.end<=stamp(w['end']) for w in view['windows']):raise HTTPException(409,'That window no longer fits availability, reservations or weekly limits.')
        if len(state['reservations'])>=1000:raise HTTPException(413,'Review and remove old planning holds before adding more.')
        held={'id':str(uuid4()),**value.model_dump(mode='json',exclude={'expected_revision'}),'uses_owner':not value.employee or facts.get('supervision',False)}
        data={k:state[k] for k in ('rules','people','exceptions','reservations')};data['reservations']=[*data['reservations'],held];data['managed']=state.get('managed',[])
        row=session.get(ScheduleState,actor.owner_id)
        if row is None:row=ScheduleState(owner_id=actor.owner_id,data=data,revision=1,updated_at=now());session.add(row)
        else:row.data=data;row.revision+=1;row.updated_at=now()
        invalidate(session,actor.owner_id);session.commit();return held

    @app.delete('/v1/schedules/reservations/{identity}')
    def release(identity:str,expected_revision:int=Query(ge=1),actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=session.get(ScheduleState,actor.owner_id)
        if not row or row.revision!=expected_revision:raise HTTPException(409,'Planning holds changed; refresh first.')
        reservations=[r for r in row.data['reservations'] if r['id']!=identity]
        if len(reservations)==len(row.data['reservations']):raise HTTPException(404,'Planning hold not found.')
        row.data={**row.data,'reservations':reservations};row.revision+=1;row.updated_at=now();invalidate(session,actor.owner_id);session.commit()
        return {'released':True}
