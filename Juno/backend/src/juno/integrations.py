"""Local, bounded evidence readers. Provider content is data, never an action."""
import csv
import hashlib
import io
import json
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
from urllib.parse import urlsplit
from .taskdock import _NoRedirect

MAX_ITEMS=20000
UTC=timezone.utc

class IntegrationError(ValueError):pass


def window(start, end, zone):
    try:
        start=date.fromisoformat(start);end=date.fromisoformat(end);tz=ZoneInfo(zone)
        if not 0<(end-start).days<=366:raise ValueError()
    except (ValueError,TypeError,ZoneInfoNotFoundError):
        raise IntegrationError('Choose a valid timezone and an import window of 1–366 days; the end date is exclusive.') from None
    return datetime.combine(start,time(),tz),datetime.combine(end,time(),tz)


def aware(value,tz):
    if not isinstance(value,datetime):return datetime.combine(value,time(),tz)
    if value.tzinfo is not None:return value
    # Floating times use the explicitly selected timezone. Reject DST ambiguity/gaps.
    candidates=[value.replace(tzinfo=tz,fold=fold) for fold in (0,1)]
    valid=[v for v in candidates if v.astimezone(UTC).astimezone(tz).replace(tzinfo=None)==value]
    if not valid or len({v.utcoffset() for v in valid})!=1:
        raise IntegrationError('A floating event falls in a DST gap or repeated hour. Export it with an explicit timezone/offset.')
    return valid[0]


def bounded_text(value,limit=2000):return str(value or '')[:limit]


def calendar_events(content,start,end,zone):
    from icalendar import Calendar
    import recurring_ical_events
    left,right=window(start,end,zone);tz=left.tzinfo
    if len(content.encode())>2_000_000:raise IntegrationError('The calendar file exceeds 2 MB. Export a smaller calendar.')
    try:
        if not content.lstrip().startswith('BEGIN:VCALENDAR') or not content.rstrip().endswith('END:VCALENDAR'):raise IntegrationError('Import a complete calendar file.')
        cal=Calendar.from_ical(content)
        if cal.name!='VCALENDAR' or str(cal.get('METHOD','')).upper() not in ('','PUBLISH'):
            raise IntegrationError('Import a complete calendar export, not an invitation or update message.')
        components=cal.walk('VEVENT')
        if len(components)>1000:raise IntegrationError('The calendar contains more than 1,000 event definitions. Export a smaller calendar.')
        seen=set()
        for event in components:
            if event.errors or not event.get('UID') or event.get('DTSTART') is None:raise IntegrationError('A calendar event is invalid or lacks its UID/start time.')
            key=(str(event['UID']),str(event.get('RECURRENCE-ID','')))
            if key in seen:raise IntegrationError('The calendar contains duplicate event versions. Export one current calendar.')
            seen.add(key)
            for field in ('DTSTART','DTEND','RECURRENCE-ID'):
                if field in event:
                    prop=event[field];value=prop.dt
                    if prop.params.get('TZID') and isinstance(value,datetime) and value.tzinfo is None:
                        raise IntegrationError('A calendar timezone could not be resolved.')
                    aware(value,tz)
            rules=event.get('RRULE');rules=rules if isinstance(rules,list) else [rules] if rules else []
            for rule in rules:
                if (str(rule.get('FREQ',[''])[0]) not in {'DAILY','WEEKLY','MONTHLY','YEARLY'} or
                    any(k in rule for k in ('BYSECOND','BYMINUTE','BYHOUR')) or int(rule.get('INTERVAL',[1])[0])<1):
                    raise IntegrationError('This calendar has a dense or unsupported recurrence rule. Export explicit events or a simpler calendar.')
            if event.get('EXRULE'):raise IntegrationError('EXRULE calendars are unsupported; export EXDATE exceptions instead.')
            for prop in ('RDATE','EXDATE'):
                values=event.get(prop,[]);values=values if isinstance(values,list) else [values]
                if sum(len(v.dts) for v in values)>1000:raise IntegrationError('Too many recurrence dates in one event.')
        # Expand one UID family at a time so the item cap bounds allocations too.
        groups={}
        for event in components:groups.setdefault(str(event['UID']),[]).append(event)
        occurrences=[]
        for group in groups.values():
            subset=Calendar()
            for key,value in cal.items():subset[key]=value
            subset.subcomponents=[c for c in cal.subcomponents if c.name!='VEVENT']+group
            occurrences.extend(recurring_ical_events.of(subset,keep_recurrence_attributes=True).between(left,right))
            if len(occurrences)>MAX_ITEMS:raise IntegrationError('The expanded calendar exceeds 20,000 events. Use a smaller date window.')
        result=[];identities=set()
        for event in occurrences:
            if str(event.get('STATUS','')).upper()=='CANCELLED':continue
            raw_start=event.decoded('DTSTART');a=aware(raw_start,tz)
            raw_end=event.decoded('DTEND',None)
            if raw_end is not None:b=aware(raw_end,tz)
            else:b=a+event.decoded('DURATION',timedelta(days=1) if not isinstance(raw_start,datetime) else timedelta())
            if b<a:raise IntegrationError('A calendar event ends before it starts.')
            if a>=right or b<=left:continue
            recurrence=str(event.get('RECURRENCE-ID',a.isoformat()))
            identity=hashlib.sha256((str(event['UID'])+'|'+recurrence).encode()).hexdigest()
            if identity in identities:raise IntegrationError('The expanded calendar contains duplicate occurrences.')
            identities.add(identity)
            result.append({'id':identity,'title':bounded_text(event.get('SUMMARY','Untitled event'),300),
                'location':bounded_text(event.get('LOCATION',''),500),'notes':bounded_text(event.get('DESCRIPTION','')),
                'start':a.astimezone(UTC).isoformat(),'end':b.astimezone(UTC).isoformat(),
                'all_day':not isinstance(raw_start,datetime),'busy':str(event.get('TRANSP','OPAQUE')).upper()!='TRANSPARENT',
                'status':str(event.get('STATUS','CONFIRMED')).lower(),'kind':'calendar_event'})
        return sorted(result,key=lambda x:(x['start'],x['id'])),{'start':start,'end':end,'timezone':zone,'notice':'Dated calendar export; not a live Google Calendar connection. End date is exclusive. Calendar availability alone does not establish room access or employee capability.'}
    except IntegrationError:raise
    except Exception:
        raise IntegrationError('The calendar could not be expanded safely. The previous import has been retained.') from None


