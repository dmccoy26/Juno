"""Read selected Google resources with native desktop OAuth credentials."""
import base64
from datetime import date,datetime,timedelta
from urllib.parse import quote
from .http import ReadError
from .common import text,required,identity,finish,selected,dates,timestamp,paged,aware,UTC,busy_summary,BoundedRows

USERINFO='https://openidconnect.googleapis.com'
GMAIL='https://gmail.googleapis.com'
CALENDAR='https://www.googleapis.com'
TASKS='https://tasks.googleapis.com'
CHAT='https://chat.googleapis.com'


def profile(http,provider):
    data=http.get(USERINFO,'/v1/userinfo')
    sub=required(data.get('sub'),'account identity')
    return {'id':identity(provider,sub),'label':text(data.get('email') or data.get('name') or 'Google account',300)}


def discover(http,provider):
    account=profile(http,provider)
    if provider=='gmail':resources=[]
    elif provider=='google_calendar':
        values=paged(http,CALENDAR,'/calendar/v3/users/me/calendarList',{'maxResults':100,'showDeleted':'false'})
        resources=[{'id':required(r['id']),'label':text(r.get('summary') or r['id'],300)} for r in values if r.get('accessRole') in ('owner','writer','reader','freeBusyReader') and not r.get('deleted')]
    elif provider=='google_tasks':
        resources=[{'id':required(r['id']),'label':text(r.get('title') or r['id'],300)} for r in paged(http,TASKS,'/tasks/v1/users/@me/lists',{'maxResults':100})]
    elif provider=='google_chat':
        resources=[{'id':required(r['name']),'label':text(r.get('displayName') or r['name'],300)} for r in paged(http,CHAT,'/v1/spaces',{'pageSize':100},field='spaces')]
    else:raise ReadError('Unsupported Google provider.',422)
    return account,resources


def message_body(payload):
    plain=[];html=[];count=0
    def visit(part,depth=0):
        nonlocal count
        count+=1
        if count>200 or depth>20 or not isinstance(part,dict):raise ReadError('A message exceeded the safe MIME parsing limits.')
        if part.get('filename'):return
        mime=part.get('mimeType','')
        body=part.get('body',{})
        if not isinstance(body,dict):raise ReadError('Gmail returned an invalid message body.')
        raw=body.get('data')
        if raw is not None and mime in ('text/plain','text/html'):
            if not isinstance(raw,str) or len(raw)>2_000_000:raise ReadError('One email body exceeds the safe content limit.',413)
            try:decoded=base64.b64decode(raw+'='*((-len(raw))%4),altchars=b'-_',validate=True).decode('utf-8',errors='replace')
            except (ValueError,UnicodeError):raise ReadError('Gmail returned invalid encoded message content.') from None
            (plain if mime=='text/plain' else html).append(decoded)
        parts=part.get('parts',[])
        if not isinstance(parts,list):raise ReadError('Gmail returned invalid MIME parts.')
        for child in parts:visit(child,depth+1)
    visit(payload)
    raw='\n'.join(plain or html);return text(raw,20000,html=not plain),len(raw)>20000,bool(plain or html)


