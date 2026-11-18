"""Read a reviewed Receipt Helper export; never access vendor/email credentials."""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import json
import hashlib
import re
from fastapi import Depends, HTTPException, Request
from pydantic import Field
from .planning import Strict
from .models import IntegrationSnapshot, now
from .integrations_api import check_evidence_size


class PurchaseImport(Strict):
    content: str = Field(max_length=4_000_000)
    observed_at: datetime
    expected_id: str | None = Field(default=None, max_length=36)


def parse(content):
    try: data = json.loads(content)
    except (ValueError, TypeError): raise ValueError('Choose a valid Receipt Helper JSON export.') from None
    rows = data.get('expenses') if isinstance(data, dict) else data
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValueError('Use an expense array or a helper plan with at most 5,000 expenses.')
    result = []; seen = set()
    for row in rows:
        if not isinstance(row, dict): raise ValueError('Every expense needs structured fields.')
        identity = row.get('expense_id', row.get('id'))
        merchant = row.get('merchant'); currency = row.get('currency')
        if not isinstance(identity, str) or not 1 <= len(identity) <= 300 or identity in seen:
            raise ValueError('Expenses need unique stable IDs.')
        if not isinstance(merchant, str) or not 1 <= len(merchant.strip()) <= 300:
            raise ValueError('Every expense needs a merchant.')
        if not isinstance(currency, str) or not re.fullmatch('[A-Z]{3}', currency):
            raise ValueError('Expenses need a three-letter currency code.')
        try:
            amount = Decimal(str(row.get('amount')))
            when = date.fromisoformat(row.get('date', ''))
        except (InvalidOperation, ValueError, TypeError): raise ValueError('Check expense amount and date.') from None
        if not amount.is_finite() or abs(amount) > 10_000_000 or amount != amount.quantize(Decimal('.01')):
            raise ValueError('Use finite expense amounts with at most two decimal places.')
        status = row.get('status') or ('already_attached' if row.get('has_receipt') is True else 'not_checked')
        if status not in {'already_attached','ambiguous','missing_receipt','review','not_checked'}:
            raise ValueError('The helper returned an unsupported receipt status.')
        seen.add(identity)
        # Deliberately omit local paths, email contents, report URLs and extra fields.
        result.append({'id': identity, 'merchant': merchant.strip(), 'title': merchant.strip(),
                       'amount': format(amount, '.2f'), 'currency': currency, 'date': str(when), 'status': status})
    return result


class PurchaseLinkInput(Strict):
    expense_id: str = Field(min_length=1, max_length=300)
    snapshot_id: str = Field(min_length=36, max_length=36)
    task_id: str = Field(min_length=1, max_length=500)
    workspace_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=0)


def expense_key(item):
    return hashlib.sha256(json.dumps([item[k] for k in ('id','merchant','amount','currency','date')], ensure_ascii=False).encode()).hexdigest()


def task_context(session, owner):
    from .taskdock_api import active_snapshot
    from .models import TaskDockState
    snapshot = active_snapshot(session, owner)
    status = session.get(TaskDockState, owner)
    usable = bool(snapshot and not snapshot.info.get('sharing_restricted') and not (status and status.error)
                  and now() - snapshot.fetched_at <= timedelta(hours=24))
    return snapshot, usable


def asset_context(session, owner):
    from .operations import sources
    _,beacon,_,stale=sources(session,owner)
    usable=bool(beacon and not stale and beacon.details.get('instance_id'))
    choices={}
    if usable:
        for item in beacon.items:
            asset=item.get('asset_id')
            if isinstance(asset,str) and asset:
                choices.setdefault(asset,{'id':asset,'title':str(item.get('item') or asset),'location':str(item.get('location') or '')})
    return beacon, choices


