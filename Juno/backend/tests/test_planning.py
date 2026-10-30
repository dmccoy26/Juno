"""Real PostgreSQL acceptance for planning constraints, privacy and conflicts."""
from datetime import datetime, timedelta, timezone, date
from fastapi.testclient import TestClient
from sqlalchemy import select
import test_memory_api as memory_tests
from juno.api import create_app
from juno.models import TaskDockSnapshot, TaskDockState, IntegrationSnapshot, CheckIn, now
from juno.planning import merge, subtract
from test_companion import FakeModel


class PlanningTests(memory_tests.MemoryTests):
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

    def save(self, **changes):
        body={**self.data,**changes}
        r=self.client.put('/v1/planning',json=body)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def plan(self):
        r=self.client.get('/v1/planning/next',params={'day':str(self.day)})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def add_source(self, kind, items, **extra):
        with self.factory() as s:
            s.add(IntegrationSnapshot(owner_id=self.actor.owner_id,kind=kind,origin='manual:test',
                items=items,details={'start':'2030-01-07','end':'2030-01-14',**extra}, fetched_at=now()));s.commit()

    def test_unknown_duration_asks_and_corrections_persist_across_devices(self):
        self.save()
        plan=self.plan()
        self.assertIsNone(plan['recommended_task_id'])
        self.assertIn('duration',plan['question'])
        self.assertEqual(len(plan['tasks']),2)
        self.save(expected_revision=1,tasks=[{'task_id':'dean','minutes':30,'dean':True,'actual_minutes':42}])
        plan=self.plan();self.assertEqual(plan['recommended_task_id'],'dean')
        self.assertEqual(plan['tasks'][0]['estimate_minutes'],30)
        self.assertEqual(plan['tasks'][0]['actual_minutes'],42)
        with TestClient(create_app(self.engine)) as c:
            c.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(c.get('/v1/planning').json()['tasks'][0]['minutes'],30)
            self.assertEqual(c.put('/v1/planning',json=self.data).status_code,409)
            c.headers['Authorization']='Bearer '+self.other_token
            self.assertEqual(c.get('/v1/planning').json()['tasks'],[])
            self.assertEqual(c.get('/v1/planning/next',params={'day':str(self.day)}).json()['tasks'],[])

    def test_overlapping_calendars_count_once_and_work_windows_cap_at_40_hours(self):
        self.add_source('calendar',[{'start':'2030-01-07T16:00:00+00:00','end':'2030-01-07T18:00:00+00:00','busy':True}])
        self.add_source('google_calendar',[{'start':'2030-01-07T17:00:00+00:00','end':'2030-01-07T19:00:00+00:00','busy':True}])
        self.save();p=self.plan()
        self.assertEqual(p['free_minutes'],300)
        self.assertEqual(p['capacity_minutes'],240)
        windows=[{'kind':'work','start':f'2030-01-{7+i:02d}T00:00:00+00:00','end':f'2030-01-{8+i:02d}T00:00:00+00:00'} for i in range(7)]
        self.save(expected_revision=1,windows=windows)
        self.assertEqual(self.plan()['capacity_minutes'],2340)

    def test_room_access_staff_independence_and_blocker_constraints(self):
        task={'task_id':'dean','minutes':30,'room':'Lab','employee':'Alex','dean':True}
        self.save(tasks=[task]);p=self.plan()
        self.assertIsNone(p['recommended_task_id'])
        self.assertTrue(any('access' in x for x in p['tasks'][0]['missing']))
        windows=self.data['windows']+[{'kind':kind,'name':name,'start':self.start,'end':self.end} for kind,name in [('room','Lab'),('staff','Alex')]]
        task.update(independent=True,capability='Dan confirmed independent printer maintenance.',blocker='Waiting for approved parts',next_action='Check delivery',next_check='2030-01-09')
        self.save(expected_revision=1,tasks=[task],windows=windows)
        p=self.plan();self.assertIsNone(p['recommended_task_id']);self.assertEqual(p['tasks'][0]['next_action'],'Check delivery')
        self.assertEqual(p['tasks'][0]['next_check'],'2030-01-09')
        task['blocker']=''
        self.save(expected_revision=2,tasks=[task],windows=windows)
        self.assertEqual(self.plan()['recommended_task_id'],'dean')
        self.add_source('schedules',[{'kind':'classroom_busy','location':'Lab','title':'Class','start':self.start,'end':self.end}])
        self.assertIsNone(self.plan()['recommended_task_id'])

    def test_competing_important_priorities_ask_before_choosing(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True},{'task_id':'room','minutes':30,'operational':True}])
        p=self.plan();self.assertIsNone(p['recommended_task_id']);self.assertIn('disrupt teaching',p['question'])
        self.save(expected_revision=1,tasks=[{'task_id':'dean','minutes':30,'dean':True},{'task_id':'room','minutes':30,'operational':True}],priority_choice='room',priority_choice_date=str(self.day))
        self.assertEqual(self.plan()['recommended_task_id'],'room')
        other_day=self.client.get('/v1/planning/next',params={'day':'2030-01-08'}).json()
        self.assertIsNone(other_day['recommended_task_id']);self.assertIn('disrupt teaching',other_day['question'])

    def test_stale_snapshot_waiting_status_and_future_start_do_not_become_actionable(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        with self.factory() as s:
            row=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            row.fetched_at=now()-timedelta(days=2);s.commit()
        self.assertIsNone(self.plan()['recommended_task_id'])
        with self.factory() as s:
            row=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            row.fetched_at=now();row.items=[{**row.items[0],'behavior':'waiting','start_date':'2030-01-10'}];s.commit()
        p=self.plan();self.assertIsNone(p['recommended_task_id']);self.assertIn('waiting',p['tasks'][0]['blocker'])

    def test_no_windows_never_means_free_and_past_windows_never_used(self):
        self.save(windows=[],tasks=[{'task_id':'dean','minutes':30}])
        self.assertEqual(self.plan()['capacity_minutes'],0)
        self.assertIsNone(self.plan()['recommended_task_id'])
        r=self.client.get('/v1/planning/next',params={'day':'2000-01-01'}).json()
        self.assertEqual(r['capacity_minutes'],0)

    def test_staff_workload_is_bounded_evidence_and_checkin_defers_unchanged_blockers(self):
        task={'task_id':'dean','minutes':45,'employee':'Alex','independent':True,'capability':'Confirmed by Dan',
              'blocker':'Parts','next_action':'Check delivery','next_check':'2030-01-09','dean':True}
        windows=self.data['windows']+[{'kind':'staff','name':'Alex','start':self.start,'end':self.end}]
        self.save(tasks=[task],windows=windows)
        p=self.plan();load=p['staff_loads'][0]
        self.assertEqual(load['reported_assignment_minutes'],45)
        self.assertEqual(load['available_minutes'],480)
        self.assertIn('not a complete workload',load['notice'])
        r=self.client.get('/v1/planning/check-in',params={'day':str(self.day)}).json()
        self.assertIn('1 blocker(s) have a later check date',r['text'])
        self.assertIn('none recorded due',r['text'])
        self.assertNotIn('Check delivery',r['text'])

    def test_calendar_failure_and_cancellation(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        self.add_source('google_calendar',[{'start':self.start,'end':self.end,'busy':True,'status':'cancelled'}])
        self.assertEqual(self.plan()['recommended_task_id'],'dean')
        with self.factory() as s:
            row=s.get(IntegrationSnapshot,(self.actor.owner_id,'google_calendar'));row.error='Synthetic failed read';s.commit()
        p=self.plan();self.assertIsNone(p['recommended_task_id'])
        self.assertTrue(any('Refresh the connected calendar' in m for m in p['tasks'][0]['missing']))
        self.assertEqual(self.client.get('/v1/planning/next?day=9999-12-31').status_code,422)

    def test_authenticated_laptop_planning_routes_and_network_boundaries(self):
        from juno.shared_host import LANBoundary
        with TestClient(LANBoundary(self.app),client=('192.168.1.9',50000)) as lan:
            self.assertEqual(lan.get('/v1/planning').status_code,401)
            lan.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(lan.get('/v1/planning').status_code,200)
            self.assertEqual(lan.put('/v1/planning',json=self.data).status_code,200)
            for path in ['next','weekly','check-in']:
                r=lan.get('/v1/planning/'+path,params={'day':str(self.day)})
                self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(lan.put('/v1/planning',json=self.data).status_code,409)
            self.assertEqual(lan.delete('/v1/planning').status_code,403)
            self.assertEqual(lan.get('/v1/providers/state').status_code,403)
        with TestClient(LANBoundary(self.app),client=('203.0.113.7',50000)) as external:
            self.assertEqual(external.get('/v1/planning',headers={'Authorization':'Bearer '+self.second_token}).status_code,403)

    def test_workspace_switch_does_not_reuse_colliding_task_facts(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        with self.factory() as s:
            row=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id))
            row.info={**row.info,'workspace_id':'another-fictional-workspace'};s.commit()
        state=self.client.get('/v1/planning').json()
        self.assertEqual(state['tasks'],[])
        self.assertIn('workspace changed',state['source_notice'])
        self.assertEqual(self.client.put('/v1/planning',json={**self.data,'expected_revision':1}).status_code,409)
        self.assertFalse(self.plan()['tasks'][0]['estimate_confirmed'])
        self.assertEqual(self.client.get('/v1/planning/weekly?day=9999-12-31').status_code,422)

    def test_validates_timezones_duplicates_and_bounds(self):
        for change in [ {'reserve_minutes':2401}, {'tasks':[{'task_id':'x','minutes':0}]},
                       {'tasks':[{'task_id':'x'},{'task_id':'x'}]},
                       {'windows':[{'kind':'work','start':'2030-01-07T09:00:00','end':'2030-01-07T10:00:00'}]},
                       {'windows':[{'kind':'staff','start':self.start,'end':self.end}]} ]:
            self.assertEqual(self.client.put('/v1/planning',json={**self.data,**change}).status_code,422)

    def test_weekly_uses_confirmed_diaries_only_and_cache_contains_facts(self):
        with self.factory() as s:
            for i,status in enumerate(['confirmed','draft']):
                s.add(CheckIn(owner_id=self.actor.owner_id,local_date=self.day+timedelta(days=i),answers={},
                              diary_text='Confirmed fictional accomplishment' if not i else 'PRIVATE UNCONFIRMED',status=status))
            s.commit()
        self.save()
        r=self.client.get('/v1/planning/weekly',params={'day':str(self.day)}).json()
        self.assertIn('Confirmed fictional accomplishment',r['text']);self.assertNotIn('PRIVATE UNCONFIRMED',r['text'])
        self.assertIn('has not been sent',r['text'])
        cache=self.client.get('/v1/cache').json()
        page=next(p for p in cache['pages'] if p['path']=='/v1/planning')
        self.assertEqual(page['body']['revision'],1)

    def test_planning_correction_invalidates_chat_and_new_prompt_uses_correction(self):
        self.client.close();FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.client=TestClient(create_app(self.engine,model_factory=FakeModel));self.client.headers['Authorization']='Bearer '+self.token
        self.save(tasks=[{'task_id':'dean','minutes':30,'resume':'FICTIONAL OLD RESUMPTION'}])
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic'})
        c=self.client.post('/v1/conversations',json={'title':'Planning'}).json()['id']
        import uuid
        path='/v1/conversations/'+c+'/messages'
        self.client.post(path,json={'text':'What next?','request_id':str(uuid.uuid4())})
        self.assertIn('FICTIONAL OLD RESUMPTION',str(FakeModel.calls[-1]))
        self.save(expected_revision=1,tasks=[])
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')
        self.client.post(path,json={'text':'What next?','request_id':str(uuid.uuid4())})
        self.assertNotIn('FICTIONAL OLD RESUMPTION',str(FakeModel.calls[-1]))


for name in list(memory_tests.MemoryTests.__dict__):
    if name.startswith('test_'):
        setattr(PlanningTests,name,None)