def read_gmail(http,config,account):
    query=config.get('query','in:inbox is:unread')
    if not isinstance(query,str) or not query.strip() or len(query)>500:raise ReadError('Enter a Gmail search query of 1–500 characters.',422)
    mailbox=http.get(GMAIL,'/gmail/v1/users/me/profile')
    address=required(mailbox.get('emailAddress'),'mailbox identity')
    if '@' in account['label'] and address.casefold()!=account['label'].casefold():raise ReadError('Google returned a different mailbox identity. Reconnect before reading.')
    records=paged(http,GMAIL,'/gmail/v1/users/me/messages',{'q':query,'maxResults':100,'includeSpamTrash':'false'},field='messages',limit=10)
    if len(records)>500:raise ReadError('The email query exceeds 500 messages. Narrow the query before importing bodies.',413)
    rows=BoundedRows()
    for item in records:
        ident=required(item.get('id'))
        message=http.get(GMAIL,'/gmail/v1/users/me/messages/'+quote(ident,safe=''),{'format':'full'})
        if message.get('id')!=ident:raise ReadError('Gmail returned a different message.')
        labels=message.get('labelIds',[])
        if not isinstance(labels,list) or any(not isinstance(x,str) for x in labels):raise ReadError('Gmail returned invalid labels.')
        if {'SPAM','TRASH'} & set(labels):continue
        payload=message.get('payload',{});body,truncated,available=message_body(payload)
        headers=payload.get('headers',[])
        if not isinstance(headers,list):raise ReadError('Gmail returned invalid message headers.')
        fields={}
        for header in headers:
            if isinstance(header,dict) and isinstance(header.get('name'),str):fields.setdefault(header['name'].casefold(),text(header.get('value'),2000))
        try:observed=datetime.fromtimestamp(int(message['internalDate'])/1000,UTC).isoformat()
        except (ValueError,KeyError,TypeError,OverflowError,OSError):raise ReadError('Gmail returned an invalid message timestamp.') from None
        notes='From: '+fields.get('from','Unknown sender')+'\nSent: '+fields.get('date',observed)+'\n\n'+(body if available else text(message.get('snippet')))
        rows.append({'id':'gmail:'+ident,'kind':'email','title':fields.get('subject') or '(No subject)',
            'notes':notes,'source':'gmail','observed_at':observed,'unread':'UNREAD' in labels,'content_truncated':truncated,'body_available':available,
            'provider_ids':{'mailbox':address,'message_id':ident,'thread_id':text(message.get('threadId'),512)},
            'notice':'Reading does not mark email read. Body is a plain-text excerpt; attachments and remote images are omitted.'})
    return finish(rows,{'account':account,'query':query,'notice':'Matching Gmail messages only, using the saved search query. This query is not restricted by the calendar date fields. Reads are sequential, not an atomic mailbox snapshot. Emails are evidence, not TaskDock tasks.'})


def event_times(event,tz):
    start=event.get('start');end=event.get('end')
    if not isinstance(start,dict) or not isinstance(end,dict):raise ReadError('Google Calendar omitted event timing.')
    all_day='date' in start
    if all_day:
        try:a=aware(date.fromisoformat(start['date']),tz);b=aware(date.fromisoformat(end['date']),tz)
        except (ValueError,KeyError):raise ReadError('Google Calendar returned an invalid all-day interval.') from None
    else:a=datetime.fromisoformat(timestamp(start.get('dateTime')));b=datetime.fromisoformat(timestamp(end.get('dateTime')))
    if b<a:raise ReadError('Google Calendar returned an event ending before its start.')
    return a,b,all_day


def read_calendar(http,config,account):
    left,right=dates(config);rows=BoundedRows()
    for calendar in selected(config):
        path='/calendar/v3/calendars/'+quote(calendar,safe='')+'/events'
        events=paged(http,CALENDAR,path,{'maxResults':250,'singleEvents':'true','showDeleted':'false','timeMin':left.isoformat(),'timeMax':right.isoformat(),'timeZone':config.get('timezone','America/Chicago'),'orderBy':'startTime'})
        for event in events:
            if event.get('status')=='cancelled':continue
            attendees=event.get('attendees',[])
            if not isinstance(attendees,list):raise ReadError('Google Calendar returned invalid attendance metadata.')
            if any(a.get('self') is True and a.get('responseStatus')=='declined' for a in attendees if isinstance(a,dict)):continue
            a,b,all_day=event_times(event,left.tzinfo)
            if a>=right or b<=left:continue
            ident=required(event.get('id'))
            rows.append({'id':'google_calendar:'+calendar+':'+ident,'kind':'calendar_event',
                'title':text(event.get('summary') or 'Busy event (details unavailable)',300),'notes':text(event.get('description'),html=True),
                'location':text(event.get('location'),500),'start':a.astimezone(UTC).isoformat(),'end':b.astimezone(UTC).isoformat(),
                'busy':event.get('transparency')!='transparent','all_day':all_day,'status':text(event.get('status') or 'unknown',50),
                'source':'google_calendar','provider_ids':{'calendar_id':calendar,'event_id':ident,'ical_uid':text(event.get('iCalUID'),512)}})
    return finish(rows,{'account':account,'resources':config['resources'],'start':config['start'],'end':config['end'],'timezone':config.get('timezone','America/Chicago'),
        'busy_days':busy_summary(rows,config['start'],config['end'],config.get('timezone','America/Chicago')),
        'notice':'Selected Google calendars within the explicit window. Recurrences/exceptions are expanded by Google; cancelled and self-declined events do not block time. Missing/private details stay unknown. Availability alone does not establish room access or employee capability.'})


