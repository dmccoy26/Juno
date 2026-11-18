"""Explicit, owner-scoped request answers; independent of old clients' planning PUTs."""
from copy import deepcopy
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import Field, model_validator
from .planning import Strict
from .taskdock_planning import FIELDS
from .models import now


def field_basis(value):
    from .operations import digest
    return digest({k:value.get(k) for k in ('state','value','source_updated_at','taskdock_flag')})


def allowed_keys(snapshot):
    from .taskdock_planning import sharing
    try: policy=sharing(snapshot.info)
    except ValueError:return set()
    return set(policy[1]['planning_fields']) if policy and not snapshot.info.get('sharing_restricted') else set()


def identity(snapshot, task_id, key):
    from .operations import digest
    return digest([snapshot.origin,snapshot.info.get('device_id'),snapshot.info.get('workspace_id'),task_id,key])


def current(session, owner, workspace, task_id):
    from .taskdock_api import active_snapshot
    snapshot=active_snapshot(session,owner)
    if not snapshot or snapshot.info.get('sharing_restricted') or snapshot.info.get('workspace_id')!=workspace:
        raise HTTPException(409,'TaskDock workspace or sharing changed. Reload Issues.')
    task=next((t for t in snapshot.items if str(t.get('id'))==task_id),None)
    if task is None:raise HTTPException(404,'Task not available in the current authorized copy.')
    return snapshot,task


def overlay(session, owner, snapshot, task, reviews=None):
    from .operations import saved
    if reviews is None:
        _,data=saved(session,owner)
        reviews=data.get('request_reviews',{})
    result=deepcopy(task)
    for key,value in result.get('planning_details',{}).items():
        if key not in allowed_keys(snapshot):continue
        review=reviews.get(identity(snapshot,str(task['id']),key))
        if not review:continue
        changed=review['basis']!=field_basis(value)
        result['planning_details'][key]={'state':review['state'],'value':review['value'],
            'origin':'Your reviewed Juno answer','updated_at':review['recorded_at'],
            'source_updated_at':value.get('source_updated_at'),'review_conflict':changed or value.get('review_conflict',False),
            **({'taskdock_flag':value['taskdock_flag']} if value.get('taskdock_flag') else {})}
    return result


def view(session,owner,workspace,task_id):
    from .operations import saved
    snapshot,task=current(session,owner,workspace,task_id)
    row,_=saved(session,owner)
    reviewed=overlay(session,owner,snapshot,task)
    return {'owner_id':owner,'scope':identity(snapshot,task_id,'request'),'revision':row.revision if row else 0,'snapshot_id':snapshot.id,
        'fields':[{'key':key,'label':FIELDS[key],**value,'basis':field_basis(value)}
                  for key,value in task.get('planning_details',{}).items() if key in FIELDS and key in allowed_keys(snapshot)],
        'reviewed_fields':{k:v for k,v in reviewed.get('planning_details',{}).items() if k in allowed_keys(snapshot)},
        'notice':'Reviewed answers stay in Juno. TaskDock is unchanged. Changed source facts require another review.'}


class ReviewInput(Strict):
    workspace_id:str=Field(min_length=1,max_length=500)
    task_id:str=Field(min_length=1,max_length=500)
    key:str=Field(min_length=1,max_length=100)
    snapshot_id:str=Field(min_length=1,max_length=36)
    expected_revision:int=Field(ge=0)
    basis:str=Field(min_length=64,max_length=64)
    state:Literal['provided','none','unknown']
    value:str|None=Field(default=None,max_length=2000)
    @model_validator(mode='after')
    def valid(self):
        if (self.state=='provided' and not self.value) or (self.state!='provided' and self.value is not None):raise ValueError('Provide an answer, or explicitly choose none/unknown.')
        return self


def install(app,db,device,lock_owner):
    @app.get('/v1/planning/request-review')
    def read(workspace_id:str=Query(min_length=1,max_length=500),task_id:str=Query(min_length=1,max_length=500),actor=Depends(device),session=Depends(db)):
        return view(session,actor.owner_id,workspace_id,task_id)

    @app.post('/v1/planning/request-review')
    def save(value:ReviewInput,actor=Depends(device),session=Depends(db)):
        from .operations import saved,write_state
        lock_owner(session,actor.owner_id)
        snapshot,task=current(session,actor.owner_id,value.workspace_id,value.task_id)
        field=task.get('planning_details',{}).get(value.key)
        if value.key not in FIELDS or value.key not in allowed_keys(snapshot) or field is None:raise HTTPException(403,'This request field is not currently shared.')
        if snapshot.id!=value.snapshot_id or field_basis(field)!=value.basis:raise HTTPException(409,'The source changed. Reload and review your answer against the current field.')
        row,data=saved(session,actor.owner_id)
        if (row.revision if row else 0)!=value.expected_revision:raise HTTPException(409,'Reviewed information changed. Your answer is retained here; reload before saving.')
        key=identity(snapshot,value.task_id,value.key)
        reviews=data.get('request_reviews',{})
        if key not in reviews and len(reviews)>=6000:raise HTTPException(422,'Review stored request answers before adding more.')
        record={'state':value.state,'value':value.value,'basis':value.basis,'recorded_at':now().isoformat(),'actor_id':actor.id}
        data['request_review_history']=[*data.get('request_review_history',[]),{'id':key,'before':reviews.get(key),'after':record}]
        data['request_reviews']={**reviews,key:record}
        write_state(session,actor,data,value.expected_revision)
        return view(session,actor.owner_id,value.workspace_id,value.task_id)
