from datetime import date
from fastapi.testclient import TestClient
import test_planning
from juno.shared_host import LANBoundary

class ScheduleTests(test_planning.PlanningTests):
    def setUp(self):
        super().setUp()
        self.rules=[self.rule('work','',9,17),self.rule('room','Lab',7,21),self.rule('staff_available','Alex',9,17)]
        self.body={'expected_revision':0,'rules':self.rules,'people':[{'name':'Alex','status':'active','weekly_limit_minutes':120}], 'exceptions':[]}

    def rule(self,kind,name,a,b):
        return {'id':kind+name,'kind':kind,'name':name,'start_date':'2030-01-01','end_date':'2030-05-01','days':[0,1,2,3,4], 'start_time':f'{a:02d}:00','end_time':f'{b:02d}:00'}

    def schedule(self,**changes):
        r=self.client.put('/v1/schedules',json={**self.body,**changes});self.assertEqual(r.status_code,200,r.text);return r.json()

    def windows(self,**changes):
        r=self.client.get('/v1/availability',params={'day':str(self.day),'room':'Lab','employee':'Alex','minutes':60,**changes});self.assertEqual(r.status_code,200,r.text);return r.json()

    def facts(self,**changes):
        self.save(windows=self.client.get('/v1/planning').json()['windows'],tasks=[{'task_id':'dean','minutes':60,'room':'Lab','employee':'Alex','capability':'Confirmed fictional training','independent':True,**changes}])

    def reserve(self,start='2030-01-07T09:00:00-06:00',end='2030-01-07T10:00:00-06:00',revision=1):
        return self.client.post('/v1/schedules/reservations',json={'expected_revision':revision,'task_id':'dean','workspace_id':'fictional','room':'Lab','employee':'Alex','start':start,'end':end})

    def test_recurring_changes_override_old_windows_and_room_aliases(self):
        self.save()
        self.schedule(rules=[self.rule('work','Dan',11,13),self.rule('room','A121',7,21),self.rule('staff_available','Alex',9,17)])
        p=self.windows(room='ARTS 121',supervision=True)
        self.assertTrue(p['windows']);self.assertIn('11:00',p['windows'][0]['start'])
        self.assertEqual(p['windows'][0]['available_minutes'],120)

    def test_candidate_and_tentative_never_count_as_confirmed_capacity(self):
        self.schedule(people=[{'name':'Alex','status':'candidate','weekly_limit_minutes':1200}])
        p=self.windows();self.assertEqual(p['windows'],[]);self.assertIn('candidate',p['warnings'][0])
        self.schedule(expected_revision=1,people=[{'name':'Alex','status':'tentative','weekly_limit_minutes':1200}])
        self.assertEqual(self.windows()['windows'],[])

    def test_classroom_busy_and_closure_exceptions(self):
        self.schedule(exceptions=[{'kind':'room','name':'Lab','day':str(self.day),'closed':True,'note':'Closed for holiday'}])
        self.assertFalse(any(w['start'].startswith(str(self.day)) for w in self.windows()['windows']))
        self.schedule(expected_revision=1,exceptions=[{'kind':'staff_available','name':'Alex','day':str(self.day),'closed':False,'start_time':'13:00','end_time':'15:00'}])
        p=self.windows();self.assertIn('13:00',p['windows'][0]['start']);self.assertEqual(p['windows'][0]['available_minutes'],120)

    def test_independent_work_does_not_require_owner_but_supervision_does(self):
        self.schedule(rules=self.rules[1:])
        self.assertTrue(self.windows()['windows'])
        self.assertEqual(self.windows(supervision=True)['windows'],[])

    def test_reservations_prevent_double_booking_and_enforce_weekly_limit(self):
        self.schedule();self.facts()
        first=self.reserve();self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.reserve(revision=2).status_code,409)
        second=self.reserve('2030-01-07T10:00:00-06:00','2030-01-07T11:00:00-06:00',2)
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(self.windows()['windows'],[])
        release=self.client.delete('/v1/schedules/reservations/'+first.json()['id'],params={'expected_revision':3})
        self.assertEqual(release.status_code,200)
        self.assertTrue(self.windows()['windows'])

    def test_schedule_conflicts_owner_and_lan_boundaries(self):
        self.schedule()
        self.assertEqual(self.client.put('/v1/schedules',json=self.body).status_code,409)
        self.assertEqual(self.client.get('/v1/schedules',headers={'Authorization':'Bearer '+self.other_token}).json()['rules'],[])
        with TestClient(LANBoundary(self.app),client=('192.168.1.9',12345)) as lan:
            lan.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(lan.get('/v1/schedules').status_code,200)
            self.assertEqual(lan.get('/v1/availability',params={'day':str(self.day),'room':'Lab'}).status_code,200)
            self.assertEqual(lan.get('/v1/providers/state').status_code,403)
        self.assertEqual(self.client.get('/v1/availability?day=9999-12-31').status_code,422)

    def test_cannot_inject_reservations_or_exceed_agreed_hours(self):
        self.assertEqual(self.client.put('/v1/schedules',json={**self.body,'reservations':[]}).status_code,422)
        self.assertEqual(self.client.put('/v1/schedules',json={**self.body,'people':[{'name':'Alex','weekly_limit_minutes':1200,'desired_minutes':1260}]}).status_code,422)
        self.schedule();self.facts(blocker='Parts not approved')
        self.assertEqual(self.reserve().status_code,409)

    def test_removing_recurring_access_does_not_restore_old_imported_windows(self):
        self.save(windows=self.data['windows']+[{'kind':'room','name':'Lab','start':self.start,'end':self.end}])
        self.schedule()
        self.assertTrue(self.windows()['windows'])
        self.schedule(expected_revision=1,rules=[r for r in self.rules if r['kind']!='room'])
        self.assertEqual(self.windows()['windows'],[])

    def test_personal_reserve_and_stale_calendar_block_booking(self):
        self.schedule(rules=self.rules[:2])
        self.save(reserve_minutes=2400,windows=[])
        self.assertEqual(self.windows(employee='')['windows'],[])
        self.save(expected_revision=1,reserve_minutes=0,windows=[])
        self.add_source('google_calendar',[])
        from juno.models import IntegrationSnapshot
        with self.factory() as session:
            row=session.get(IntegrationSnapshot,(self.actor.owner_id,'google_calendar'));row.error='Synthetic failure';session.commit()
        view=self.windows(employee='')
        self.assertFalse(view['calendar_ready'])
        self.assertTrue(any('calendar' in warning for warning in view['warnings']))

    def test_new_schedule_profiles_and_cache_invalidate_old_chat(self):
        from test_companion import FakeModel
        from juno.api import create_app
        import uuid
        self.client.close();FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.client=TestClient(create_app(self.engine,model_factory=FakeModel));self.client.headers['Authorization']='Bearer '+self.token
        self.schedule()
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'fake'})
        conv=self.client.post('/v1/conversations',json={'title':'Synthetic schedule continuity'}).json()['id']
        path='/v1/conversations/'+conv+'/messages'
        self.client.post(path,json={'text':'When can Alex work?','request_id':str(uuid.uuid4())})
        self.schedule(expected_revision=1,people=[{'name':'Alex','status':'candidate','weekly_limit_minutes':120}])
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')
        cache=self.client.get('/v1/cache').json()
        saved=next(p for p in cache['pages'] if p['path']=='/v1/schedules')
        self.assertEqual(saved['body']['people'][0]['status'],'candidate')

    def test_older_client_cannot_silently_override_recurring_hours(self):
        self.save();self.schedule()
        changed=[{**self.data['windows'][0],'end':'2030-01-07T23:30:00+00:00'}]
        r=self.client.put('/v1/planning',json={**self.data,'expected_revision':1,'windows':changed})
        self.assertEqual(r.status_code,409)
        self.assertIn('recurring schedules',r.json()['detail'])
        self.save(expected_revision=1,tasks=[{'task_id':'dean','minutes':45}])

    def test_estimate_fallback_does_not_change_confirmed_duration(self):
        self.facts()
        r=self.client.post('/v1/planning/estimate',json={'task_id':'dean'})
        self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['source'],'uncalibrated starter')
        self.assertEqual(self.client.get('/v1/planning').json()['tasks'][0]['minutes'],60)
        self.assertEqual(self.client.post('/v1/planning/estimate',json={'task_id':'missing'}).status_code,404)

for name in dir(test_planning.PlanningTests):
    if name.startswith('test_') and name not in ScheduleTests.__dict__:setattr(ScheduleTests,name,None)
