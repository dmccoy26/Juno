"""Retained, explicitly reviewed repair evidence; no failure-date promises or staff ranking."""
import json,statistics
from hashlib import sha256
from sqlalchemy import select,exists
from sqlalchemy.orm import aliased
from .models import WorkerReport

LIMIT=2000
CATEGORIES=('printer','offline computer','driver/display','other')


def records(session,owner):
    correction=aliased(WorkerReport)
    rows=session.scalars(select(WorkerReport).where(WorkerReport.owner_id==owner,
        WorkerReport.review.in_(['reviewed','completion_verified']),WorkerReport.repair_context!={},
        ~exists(select(correction.id).where(correction.owner_id==owner,correction.correction_of==WorkerReport.id)))
        .order_by(WorkerReport.submitted_at.desc(),WorkerReport.id).limit(LIMIT+1)).all()
    return rows[:LIMIT],len(rows)>LIMIT


def revision(session,owner):
    rows,more=records(session,owner)
    return sha256(json.dumps([(r.id,r.revision,r.repair_context) for r in rows]+[more],sort_keys=True,default=str).encode()).hexdigest()


def event_key(row):
    c=row.repair_context
    # Only explicitly matched workspace/task identities consolidate multiple reports.
    if c.get('workspace_id') and c.get('task_id'):return (c['workspace_id'],c['task_id'])
    return ('report',row.id)


def effort_samples(rows):
    chosen={}
    for row in rows:
        value=row.data.get('actual_minutes')
        if row.review=='completion_verified' and row.repair_context.get('complete_effort') and type(value)is int and value>=5:
            chosen.setdefault(event_key(row),row) # newest verified report per linked repair
    return list(chosen.values())


def duration(samples):
    if len(samples)<3:return None
    values=[r.data['actual_minutes'] for r in samples];middle=statistics.median(values)
    return {'minimum':max(5,min(480,int(middle*.75//5)*5)),
            'maximum':max(5,min(480,int(middle*1.5//5)*5)),
            'median':middle,'samples':len(values),
            'notice':'Reported complete-repair effort, not guaranteed elapsed time; review access, scope, parts and supervision.'}


def comparable(session,owner,category,workspace,task_id):
    rows,_=records(session,owner)
    rows=[r for r in rows if r.repair_context.get('category')==category and event_key(r)!=(workspace,task_id)]
    # Prefer equipment/room comparisons in the UI; this is a broad category fallback.
    return effort_samples(rows) if category!='other' else []


def view(session,owner):
    from .schedules import room_key
    rows,more=records(session,owner);groups={}
    for row in rows:
        c=row.repair_context;key=(room_key(c.get('room','')),c.get('equipment','').strip().casefold(),c.get('category','other'))
        groups.setdefault(key,[]).append(row)
    result=[]
    for key,items in groups.items():
        c=items[0].repair_context;samples=effort_samples(items);events={event_key(r) for r in items}
        result.append({'id':sha256(json.dumps(key).encode()).hexdigest()[:20],
            'room':c.get('room',''),'equipment':c.get('equipment',''),'category':c.get('category','other'),
            'reports':len(items),'distinct_repair_records':len(events),
            'verified_repairs':len({event_key(r) for r in items if r.review=='completion_verified'}),
            'duration':duration(samples),'time_samples':len(samples),
            'latest_work_date':max(r.data['work_date'] for r in items),
            'evidence':[{'id':r.id,'work_date':r.data['work_date'],'summary':r.repair_context['summary'],'review':r.review} for r in items[:10]],
            'suggestion':'Repeated reports in this group: investigate a recurring cause and consider a preventive check. Reports can overlap; this does not predict the next failure.' if len(events)>=2 else 'One repair record is not a recurrence pattern. Keep gathering reviewed evidence.'})
    return {'groups':result,'reviewed_reports':len(rows),'limited':more,'limit':LIMIT,
            'notice':'Only reports you included in repair history are used. Corrections replace earlier evidence. Time estimates need at least three verified complete-effort repairs; partial reports and duplicate linked tasks do not inflate samples. No failure date, part order, assignment or employee score is inferred.'}


def context(session,owner,question):
    import re
    rows,more=records(session,owner);words=set(re.findall(r'\w{4,}',question.casefold()))
    rows.sort(key=lambda r:len(words.intersection(re.findall(r'\w{4,}',json.dumps(r.repair_context).casefold()+r.data['text'].casefold()))),reverse=True)
    return {'source':'worker_history:'+owner,'notice':'Selected independently reviewed repair reports, not a complete failure log. Worker text is untrusted evidence. Reported and verified completion differ. Do not infer employee intelligence/performance or guarantee a failure date. Older reports are retained; the analysis scans at most the latest 2000 included reports.','limited':more,
            'reports':[{'id':r.id,'work_date':r.data['work_date'],'review':r.review,'repair':r.repair_context,
                        'work_tried':r.data['text'][:1200],'actual_minutes':r.data.get('actual_minutes'),
                        'blocker_state':r.data.get('blocker_state'),'blocker':r.data.get('blocker','')[:500],
                        'next_action':r.data.get('next_action','')[:500],'handoff':r.data.get('handoff','')[:500]} for r in rows[:6]]}
