"""Report recorded closures from an explicitly selected Smartsheet archive."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .models import IntegrationSnapshot, now

CENTRAL = ZoneInfo('America/Chicago')


def snapshot(session, owner):
    return session.scalar(select(IntegrationSnapshot).where(
        IntegrationSnapshot.owner_id == owner, IntegrationSnapshot.kind == 'smartsheet'))


def archive_source(session, owner):
    row = snapshot(session, owner)
    if row and row.details.get('completion_archive'):
        return row
    return None


def archive_basis(session, owner):
    row = archive_source(session, owner)
    if row:
        return {'snapshot_id': row.id, 'available': row.details.get('active') is not False,
                'uncertain': bool(row.error) or now() - row.fetched_at > timedelta(days=1)}
    return None


def report_lines(session, owner, start, end, *, limit=24, include_notes=True, include_item=lambda item: True):
    row = archive_source(session, owner)
    if row is None:
        return []
    lines = ['', 'Smartsheet: completed-task archive']
    if row.details.get('active') is False:
        return [*lines, 'Archive access needs review in Connections.']
    archive = row.details['completion_archive']
    if not archive.get('completion_date_column'):
        return [*lines, 'Choose the archive’s completion-date column in Connections to include dated closures.']

    meeting_window = isinstance(start, datetime)
    start_day, end_day = (start.date(), end.date()) if meeting_window else (start, end)
    matches = []
    undated = 0
    for item in row.items:
        if (item.get('provider_ids') or {}).get('sheet_id') != archive['sheet_id'] or not include_item(item):
            continue
        value = item.get('archive_completed_on')
        if not value:
            undated += 1
            continue
        if len(value) == 10:
            local_day = date.fromisoformat(value)
            included = (start_day < local_day <= end_day if meeting_window else start_day <= local_day <= end_day)
        else:
            stamp = datetime.fromisoformat(value).astimezone(CENTRAL)
            local_day = stamp.date()
            included = start < stamp <= end if meeting_window else start_day <= local_day <= end_day
        if included:
            matches.append((local_day, item))

    matches.sort(key=lambda pair: (pair[0], pair[1]['id']), reverse=True)
    for day, item in matches[:limit]:
        title = ' '.join(item['title'].split())[:160]
        notes = ' '.join((item.get('archive_notes') or '').split())[:150] if include_notes else ''
        lines.append(f'• {title} — recorded closed {day:%b %d}.' + (f' Archive note: {notes}' if notes else ''))
    if not matches:
        lines.append('No dated closures in this reporting window in the saved archive.')
    if limit is not None and len(matches) > limit:
        lines.append(f'{len(matches)-limit} more dated archive rows in this reporting window.')
    if undated:
        label = 'archive row has' if undated == 1 else 'archive rows have'
        lines.append(f'{undated} {label} no usable completion date. Dated reporting excludes these rows.')
    lines.append('Archive rows can overlap TaskDock. A recorded closure does not verify a repair.')
    if meeting_window:
        lines.append('For dates without times, coverage starts the day after the previous meeting.')
    if row.error or now() - row.fetched_at > timedelta(days=1):
        lines.append(f'Using the saved archive from {row.fetched_at.astimezone(CENTRAL):%b %d at %-I:%M %p} Central. The copy may be out of date.')
    return lines
