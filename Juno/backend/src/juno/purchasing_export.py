"""Version-1 Concur Helper projection. Never retain raw export/private paths."""
from datetime import datetime, timezone
from uuid import UUID
import hashlib
import json


def text(value, limit=300):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
        raise ValueError('The helper export has an invalid text field.')
    return value


def instant(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None or result>datetime.now(timezone.utc): raise ValueError()
        return result.astimezone(timezone.utc).isoformat()
    except (ValueError,TypeError,AttributeError):
        raise ValueError('Helper timestamps must be dated, timezone-aware observations no later than now.') from None


def identity(value):
    try:return str(UUID(value))
    except (ValueError,TypeError,AttributeError):raise ValueError('Helper exports need valid instance and export identifiers.') from None


def period(value):
    from datetime import date
    if not isinstance(value,dict) or value.get('state') not in ('observed','unknown','not_searched'):
        raise ValueError('Helper date coverage needs an explicit observation state.')
    result={'state':value['state']}
    if value['state']=='observed':
        try:
            start=date.fromisoformat(value['start']);end=date.fromisoformat(value['end'])
            if start>end:raise ValueError()
        except (ValueError,TypeError,KeyError):raise ValueError('Invalid helper observation window.') from None
        result.update(start=str(start),end=str(end))
    return result


def read(content):
    from .purchasing import parse
    try: raw=json.loads(content)
    except (ValueError,TypeError):raise ValueError('Choose a valid Receipt Helper JSON export.') from None
    if not isinstance(raw,dict) or 'schema_version' not in raw:return parse(content),None
    if type(raw['schema_version']) is not int or raw['schema_version']!=1:
        raise ValueError('This helper export version is not supported.')
    meta={'schema_version':1,'helper_instance_id':identity(raw.get('helper_instance_id')),
          'export_id':identity(raw.get('export_id')),'created_at':instant(raw.get('created_at')),
          'observation_window':period(raw.get('observation_window')),
          'fingerprint':hashlib.sha256(content.encode()).hexdigest()}
    completeness=raw.get('completeness')
    if not isinstance(completeness,dict):raise ValueError('Helper source completeness is required.')
    allowed={'complete','partial','unknown','not_searched','current_session'}
    meta['completeness']={k:completeness.get(k,'unknown') for k in ('expenses','reports','orders','runs')}
    if any(not isinstance(v,str) or v not in allowed for v in meta['completeness'].values()):raise ValueError('Unknown helper completeness state.')
    meta['reports']=[];seen=set()
    reports=raw.get('reports');runs=raw.get('runs');orders=raw.get('orders')
    if not isinstance(reports,list) or len(reports)>100 or not isinstance(runs,list) or not 1<=len(runs)<=1000:
        raise ValueError('Use a bounded helper report and run export.')
    if orders!=[] or meta['completeness']['orders']!='not_searched':
        raise ValueError('This helper contract does not yet provide observed order records.')
    meta['orders']=[]
    for report in reports:
        if not isinstance(report,dict):raise ValueError('Invalid helper report.')
        ident=text(report.get('id'))
        if ident in seen:raise ValueError('Duplicate report identifier.')
        seen.add(ident)
        meta['reports'].append({'id':ident,'source_status':text(report.get('source_status')),
            'observed_at':instant(report.get('observed_at')),'reporting_period':period(report.get('reporting_period')),
            'submission_time_state':text(report.get('submission_time_state'))})
    meta['runs']=[];seen=set();last_scan=None
    for run in runs:
        if not isinstance(run,dict):raise ValueError('Invalid helper run.')
        ident=identity(run.get('id'));start=instant(run.get('started_at'));end=instant(run.get('ended_at'))
        if ident in seen or datetime.fromisoformat(start)>datetime.fromisoformat(end):raise ValueError('Invalid or duplicate helper run.')
        seen.add(ident)
        operation=text(run.get('operation'));outcome=text(run.get('outcome'))
        if operation not in ('scan','attach_and_verify','read_report_status') or outcome not in ('success','partial','failure','cancelled','unknown'):
            raise ValueError('Unknown helper run operation or outcome.')
        coverage=run.get('coverage')
        if not isinstance(coverage,dict) or any(v not in ('complete','failed','not_searched') for v in coverage.values()):
            raise ValueError('Invalid helper run source coverage.')
        safe_coverage={k:v for k,v in coverage.items() if k in ('concur','pcard','gmail','orders','vendor','receipts_folder')}
        meta['runs'].append({'id':ident,'operation':operation,'started_at':start,'ended_at':end,'outcome':outcome,
            'coverage':safe_coverage,'sign_in_state':text(run.get('sign_in_state'))})
        if operation=='scan':last_scan=meta['runs'][-1]
    expenses=raw.get('expenses')
    if expenses is None:
        if meta['completeness']['expenses']=='complete':raise ValueError('A complete expense scan cannot omit its rows.')
        meta['expense_observed_at']=None
        return None,meta
    if not last_scan or last_scan['outcome']!='success':raise ValueError('Expense rows require a successful scan.')
    rows=parse(json.dumps(expenses));report_ids={r['id'] for r in meta['reports']}
    for source,row in zip(expenses,rows):
        if text(source.get('report_id')) not in report_ids:raise ValueError('Expense report identity is missing from the export.')
        row['report_id']=source['report_id']
        row['receipt_search_outcome']=text(source.get('receipt_search_outcome'))
        row['account_coding_status']=text(source.get('account_coding_status'))
    meta['expense_observed_at']=last_scan['ended_at']
    return rows,meta
