"""Reviewed carry-forward and saved weekly drafts with real isolated PostgreSQL."""
import uuid
from sqlalchemy import select,func
from fastapi.testclient import TestClient
import test_daily_brief as daily_tests
from juno.api import create_app
from juno.models import CheckIn,PlanningCarry,DeanDraft,PlanningState,TaskDockSnapshot


class ContinuityTests(daily_tests.DailyBriefTests):
    def diary(self):
        row=self.client.post('/v1/check-ins',json={'local_date':'2030-01-06'}).json()
        for question in row['questions']:
            answer = ('- Restored a fictional printer.\n- Updated a fictional lab checklist.'
                      if question['key'] == 'completed' else 'Fictional '+question['key'])
            row=self.client.put('/v1/check-ins/'+row['id']+'/answer',json={'key':question['key'],'text':answer,'expected_revision':row['revision']}).json()
        return self.client.put('/v1/check-ins/'+row['id']+'/diary',json={'text':row['diary_text'],'expected_revision':row['revision'],'confirm':True}).json()

    def intent(self):
        self.diary();source=self.client.get('/v1/planning/carry-forward?day=2030-01-06').json()
        return {key:source[key] for key in ('diary_id','diary_revision','planning_revision','workspace_id','snapshot_id')}|{'task_id':'dean','source_quote':'Fictional tomorrow','changes':{'resume':'Resume the fictional test'}}

    def test_carry_preview_is_read_only_and_save_changes_only_selected_fields_once(self):
        self.save(tasks=[{'task_id':'dean','minutes':45,'employee':'Fictional Alex','capability':'Reviewed training','independent':True,'blocker':'Existing parts blocker','resume':'Old note'}])
        intent=self.intent();before=self.client.get('/v1/planning').json()
        r=self.client.post('/v1/planning/carry-forward/preview',json=intent);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['rows'][0]['before'],'Old note');self.assertEqual(self.client.get('/v1/planning').json(),before)
        body=intent|{'operation_id':str(uuid.uuid4())};r=self.client.post('/v1/planning/carry-forward/save',json=body);self.assertEqual(r.status_code,200,r.text)
        after=self.client.get('/v1/planning').json();task=after['tasks'][0]
        self.assertEqual(task['resume'],'Resume the fictional test');self.assertEqual(task['blocker'],'Existing parts blocker');self.assertEqual(task['minutes'],45);self.assertEqual(task['employee'],'Fictional Alex')
        retry=self.client.post('/v1/planning/carry-forward/save',json=body);self.assertEqual(retry.status_code,200);self.assertEqual(retry.json()['planning_revision'],after['revision'])
        self.assertEqual(self.client.post('/v1/planning/carry-forward/save',json=body|{'changes':{'resume':'Different'}}).status_code,409)
        self.assertEqual(self.client.post('/v1/planning/carry-forward/save',json=body|{'changes':{**body['changes'],'blocker':''}}).status_code,409)
        with self.factory() as session:self.assertEqual(session.scalar(select(func.count()).select_from(PlanningCarry).where(PlanningCarry.owner_id==self.actor.owner_id)),1)
        history=self.client.get('/v1/planning/carry-forward/history?workspace_id=fictional&task_id=dean').json()['items'];self.assertEqual(history[0]['source_quote'],'Fictional tomorrow')

    def test_carry_rejects_stale_source_plan_workspace_and_invented_quote(self):
        intent=self.intent();path='/v1/planning/carry-forward/preview'
        for change in ({'diary_revision':99},{'planning_revision':99},{'workspace_id':'other'},{'snapshot_id':str(uuid.uuid4())},{'source_quote':'Not in the diary'},{'task_id':'done'}):
            self.assertEqual(self.client.post(path,json=intent|change).status_code,409)
        self.assertEqual(self.client.post(path,json=intent|{'changes':{'independent':True}}).status_code,422)
        self.assertEqual(self.client.post(path,json=intent|{'changes':{'minutes':4}}).status_code,422)
        with TestClient(create_app(self.engine)) as client:
            client.headers['Authorization']='Bearer '+self.other_token
            self.assertEqual(client.post(path,json=intent).status_code,404)
        self.assertEqual(self.client.get('/v1/planning').json()['revision'],0)

    def test_carry_clear_is_explicit_and_unknown_fields_do_not_clear_other_values(self):
        self.save(tasks=[{'task_id':'dean','minutes':45,'blocker':'Old dependency','resume':'Keep this'}]);intent=self.intent()
        r=self.client.post('/v1/planning/carry-forward/save',json=intent|{'changes':{'blocker':''},'operation_id':str(uuid.uuid4())});self.assertEqual(r.status_code,200,r.text)
        task=self.client.get('/v1/planning').json()['tasks'][0];self.assertEqual(task['blocker'],'');self.assertEqual(task['resume'],'Keep this');self.assertEqual(task['minutes'],45)

    def test_unconfirmed_or_corrected_diary_requires_a_new_review(self):
        row=self.client.post('/v1/check-ins',json={'local_date':'2030-01-06'}).json();self.assertEqual(self.client.get('/v1/planning/carry-forward?day=2030-01-06').status_code,409)
        intent=self.intent()
        with self.factory() as session:
            row=session.get(CheckIn,intent['diary_id']);row.diary_text='Corrected source';row.revision+=1;session.commit()
        self.assertEqual(self.client.post('/v1/planning/carry-forward/save',json=intent|{'operation_id':str(uuid.uuid4())}).status_code,409)

    def weekly(self):
        self.diary();return self.client.get('/v1/planning/weekly?day=2030-01-06').json()

    def assert_check_in_bullets(self, draft):
        lines = draft['text'].splitlines()
        self.assertIn('• Accomplishments — Restored a fictional printer.', lines)
        self.assertIn('• Accomplishments — Updated a fictional lab checklist.', lines)
        self.assertIn('• Tomorrow — Fictional tomorrow', lines)

    def test_weekly_save_reopens_across_restart_device_and_keeps_source_changes_separate(self):
        draft=self.weekly();body={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':draft['text']+'\nReviewed wording','basis':draft['basis']};path='/v1/planning/weekly-draft/2030-01-06'
        self.assert_check_in_bullets(draft)
        r=self.client.put(path,json=body);self.assertEqual(r.status_code,200,r.text);receipt=r.json()
        with TestClient(create_app(self.engine)) as client:
            client.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(client.get(path).json()['text'],body['text']);self.assertEqual(client.put(path,json=body).json(),receipt)
            client.headers['Authorization']='Bearer '+self.other_token;self.assertFalse(client.get(path).json()['exists'])
        with self.factory() as session:
            diary=session.scalar(select(CheckIn).where(CheckIn.owner_id==self.actor.owner_id));diary.diary_text='Corrected later';diary.revision+=1;session.commit()
        saved=self.client.get(path).json();self.assertTrue(saved['sources_changed']);self.assertEqual(saved['text'],body['text'])
        r=self.client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':1,'text':'Reviewed second revision','basis':saved['basis']});self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get(path).json()['revision'],2)

    def test_weekly_conflict_and_new_generation_do_not_overwrite_saved_writing(self):
        draft=self.weekly();path='/v1/planning/weekly-draft/2030-01-06';body={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'My reviewed draft','basis':draft['basis']}
        self.assertEqual(self.client.put(path,json=body).status_code,200)
        self.assertEqual(self.client.put(path,json=body|{'operation_id':str(uuid.uuid4()),'text':'Competing stale edit'}).status_code,409)
        self.client.get('/v1/planning/weekly?day=2030-01-06');self.assertEqual(self.client.get(path).json()['text'],'My reviewed draft')
        self.assertEqual(len(draft['missing_diary_dates']),6)

    def test_weekly_creation_rejects_changed_or_forged_evidence(self):
        draft=self.weekly();path='/v1/planning/weekly-draft/2030-01-06'
        body={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'Draft','basis':{}}
        self.assertEqual(self.client.put(path,json=body).status_code,409)
        self.assertFalse(self.client.get(path).json()['exists'])

    def test_atomic_carry_rollback_if_provenance_cannot_be_saved(self):
        from sqlalchemy import event
        self.save(tasks=[{'task_id':'dean','resume':'Before'}]);intent=self.intent();before=self.client.get('/v1/planning').json()
        def fail(mapper,connection,target):
            if target.owner_id==self.actor.owner_id:raise RuntimeError('Fictional audit-storage failure')
        event.listen(PlanningCarry,'before_insert',fail)
        try:
            with TestClient(self.app,raise_server_exceptions=False) as client:
                client.headers['Authorization']='Bearer '+self.token
                response=client.post('/v1/planning/carry-forward/save',json=intent|{'operation_id':str(uuid.uuid4())})
                self.assertEqual(response.status_code,500)
        finally:event.remove(PlanningCarry,'before_insert',fail)
        self.assertEqual(self.client.get('/v1/planning').json(),before)

    def test_paired_routes_and_saved_weekly_cache_stay_owner_scoped(self):
        from juno.shared_host import LANBoundary
        draft=self.weekly();path='/v1/planning/weekly-draft/2030-01-06';body={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'Reviewed paired draft','basis':draft['basis']}
        with TestClient(LANBoundary(self.app),client=('10.1.2.3',50000)) as client:
            self.assertEqual(client.get(path).status_code,401)
            client.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(client.put(path,json=body).status_code,200)
            self.assertEqual(client.get('/v1/planning/carry-forward?day=2030-01-06').status_code,200)
            self.assertEqual(client.delete(path).status_code,403)
        pages=self.client.get('/v1/cache').json()['pages'];saved=next(p for p in pages if p['path']==path)
        self.assertEqual(saved['body']['text'],'Reviewed paired draft')
        with TestClient(self.app) as client:
            client.headers['Authorization']='Bearer '+self.other_token
            self.assertFalse(any(p['path']==path for p in client.get('/v1/cache').json()['pages']))

    def test_competing_weekly_edits_compare_revisions(self):
        from concurrent.futures import ThreadPoolExecutor
        draft=self.weekly();path='/v1/planning/weekly-draft/2030-01-06'
        initial={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'Original reviewed draft','basis':draft['basis']};self.assertEqual(self.client.put(path,json=initial).status_code,200)
        def edit(text):
            with TestClient(create_app(self.engine)) as client:
                client.headers['Authorization']='Bearer '+self.second_token
                return client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':1,'text':text,'basis':draft['basis']}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(edit,['First competing edit','Second competing edit']))
        self.assertEqual(sorted(statuses),[200,409]);self.assertEqual(self.client.get(path).json()['revision'],2)

    def test_additive_upgrade_preserves_prior_diary_and_planning(self):
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        from sqlalchemy import create_engine,text
        from juno.auth import provision
        from juno.database import sessions
        name='juno_upgrade_'+uuid.uuid4().hex
        with self.admin.connect() as connection:connection.execute(text(f'CREATE DATABASE "{name}"'))
        engine=create_engine(self.admin.url.set(database=name),hide_parameters=True)
        config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
        try:
            with engine.connect() as connection:
                config.attributes['connection']=connection;command.upgrade(config,'0011_worker_assignments')
            with sessions(engine)() as session:
                actor,_=provision(session,'Fictional legacy owner');session.add(CheckIn(owner_id=actor.owner_id,local_date=__import__('datetime').date(2030,1,6),answers={},diary_text='Legacy diary must survive',status='confirmed',revision=4));session.add(PlanningState(owner_id=actor.owner_id,data={'tasks':[{'task_id':'legacy','resume':'Legacy planning note'}]},revision=3));session.commit();owner=actor.owner_id
            with engine.connect() as connection:
                config.attributes['connection']=connection;command.upgrade(config,'head')
            with sessions(engine)() as session:
                diary=session.scalar(select(CheckIn).where(CheckIn.owner_id==owner));self.assertEqual(diary.diary_text,'Legacy diary must survive');self.assertEqual(diary.revision,4)
                self.assertEqual(session.get(PlanningState,owner).data['tasks'][0]['resume'],'Legacy planning note')
                self.assertEqual(session.scalar(select(func.count()).select_from(DeanDraft)),0)
        finally:
            engine.dispose()
            with self.admin.connect() as connection:connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))

    def test_older_saved_preparation_metadata_remains_editable_with_unknown_quality(self):
        draft=self.weekly();path='/v1/planning/weekly-draft/2030-01-06'
        self.assertEqual(self.client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'Earlier reviewed writing','basis':draft['basis']}).status_code,200)
        with self.factory() as session:
            row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==self.actor.owner_id));row.basis={k:v for k,v in row.basis.items() if k!='taskdock_uncertain'};session.commit()
        saved=self.client.get(path).json();self.assertTrue(saved['basis']['taskdock_uncertain'])
        response=self.client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':1,'text':'Later reviewed writing','basis':saved['basis']})
        self.assertEqual(response.status_code,200,response.text)


    def test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing(self):
        from datetime import datetime
        from unittest.mock import patch
        from juno.models import IntegrationSnapshot,TaskDockHistory
        stamp=datetime.fromisoformat('2030-01-10T15:00:00+00:00')
        self.diary()
        follow_up = self.client.put('/v1/planning/dean-follow-up/2030-01-03', json={
            'expected_revision': 0, 'notes': 'Confirm fictional council attendance.',
            'items': [{'id': str(uuid.uuid4()), 'title': 'Confirm fictional council attendance',
                       'quote': 'Confirm fictional council attendance.'}],
        })
        self.assertEqual(follow_up.status_code, 200, follow_up.text)
        self.snapshot(lambda items:items+[
            {'id':'in','title':'In-window completion','completed_at':'2030-01-03T16:00:01Z'},
            {'id':'out','title':'Before or at last meeting','completed_at':'2030-01-03T16:00:00Z'},
            {'id':'future','title':'Future completion','completed_at':'2030-01-10T15:00:01Z'},
            {'id':'progress','title':'In-window progress','behavior':'open','blocked_reason':'Awaiting fictional part',
             'source_updates':{'items':[{'created_at':'2030-01-09T18:00:00Z','body':'Tested fictional cable'}]}}])
        with self.factory() as session:
            snapshot=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            snapshot.fetched_at=stamp
            beacon=IntegrationSnapshot(owner_id=self.actor.owner_id,kind='beacon',origin='http://localhost:12108',
                fetched_at=stamp,details={'generated_at':stamp.isoformat()},items=[
                    {'id':'observation','item':'Example printer','problem':'Alignment warning','observed_at':'2030-01-09T18:00:00Z'}])
            session.add(beacon)
            session.add(IntegrationSnapshot(owner_id=self.actor.owner_id, kind='smartsheet', origin='Synthetic archive',
                fetched_at=stamp, details={'completion_archive': {'sheet_id': '1001', 'completion_date_column': 'Closed Date'}},
                items=[
                    {'id': 'smartsheet:1001:1', 'title': 'Archived fictional closure',
                     'archive_completed_on': '2030-01-09', 'archive_notes': 'Cable replaced.',
                     'provider_ids': {'sheet_id': '1001'}},
                    {'id': 'smartsheet:1001:2', 'title': 'Undated fictional archive row',
                     'provider_ids': {'sheet_id': '1001'}},
                    {'id': 'smartsheet:1001:3', 'title': 'Archive row from before the meeting',
                     'archive_completed_on': '2030-01-03T15:59:00+00:00', 'provider_ids': {'sheet_id': '1001'}},
                    {'id': 'smartsheet:1001:4', 'title': 'Archive row after the cutoff',
                     'archive_completed_on': '2030-01-10T15:00:01+00:00', 'provider_ids': {'sheet_id': '1001'}},
                ]))
            session.add(TaskDockHistory(owner_id=self.actor.owner_id,snapshot_id=snapshot.id,kind='updates',
                task_id='dean',items=[{'body':'Confirmed the fictional request','created_at':'2030-01-09T20:00:00Z'}],read_at=stamp))
            session.flush()
            intent={'previous':'2030-01-03T16:00:00Z','meeting':'2030-01-10T16:00:00Z','previous_confirmed':True,
                    'taskdock_id':snapshot.id,'beacon_id':beacon.id}
            session.commit()
        endpoint='/v1/planning/dean-meeting/prepare'
        with patch('juno.planning_continuity.now',return_value=stamp),patch('juno.operations.now',return_value=stamp):
            self.assertEqual(self.client.post(endpoint,json=intent|{'beacon_id':'stale'}).status_code,409)
            with TestClient(self.app) as other:
                other.headers['Authorization']='Bearer '+self.other_token
                self.assertEqual(other.post(endpoint,json=intent).status_code,409)
            reply=self.client.post(endpoint,json=intent);self.assertEqual(reply.status_code,200,reply.text)
            self.assertTrue(reply.json()['created'])
            path='/v1/planning/weekly-draft/2030-01-07'
            draft=self.client.get(path).json()
            evidence={**draft,'text':draft['basis']['dean_review_notes']}
            self.assertEqual(draft['basis']['dean_format'],'leadership-v1')
            self.assertFalse(draft['sources_changed'])
            self.assertNotIn('Alignment warning',draft['text'])
            self.assert_check_in_bullets(evidence)
            self.assertIn('• Confirm fictional council attendance', evidence['text'])
            self.assertIn('• Archived fictional closure — recorded closed Jan 09. Archive note: Cable replaced.',evidence['text'])
            self.assertIn('1 archive row has no usable completion date',evidence['text'])
            for excluded in ('Undated fictional archive row', 'Archive row from before the meeting', 'Archive row after the cutoff'):
                self.assertNotIn(excluded, evidence['text'])
            self.assertTrue(draft['basis']['completion_archive']['available'])
            for piece in ('Fictional tomorrow','In-window completion','Tested fictional cable','Awaiting fictional part','Alignment warning','last meeting as confirmed','Confirmed the fictional request'):
                self.assertIn(piece,evidence['text'])
            self.assertNotIn('Before or at last meeting',evidence['text'])
            self.assertNotIn('Future completion',evidence['text'])
            self.assertTrue(draft['basis']['meeting_window']['previous_confirmed'])
            old_client_basis = {key: value for key, value in draft['basis'].items() if key not in {'completion_archive','dean_format','dean_review_notes'}}
            body={'operation_id':str(uuid.uuid4()),'expected_revision':1,'text':'Reviewed draft','basis':old_client_basis}
            self.assertEqual(self.client.put(path,json=body).status_code,200)
            self.assertFalse(self.client.post(endpoint,json=intent).json()['created'])
            self.assertEqual(self.client.get(path).json()['text'],'Reviewed draft')
            self.assertEqual(self.client.get(path).json()['basis']['completion_archive'], draft['basis']['completion_archive'])

    def test_saved_additions_can_be_prepared_late_without_losing_notes_or_reviewed_drafts(self):
        from datetime import datetime
        from unittest.mock import patch
        from juno.models import IntegrationSnapshot, ReportVersion
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        stamp=datetime.fromisoformat('2030-01-10T17:00:00+00:00')
        with self.factory() as session:
            row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==self.actor.owner_id))
            row.text='Fictional reviewed budget addition';row.basis={};row.revision+=1
            revision=row.revision
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            td.fetched_at=stamp
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));beacon.fetched_at=stamp
            intent={'previous':'2030-01-03T16:00:00Z','meeting':'2030-01-10T16:00:00Z',
                    'taskdock_id':td.id,'beacon_id':beacon.id,'preserve_saved_revision':revision}
            session.commit()
        path='/v1/planning/weekly-draft/2030-01-07';endpoint='/v1/planning/dean-meeting/prepare'
        with patch('juno.planning_continuity.now',return_value=stamp),patch('juno.operations.now',return_value=stamp):
            self.assertEqual(self.client.post(endpoint,json=intent).status_code,422)
            self.assertEqual(self.client.post(endpoint,json=intent|{'allow_late':True,'previous':'2029-12-27T16:00:00Z','meeting':'2030-01-03T16:00:00Z'}).status_code,422)
            self.assertEqual(self.client.post(endpoint,json=intent|{'allow_late':True,'preserve_saved_revision':revision-1}).status_code,409)
            reply=self.client.post(endpoint,json=intent|{'allow_late':True})
            self.assertEqual(reply.status_code,200,reply.text);self.assertTrue(reply.json()['created'])
            draft=self.client.get(path).json()
            self.assertIn('In-window completion',draft['basis']['dean_review_notes'])
            self.assertTrue(draft['text'].endswith('Fictional reviewed budget addition'))
            self.assertEqual(draft['revision'],revision+1)
            self.assertEqual(datetime.fromisoformat(draft['basis']['meeting_window']['prepared']),stamp)
            self.assertFalse(self.client.post(endpoint,json=intent|{'allow_late':True,'preserve_saved_revision':draft['revision']}).json()['created'])
            self.assertEqual(self.client.get(path).json()['text'],draft['text'])
        with self.factory() as session:
            old=session.scalar(select(ReportVersion).where(ReportVersion.owner_id==self.actor.owner_id,ReportVersion.kind=='dean',ReportVersion.revision==revision))
            self.assertEqual(old.content['text'],'Fictional reviewed budget addition')


    def test_undated_archive_completed_updates_are_not_reported_as_dated_closures(self):
        from datetime import datetime
        from juno.models import IntegrationSnapshot
        from juno.completion_archive import undated_update_lines
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        start=datetime.fromisoformat('2030-01-03T16:00:00+00:00')
        end=datetime.fromisoformat('2030-01-10T15:00:00+00:00')
        def item(title, modified, status='Completed', **extra):
            return dict(id=title,title=title,provider_ids={'sheet_id':'1001'},
                        notes=f'Status: {status}\nModified: {modified}',**extra)
        with self.factory() as session:
            archive=session.get(IntegrationSnapshot,(self.actor.owner_id,'smartsheet'))
            archive.items=[item('Fictional delivered part','2030-01-09T18:00:00Z'),
                           item('Old update','2030-01-02T18:00:00Z'),
                           item('Future update','2030-01-11T18:00:00Z'),
                           item('Still open','2030-01-09T18:00:00Z','Open'),
                           item('Unknown timezone','2030-01-09T18:00:00'),
                           item('Known closure','2030-01-09T18:00:00Z',archive_completed_on='2030-01-09')]
            archive.details={'completion_archive':{'sheet_id':'1001','completion_date_column':None}}
            lines='\n'.join(undated_update_lines(session,self.actor.owner_id,start,end))
            self.assertIn('Fictional delivered part — marked completed; completion date unknown.',lines)
            self.assertIn('Last updated Jan 09 at 12:00 PM Central.',lines)
            self.assertIn('not the completion date',lines)
            for excluded in ('Old update','Future update','Still open','Unknown timezone','Known closure','recorded closed'):
                self.assertNotIn(excluded,lines)


    def test_leadership_agenda_is_durable_owner_scoped_and_keeps_routine_evidence_separate(self):
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        from datetime import datetime
        from juno.models import IntegrationSnapshot
        from juno.dean_briefing import compose
        agenda='/v1/planning/dean-agenda'
        topics=[{'title':'Fictional Technology Policies','status':'In progress','category':'progress'},
                {'title':'Fictional Technical Assistant Training Manual','status':'In progress','category':'progress'},
                {'title':'Temporary student worker office','status':'In progress','category':'progress'},
                {'title':'Fictional spending','status':'Submitted; validation pending','detail':'Total $123.45','category':'spending','week':'2030-01-07'},
                {'title':'Old spending','status':'Submitted','category':'spending','week':'2029-12-31'}]
        reply=self.client.put(agenda,json={'expected_revision':0,'topics':topics})
        self.assertEqual(reply.status_code,200,reply.text)
        self.assertEqual(self.client.put(agenda,json={'expected_revision':0,'topics':[]}).status_code,409)
        with TestClient(self.app) as other:
            other.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(other.get(agenda).json()['topics'],reply.json()['topics'])
            other.headers['Authorization']='Bearer '+self.other_token
            self.assertEqual(other.get(agenda).json()['topics'],[])
        from juno.shared_host import LANBoundary
        with TestClient(LANBoundary(self.app),client=('192.168.1.9',50000)) as laptop:
            laptop.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(laptop.get(agenda).status_code,200)
            self.assertEqual(laptop.put(agenda,json={'expected_revision':reply.json()['revision'],'topics':reply.json()['topics']}).status_code,200)
        with self.factory() as session:
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            td.items=[{'id':'paper','title':'Printer needs paper','blocked_reason':'Paper delivery'},
                      {'id':'closed','title':'Wacom classroom driver update','completed_at':'2030-01-09T18:00:00Z'},
                      {'id':'jamf','title':'Instructor remote access','blocked_reason':'Waiting on central IT'},
                      {'id':'computer','title':'Instructor computer replacement','description':''},
                      {'id':'system','title':'Printing unavailable across multiple classrooms'},
                      {'id':'wifi','title':'Continued WiFi issues in the classroom building'}]
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'))
            text=compose(session,self.actor.owner_id,datetime.fromisoformat('2030-01-03T16:00:00Z'),datetime.fromisoformat('2030-01-10T15:00:00Z'),datetime.fromisoformat('2030-01-10T16:00:00Z'),td,beacon)
            for expected in ('Technology Policies','Training Manual','Temporary student worker office','In progress','Total $123.45','Waiting on central IT','Planned cost not recorded','Wacom classroom driver update','Printing unavailable across multiple classrooms','Building wireless connectivity'):
                self.assertIn(expected,text)
            for excluded in ('Printer needs paper','Paper delivery','Alignment warning','Old spending'):
                self.assertNotIn(excluded,text)


    def test_explicit_leadership_rebuild_requires_current_revision_and_keeps_original_history(self):
        from datetime import datetime
        from unittest.mock import patch
        from juno.models import IntegrationSnapshot,ReportVersion
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        path='/v1/planning/weekly-draft/2030-01-07'
        old=self.client.get(path).json()
        with self.factory() as session:
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'))
            intent={'previous':'2030-01-03T16:00:00Z','meeting':'2030-01-10T16:00:00Z','taskdock_id':td.id,'beacon_id':beacon.id,'reformat_saved_revision':old['revision']}
        stamp=datetime.fromisoformat('2030-01-10T15:00:00Z')
        with patch('juno.planning_continuity.now',return_value=stamp),patch('juno.operations.now',return_value=stamp):
            self.assertEqual(self.client.post('/v1/planning/dean-meeting/prepare',json=intent|{'reformat_saved_revision':99}).status_code,409)
            response=self.client.post('/v1/planning/dean-meeting/prepare',json=intent)
            self.assertEqual(response.status_code,200,response.text)
            new=self.client.get(path).json()
            self.assertEqual(new['revision'],old['revision']+1)
            self.assertNotIn('Reviewed draft',new['text'])
            self.assertTrue(new['basis']['dean_review_notes'])
        with self.factory() as session:
            retained=session.get(ReportVersion,(self.actor.owner_id,'dean',datetime(2030,1,7).date(),old['revision']))
            self.assertEqual(retained.content['text'],old['text'])

    def test_semantic_selection_can_add_novel_work_but_cannot_reintroduce_routine_tickets(self):
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        from datetime import datetime
        from juno.models import IntegrationSnapshot
        from juno.dean_briefing import compose
        with self.factory() as session:
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            td.items=[{'id':'space','title':'Borrowed space for service crew','behavior':'open'},
                      {'id':'paper','title':'Printer needs paper','behavior':'open'}]
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'))
            text=compose(session,self.actor.owner_id,datetime.fromisoformat('2030-01-03T16:00:00Z'),datetime.fromisoformat('2030-01-10T15:00:00Z'),datetime.fromisoformat('2030-01-10T16:00:00Z'),td,beacon,
                         reasoning={'selected':{'task:space':'progress','task:paper':'progress'}})
            self.assertIn('Borrowed space for service crew',text)
            self.assertNotIn('Printer needs paper',text)
            self.assertNotIn('approved',text.casefold())

    def test_model_review_releases_owner_lock_and_does_not_replace_concurrent_writing(self):
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        from datetime import datetime
        from unittest.mock import patch
        from juno.models import IntegrationSnapshot,ModelConnection
        path='/v1/planning/weekly-draft/2030-01-07'
        old=self.client.get(path).json()
        with self.factory() as session:
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'))
            config=session.get(ModelConnection,self.actor.owner_id)
            if config is None:session.add(ModelConnection(owner_id=self.actor.owner_id,base_url='http://127.0.0.1:1234/v1',model='fixture'))
            intent={'previous':'2030-01-03T16:00:00Z','meeting':'2030-01-10T16:00:00Z','taskdock_id':td.id,'beacon_id':beacon.id,'reformat_saved_revision':old['revision']}
            session.commit()
        owner=self
        class Concurrent:
            def __init__(self,origin):pass
            def complete(self,messages,model):
                result=owner.client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':old['revision'],'basis':old['basis'],'text':'New writing from the paired laptop'})
                owner.assertEqual(result.status_code,200,result.text)
                return '{"include":[],"clarify":[]}'
        stamp=datetime.fromisoformat('2030-01-10T15:00:00Z')
        with patch('juno.planning_continuity.now',return_value=stamp),patch('juno.operations.now',return_value=stamp),TestClient(create_app(self.engine,model_factory=Concurrent)) as client:
            client.headers['Authorization']='Bearer '+self.token
            response=client.post('/v1/planning/dean-meeting/prepare',json=intent)
            self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.client.get(path).json()['text'],'New writing from the paired laptop')

    def test_full_preparation_uses_local_semantic_selection_and_preserves_preexisting_notes(self):
        self.test_meeting_compiles_refreshed_sources_with_cutoff_and_preserves_reviewed_writing()
        import json
        from datetime import datetime
        from unittest.mock import patch
        from juno.models import IntegrationSnapshot,ModelConnection
        with self.factory() as session:
            row=session.scalar(select(DeanDraft).where(DeanDraft.owner_id==self.actor.owner_id))
            row.text='Reviewed budget note';row.basis={};row.revision+=1;revision=row.revision
            td=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            td.items=[*td.items,{'id':'new-project','title':'Borrowed space for service crew','behavior':'open'}]
            beacon=session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'))
            if session.get(ModelConnection,self.actor.owner_id) is None:session.add(ModelConnection(owner_id=self.actor.owner_id,base_url='http://127.0.0.1:1234/v1',model='fixture'))
            intent={'previous':'2030-01-03T16:00:00Z','meeting':'2030-01-10T16:00:00Z','taskdock_id':td.id,'beacon_id':beacon.id,'preserve_saved_revision':revision}
            session.commit()
        class Semantic:
            def __init__(self,origin):pass
            def complete(self,messages,model):
                payload=json.loads(messages[1]['content'])
                selected=next(e for e in payload['evidence'] if e['title']=='Borrowed space for service crew')
                return json.dumps({'include':[{'id':selected['id'],'section':'progress'}],'clarify':[]})
        stamp=datetime.fromisoformat('2030-01-10T15:00:00Z')
        with patch('juno.planning_continuity.now',return_value=stamp),patch('juno.operations.now',return_value=stamp),TestClient(create_app(self.engine,model_factory=Semantic)) as client:
            client.headers['Authorization']='Bearer '+self.token
            response=client.post('/v1/planning/dean-meeting/prepare',json=intent)
            self.assertEqual(response.status_code,200,response.text)
            self.assertTrue(response.json()['created']);self.assertIsNone(response.json()['review_notice'])
            draft=client.get('/v1/planning/weekly-draft/2030-01-07').json()
            self.assertIn('Borrowed space for service crew',draft['text'])
            self.assertTrue(draft['text'].endswith('Reviewed budget note'))
            self.assertIn('Local model classified recorded evidence',draft['basis']['dean_review_notes'])
