"""Real PostgreSQL daily interview/next-workday bridge, fictional records only."""
from datetime import date, timedelta
from unittest.mock import patch
from sqlalchemy import select, func
from fastapi.testclient import TestClient
import test_memory_api as memory_tests
import test_planning as planning_tests
from juno.models import CheckIn, PlanningState, TaskDockSnapshot, TaskDockState, now
from juno.api import create_app


class DailyBriefTests(memory_tests.MemoryTests):
    def setUp(self):
        super().setUp()
        self.day = date(2030,1,7)
        self.start = '2030-01-07T15:00:00+00:00'
        self.end = '2030-01-07T23:00:00+00:00'
        self.data = {'expected_revision':0,'workspace_id':'fictional','reserve_minutes':60,
                     'windows':[{'kind':'work','name':'','start':self.start,'end':self.end}], 'tasks':[]}
        with self.factory() as s:
            snap = TaskDockSnapshot(owner_id=self.actor.owner_id, origin='http://localhost:8100',
                info={'workspace_id':'fictional','definitions':{}},items=[
                    {'id':'dean','title':'Fictional Dean request','priority':1,'behavior':'open'},
                    {'id':'room','title':'Fictional classroom repair','priority':2,'behavior':'open'},
                    {'id':'done','title':'Completed fictional task','behavior':'completed'}],sources=[],snapshot='fictional',fetched_at=now())
            s.add(snap);s.flush();s.add(TaskDockState(owner_id=self.actor.owner_id, active_id=snap.id));s.commit()

    save = planning_tests.PlanningTests.save
    add_source = planning_tests.PlanningTests.add_source

    def brief(self, day='2030-01-06'):
        response=self.client.get('/v1/planning/daily-brief',params={'day':day})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def snapshot(self, transform):
        with self.factory() as session:
            row=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            row.items=transform(list(row.items));session.commit()

    def test_read_only_owner_scope_and_next_scheduled_workday(self):
        self.save(tasks=[{'task_id':'dean','minutes':45,'dean':True,'resume':'Check the saved cable test'}])
        before=self.client.get('/v1/planning').json()
        with patch('juno.local_model.LocalModel.complete',create=True,side_effect=AssertionError('No model should be needed')):
            value=self.brief('2030-01-04') # Friday → saved Monday work window, not Saturday.
        self.assertEqual(value['next_day'],'2030-01-07')
        self.assertTrue(value['has_scheduled_workday'])
        self.assertEqual(value['recommended_task_id'],'dean')
        self.assertEqual(value['alternatives'][0]['resume'],'Check the saved cable test')
        self.assertEqual(value['diary_status'],'not_started')
        self.assertEqual(self.client.get('/v1/planning').json(),before)
        with self.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(CheckIn).where(CheckIn.owner_id==self.actor.owner_id)),0)
        with TestClient(create_app(self.engine)) as client:
            client.headers['Authorization']='Bearer '+self.other_token
            other=client.get('/v1/planning/daily-brief',params={'day':'2030-01-04'}).json()
            self.assertFalse(other['alternatives']);self.assertFalse(other['completed']);self.assertIsNone(other['workspace_id'])

    def test_completion_dates_use_chicago_not_current_status_or_undated_flags(self):
        self.snapshot(lambda items:items+[
            {'id':'late','title':'Previous Chicago day','completed_at':'2030-01-07T02:00:00Z'},
            {'id':'today','title':'Correct Chicago day','completed_at':'2030-01-07T20:00:00Z'},
            {'id':'naive','title':'Unknown zone','completed_at':'2030-01-07T10:00:00'},
            {'id':'flag','title':'Undated completion','source_completed':True}])
        value=self.brief('2030-01-07');self.assertEqual([r['task_id'] for r in value['completed']],['today'])
        value=self.brief('2030-01-06');self.assertEqual([r['task_id'] for r in value['completed']],['late'])

    def test_conflicting_priorities_require_a_question_and_stale_copies_offer_no_task(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True},{'task_id':'room','minutes':30,'operational':True}])
        value=self.brief();self.assertTrue(value['question']);self.assertIsNone(value['recommended_task_id']);self.assertFalse(value['alternatives'])
        self.save(expected_revision=1,tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        with self.factory() as session:
            row=session.get(TaskDockState,self.actor.owner_id);row.error='Fictional refresh failure';session.commit()
        value=self.brief();self.assertTrue(value['source_stale']);self.assertFalse(value['alternatives'])

    def test_daily_slots_cannot_escape_into_later_days_and_reserve_is_disclosed(self):
        self.data['windows'] += [{'kind':'work','start':'2030-01-08T15:00:00Z','end':'2030-01-08T23:00:00Z'}]
        self.save(reserve_minutes=120,tasks=[{'task_id':'dean','minutes':450,'dean':True}])
        value=self.brief();self.assertEqual(value['reserve_minutes'],60)
        self.assertEqual(value['capacity_minutes'],420);self.assertFalse(value['alternatives'])
        self.save(expected_revision=1,reserve_minutes=120,tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        self.add_source('calendar',[{'start':self.start,'end':self.end,'busy':True}])
        value=self.brief();self.assertEqual(value['next_day'],'2030-01-07');self.assertFalse(value['alternatives'])
        self.assertEqual(value['capacity_minutes'],0) # Tuesday's room/free time is not Monday's suggestion.

    def test_deferred_blockers_and_saved_answers_are_guidance_not_automatic_facts(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True,'blocker':'Parts ordered','next_action':'Check delivery','next_check':'2030-01-10'}])
        row=self.client.post('/v1/check-ins',json={'local_date':'2030-01-06'}).json()
        for key,text in [('interruptions','Walk-in display issue, time unknown'),('tomorrow','Remember the cable test')]:
            row=self.client.put('/v1/check-ins/'+row['id']+'/answer',json={'key':key,'text':text,'expected_revision':row['revision']}).json()
        before=self.client.get('/v1/planning').json();value=self.brief()
        self.assertEqual(value['deferred_blocker_count'],1);self.assertFalse(value['blockers'])
        self.assertNotIn('Check delivery',' '.join(value['guidance']['blockers']))
        self.assertEqual(value['continuity'],'Remember the cable test');self.assertEqual(value['diary_status'],'draft')
        self.assertEqual(self.client.get('/v1/planning').json(),before)

    def test_workspace_switch_and_missing_work_hours_do_not_reuse_old_facts(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True,'resume':'Old private workspace note'}])
        with self.factory() as session:
            row=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id));row.info={**row.info,'workspace_id':'different'};session.commit()
        value=self.brief();self.assertFalse(value['alternatives']);self.assertNotIn('Old private workspace note',str(value))
        # No saved hours after Monday: Tuesday is explicitly an unknown fallback, never assumed available.
        value=self.brief('2030-01-07');self.assertFalse(value['has_scheduled_workday']);self.assertFalse(value['alternatives'])
        self.assertEqual(self.client.get('/v1/planning/daily-brief?day=1900-01-01').status_code,422)

    def test_corrected_diary_does_not_resurrect_old_interview_notes(self):
        row=self.client.post('/v1/check-ins',json={'local_date':'2030-01-06'}).json()
        for key,text in [('completed','Fictional work'),('interruptions','Old interruption note'),('blockers','Unknown'),('employee_work',''),('tomorrow','Old carry-forward note')]:
            row=self.client.put('/v1/check-ins/'+row['id']+'/answer',json={'key':key,'text':text,'expected_revision':row['revision']}).json()
        corrected=self.client.put('/v1/check-ins/'+row['id']+'/diary',json={'expected_revision':row['revision'],'text':'Corrected confirmed diary with a different next step.','confirm':True})
        self.assertEqual(corrected.status_code,200)
        value=self.brief();self.assertEqual(value['diary_status'],'confirmed');self.assertEqual(value['continuity'],'')
        self.assertNotIn('Old interruption note',str(value));self.assertNotIn('Old carry-forward note',str(value))
