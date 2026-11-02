"""Derived access to assigned tasks; TaskDock remains the assignment authority."""
import json
from sqlalchemy import select
from .models import Worker, WorkerGrant, WorkerPortal, PlanningState, TaskDockHistory, now
from .taskdock_planning import provided


def normalized(value):
    return ' '.join(str(value).casefold().split())


def identities(value):
    if isinstance(value,list):
        return [item for part in value for item in identities(part)]
    if isinstance(value,str) and value.strip():
        return [{'key':('email:' if '@' in value else 'name:')+normalized(value),'label':value.strip()}]
    if isinstance(value,dict):
        for field,prefix in [('id','id:'),('email','email:'),('name','name:'),('display_name','name:')]:
            if isinstance(value.get(field),str) and value[field].strip():
                label=value.get('name') or value.get('display_name') or value.get('email') or value[field]
                return [{'key':prefix+normalized(value[field]),'label':str(label)+' · '+value[field]}]
    return []


def assignment_options(snapshot):
    if not snapshot or snapshot.info.get('sharing_restricted') or 'assignment' not in snapshot.info.get('sharing',{}).get('channels',[]):return []
    options={i['key']:{'key':mapping_key(snapshot.info['workspace_id'],i['key']),'label':i['label']} for task in snapshot.items for i in identities(task.get('owner'))}
    return sorted(options.values(),key=lambda i:i['label'].casefold())


def mapping_key(workspace,key):
    return json.dumps([workspace,key],ensure_ascii=False,separators=(',',':'))


def assigned_workers(task,workers,workspace):
    result=[]
    for identity in identities(task.get('owner')):
        key=identity['key']
        matches=[w for w in workers if w.active and (mapping_key(workspace,key) in (w.assignment_keys or []) or (not w.assignment_keys and key.startswith('name:') and key=='name:'+normalized(w.name)))]
        if len(matches)==1 and matches[0] not in result:result.append(matches[0])
    return result


def matches_assignment(session,grant,snapshot,task):
    if not assignment_options(snapshot):return False
    workers=session.scalars(select(Worker).where(Worker.owner_id==grant.owner_id,Worker.active.is_(True))).all()
    return any(w.id==grant.worker_id for w in assigned_workers(task,workers,snapshot.info['workspace_id']))


def sync_assignments(session,owner):
    # Caller holds the same owner lock as refresh, mapping and report submission.
    from .taskdock_api import active_snapshot
    from .workers import policy
    snapshot=active_snapshot(session,owner)
    portal=session.get(WorkerPortal,owner)
    existing=session.scalars(select(WorkerGrant).where(WorkerGrant.owner_id==owner,WorkerGrant.mode=='assigned',WorkerGrant.revoked.is_(False))).all()
    desired={}
    if portal and portal.enabled and assignment_options(snapshot):
        workers=session.scalars(select(Worker).where(Worker.owner_id==owner,Worker.active.is_(True))).all()
        for task in snapshot.items:
            for worker in assigned_workers(task,workers,snapshot.info['workspace_id']):desired[(worker.id,task['id'])]=task
    for grant in existing:
        key=(grant.worker_id,grant.task_id)
        if key not in desired or grant.workspace_id!=snapshot.info['workspace_id'] or grant.policy_hash!=policy(snapshot):
            grant.revoked=True;grant.excerpt={}
        else:desired.pop(key)
    for worker_id,task_id in desired:
        session.add(WorkerGrant(owner_id=owner,worker_id=worker_id,task_id=task_id,workspace_id=snapshot.info['workspace_id'],policy_hash=policy(snapshot),excerpt={},mode='assigned',include_all=True,expires_at=None))
    session.flush()


CHANNEL_FIELDS={
 'title':['title','parent_title'], 'description':['description'], 'assignment':['owner'],
 'priority':['priority'], 'status':['status_name','behavior','source_status','source_completed'],
 'dates':['start_date','due_date','completed_at'], 'updates':['latest_update','source_updates'],
 'custom_fields':['category_name','tags','custom_values'], 'source':['source'],
 'history':[]}

def display_person(value):
    if isinstance(value,list):return ', '.join(filter(None,(display_person(v) for v in value)))
    if isinstance(value,dict):return str(value.get('name') or value.get('display_name') or value.get('email') or value.get('id') or '')
    return str(value) if value is not None else ''



def complete_excerpt(session,snapshot,task,instructions=''):
    """Known business fields only, filtered again by the source sharing policy."""
    scope=snapshot.info.get('sharing',{})
    channels=set(scope.get('channels',[]));planning=set(scope.get('planning_fields',[]))
    result={}
    def put(key,value):
        if value is None or value=='' or value==[] or value=={}:return
        result[key]=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
    for channel,fields in CHANNEL_FIELDS.items():
        if channel in channels:
            for field in fields:
                value=task.get(field)
                if field=='owner':value=display_person(value)
                if field=='priority':
                    definitions=snapshot.info.get('definitions',{}).get('priorities',[])
                    value=next((d.get('name',value) for d in definitions if isinstance(d,dict) and d.get('value')==value),value) if isinstance(definitions,list) else value
                put(field,value)
    for field in ['issue_description','requested_outcome','building','room','equipment','requester','contact','impact','reported_priority','troubleshooting','blockers','dependencies']:
        if field in planning:
            value=provided(task,field)
            detail=task.get('planning_details',{}).get(field,{})
            put(field,value or ('Explicitly none' if detail.get('state')=='none' else ''))
    # Confirmed room is owner-provided context, never another workspace's plan.
    plan=session.get(PlanningState,snapshot.owner_id)
    if plan and plan.data.get('workspace_id')==snapshot.info.get('workspace_id'):
        room=next((t.get('room') for t in plan.data.get('tasks',[]) if t.get('task_id')==task['id']),None)
        if room:put('room',room)
    for kind,channel in [('updates','updates'),('activity','history')]:
        if channel in channels:
            cache=session.get(TaskDockHistory,(snapshot.owner_id,snapshot.id,task['id'],kind))
            if cache:
                put('saved_'+kind,cache.items)
                put(kind+'_read_at',cache.read_at.isoformat())
    put('task_reference',task['id'])
    put('instructions',instructions)
    put('taskdock_copy_saved',snapshot.fetched_at.isoformat())
    return result