SCHEDULE_COLUMNS=['kind','name','location','start_date','end_date','days','start_time','end_time','timezone']
DAYS={'MO':0,'TU':1,'WE':2,'TH':3,'FR':4,'SA':5,'SU':6}


def schedule_events(content,start,end,zone):
    left,right=window(start,end,zone)
    if len(content.encode())>2_000_000:raise IntegrationError('The schedule exceeds 2 MB.')
    reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if reader.fieldnames!=SCHEDULE_COLUMNS:raise IntegrationError('Use the supplied schedule CSV template with its exact column order.')
    rows=[];seen=set()
    try:
        for index,row in enumerate(reader):
            if index>=1000:raise IntegrationError('Import at most 1,000 weekly schedule rows.')
            if None in row or any(v is None for v in row.values()):raise ValueError()
            row={k:v.strip() for k,v in row.items()}
            signature=json.dumps(row,sort_keys=True)
            if signature in seen:raise IntegrationError('The schedule contains a duplicate row.')
            seen.add(signature)
            if row['kind'] not in {'classroom_busy','staff_available','meeting'} or not row['name'] or len(row['name'])>300 or len(row['location'])>500:raise ValueError()
            first=date.fromisoformat(row['start_date']);last=date.fromisoformat(row['end_date'])
            if not 0<=(last-first).days<=366:raise ValueError()
            a=time.fromisoformat(row['start_time']);b=time.fromisoformat(row['end_time']);tz=ZoneInfo(row['timezone'])
            if a.tzinfo or b.tzinfo or b<=a:raise ValueError()
            days=row['days'].split('|')
            if not days or len(set(days))!=len(days) or any(day not in DAYS for day in days):raise ValueError()
            day=max(first,left.astimezone(tz).date()-timedelta(days=1))
            stop=min(last,right.astimezone(tz).date())
            while day<=stop:
                if day.weekday() in {DAYS[d] for d in days}:
                    begin=aware(datetime.combine(day,a),tz);finish=aware(datetime.combine(day,b),tz)
                    if begin<right and finish>left:
                        rows.append({'id':hashlib.sha256((signature+'|'+str(day)).encode()).hexdigest(),
                            'kind':row['kind'],'title':row['name'],'location':row['location'],
                            'start':begin.astimezone(UTC).isoformat(),'end':finish.astimezone(UTC).isoformat(),
                            'all_day':False,'busy':row['kind']=='meeting','status':'scheduled'})
                day+=timedelta(days=1)
            if len(rows)>MAX_ITEMS:raise IntegrationError('The expanded schedule exceeds 20,000 intervals.')
    except IntegrationError:raise
    except (ValueError,KeyError,TypeError,ZoneInfoNotFoundError,csv.Error):
        raise IntegrationError('A schedule row is invalid. Use ISO dates, 24-hour same-day times, MO|TU weekdays and an IANA timezone. Semester end dates are inclusive.') from None
    return sorted(rows,key=lambda x:(x['start'],x['id'])),{'start':start,'end':end,'timezone':zone,
        'notice':'Manually supplied semester schedule, not observed attendance. Classroom rows mean occupied; staff rows mean scheduled availability, not skill or independent capability. Missing rows do not prove availability.'}


