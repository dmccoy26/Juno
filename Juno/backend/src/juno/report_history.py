"""Immutable owner-scoped report revisions; the current draft remains editable."""
from copy import deepcopy
from datetime import date, timezone
from hashlib import sha256
import json
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from .models import ReportVersion, ReportReview, DeanDraft, ChairsDraft, now
from .planning import Strict


class ReviewInput(Strict):
    expected_revision: int = Field(ge=1)
    audience: Literal['dean','lwr','visu','performing']


def report_row(session, owner, kind, week):
    if kind not in {'dean','chairs'}: raise HTTPException(404, 'Report type not found.')
    model = DeanDraft if kind == 'dean' else ChairsDraft
    return session.scalar(select(model).where(model.owner_id == owner, model.week_start == week))


def contents(row, kind):
    if row is None: return {}
    if kind == 'dean': return {'dean': row.text}
    return {audience: [email['subject'], email['body']] for audience, email in row.emails.items()}


def fingerprint(value):
    return sha256(json.dumps(value, ensure_ascii=False, separators=(',',':')).encode()).hexdigest()


def review_state(session, owner, kind, week):
    row = report_row(session, owner, kind, week)
    result = []
    for audience, content in contents(row, kind).items():
        review = session.get(ReportReview, (owner, kind, week, audience))
        valid = review is not None and review.fingerprint == fingerprint(content)
        result.append({'audience': audience, 'reviewed': valid,
                       'reviewed_at': review.reviewed_at.astimezone(timezone.utc) if valid else None})
    return {'items': result}


def retain(session, row, kind, action):
    session.flush()
    key = (row.owner_id, kind, row.week_start, row.revision)
    if session.get(ReportVersion, key) is not None:
        return
    fields = ('text','basis') if kind == 'dean' else ('subject','body','emails','coverage')
    content = deepcopy({field: getattr(row, field) for field in fields})
    session.add(ReportVersion(owner_id=row.owner_id, kind=kind, week_start=row.week_start,
                              revision=row.revision, content=content, action=action))

def library(session, owner, offset=0):
    weeks = select(DeanDraft.week_start).where(DeanDraft.owner_id == owner).union(
        select(ChairsDraft.week_start).where(ChairsDraft.owner_id == owner)).subquery()
    dates = session.scalars(select(weeks.c.week_start).order_by(weeks.c.week_start.desc()).offset(offset).limit(21)).all()
    items = []
    for week in dates[:20]:
        for kind in ('dean', 'chairs'):
            row = report_row(session, owner, kind, week)
            if row is None: continue
            reviews = {r['audience']:r['reviewed'] for r in review_state(session,owner,kind,week)['items']}
            if kind == 'dean':
                items.append({'id':f'dean:{week}:dean','week':str(week),'kind':kind,'audience':'dean',
                    'title':'Dean talking points','revision':row.revision,'reviewed':reviews.get('dean',False)})
            else:
                for audience in ('lwr','visu','performing'):
                    email = row.emails.get(audience)
                    if email:
                        items.append({'id':f'chairs:{week}:{audience}','week':str(week),'kind':kind,'audience':audience,
                            'title':email['subject'],'revision':row.revision,'reviewed':reviews.get(audience,False)})
                if not row.emails:
                    items.append({'id':f'chairs:{week}:all','week':str(week),'kind':kind,'audience':'all',
                        'title':row.subject,'revision':row.revision,'reviewed':False})
    return {'owner_id':owner,'items':items,'has_more':len(dates)>20,'next_offset':offset+20}


def install(app, db, device, lock_owner):
    @app.get('/v1/reports/index')
    def documents(offset: int = Query(default=0,ge=0),actor=Depends(device),session=Depends(db)):
        return library(session,actor.owner_id,offset)

    @app.get('/v1/reports/{kind}/{week}/review')
    def reviewed(kind: str, week: date, actor=Depends(device), session=Depends(db)):
        return review_state(session, actor.owner_id, kind, week)

    @app.post('/v1/reports/{kind}/{week}/review')
    def review(kind: str, week: date, value: ReviewInput, actor=Depends(device), session=Depends(db)):
        lock_owner(session, actor.owner_id)
        row = report_row(session, actor.owner_id, kind, week)
        current = contents(row, kind)
        if row is None or value.audience not in current: raise HTTPException(404, 'Saved report not found.')
        if row.revision != value.expected_revision: raise HTTPException(409, 'The saved report changed. Reopen it before marking it reviewed.')
        key = (actor.owner_id, kind, week, value.audience)
        record = session.get(ReportReview, key)
        if record is None:
            record = ReportReview(owner_id=actor.owner_id, kind=kind, week_start=week, audience=value.audience)
            session.add(record)
        record.fingerprint = fingerprint(current[value.audience]); record.reviewed_at = now()
        session.commit()
        return review_state(session, actor.owner_id, kind, week)

    @app.get('/v1/reports/{kind}/{week}/history')
    def read(kind: str, week: date, offset: int = Query(default=0, ge=0), actor=Depends(device), session=Depends(db)):
        if kind not in {'dean','chairs'}: raise HTTPException(404, 'Report type not found.')
        lock_owner(session, actor.owner_id)
        rows = session.scalars(select(ReportVersion).where(ReportVersion.owner_id == actor.owner_id,
            ReportVersion.kind == kind, ReportVersion.week_start == week).order_by(ReportVersion.revision.desc()).offset(offset).limit(21)).all()
        result = {'items': [{'revision': r.revision, 'content': r.content, 'action': r.action,
                             'saved_at': r.saved_at.astimezone(timezone.utc)} for r in rows[:20]],
                  'has_more': len(rows) > 20}
        return result
