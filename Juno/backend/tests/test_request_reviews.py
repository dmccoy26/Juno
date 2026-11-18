"""Reviewed inline answers: scope, source conflicts and older-client preservation."""
from copy import deepcopy
from datetime import date
from fastapi.testclient import TestClient
import test_memory_api as memory
from juno.api import create_app
from juno.models import TaskDockSnapshot, TaskDockState, now

class RequestReviewTests(memory.MemoryTests):
    def setUp(self):
        super().setUp()
        self.workspace='fictional-review'
        self.task={'id':'fixture','title':'Fictional request','behavior':'open','planning_details':{
            'requested_outcome':{'state':'unknown','value':None},'impact':{'state':'unknown','value':None}}}
        with self.factory() as s:
            row=TaskDockSnapshot(owner_id=self.actor.owner_id,origin='http://localhost:8100',info={
                'workspace_id':self.workspace,'device_id':'fictional-device','capabilities':{'controlled_sharing':True},
                'sharing_version':1,'sharing':{'controlled':True,'channels':['title'],'planning_fields':['requested_outcome','impact']}},
                items=[deepcopy(self.task)],sources=[],snapshot='fixture',fetched_at=now())
            s.add(row);s.flush();self.snapshot=row.id;s.add(TaskDockState(owner_id=self.actor.owner_id,active_id=row.id));s.commit()
    def read_review(self,**extra):
        return self.client.get('/v1/planning/request-review',params={'workspace_id':self.workspace,'task_id':'fixture',**extra})
    def body(self,**extra):
        state=self.read_review().json()
        return {'workspace_id':self.workspace,'task_id':'fixture','key':'requested_outcome','snapshot_id':state['snapshot_id'],
            'expected_revision':state['revision'],'basis':next(f['basis'] for f in state['fields'] if f['key']=='requested_outcome'),'state':'provided','value':'A fictional successful print test',**extra}
    def save_review(self,**extra):
        r=self.client.post('/v1/planning/request-review',json=self.body(**extra));self.assertEqual(r.status_code,200,r.text);return r.json()
    def test_answer_restarts_other_devices_and_old_planning_put_preserve_it(self):
        self.save_review()
        with TestClient(create_app(self.engine)) as other:
            other.headers['Authorization']='Bearer '+self.second_token
            v=other.get('/v1/planning/request-review',params={'workspace_id':self.workspace,'task_id':'fixture'}).json()
            self.assertEqual(v['reviewed_fields']['requested_outcome']['value'],'A fictional successful print test')
            p=other.get('/v1/planning').json();p.pop('updated_at');p.pop('source_notice');p['expected_revision']=p.pop('revision')
            self.assertEqual(other.put('/v1/planning',json=p).status_code,200)
            self.assertEqual(other.get('/v1/planning/request-review',params={'workspace_id':self.workspace,'task_id':'fixture'}).json()['reviewed_fields'],v['reviewed_fields'])
        with self.factory() as s:self.assertEqual(s.get(TaskDockSnapshot,self.snapshot).items[0],self.task)
    def test_cas_source_change_and_quality_validation(self):
        stale=self.body();self.save_review()
        self.assertEqual(self.client.post('/v1/planning/request-review',json=stale).status_code,409)
        stale=self.body()
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot);task=deepcopy(row.items[0]);task['planning_details']['requested_outcome']={'state':'provided','value':'Source changed'};row.items=[task];s.commit()
        self.assertEqual(self.client.post('/v1/planning/request-review',json=stale).status_code,409)
        view=self.read_review().json();self.assertTrue(view['reviewed_fields']['requested_outcome']['review_conflict'])
        plan=self.client.get('/v1/planning/next',params={'day':str(date.today())}).json()
        task=next(t for t in plan['tasks'] if t['task_id']=='fixture')
        self.assertIn('requested_outcome',[q['key'] for q in task['request_questions']])
        self.assertTrue(any('Review changed request' in x for x in task['missing']))
        self.assertEqual(self.client.post('/v1/planning/request-review',json=self.body(state='none',value='not allowed')).status_code,422)
        self.assertEqual(self.client.post('/v1/planning/request-review',json=self.body(value='   ')).status_code,422)
        saved=self.save_review(state='none',value=None)
        self.assertEqual(saved['reviewed_fields']['requested_outcome']['state'],'none')
        self.assertFalse(saved['reviewed_fields']['requested_outcome']['review_conflict'])
    def test_owner_workspace_task_and_field_scope(self):
        self.save_review()
        r=self.client.get('/v1/planning/request-review',params={'workspace_id':self.workspace,'task_id':'fixture'},headers={'Authorization':'Bearer '+self.other_token})
        self.assertEqual(r.status_code,409);self.assertNotIn('successful print',r.text)
        self.assertEqual(self.read_review(workspace_id='wrong').status_code,409)
        self.assertEqual(self.read_review(task_id='absent').status_code,404)
        self.assertEqual(self.client.post('/v1/planning/request-review',json=self.body(key='contact')).status_code,403)
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot);row.info={**row.info,'sharing':{'controlled':True,'channels':['title'],'planning_fields':['impact']}};row.items=[{**self.task,'planning_details':{'impact':self.task['planning_details']['impact']}}];s.commit()
        r=self.read_review();self.assertNotIn('successful print',r.text);self.assertNotIn('requested_outcome',r.json()['reviewed_fields'])
    def test_lan_authenticated_device_can_review_local_admin_stays_denied(self):
        from juno.shared_host import LANBoundary
        with TestClient(LANBoundary(create_app(self.engine)),client=('10.1.2.3',50000)) as client:
            client.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(client.get('/v1/planning/request-review',params={'workspace_id':self.workspace,'task_id':'fixture'}).status_code,200)
            self.assertEqual(client.post('/v1/planning/request-review',json=self.body()).status_code,200)
            self.assertEqual(client.post('/v1/integrations/import',json={}).status_code,403)
