import copy
from datetime import timedelta
import threading
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
import test_memory_api as memory_tests
from test_companion import FakeModel
from test_taskdock import Transport, FIXTURE
from juno.api import create_app
from juno.models import TaskDockSnapshot, TaskDockState, now
from juno.taskdock import TaskDockReader, TaskDockError


class ReaderFactory:
    controlled_version = None
    workspace = None
    device = None
    failure = None
    entered = None
    release = None
    calls = []
    def __new__(cls, base_url, token):
        if cls.controlled_version is not None:
            from test_taskdock_sharing import Controlled
            transport=Controlled()
            transport.discovery['sharing_version']=cls.controlled_version
            for page in transport.pages:page['sharing_version']=cls.controlled_version
        else:transport=Transport()
        if cls.workspace: transport.discovery['workspace_id']=cls.workspace
        if cls.device: transport.discovery['device_id']=cls.device
        transport.fail=cls.failure
        def send(url,headers):
            cls.calls.append((url,headers))
            if cls.entered and '/workspace/tasks?' in url:
                cls.entered.set();cls.release.wait(5)
            if '/timeline?' in url and transport.fail is None:
                return {'items':[{'id':'synthetic-update', 'body':'Student Test — Fictional update.'}], 'next_cursor':None}
            return transport(url,headers)
        return TaskDockReader(base_url,token,send)


