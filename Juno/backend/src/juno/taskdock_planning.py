"""TaskDock's optional reviewed request facts and controlled-sharing contract."""
FIELDS = {
    'issue_description':'Issue description','requested_outcome':'Requested outcome','building':'Building',
    'room':'Room','equipment':'Affected equipment','requester':'Requester','contact':'Access / contact person',
    'impact':'Operational impact','reported_priority':'Reported priority','troubleshooting':'Troubleshooting attempted',
    'blockers':'Blockers','dependencies':'Dependencies',
}
CHANNELS = {'title','description','assignment','dates','priority','status','source','updates','custom_fields','history'}

def sharing(info):
    """Only an advertised, fully validated controlled policy has a version."""
    if info.get('capabilities',{}).get('controlled_sharing') is not True:
        if 'sharing_version' in info or 'sharing' in info: raise ValueError('Inconsistent TaskDock sharing metadata.')
        return None
    version=info.get('sharing_version');policy=info.get('sharing')
    if type(version) is not int or version<0 or not isinstance(policy,dict) or policy.get('controlled') is not True:
        raise ValueError('Invalid TaskDock sharing metadata.')
    for name,allowed in [('channels',CHANNELS),('planning_fields',set(FIELDS))]:
        rows=policy.get(name)
        if not isinstance(rows,list) or any(not isinstance(x,str) for x in rows) or len(set(rows))!=len(rows) or set(rows)-allowed:
            raise ValueError('Invalid TaskDock sharing selection.')
    return version,{'controlled':True,'channels':list(policy['channels']),'planning_fields':list(policy['planning_fields'])}

def fact(task,key):
    value=task.get('planning_details',{}).get(key,{})
    return value if isinstance(value,dict) else {}

def provided(task,key):
    value=fact(task,key)
    return value.get('value') if value.get('state')=='provided' and isinstance(value.get('value'),str) else ''

def blockers(task):
    return ' • '.join(x for x in (task.get('blocked_reason'),provided(task,'blockers'),provided(task,'dependencies'),fact(task,'blockers').get('taskdock_flag')) if isinstance(x,str) and x.strip())

def validate_task(task,info):
    policy=sharing(info)
    if policy is None:
        # Legacy credentials do not grant the new structured request facts/comments.
        return {k:v for k,v in task.items() if k not in {'planning_details','planning_readiness','planning_values','planning_source_updates','source_updates','planning_scope'}}
    selected=set(policy[1]['planning_fields'])
    details=task.get('planning_details',{})
    if not isinstance(details,dict) or set(details)!=selected:raise ValueError('TaskDock planning facts do not match the shared field selection.')
    normalized={}
    for key,value in details.items():
        if not isinstance(value,dict) or value.get('state') not in {'unknown','none','provided'}:raise ValueError('Invalid TaskDock planning information quality.')
        state=value['state'];text=value.get('value')
        if state=='provided' and (not isinstance(text,str) or not text.strip() or len(text)>100000) or state!='provided' and text is not None:
            raise ValueError('Invalid TaskDock planning value.')
        entry={'state':state,'value':text}
        for name in ('origin','updated_at','source_updated_at','taskdock_flag'):
            content=value.get(name)
            if content is not None and not isinstance(content,str):raise ValueError('Invalid TaskDock planning provenance.')
            if content is not None:entry[name]=content[:5000]
        if 'review_conflict' in value:
            if type(value['review_conflict']) is not bool:raise ValueError('Invalid TaskDock blocker conflict.')
            entry['review_conflict']=value['review_conflict']
        normalized[key]=entry
    result={k:v for k,v in task.items() if k not in {'planning_values','planning_source_updates'}}
    if selected:result['planning_details']=normalized
    readiness=result.get('planning_readiness')
    if readiness is not None:
        if not selected or not isinstance(readiness,dict) or readiness.get('state') not in {'limited_sharing','needs_information','request_details_complete'} or readiness.get('staffing_review_required') is not True:
            raise ValueError('Invalid TaskDock request readiness.')
        missing=readiness.get('missing')
        if not isinstance(missing,list) or any(not isinstance(key,str) or key not in selected or normalized[key]['state']!='unknown' for key in missing):
            raise ValueError('Invalid TaskDock missing request facts.')
    if 'source_updates' in result:
        sample=result['source_updates']
        if 'updates' not in policy[1]['channels'] or not isinstance(sample,dict) or type(sample.get('complete')) is not bool or not isinstance(sample.get('items'),list) or len(sample['items'])>50:
            raise ValueError('Invalid TaskDock comment sample or sharing scope.')
        if any(not isinstance(row,dict) or not isinstance(row.get('body',''),str) or len(row.get('body',''))>5000 for row in sample['items']):raise ValueError('Invalid TaskDock comment sample.')
    return result

QUESTIONS = {
    'issue_description':'What exactly is going wrong?',
    'requested_outcome':'What would a successful fix look like?',
    'impact':'What teaching or operations is this issue affecting?',
    'blockers':'Is anything preventing the work from starting, such as parts, approval or research?',
    'room':'Which room needs the work, or is this not room-related?',
    'equipment':'Which equipment is affected, or is equipment not involved?',
    'dependencies':'Does another task or person need to finish something first?',
    'troubleshooting':'What troubleshooting has already been tried?',
    'building':'Which building is involved, or is this not building-related?',
    'reported_priority':'What priority did the requester report?',
    'requester':'Who requested this work?',
    'contact':'Who should we contact for access or more information?',
}

def request_overview(task,info,fetched_at):
    """Read-only display/clarification facts; never manufactures staffing readiness."""
    details=task.get('planning_details',{})
    fields=[{'key':key,'label':FIELDS[key],**details[key]} for key in FIELDS if key in details]
    required=task.get('planning_readiness',{}).get('missing',[])
    order=list(dict.fromkeys([*required,*QUESTIONS]))
    questions=[{'key':key,'label':FIELDS[key],'question':QUESTIONS[key]} for key in order
               if key in QUESTIONS and fact(task,key).get('state')=='unknown']
    priority=task.get('priority')
    priority_label='Unknown'
    if priority is not None and task.get('priority_state')!='default_or_unknown':
        priority_label=next((str(row['name']) for row in info.get('definitions',{}).get('priorities',[])
                             if isinstance(row,dict) and row.get('value',row.get('id'))==priority and row.get('name')),str(priority))
    limited=bool(info.get('sharing',{}).get('controlled') and task.get('planning_readiness',{}).get('state')=='limited_sharing')
    return {'request_fields':fields,'request_questions':questions,'due_date':task.get('due_date'),
            'priority_label':priority_label,'taskdock_saved_at':fetched_at.isoformat(),
            'request_scope_notice':('Some request details are withheld by the sharing selection.' if limited else
                'Shared request facts only. Missing details remain unknown.' if fields else
                'Structured request facts are not shared in this saved copy. Enable fields in TaskDock, then refresh.')}