def asset_state(session,owner,data,expenses):
    beacon,choices=asset_context(session,owner)
    links=[]
    for expense_id,link in data.get('purchasing_asset_links',{}).items():
        expense=expenses.get(expense_id)
        valid=bool(expense and expense_key(expense)==link['expense_key'] and beacon and choices.get(link['asset_id'])
            and beacon.origin==link['beacon_origin'] and beacon.details.get('instance_id')==link['beacon_instance'])
        links.append({'expense_id':expense_id,'asset_id':link['asset_id'],'active':valid,
            'asset_title':choices[link['asset_id']]['title'] if valid else None,'recorded_at':link['recorded_at']})
    return {'asset_choices':list(choices.values()),'asset_links':links,
        'beacon_snapshot_id':beacon.id if beacon and choices else None,
        'beacon_instance':beacon.details.get('instance_id') if beacon and choices else None,
        'asset_notice':'Choose exact equipment IDs from the current shared Beacon copy. This list covers only equipment referenced by the feed, not the whole inventory. A link is not proof of receipt, compatibility, installation or repair.' if choices else 'Refresh a Beacon feed with stable equipment and instance IDs before reviewing equipment links. Unavailable equipment is not considered repaired.'}


class PurchaseAssetInput(Strict):
    expense_id:str=Field(min_length=1,max_length=300)
    snapshot_id:str=Field(min_length=1,max_length=36)
    expected_revision:int=Field(ge=0)
    asset_id:str=Field(min_length=1,max_length=500)
    beacon_snapshot_id:str|None=Field(default=None,max_length=36)
    beacon_instance:str|None=Field(default=None,max_length=500)


def parse_reports(content):
    payload = json.loads(content)
    if not isinstance(payload, dict) or payload.get('schema_version') != 1:
        return []
    raw = payload.get('reports', [])
    if not isinstance(raw, list) or len(raw) > 50:
        raise ValueError('Choose an export with at most 50 Concur report records.')
    reports = {}
    def money(value):
        if not isinstance(value, str) or not re.fullmatch(r'-?[0-9]{1,8}\.[0-9]{2}', value):
            raise ValueError('Use exact two-decimal report and Org amounts.')
        return Decimal(value)
    for source in raw:
        if not isinstance(source, dict):
            raise ValueError('Every report needs structured fields.')
        if source.get('total') is None and source.get('allocation_state', 'not_searched') == 'not_searched':
            continue  # Older draft-only expense export.
        try:
            identity = source['id']
            title = source['title'].strip()
            status = source['source_status'].strip()
            observed = datetime.fromisoformat(source['observed_at'])
            period = source['reporting_period']
            start = date.fromisoformat(period['start'])
            end = date.fromisoformat(period['end'])
            currency = source['currency']
            total = money(source['total'])
            allocation = source['allocation_state']
            amounts = source.get('org_totals', [])
            if not re.fullmatch(r'[0-9a-f]{64}', identity) or identity in reports:
                raise ValueError
            if (not 1 <= len(title) <= 250 or not 1 <= len(status) <= 120
                    or any(ord(c) < 32 for c in title + status)
                    or observed.tzinfo is None or observed > now() or start > end
                    or not re.fullmatch('[A-Z]{3}', currency)
                    or allocation not in {'verified', 'unavailable'} or not isinstance(amounts, list)
                    or len(amounts) > 100 or (allocation == 'verified') != bool(amounts)):
                raise ValueError
            totals = {}
            for entry in amounts:
                org = entry['org']
                if not re.fullmatch(r'[0-9]{5}', org) or org in totals:
                    raise ValueError
                totals[org] = money(entry['amount'])
            if totals and sum(totals.values(), Decimal(0)) != total:
                raise ValueError
        except (AttributeError, KeyError, TypeError, ValueError, InvalidOperation):
            raise ValueError('Check the Concur report status, dates, and reconciled Org totals.') from None
        reports[identity] = {
            'id': identity, 'title': title, 'source_status': status,
            'observed_at': observed.astimezone(timezone.utc).isoformat(),
            'start': start.isoformat(), 'end': end.isoformat(),
            'currency': currency, 'total': format(total, '.2f'), 'allocation_state': allocation,
            'org_totals': [{'org': org, 'amount': format(amount, '.2f')} for org, amount in sorted(totals.items())],
        }
    return list(reports.values())