def busy_summary(items,start,end,zone):
    left,right=window(start,end,zone);result=[];day=left.date()
    while day<right.date():
        begin=datetime.combine(day,time(),left.tzinfo).astimezone(UTC);finish=datetime.combine(day+timedelta(days=1),time(),left.tzinfo).astimezone(UTC)
        intervals=sorted((max(datetime.fromisoformat(r['start']),begin),min(datetime.fromisoformat(r['end']),finish)) for r in items if r.get('busy'))
        total=0;last=None;all_day=False
        for a,b in intervals:
            if b<=a:continue
            if last is None or a>last:total+=(b-a).total_seconds();last=b
            elif b>last:total+=(b-last).total_seconds();last=b
        all_day=any(r.get('busy') and r.get('all_day') and datetime.fromisoformat(r['start'])<finish and datetime.fromisoformat(r['end'])>begin for r in items)
        if total:result.append({'date':str(day),'busy_minutes':round(total/60,2),'all_day_event':all_day})
        day+=timedelta(days=1)
    return result


def beacon_feed(feed):
    if (not isinstance(feed,dict) or type(feed.get('schema_version')) is not int or feed.get('schema_version')!=1 or feed.get('complete') is not True or
        not isinstance(feed.get('rows'),list) or type(feed.get('total')) is not int or feed['total']!=len(feed['rows']) or len(feed['rows'])>MAX_ITEMS):
        raise IntegrationError('Beacon did not return a complete supported alert feed. The previous snapshot has been retained.')
    try:
        stamp=datetime.fromisoformat(feed['generated_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
    except (ValueError,KeyError,TypeError,AttributeError):raise IntegrationError('Beacon omitted a valid generated-at timestamp.') from None
    result=[];seen=set()
    for row in feed['rows']:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] or row['id'] in seen or len(row['id'])>200:
            raise IntegrationError('Beacon returned missing or duplicate alert identities.')
        seen.add(row['id'])
        required=('category','item','problem','action','source','evidence')
        if any(not isinstance(row.get(k),str) or not row[k].strip() for k in required):raise IntegrationError('Beacon omitted required alert evidence. The previous snapshot has been retained.')
        fields=('category','item','location','problem','action','observed_at','source','detail','evidence')
        if any(row.get(k) is not None and not isinstance(row.get(k),str) for k in fields):raise IntegrationError('Beacon returned invalid alert fields.')
        # Exclude arbitrary URLs, cartridges/unknown extension fields and credentials from stored/model evidence.
        cartridges=row.get('cartridges',[])
        if not isinstance(cartridges,list) or len(cartridges)>30:raise IntegrationError('Beacon returned invalid cartridge evidence.')
        safe=[]
        for cartridge in cartridges:
            if not isinstance(cartridge,dict) or any(not isinstance(cartridge.get(k,''),str) for k in ('color','reference')):raise IntegrationError('Beacon returned invalid cartridge evidence.')
            remaining=cartridge.get('remaining')
            if remaining is not None and (type(remaining) not in (int,float) or not 0<=remaining<=100):raise IntegrationError('Beacon returned invalid cartridge percentage.')
            safe.append({'color':bounded_text(cartridge.get('color',''),100),'reference':bounded_text(cartridge.get('reference',''),200),'remaining':remaining})
        result.append({'id':row['id'],**{k:bounded_text(row.get(k,'')) for k in fields},'cartridges':safe})
    return result,{'generated_at':stamp.isoformat(),'complete':True,'notice':bounded_text(feed.get('note',''),1000) or 'Cached observations; not an atomic physical-world snapshot or network probe.'}


class BeaconReader:
    def __init__(self,base_url,token):
        try:
            parts=urlsplit(base_url)
            if not (parts.scheme in {'http','https'} and parts.hostname in {'127.0.0.1','localhost','::1'} and parts.path in {'','/'} and not parts.username and not parts.password and not parts.query and not parts.fragment and (parts.port is None or 1<=parts.port<=65535)):raise ValueError()
        except ValueError:raise IntegrationError('Use Beacon’s loopback API address on this work Mac, without a path or credentials.') from None
        if not token or len(token)>4096 or any(c.isspace() or ord(c)<32 or ord(c)==127 for c in token):raise IntegrationError('Enter a dedicated read-only Beacon integration key.')
        self.origin=base_url.rstrip('/');self.token=token
    def fetch(self):
        try:
            with build_opener(ProxyHandler({}),_NoRedirect).open(Request(self.origin+'/api/alerts',headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'},method='GET'),timeout=10) as response:
                data=response.read(8_000_001)
                if len(data)>8_000_000:raise IntegrationError('Beacon’s response exceeded 8 MB.')
                if self.token in data.decode("utf-8"):raise IntegrationError("Beacon returned credential-bearing content. The previous snapshot has been retained.")
                return beacon_feed(json.loads(data))
        except HTTPError as error:
            code=error.code;error.close()
            raise IntegrationError('Beacon denied the dedicated integration key.' if code in (401,403) else f'Beacon returned HTTP {code}; the previous snapshot has been retained.') from None
        except (URLError,TimeoutError,OSError):raise IntegrationError('Beacon is unavailable. The previous snapshot has been retained.') from None
        except (ValueError,UnicodeError) as error:
            if isinstance(error,IntegrationError):raise
            raise IntegrationError('Beacon returned invalid JSON. The previous snapshot has been retained.') from None
