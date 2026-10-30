"""Explicit-resource Slack, Smartsheet and Microsoft calendar reads; no write methods."""
import re
from datetime import datetime
from urllib.parse import quote
from .http import ReadError
from .common import required,text,identity,finish,selected,dates,timestamp,graph_pages,BoundedRows,UTC,busy_summary

SLACK='https://slack.com'
SMARTSHEET='https://api.smartsheet.com'


def slack_get(http,method,params=None):
    data=http.get(SLACK,'/api/'+method,params)
    if data.get('ok') is not True:
        error=data.get('error')
        if error in {'invalid_auth','not_authed','token_revoked','account_inactive'}:raise ReadError('Slack authorization is invalid or revoked. Enter an approved token again.',401)
        if error=='missing_scope':raise ReadError('Slack needs additional read permission for this selection. Use an approved token with the required history/read scopes.',403)
        if error in {'ratelimited','rate_limited'}:raise ReadError('Slack is rate limiting this connection. Wait before retrying.',429,60)
        raise ReadError('Slack could not read the selected conversation. The previous copy has been retained.',403)
    return data


def slack_pages(http,method,params,field):
    result=BoundedRows();cursor='';cursors=set();ids=set()
    for _ in range(50):
        data=slack_get(http,method,{**params,'limit':100,**({'cursor':cursor} if cursor else {})})
        rows=data.get(field)
        if not isinstance(rows,list):raise ReadError('Slack returned invalid pagination.')
        for row in rows:
            if not isinstance(row,dict):raise ReadError('Slack returned an invalid record.')
            ident=required(row.get('id') or row.get('ts'))
            if ident in ids:raise ReadError('Slack repeated a record during pagination.')
            ids.add(ident);result.append(row)
        meta=data.get('response_metadata',{})
        if not isinstance(meta,dict):raise ReadError('Slack returned invalid page metadata.')
        cursor=meta.get('next_cursor','')
        if not cursor:
            if data.get('has_more'):raise ReadError('Slack returned partial history without a next cursor.')
            return result
        if not isinstance(cursor,str) or len(cursor)>4096 or cursor in cursors:raise ReadError('Slack returned an invalid or repeated cursor.')
        cursors.add(cursor)
    raise ReadError('Slack page limit reached. Narrow the selected resources/window.',413)


def slack_profile(http):
    auth=slack_get(http,'auth.test')
    team=required(auth.get('team_id'));user=required(auth.get('user_id'))
    return {'id':identity('slack',team+':'+user),'label':text(auth.get('team') or team,200)+' · '+text(auth.get('user') or user,100)}


def discover_slack(http):
    account=slack_profile(http)
    try:values=slack_pages(http,'conversations.list',{'types':'public_channel,private_channel,im,mpim','exclude_archived':'true'},'channels')
    except ReadError as error:
        if error.status==403:return account,[],True
        raise
    resources=[{'id':required(r['id']),'label':text(r.get('name') or r.get('user') or r['id'],300)} for r in values]
    return account,resources,False


def slack_stamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9]{1,12}\.[0-9]{1,10}',value):raise ReadError('Slack returned an invalid message timestamp.')
    try:return datetime.fromtimestamp(float(value),UTC)
    except (ValueError,OverflowError,OSError):raise ReadError('Slack returned an invalid message timestamp.') from None


def read_slack(http,config,account):
    left,right=dates(config);rows=BoundedRows();seen=set();threads=config.get('include_threads',True)
    if type(threads) is not bool:raise ReadError('Choose whether to include Slack thread replies.',422)
    for channel in selected(config,r'[CDG][A-Z0-9]{3,32}'):
        info=slack_get(http,'conversations.info',{'channel':channel}).get('channel')
        if not isinstance(info,dict) or info.get('id')!=channel:raise ReadError('Slack returned a different selected conversation.')
        title=text(info.get('name') or info.get('user') or channel,300)
        params={'channel':channel,'oldest':str(left.timestamp()),'latest':str(right.timestamp()),'inclusive':'true'}
        parents=slack_pages(http,'conversations.history',params,'messages')
        def add(message):
            stamp=slack_stamp(message.get('ts'))
            if not left<=stamp<right:return
            ident=channel+':'+message['ts']
            if ident in seen:return
            seen.add(ident);body=text(message.get('text') or '(No readable text; attachment or system event omitted.)')
            rows.append({'id':'slack:'+ident,'kind':'message','title':body.splitlines()[0][:300],'notes':body,'location':title,'source':'slack',
                'observed_at':stamp.isoformat(),'sender':text(message.get('user') or message.get('bot_id') or 'Unknown sender',300),
                'provider_ids':{'channel':channel,'timestamp':message['ts'],'thread':text(message.get('thread_ts'),100)},
                'content_truncated':len(str(message.get('text') or ''))>20000})
        for parent in parents:
            add(parent)
            if threads and parent.get('reply_count',0):
                replies=slack_pages(http,'conversations.replies',{**params,'ts':parent['ts']},'messages')
                for reply in replies:add(reply)
    return finish(rows,{'account':account,'resources':config['resources'],'start':config['start'],'end':config['end'],'timezone':config.get('timezone','America/Chicago'),'include_threads':threads,
        'notice':'Selected conversation history in the chosen window'+(' plus readable replies to parents in that window.' if threads else '; thread replies were excluded by your selection.')+' Replies to older parents, provider retention and membership limits can omit context. Slack is not an atomic snapshot. Juno sends no messages and does not mark conversations read.'})