def merge_reports(previous, incoming):
    reports = {report['id']: report for report in previous}
    for report in incoming:
        existing = reports.get(report['id'])
        if existing and (report['observed_at'] < existing['observed_at']
                         or report['observed_at'] == existing['observed_at'] and report != existing):
            raise ValueError('A newer or conflicting observation already exists for this Concur report.')
        reports[report['id']] = report
    if len(reports) > 100:
        raise ValueError('The saved Concur report limit is 100.')
    return sorted(reports.values(), key=lambda report: (report['start'], report['id']), reverse=True)


def state(session, owner):
    from .operations import saved
    row = session.get(IntegrationSnapshot, (owner, 'purchasing'))
    active = row is not None and not row.details.get('tombstone')
    items = row.items if active else []
    operation, data = saved(session, owner)
    td, usable = task_context(session, owner)
    tasks = {str(task['id']): task for task in td.items} if usable else {}
    expenses = {item['id']: item for item in items}
    links = []
    for identity, link in data.get('purchasing_links', {}).items():
        expense = expenses.get(identity)
        valid = bool(expense and expense_key(expense) == link['expense_key'] and td
                     and td.info.get('workspace_id') == link['workspace_id'] and link['task_id'] in tasks)
        links.append({'expense_id': identity, 'active': valid, 'task_id':link['task_id'], 'workspace_id':link['workspace_id'],
                      'task_title':tasks[link['task_id']].get('title','Untitled task') if valid else None,
                      'recorded_at':link['recorded_at']})
    return {**asset_state(session,owner,data,expenses), 'items': items, 'id': row.id if active else None,
            'observed_at': row.details.get('observed_at') if active else None,
            'imported_at': row.fetched_at if active else None,
            'reports': row.details.get('reports', []) if active else [],
            'links_revision': operation.revision if operation else 0, 'links': links,
            'workspace_id':td.info.get('workspace_id') if usable else None,
            'task_choices':[{'id': identity, 'title':task.get('title') or 'Untitled task'} for identity, task in tasks.items()],
            'link_notice':'Links are reviewed references only. They do not establish funding, receipt, approval, delivery or equipment readiness. Financial details are not automatically added to chair emails.' if usable else 'Refresh TaskDock successfully before reviewing purchase-to-task links. Unavailable or changed records do not retain an active link.',
            'helper_export': row.details.get('helper_export') if active else None,
            'notice': ((row.details.get('notice','')+' ') if active else '') + 'Receipt-match states come from your imported helper copy. Review them in the helper; submission, approval and payment stay in Concur.'}


