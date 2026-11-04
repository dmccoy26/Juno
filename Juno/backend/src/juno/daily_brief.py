"""Read-only bridge between the saved daily interview and constrained planning."""
from datetime import timedelta
from math import ceil
from zoneinfo import ZoneInfo
from sqlalchemy import select
from .models import CheckIn, TaskDockState, now
from .planning import build_plan, stamp
from .taskdock_api import active_snapshot

ZONE = ZoneInfo('America/Chicago')


def completion_day(value):
    # Undated completion and timestamps without a timezone cannot prove a local day.
    if not isinstance(value, str):
        return None
    try:
        return stamp(value).astimezone(ZONE).date()
    except (ValueError, TypeError):
        return None


def briefing(session, owner, day):
    if not 2000 <= day.year <= 2100:
        from fastapi import HTTPException
        raise HTTPException(422, 'Choose a check-in date between 2000 and 2100.')
    from .schedules import schedule_intervals
    after = day + timedelta(days=1)
    _, effective, _ = schedule_intervals(session, owner, after)
    work_days = sorted({a.astimezone(ZONE).date() for kind, _, a, b in effective
                        if kind == 'work' and a < b and a.astimezone(ZONE).date() >= after})
    target = work_days[0] if work_days else after
    weekly = build_plan(session, owner, target)
    probe = build_plan(session, owner, target, horizon_days=1, reserve_override=0)
    # A disclosed proportional share of the saved weekly interruption reserve,
    # not a new saved preference or a deduction of the entire week from one day.
    reserve = min(probe['free_minutes'], ceil(weekly['reserve_minutes'] * probe['free_minutes'] /
                                             max(1, weekly['free_minutes'])))
    plan = build_plan(session, owner, target, horizon_days=1, reserve_override=reserve)
    snapshot = active_snapshot(session, owner)
    source_state = session.get(TaskDockState, owner)
    stale = not snapshot or bool(source_state and source_state.error) or (now()-snapshot.fetched_at).total_seconds() > 86400
    diary = session.scalar(select(CheckIn).where(CheckIn.owner_id == owner, CheckIn.local_date == day))
    answers = diary.answers if diary else {}
    from .companion import QUESTIONS, LABELS
    interview_text = '\n\n'.join(LABELS[key]+'\n'+(answers[key] or 'Not provided.') for key, _ in QUESTIONS if key in answers)
    # A manually corrected diary supersedes its original interview wording.
    # Do not resurrect an old tomorrow/interruption answer as reviewed evidence.
    answers_current = not diary or diary.diary_text == interview_text
    completed = []
    if snapshot:
        for task in snapshot.items:
            if completion_day(task.get('completed_at')) == day:
                completed.append({'task_id': str(task['id']), 'title': str(task.get('title') or 'Untitled task')})
    blockers = [t for t in plan['tasks'] if t['blocker'] and (not t['next_check'] or t['next_check'] <= str(day))]
    deferred = sum(bool(t['blocker'] and t['next_check'] and t['next_check'] > str(day)) for t in plan['tasks'])
    # After today's check-in, a blocker due before the next workday belongs in
    # tomorrow's preparation, even when it did not need questioning today.
    upcoming = [t for t in plan['tasks'] if t['blocker'] and t['next_check'] and str(day) < t['next_check'] <= str(target)]
    candidates = [] if plan['question'] else [t for t in plan['tasks'] if t['actionable']][:3]
    for task in candidates:
        task['slot_end'] = (stamp(task['slot_start']) + timedelta(minutes=task['estimate_minutes'])).isoformat()
    review = []
    if completed:
        review.append(f'{len(completed)} task(s) have a completion timestamp on this day in the saved TaskDock copy. Confirm what you actually completed.')
    else:
        review.append('No task completion timestamp establishes work completed on this day. This does not mean you did no work.')
    if not answers_current:
        review.append('Your diary was edited after the interview. Use the reviewed diary below; original interview notes are not carried forward automatically.')
    if answers_current and answers.get('interruptions'):
        review.append('Your saved interruption note: ' + answers['interruptions'][:1200])
    if not work_days:
        review.append('No confirmed workday is recorded in the next seven days. The next calendar day is shown with availability unknown.')
    guidance = {
        'completed': [t['title'] for t in completed[:3]] or ['Include work that never became a TaskDock task. Saved completion dates are evidence to review, not an automatic diary.'],
        'interruptions': ['What displaced the plan? A rough time estimate or “unknown” is enough. Unexpected work is part of the day.'],
        'blockers': [t['title'] + ': ' + (t['next_action'] or t['blocker']) for t in blockers[:3]] or ['No recorded blocker is due for review today. Mention a new blocker or a change if there was one.'],
        'employee_work': ['Record what you directly know. Missing updates do not establish inactivity or a change in capability.'],
        'tomorrow': [plan['question']] if plan['question'] else ['What should we carry forward to ' + str(target) + '? Saved alternatives below remain proposals until you review them in Plan.'],
    }
    question = plan['question']
    if not question and not candidates and plan['tasks']:
        question = 'No issue is ready for this workday. Open Plan to review the missing details or next unblocking action.'
    return {
        'day': str(day), 'generated_at': now(), 'workspace_id': snapshot.info.get('workspace_id') if snapshot else None,
        'taskdock_saved_at': snapshot.fetched_at if snapshot else None, 'source_stale': stale,
        'diary_status': diary.status if diary else 'not_started', 'diary_revision': diary.revision if diary else None,
        'review': review, 'completed': completed[:20], 'completed_count': len(completed),
        'blockers': [{'task_id': t['task_id'], 'title': t['title'], 'next_action': t['next_action'], 'blocker': t['blocker']} for t in blockers[:5]],
        'deferred_blocker_count': deferred, 'upcoming_blocker_count': len(upcoming),
        'guidance': guidance, 'next_day': str(target), 'has_scheduled_workday': bool(work_days),
        'capacity_minutes': plan['capacity_minutes'], 'reserve_minutes': reserve,
        'reserve_notice': 'A proportional share of your saved weekly interruption reserve; a preview, not a new saved setting.',
        'question': question, 'recommended_task_id': plan['recommended_task_id'], 'alternatives': candidates,
        'continuity': answers.get('tomorrow', '') if answers_current else '',
        'notices': list(dict.fromkeys(plan['notices'])),
        'notice': 'Saved evidence only. Review the diary and choose one next step; alternatives are not simultaneous allocations, bookings or employee assignments. Diary answers do not change confirmed planning facts.',
    }
