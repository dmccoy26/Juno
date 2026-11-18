"""Disposable owner-private work bookmarks, reconnect receipts and conflicts."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select,func
import test_memory_api as memory_tests
from juno.api import create_app
from juno.models import WorkBookmark,WorkSupport
from juno.shared_host import LANBoundary

class WorkSupportTests(memory_tests.MemoryTests):
    def state(self,client=None):
        result=(client or self.client).get('/v1/work-support')
        self.assertEqual(result.status_code,200,result.text);return result.json()
    def action(self,command,expected=None,client=None,**body):
        client=client or self.client
        state=self.state(client)
        body={'operation_id':str(uuid4()),'expected_revision':state['revision'] if expected is None else expected,'command':command,**body}
        if command!='start' and 'bookmark_id' not in body:body['bookmark_id']=state['current']['id']
        return client.post('/v1/work-support/actions',json=body)
    def start(self,**body):
        result=self.action('start',title='Synthetic printer check',first_action='Open the issue and write one thing to check.',finish_point='One check is written down.',**body)
        self.assertEqual(result.status_code,200,result.text);return result.json()

    def test_interrupt_restart_finish_retains_concrete_step_without_operational_writes(self):
        started=self.start();identity=started['current']['id']
        interrupted=self.action('interrupt',where_stopped='Stopped before opening the device list.').json()
        self.assertEqual(interrupted['current']['status'],'interrupted')
        smaller=self.action('revise',first_action='Open the device list.',finish_point='The list is visible.').json()
        resumed=self.action('resume').json()
        self.assertEqual(resumed['current']['resume_count'],1)
        self.assertEqual(resumed['current']['where_stopped'],interrupted['current']['where_stopped'])
        finished=self.action('finish').json()
        self.assertIsNone(finished['current']);self.assertEqual(finished['recent_finished'][0]['id'],identity)
        self.assertEqual(finished['recent_finished'][0]['first_action'],'Open the device list.')
        self.assertEqual(self.client.get('/v1/planning').json()['tasks'],[])
        self.assertFalse(self.client.get('/v1/taskdock').json()['snapshot'])
        self.assertFalse(self.client.get('/v1/recurring').json()['items'])
        self.assertIn('does not assign',finished['notice'])

    def test_park_switch_and_resume_do_not_lose_old_bookmark(self):
        old=self.start()['current']['id']
        denied=self.action('start',title='Synthetic other work',first_action='Open notes.',finish_point='Notes are open.')
        self.assertEqual(denied.status_code,409)
        switched=self.start(switch_current=True)
        self.assertEqual(switched['parked'][0]['id'],old)
        resumed=self.action('resume',bookmark_id=old,switch_current=True).json()
        self.assertEqual(resumed['current']['id'],old)
        self.assertEqual(resumed['parked'][0]['id'],switched['current']['id'])
        blocked=self.action('interrupt',blocker='Waiting for a reviewed access decision.').json()
        self.assertEqual(blocked['current']['blocker'],'Waiting for a reviewed access decision.')
        cleared=self.action('revise',blocker='').json()
        self.assertEqual(cleared['current']['blocker'],'')
        self.assertEqual(cleared['current']['status'],'interrupted')

    def test_lost_response_replay_and_request_id_collision(self):
        body={'operation_id':str(uuid4()),'expected_revision':0,'command':'start','title':'Synthetic start','first_action':'Open notes.','finish_point':'Notes visible.'}
        first=self.client.post('/v1/work-support/actions',json=body)
        self.assertEqual(first.status_code,200,first.text)
        self.action('interrupt')
        repeat=self.client.post('/v1/work-support/actions',json=body)
        self.assertTrue(repeat.json()['replayed']);self.assertEqual(repeat.json()['current']['status'],'interrupted')
        self.assertEqual(self.client.post('/v1/work-support/actions',json={**body,'title':'Another task'}).status_code,409)
        with self.factory() as s:self.assertEqual(s.scalar(select(func.count()).select_from(WorkBookmark).where(WorkBookmark.owner_id==self.actor.owner_id)),1)

    def test_second_device_conflict_owner_isolation_and_private_cache(self):
        started=self.start();identity=started['current']['id']
        with TestClient(create_app(self.engine)) as second:
            second.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(self.state(second)['current']['id'],identity)
            saved=self.action('interrupt',client=second)
            self.assertEqual(saved.status_code,200,saved.text)
            self.assertEqual(self.action('finish',expected=started['revision']).status_code,409)
        auth={'Authorization':'Bearer '+self.other_token}
        self.assertIsNone(self.client.get('/v1/work-support',headers=auth).json()['current'])
        other={'operation_id':str(uuid4()),'expected_revision':0,'command':'resume','bookmark_id':identity}
        self.assertEqual(self.client.post('/v1/work-support/actions',json=other,headers=auth).status_code,404)
        pages=self.client.get('/v1/cache').json()['pages']
        page=next(p['body'] for p in pages if p['path']=='/v1/work-support')
        self.assertEqual(page['current']['id'],identity)

    def test_connected_laptop_can_update_but_browser_and_unpaired_clients_cannot(self):
        with TestClient(LANBoundary(self.app),client=('10.2.3.4',50001)) as laptop:
            laptop.headers['Authorization']='Bearer '+self.second_token
            body={'operation_id':str(uuid4()),'expected_revision':0,'command':'start','title':'Synthetic laptop work','first_action':'Open notes.','finish_point':'Notes open.'}
            result=laptop.post('/v1/work-support/actions',json=body)
            self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(laptop.post('/v1/work-support/actions',json=body,headers={'Origin':'https://untrusted.example'}).status_code,403)
            self.assertEqual(laptop.post('/v1/recurring/tick',json={}).status_code,403)
        with TestClient(LANBoundary(self.app),client=('203.0.113.1',50001)) as public:
            self.assertEqual(public.get('/v1/work-support',headers={'Authorization':'Bearer '+self.token}).status_code,403)

    def test_simultaneous_changes_have_one_winner_and_keep_notes(self):
        state=self.start();identity=state['current']['id']
        def write(note):
            with TestClient(create_app(self.engine)) as client:
                return client.post('/v1/work-support/actions',headers={'Authorization':'Bearer '+self.token},json={
                    'operation_id':str(uuid4()),'expected_revision':state['revision'],'command':'interrupt','bookmark_id':identity,'where_stopped':note}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(write,['Synthetic stopping point A','Synthetic stopping point B']))
        self.assertEqual(sorted(results),[200,409])
        self.assertIn(self.state()['current']['where_stopped'],['Synthetic stopping point A','Synthetic stopping point B'])

    def test_invalid_first_steps_and_stale_sources_do_not_write(self):
        for body in [dict(title=' ',first_action='Open notes.',finish_point='Visible.'),dict(title='Work',first_action=' ',finish_point='Visible.'),dict(title='Work',first_action='Open notes.',finish_point='')]:
            self.assertEqual(self.action('start',**body).status_code,422)
        bad=self.action('start',title='Work',first_action='Open notes.',finish_point='Visible.',source_ref={'task_id':'other','workspace_id':'other','snapshot_id':str(uuid4())})
        self.assertEqual(bad.status_code,409)
        self.assertIsNone(self.state()['current']);self.assertEqual(self.state()['revision'],0)

    def test_reviewed_issue_reference_is_retained_without_mutating_source(self):
        from juno.models import TaskDockSnapshot,TaskDockState,now
        with self.factory() as session:
            copy=TaskDockSnapshot(owner_id=self.actor.owner_id,origin='http://localhost:8100',info={'workspace_id':'synthetic-workspace','definitions':{}},
                items=[{'id':'synthetic-issue','title':'Synthetic issue','behavior':'open'}],sources=[],snapshot='synthetic',fetched_at=now())
            session.add(copy);session.flush();session.add(TaskDockState(owner_id=self.actor.owner_id,active_id=copy.id));session.commit();identity=copy.id
        source={'task_id':'synthetic-issue','workspace_id':'synthetic-workspace','snapshot_id':identity}
        started=self.start(source_ref=source)
        self.assertEqual(started['current']['source_ref'],source)
        with self.factory() as session:
            self.assertEqual(session.get(TaskDockSnapshot,identity).items,[{'id':'synthetic-issue','title':'Synthetic issue','behavior':'open'}])
        self.assertEqual(self.action('revise',source_ref=source,first_action='Open the notes.').status_code,422)