def smart_profile(http):
    data=http.get(SMARTSHEET,'/2.0/users/me')
    ident=str(data.get('id',''))
    if not ident.isdigit():raise ReadError('Smartsheet omitted the account identity.')
    return {'id':identity('smartsheet',ident),'label':text(data.get('email') or data.get('firstName') or 'Smartsheet account',300)}


def discover_smart(http):
    account=smart_profile(http);resources=[];seen=set();total=None
    for page in range(1,51):
        data=http.get(SMARTSHEET,'/2.0/sheets',{'page':page,'pageSize':100,'includeAll':'false'})
        values=data.get('data');count=data.get('totalCount');pages=data.get('totalPages')
        if not isinstance(values,list) or type(count) is not int or type(pages) is not int or count<0 or not 0<=pages<=50 or data.get('pageNumber')!=page:raise ReadError('Smartsheet returned invalid sheet-list pagination.')
        if total is not None and count!=total:raise ReadError('The Smartsheet resource list changed while paging. Discover again.')
        total=count
        for value in values:
            ident=str(value.get('id',''))
            if not ident.isdigit() or ident in seen:raise ReadError('Smartsheet returned duplicate or invalid sheet identities.')
            seen.add(ident);resources.append({'id':ident,'label':text(value.get('name') or ident,300)})
        if page>=pages:
            if len(resources)!=total:raise ReadError('Smartsheet returned an incomplete sheet list.')
            return account,resources
    raise ReadError('Smartsheet sheet-list page limit reached.',413)


def read_smart(http,config,account):
    result=BoundedRows()
    for sheet in selected(config,r'[1-9][0-9]{0,19}'):
        version=None;total=None;seen=set();count=0
        for page in range(1,51):
            data=http.get(SMARTSHEET,'/2.0/sheets/'+sheet,{'page':page,'pageSize':100})
            if str(data.get('id'))!=sheet or type(data.get('totalRowCount')) is not int or data['totalRowCount']<0 or type(data.get('version')) is not int:raise ReadError('Smartsheet returned invalid sheet identity/version/counts.')
            if total is None:total=data['totalRowCount'];version=data['version']
            elif total!=data['totalRowCount'] or version!=data['version']:raise ReadError('The sheet changed during the read. The previous copy has been retained.',409)
            if total>5000:raise ReadError('A selected sheet exceeds 5,000 rows. Select a smaller sheet/view.',413)
            columns=data.get('columns');values=data.get('rows')
            if not isinstance(columns,list) or not isinstance(values,list) or len(values)>100:raise ReadError('Smartsheet returned invalid sheet rows or columns.')
            titles={};primary=[]
            for column in columns:
                ident=str(column.get('id',''))
                if not ident.isdigit() or ident in titles:raise ReadError('Smartsheet returned invalid column identities.')
                titles[ident]=text(column.get('title') or ident,300)
                if column.get('primary') is True:primary.append(ident)
            if len(primary)!=1:raise ReadError('Smartsheet did not identify one primary column.')
            for row in values:
                ident=str(row.get('id',''));cells=row.get('cells')
                if not ident.isdigit() or ident in seen or not isinstance(cells,list):raise ReadError('Smartsheet repeated or returned an invalid row.')
                seen.add(ident);count+=1;parts=[];heading='';cell_ids=set()
                for cell in cells:
                    column=str(cell.get('columnId',''))
                    if column not in titles or column in cell_ids:raise ReadError('Smartsheet returned inconsistent row cells.')
                    cell_ids.add(column);value=cell.get('displayValue',cell.get('value',''))
                    if value is None:value=''
                    if isinstance(value,(dict,list)):value='[Structured value omitted]'
                    value=text(str(value),2000)
                    if column==primary[0]:heading=value
                    if value:parts.append(titles[column]+': '+value)
                raw='\n'.join(parts)
                result.append({'id':'smartsheet:'+sheet+':'+ident,'kind':'sheet_row','title':heading[:300] or 'Row '+str(row.get('rowNumber') or ident),
                    'notes':raw[:20000],'location':text(data.get('name') or sheet,300),'source':'smartsheet','content_truncated':len(raw)>20000,
                    'provider_ids':{'sheet_id':sheet,'row_id':ident,'parent_row_id':str(row['parentId']) if row.get('parentId') else None},'sheet_version':version})
            if count==total:break
            if not values or count>total:raise ReadError('Smartsheet returned partial or inconsistent rows.')
        else:raise ReadError('Smartsheet page limit reached. Select a smaller sheet.',413)
        check=http.get(SMARTSHEET,'/2.0/sheets/'+sheet,{'page':1,'pageSize':1})
        if check.get('version')!=version or check.get('totalRowCount')!=total:raise ReadError('The sheet changed before the read completed. Refresh again.',409)
    return finish(result,{'account':account,'resources':config['resources'],'notice':'Selected Smartsheet rows with primary-column titles and readable cell excerpts. No row/status/checkbox changes, attachments or comments are requested. Per-sheet versions are checked; separate sheets are not one atomic snapshot. TaskDock remains authoritative for consolidated tasks.'})


