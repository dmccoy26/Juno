"""Explicit chat absence reports become dated schedule exceptions, never assignments.

Parsing is deliberately bounded. Quoted/reference text and model output never authorize
writes. Unresolved dates/names receive a deterministic clarification, without mutation.
"""
from datetime import date, timedelta
import re
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy import select
from .models import IntegrationSnapshot, now
from .schedules import ZONE, ScheduleInput, availability, persist_schedule, room_key, state_view


def absence_request(text, people, today):
    # Only a direct, single staffing assertion; questions and pasted multi-line material
    # must not be interpreted as commands from reference sources.
    if '\n' in text or '?' in text or text.lstrip().startswith(('"', '“', '>', '`')):
        return None
    match = re.fullmatch(r"(?:please (?:note|record)(?: that)?[,:]?\s+)?([\w '-]{1,100}?) (?:is|will be) (?:out|unavailable|absent)(?:\s+(.+?))?[.!]?", text.strip(), re.I)
    if not match:
        return None
    name, period = match.groups()
    period = period or ''
    people = [p['name'] for p in people if p['name'].casefold() == name.casefold()]
    if len(people) != 1:
        return {'question': f'I could not match “{name}” to one student-worker profile. What is their name as shown in Schedules? No schedule was changed.'}
    period = re.sub(r'\s+for (?:the )?(?:thanksgiving|holiday|break).*$', '', period, flags=re.I).strip().lower()
    next_monday = today + timedelta(days=7-today.weekday())
    if period == 'today': start = end = today
    elif period == 'tomorrow': start = end = today + timedelta(days=1)
    elif period == 'next week': start, end = next_monday, next_monday+timedelta(days=6)
    elif period in ('today through next week', 'today until the end of next week', 'today through the end of next week'):
        start, end = today, next_monday+timedelta(days=6)
    else:
        dates = re.fullmatch(r'(\d{4}-\d{2}-\d{2})(?: (?:through|to) (\d{4}-\d{2}-\d{2}))?', period)
        try:
            if not dates: raise ValueError()
            start = date.fromisoformat(dates[1]); end = date.fromisoformat(dates[2] or dates[1])
        except ValueError:
            return {'question': 'What are the first and last full days of the absence? For example: “'+people[0]+' is out 2026-11-23 through 2026-11-27.” No schedule was changed.'}
    if not 0 <= (end-start).days <= 365 or start < today:
        return {'question': 'Please give an absence starting today or later, with an end within one year. No schedule was changed.'}
    return {'name': people[0], 'start': start, 'end': end, 'suggestion_day': next_monday if 'next week' in period else start}


def apply_absence(session, owner, request, text, history):
    if 'question' in request: return request['question']
    name, start, end = (request[k] for k in ('name', 'start', 'end'))
    state = state_view(session, owner)
    exceptions = list(state['exceptions'])
    changed = False
    for offset in range((end-start).days+1):
        day = str(start+timedelta(days=offset))
        existing = next((e for e in exceptions if e['kind']=='staff_available' and e['name'].casefold()==name.casefold() and e['day']==day), None)
        if existing and existing['closed']: continue
        if existing: exceptions.remove(existing)
        exceptions.append({'id': str(uuid5(NAMESPACE_URL, f'juno:chat-absence:{owner}:{name}:{day}')),
                           'kind':'staff_available', 'name':name, 'day':day, 'closed':True,
                           'note':'Owner reported full-day absence in Juno chat: '+text[:800]})
        changed = True
    if changed:
        state = persist_schedule(session, owner, ScheduleInput.model_validate({
            'expected_revision':state['revision'], 'rules':state['rules'], 'people':state['people'], 'exceptions':exceptions}))
    lines = [f'Saved {name} as unavailable {start:%B %d, %Y} through {end:%B %d, %Y}, inclusive (Central).',
             'Those full days are excluded from suggested times. Regular shifts resume afterward.']
    affected = [r for r in state['reservations'] if r['employee'].casefold()==name.casefold() and
                str(r['start'])[:10] <= str(end) and str(r['end'])[:10] >= str(start)]
    if affected: lines.append(f'{len(affected)} existing hold(s) need review; I have not cancelled or reassigned them.')
    # Resolve room scope only from direct user chat and known schedule rooms.
    user_text = ' '.join([m.text for m in history if m.role=='user'][-8:]+[text])
    compact = re.sub(r'[^A-Z0-9]', '', user_text.upper())
    rooms = []
    for rule in state['rules']:
        if rule['kind']!='room': continue
        room = room_key(rule['name'])
        aliases = [room, 'LIB115', 'LIBRARY115'] if room=='LIBR 115' else [room]
        if any(re.sub(r'[^A-Z0-9]', '', a) in compact for a in aliases) and room not in rooms:
            rooms.append(room)
    if not rooms:
        return '\n\n'.join(lines+['Which classrooms should I find replacement times for? No work was reserved or assigned.'])
    day = request['suggestion_day']
    calendar = session.get(IntegrationSnapshot, (owner,'google_calendar'))
    if not calendar or calendar.details.get('active') is False or calendar.error or (now()-calendar.fetched_at).total_seconds()>86400 or not (
        calendar.details.get('start','9999') <= str(day) and calendar.details.get('end','0000') >= str(day+timedelta(days=7))):
        return '\n\n'.join(lines+['I need a current work Google Calendar covering the next seven days before offering replacement times. Refresh it in Sources, then ask for times again. The absence is saved; no work was reserved or assigned.'])
    lines.append('Possible 30-minute assessment windows for the seven days starting '+str(day)+
                 ' (Central; alternatives, not a coordinated work plan):')
    for room in rooms[:4]:
        choices = []
        for person in [p['name'] for p in state['people'] if p['status']=='active' and p['name'].casefold()!=name.casefold()]+['']:
            view = availability(session,owner,day,room,person,30,True)
            if not view['calendar_ready']: continue
            for window in view['windows'][:1]:
                from .planning import stamp
                a = stamp(window['start']).astimezone(ZONE)
                b = a+timedelta(minutes=30)
                choices.append(f'{a:%a %b %d, %I:%M %p}–{b:%I:%M %p}: '+('you with '+person if person else 'you alone'))
        lines.append('• '+room+': '+('; '.join(choices[:3]) if choices else 'no confirmed overlap found.'))
    lines.append('Checked room access/classes, your saved work Google Calendar, confirmed worker shifts and Juno holds. Google Calendar last refreshed '+calendar.fetched_at.astimezone(ZONE).strftime('%b %d at %I:%M %p Central')+'.')
    lines.append('Confirm qualifications, task scope and holiday attendance before choosing. Thirty minutes is a proposed assessment block, not a completion estimate. Options may overlap. No work was reserved or assigned.')
    return '\n\n'.join(lines)