class TaskDockAPITests(memory_tests.MemoryTests):
    def setUp(self):
        super().setUp();self.client.close()
        ReaderFactory.controlled_version=None
        ReaderFactory.workspace=None;ReaderFactory.device=None;ReaderFactory.failure=None
        ReaderFactory.entered=None;ReaderFactory.release=None;ReaderFactory.calls=[]
        FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.app=create_app(self.engine,model_factory=FakeModel,taskdock_factory=ReaderFactory)
        self.client=TestClient(self.app);self.client.headers['Authorization']='Bearer '+self.token
        self.body={'base_url':'http://localhost:8100','token':'SYNTHETIC-PAIRING-SECRET'}

    def refresh(self, **extra):
        return self.client.post('/v1/taskdock/refresh',json={**self.body,**extra})

    def pair(self):
        review=self.refresh()
        self.assertEqual(review.status_code,200,review.text)
        self.assertTrue(review.json()['review_required'])
        result=self.refresh(reviewed_workspace_id=review.json()['info']['workspace_id'],reviewed_device_id=review.json()['info']['device_id'])
        self.assertEqual(result.status_code,200,result.text)
        return result.json()['snapshot']

    def test_pair_persistence_owner_scope_and_no_credential_storage(self):
        self.assertIsNone(self.client.get('/v1/taskdock').json()['snapshot'])
        snapshot=self.pair()
        self.assertEqual(snapshot['items'],FIXTURE['tasks']['items'])
        self.assertEqual(snapshot['sources'],FIXTURE['sources']['items'])
        with TestClient(create_app(self.engine)) as other:
            other.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(other.get('/v1/taskdock').json()['snapshot']['id'],snapshot['id'])
            other.headers['Authorization']='Bearer '+self.other_token
            self.assertIsNone(other.get('/v1/taskdock').json()['snapshot'])
            self.assertEqual(other.get('/v1/taskdock/snapshots').json()['items'],[])
            self.assertEqual(other.get('/v1/taskdock/snapshots/'+snapshot['id']).status_code,404)
        with self.factory() as session:
            row=session.get(TaskDockSnapshot,snapshot['id'])
            self.assertNotIn(self.body['token'],str(vars(row)))
            self.assertNotIn(self.body['token'],str(vars(session.get(TaskDockState,self.actor.owner_id))))

    def test_outage_retains_but_revocation_clears_saved_content_without_retries(self):
        snapshot=self.pair()
        for code in (None,401,403,422,500):
            ReaderFactory.failure=TaskDockError('Synthetic outage or revoked access.',code)
            before=len(ReaderFactory.calls)
            result=self.refresh(expected_snapshot_id=snapshot['id'])
            self.assertEqual(result.status_code,502,result.text)
            self.assertEqual(len(ReaderFactory.calls)-before,1)
            saved=self.client.get('/v1/taskdock').json()['snapshot']
            self.assertEqual(saved['id'],snapshot['id']);self.assertTrue(saved['stale'])
            self.assertEqual(saved['items'],snapshot['items'] if code is None else [])
            if code in (401,403):
                self.assertTrue(saved['info']['sharing_restricted'])
                self.assertEqual(saved['sources'],[])
        ReaderFactory.failure=None
        fresh=self.refresh(expected_snapshot_id=snapshot['id']).json()['snapshot']
        self.assertNotEqual(fresh['id'],snapshot['id']);self.assertFalse(fresh['stale'])

    def test_changed_policy_clears_old_archives_and_replaces_active_copy(self):
        old=self.pair()
        ReaderFactory.controlled_version=7
        result=self.refresh(expected_snapshot_id=old['id'])
        self.assertEqual(result.status_code,200,result.text)
        fresh=result.json()['snapshot']
        self.assertEqual(fresh['info']['sharing_version'],7)
        self.assertTrue(fresh['items'])
        archived=self.client.get('/v1/taskdock/snapshots/'+old['id']).json()
        self.assertEqual(archived['items'],[])
        self.assertTrue(archived['info']['sharing_restricted'])
        ReaderFactory.controlled_version=8
        newer=self.refresh(expected_snapshot_id=fresh['id'])
        self.assertEqual(newer.status_code,200,newer.text)
        self.assertEqual(self.client.get('/v1/taskdock/snapshots/'+fresh['id']).json()['items'],[])

    def test_both_identity_changes_require_review_and_preserve_archive(self):
        for field in ('workspace','device'):
            snapshot=self.pair() if field=='workspace' else self.client.get('/v1/taskdock').json()['snapshot']
            setattr(ReaderFactory,field,'new-'+field)
            result=self.refresh(expected_snapshot_id=snapshot['id']).json()
            self.assertTrue(result['review_required'])
            self.assertEqual(self.client.get('/v1/taskdock').json()['snapshot']['id'],snapshot['id'])
            accepted=self.refresh(expected_snapshot_id=snapshot['id'],reviewed_workspace_id=result['info']['workspace_id'],reviewed_device_id=result['info']['device_id']).json()['snapshot']
            self.assertNotEqual(accepted['id'],snapshot['id'])
            old=self.client.get('/v1/taskdock/snapshots/'+snapshot['id']).json()
            self.assertEqual(old['items'],snapshot['items'])
        self.assertEqual(len(self.client.get('/v1/taskdock/snapshots').json()['items']),3)

    def test_task_context_is_dated_untrusted_bounded_and_invalidated(self):
        snapshot=self.pair()
        self.client.put('/v1/model',json={'base_url':'http://localhost:1234/v1','model':'synthetic'})
        conv=self.client.post('/v1/conversations',json={'title':'Synthetic'}).json()['id']
        path='/v1/conversations/'+conv+'/messages'
        turn=lambda:self.client.post(path,json={'text':'What needs my attention?','request_id':str(uuid.uuid4())})
        self.assertEqual(turn().json()['status'],'complete')
        prompt=str(FakeModel.calls[-1])
        self.assertIn(snapshot['items'][0]['title'],prompt)
        self.assertIn(snapshot['fetched_at'][:10],prompt)
        self.assertIn('untrusted',prompt);self.assertNotIn(self.body['token'],prompt)
        ReaderFactory.failure=TaskDockError('Synthetic offline')
        self.refresh(expected_snapshot_id=snapshot['id'])
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')
        self.assertEqual(turn().json()['status'],'complete')
        self.assertIn('"stale": true',FakeModel.calls[-1][0]['content'])
        ReaderFactory.failure=None
        self.refresh(expected_snapshot_id=snapshot['id'])
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')

    def test_concurrent_refresh_cannot_replace_an_unreviewed_binding(self):
        snapshot=self.pair();ReaderFactory.entered=threading.Event();ReaderFactory.release=threading.Event()
        result=[]
        worker=threading.Thread(target=lambda:result.append(self.refresh(expected_snapshot_id=snapshot['id'])))
        worker.start();self.assertTrue(ReaderFactory.entered.wait(3))
        with self.factory() as session:
            state=session.get(TaskDockState,self.actor.owner_id);state.active_id=None;session.commit()
        ReaderFactory.release.set();worker.join(5)
        self.assertEqual(result[0].status_code,409)
        self.assertIsNone(self.client.get('/v1/taskdock').json()['snapshot'])
        self.assertEqual(len(self.client.get('/v1/taskdock/snapshots').json()['items']),1)

    def test_history_cache_is_owner_scoped_and_survives_failed_read_and_restart(self):
        snapshot=self.pair();task=snapshot['items'][0]['id']
        from urllib.parse import urlencode
        params=urlencode({'task_id':task,'kind':'updates'})
        path='/v1/taskdock/history?'+params
        body={**self.body,'expected_snapshot_id':snapshot['id']}
        first=self.client.post(path,json=body)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()['items'][0]['id'],'synthetic-update')
        get_path=path+'&'+urlencode({'snapshot_id':snapshot['id']})
        ReaderFactory.failure=TaskDockError('Synthetic history failure',409)
        self.assertEqual(self.client.post(path,json=body).status_code,502)
        with TestClient(create_app(self.engine)) as reopened:
            reopened.headers['Authorization']='Bearer '+self.second_token
            cached=reopened.get(get_path).json()
            self.assertEqual(cached['items'],first.json()['items'])
            from datetime import datetime
            self.assertEqual(datetime.fromisoformat(cached['read_at']),datetime.fromisoformat(first.json()['read_at']))
            reopened.headers['Authorization']='Bearer '+self.other_token
            self.assertEqual(reopened.get(get_path).status_code,404)
        self.assertNotIn(self.body['token'],first.text)

    def test_inflight_chat_fails_after_task_snapshot_changes(self):
        snapshot=self.pair()
        self.client.put('/v1/model',json={'base_url':'http://localhost:1234/v1','model':'synthetic'})
        conv=self.client.post('/v1/conversations',json={'title':'Synthetic'}).json()['id']
        path='/v1/conversations/'+conv+'/messages'
        FakeModel.entered=threading.Event();FakeModel.release=threading.Event()
        result=[]
        worker=threading.Thread(target=lambda:result.append(self.client.post(path,json={'text':'What is blocked?','request_id':str(uuid.uuid4())})))
        worker.start();self.assertTrue(FakeModel.entered.wait(3))
        self.assertEqual(self.refresh(expected_snapshot_id=snapshot['id']).status_code,200)
        FakeModel.release.set();worker.join(5)
        self.assertEqual(result[0].json()['status'],'failed')

    def test_aged_snapshot_is_stale_and_remote_and_empty_token_never_called(self):
        snapshot=self.pair()
        with self.factory() as session:
            session.get(TaskDockSnapshot,snapshot['id']).fetched_at=now()-timedelta(hours=1);session.commit()
        self.assertTrue(self.client.get('/v1/taskdock').json()['snapshot']['stale'])
        ReaderFactory.calls=[]
        for extra in ({'base_url':'https://example.com'}, {'token':''}):
            response=self.refresh(expected_snapshot_id=snapshot['id'],**extra)
            self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(ReaderFactory.calls,[])
        self.assertEqual(self.client.post('/v1/taskdock/refresh',json=self.body,headers={'Authorization':'Bearer invalid'}).status_code,401)


for name in list(vars(memory_tests.MemoryTests)):
    if name.startswith('test_') and name not in TaskDockAPITests.__dict__:
        setattr(TaskDockAPITests,name,None)