def discover_microsoft(http):
    data=http.get('https://graph.microsoft.com','/v1.0/me',{'$select':'id,displayName,mail,userPrincipalName'})
    account={'id':identity('outlook_calendar',required(data.get('id'))),'label':text(data.get('mail') or data.get('userPrincipalName') or data.get('displayName') or 'Microsoft account',300)}
    resources=[{'id':required(r['id']),'label':text(r.get('name') or r['id'],300)} for r in graph_pages(http,'/v1.0/me/calendars',{'$top':100,'$select':'id,name'})]
    return account,resources


def read_microsoft(http,config,account):
    left,right=dates(config);rows=BoundedRows()
    for calendar in selected(config):
        path='/v1.0/me/calendars/'+quote(calendar,safe='')+'/calendarView'
        events=graph_pages(http,path,{'startDateTime':left.isoformat(),'endDateTime':right.isoformat(),'$top':100},headers={'Prefer':'outlook.timezone="UTC"'})
        for event in events:
            if event.get('isCancelled') or (event.get('responseStatus') or {}).get('response')=='declined':continue
            try:
                def instant(value):
                    if not isinstance(value,dict) or value.get('timeZone') not in ('UTC','Etc/UTC'):raise ReadError('Microsoft did not return the requested UTC event timezone.')
                    stamp=value['dateTime']
                    if not isinstance(stamp,str):raise ValueError()
                    if not stamp.endswith('Z') and not re.search(r'[+-][0-9]{2}:[0-9]{2}$',stamp):stamp+='Z'
                    return datetime.fromisoformat(timestamp(stamp))
                a=instant(event.get('start'));b=instant(event.get('end'))
                if b<a:raise ValueError()
            except (KeyError,TypeError,ValueError):raise ReadError('Microsoft returned invalid event timing.') from None
            if a>=right or b<=left:continue
            body=event.get('body',{})
            if not isinstance(body,dict):raise ReadError('Microsoft returned invalid event content.')
            ident=required(event.get('id'))
            rows.append({'id':'outlook_calendar:'+calendar+':'+ident,'kind':'calendar_event','title':text(event.get('subject') or 'Busy event (details unavailable)',300),
                'notes':text(body.get('content'),html=str(body.get('contentType','')).lower()=='html'),
                'location':text((event.get('location') or {}).get('displayName'),500),'start':a.isoformat(),'end':b.isoformat(),
                'busy':event.get('showAs')!='free','all_day':event.get('isAllDay') is True,'source':'outlook_calendar',
                'provider_ids':{'calendar_id':calendar,'event_id':ident,'ical_uid':text(event.get('iCalUId'),512)}})
    return finish(rows,{'account':account,'resources':config['resources'],'start':config['start'],'end':config['end'],'timezone':config.get('timezone','America/Chicago'),
        'busy_days':busy_summary(rows,config['start'],config['end'],config.get('timezone','America/Chicago')),
        'notice':'Selected Microsoft calendars in the explicit window, expanded by calendarView. Cancelled/self-declined events are omitted; showAs free does not block time. No calendar writes or attendee actions are performed.'})