def install(app, db, device, lock_owner):
    def asset_change(value,actor,session,remove):
        from .operations import saved,write_state
        lock_owner(session,actor.owner_id)
        purchase=session.get(IntegrationSnapshot,(actor.owner_id,'purchasing'))
        if not purchase or purchase.id!=value.snapshot_id or purchase.details.get('tombstone'):
            raise HTTPException(409,'Purchasing copy changed. Reload before reviewing equipment.')
        expense=next((item for item in purchase.items if item['id']==value.expense_id),None)
        if expense is None:raise HTTPException(404,'Expense not available in your current copy.')
        operation,data=saved(session,actor.owner_id)
        if (operation.revision if operation else 0)!=value.expected_revision:raise HTTPException(409,'Reviewed references changed. Reload before saving.')
        links=data.get('purchasing_asset_links',{})
        previous=links.get(value.expense_id)
        if remove:
            if not previous or previous['asset_id']!=value.asset_id:raise HTTPException(409,'Equipment link changed. Reload before removing it.')
            links.pop(value.expense_id);record=None
        else:
            beacon,choices=asset_context(session,actor.owner_id)
            if not beacon or beacon.id!=value.beacon_snapshot_id or beacon.details.get('instance_id')!=value.beacon_instance or value.asset_id not in choices:
                raise HTTPException(409,'Beacon equipment or sharing changed. Refresh and review the exact equipment again.')
            record={'asset_id':value.asset_id,'expense_key':expense_key(expense),'beacon_origin':beacon.origin,
                'beacon_instance':value.beacon_instance,'beacon_snapshot_id':beacon.id,'recorded_at':now().isoformat(),'actor_id':actor.id}
            links[value.expense_id]=record
        data['purchasing_asset_links']=links
        data['purchasing_asset_history']=[*data.get('purchasing_asset_history',[]),{'expense_id':value.expense_id,'before':previous,'after':record}]
        write_state(session,actor,data,value.expected_revision)
        return state(session,actor.owner_id)

    @app.post('/v1/purchasing/asset-link')
    def link_asset(value:PurchaseAssetInput,actor=Depends(device),session=Depends(db)):
        return asset_change(value,actor,session,False)

    @app.post('/v1/purchasing/asset-unlink')
    def unlink_asset(value:PurchaseAssetInput,actor=Depends(device),session=Depends(db)):
        return asset_change(value,actor,session,True)

    @app.post('/v1/purchasing/preview')
    def preview_copy(value: PurchaseImport, actor=Depends(device)):
        try:
            from .purchasing_export import read
            items,meta=read(value.content)
            return {'items':items or [],'reports':parse_reports(value.content),'helper_export':meta,'preserves_expenses':items is None}
        except ValueError as error: raise HTTPException(422, str(error)) from None

    @app.get('/v1/purchasing')
    def read(actor=Depends(device), session=Depends(db)):
        return state(session, actor.owner_id)

    @app.post('/v1/purchasing/link')
    def link_task(value: PurchaseLinkInput, actor=Depends(device), session=Depends(db)):
        from .operations import saved, write_state
        lock_owner(session, actor.owner_id)
        row = session.get(IntegrationSnapshot, (actor.owner_id, 'purchasing'))
        if row is None or row.id != value.snapshot_id or row.details.get('tombstone'):
            raise HTTPException(409, 'Purchasing evidence changed. Reload before reviewing the link.')
        expense = next((item for item in row.items if item['id'] == value.expense_id), None)
        if expense is None: raise HTTPException(404, 'This expense is not in your saved purchasing copy.')
        td, usable = task_context(session, actor.owner_id)
        if not usable or td.info.get('workspace_id') != value.workspace_id:
            raise HTTPException(409, 'Refresh and review the current TaskDock workspace before linking.')
        if not any(str(task['id']) == value.task_id for task in td.items):
            raise HTTPException(404, 'This task is not in your authorized TaskDock copy.')
        operation, data = saved(session, actor.owner_id)
        links = data.get('purchasing_links', {})
        current = links.get(value.expense_id)
        proposed = {'task_id':value.task_id, 'workspace_id':value.workspace_id, 'expense_key':expense_key(expense)}
        if current and all(current.get(key) == content for key, content in proposed.items()):
            return state(session, actor.owner_id)
        if (operation.revision if operation else 0) != value.expected_revision:
            raise HTTPException(409, 'Reviewed references changed. Reload before saving this link.')
        record = {**proposed, 'recorded_at':now().isoformat(), 'snapshot_id':row.id}
        history = data.get('purchasing_link_history', [])
        data['purchasing_link_history'] = [*history, {'expense_id':value.expense_id, 'before':current, 'after':record}]
        data['purchasing_links'] = {**links, value.expense_id:record}
        write_state(session, actor, data, value.expected_revision)
        return state(session, actor.owner_id)

    @app.post('/v1/purchasing/unlink')
    def unlink_task(value: PurchaseLinkInput, actor=Depends(device), session=Depends(db)):
        from .operations import saved, write_state
        lock_owner(session, actor.owner_id)
        operation, data = saved(session, actor.owner_id)
        current = data.get('purchasing_links', {}).get(value.expense_id)
        if current is None: return state(session, actor.owner_id)
        if (operation.revision if operation else 0) != value.expected_revision:
            raise HTTPException(409, 'Reviewed references changed. Reload before removing a link.')
        if current['task_id'] != value.task_id or current['workspace_id'] != value.workspace_id:
            raise HTTPException(409, 'This expense is now linked differently. Reload before removing a link.')
        data['purchasing_link_history'] = [*data.get('purchasing_link_history', []), {'expense_id':value.expense_id,'before':current,'after':None,'recorded_at':now().isoformat()}]
        data['purchasing_links'] = {key:link for key,link in data['purchasing_links'].items() if key != value.expense_id}
        write_state(session, actor, data, value.expected_revision)
        return state(session, actor.owner_id)

    @app.post('/v1/purchasing/import')
    def import_copy(value: PurchaseImport, request: Request, actor=Depends(device), session=Depends(db)):
        if request.scope.get('juno_lan'): raise HTTPException(403, 'Import purchasing evidence on the work Mac.')
        if value.observed_at.tzinfo is None or value.observed_at > now():
            raise HTTPException(422, 'Use a dated observation with an explicit timezone, no later than now.')
        try:
            from .purchasing_export import read
            items,meta=read(value.content)
            reports=parse_reports(value.content)
        except ValueError as error: raise HTTPException(422, str(error)) from None
        lock_owner(session, actor.owner_id)
        row = session.get(IntegrationSnapshot, (actor.owner_id, 'purchasing'))
        from .operations import saved
        from .models import OperationalState
        operation,data=saved(session,actor.owner_id)
        receipt_key=(meta['helper_instance_id']+':'+meta['export_id']) if meta else None
        receipts=data.get('purchasing_exports',{})
        if receipt_key in receipts:
            if receipts[receipt_key]!=meta['fingerprint']:
                raise HTTPException(409,'This helper export ID was already used with different contents.')
            return {**state(session,actor.owner_id),'already_imported':True}
        if (row.id if row else None) != value.expected_id:
            raise HTTPException(409, 'Purchasing evidence changed. Reload before importing.')
        from uuid import uuid4
        try:
            retained_reports = merge_reports(row.details.get('reports', []) if row else [], reports)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
        replaces_expenses=items is not None
        if not replaces_expenses:items=list(row.items) if row and not row.details.get('tombstone') else []
        observed=(meta.get('expense_observed_at') if meta and replaces_expenses else value.observed_at.astimezone(timezone.utc).isoformat())
        details={'reports':retained_reports,'observed_at':observed if replaces_expenses else (row.details.get('observed_at') if row else None),
                 'notice':'Explicit reviewed file import; no email or vendor connection is implied.'}
        if meta:
            details['helper_export']=meta
            receipts[receipt_key]=meta['fingerprint'];data['purchasing_exports']=receipts
            if operation is None:operation=OperationalState(owner_id=actor.owner_id);session.add(operation)
            operation.data=data;operation.revision=(operation.revision or 0)+1;operation.updated_at=now()
        if not replaces_expenses:
            details['notice']='Run diagnostics imported; earlier expense rows and their observation date are retained. No successful expense scan is inferred.'
        check_evidence_size(session, actor.owner_id, 'purchasing', items, details)
        from .companion import invalidate_context
        invalidate_context(session, actor.owner_id, 'integration:purchasing')
        if row is None:
            row = IntegrationSnapshot(owner_id=actor.owner_id, kind='purchasing'); session.add(row)
        row.id = str(uuid4()); row.origin = 'Reviewed Receipt Helper export'; row.items = items
        row.details = details; row.fetched_at = now(); row.error = None
        session.commit()
        return state(session, actor.owner_id)