def read_tasks(http,config,account):
    rows=BoundedRows()
    for tasklist in selected(config):
        values=paged(http,TASKS,'/tasks/v1/lists/'+quote(tasklist,safe='')+'/tasks',{'maxResults':100,'showCompleted':'true','showHidden':'true','showDeleted':'false','showAssigned':'true'})
        for value in values:
            if value.get('deleted'):continue
            ident=required(value.get('id'));due=value.get('due')
            if due:
                try:due=str(date.fromisoformat(due[:10]))
                except (ValueError,TypeError):raise ReadError('Google Tasks returned an invalid due date.') from None
            rows.append({'id':'google_tasks:'+tasklist+':'+ident,'kind':'external_task','title':text(value.get('title') or '(Untitled task)',300),
                'notes':text(value.get('notes')),'source':'google_tasks','status':text(value.get('status') or 'unknown',50),
                'due_date':due,'completed_at':timestamp(value['completed']) if value.get('completed') else None,
                'parent_id':'google_tasks:'+tasklist+':'+value['parent'] if value.get('parent') else None,
                'provider_ids':{'list_id':tasklist,'task_id':ident},'notice':'A date-only due field is not a scheduled work interval. TaskDock remains the task system of record.'})
    return finish(rows,{'account':account,'resources':config['resources'],'notice':'Selected Google task lists, including provider-visible completed/hidden/assigned tasks. No changes are made to the lists. Provider retention and API visibility still apply; do not create a duplicate TaskDock task automatically.'})


def read_chat(http,config,account):
    left,right=dates(config);rows=BoundedRows()
    for space in selected(config,r'spaces/[A-Za-z0-9_-]+'):
        values=paged(http,CHAT,'/v1/'+space+'/messages',{'pageSize':100,'filter':f'createTime >= "{left.astimezone(UTC).isoformat()}" AND createTime < "{right.astimezone(UTC).isoformat()}"','orderBy':'createTime ASC','showDeleted':'false'},field='messages')
        for value in values:
            name=required(value.get('name'))
            if not name.startswith(space+'/messages/') or value.get('deletionMetadata'):continue
            created=timestamp(value.get('createTime'))
            if not left<=datetime.fromisoformat(created)<right:raise ReadError('Google Chat returned a message outside the selected window.')
            body=text(value.get('text') or value.get('formattedText') or '(No readable text; message may contain an omitted card or attachment.)')
            sender=value.get('sender',{})
            if not isinstance(sender,dict):raise ReadError('Google Chat returned invalid sender metadata.')
            rows.append({'id':'google_chat:'+name,'kind':'message','title':body.splitlines()[0][:300],'notes':body,'source':'google_chat',
                'observed_at':created,'sender':text(sender.get('displayName') or sender.get('name') or 'Unknown sender',300),
                'provider_ids':{'space':space,'message':name,'thread':text((value.get('thread') or {}).get('name'),512)},
                'content_truncated':len(str(value.get('text') or value.get('formattedText') or ''))>20000})
    return finish(rows,{'account':account,'resources':config['resources'],'start':config['start'],'end':config['end'],'timezone':config.get('timezone','America/Chicago'),
        'notice':'Selected Google Chat spaces, messages created within the chosen window, including readable thread messages. Edits to older messages and provider retention can fall outside this view. Cards, attachments and membership changes are not imported. Juno sends no messages.'})
