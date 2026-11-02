"""Isolated worker/owner authorization and transactional review tests; no real staff."""
import os,unittest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select,func
import test_memory_api as memory_tests
from juno.api import create_app
from juno.auth import digest,provision
from juno.models import WorkerPortal,Worker,WorkerReport,WorkerInvitation,WorkerSession,WorkerGrant,ScheduleState,TaskDockSnapshot,TaskDockState,PlanningState,now
from juno.worker_host import WorkerBoundary
from juno.taskdock_api import restrict_copies


class FakeHost:
    def __init__(self):self.running=False
    def readiness(self):return {'ready':True,'address':'https://localhost','reason':'Synthetic HTTPS test only'}
    def status(self):return {**self.readiness(),'running':self.running,'error':None}
    def start(self):self.running=True
    def close(self):self.running=False


@unittest.skipUnless(os.environ.get('JUNO_TEST_ADMIN_URL'),'Set JUNO_TEST_ADMIN_URL for isolated PostgreSQL tests')
class WorkerTests(unittest.TestCase):
    setUpClass=classmethod(memory_tests.MemoryTests.setUpClass.__func__)
    tearDownClass=classmethod(memory_tests.MemoryTests.tearDownClass.__func__)
    def setUp(self):
        memory_tests.MemoryTests.setUp(self);self.client.close();self.host=FakeHost();self.app=create_app(self.engine,worker_manager=self.host);self.client=TestClient(self.app);self.client.headers['Authorization']='Bearer '+self.token
        self.portal=TestClient(WorkerBoundary(self.app),base_url='https://localhost',client=('127.0.0.1',51000));self.portal.headers['Origin']='https://localhost'
        with self.factory() as s:
            s.add(ScheduleState(owner_id=self.actor.owner_id,data={'people':[{'name':'Synthetic Alex'},{'name':'Synthetic Pat'}],'rules':[],'exceptions':[],'reservations':[]},revision=1))
            row=TaskDockSnapshot(owner_id=self.actor.owner_id,origin='http://127.0.0.1:18114',info={'workspace_id':'worker-test','device_id':'test','definitions':{},'sharing_version':1,'sharing':{'channels':['title','dates'],'planning_fields':['room','issue_description']}},items=[{'id':'task-1','title':'Synthetic repair','due_date':'2026-11-09','planning_details':{'room':{'state':'provided','value':'ARTS 121'},'issue_description':{'state':'provided','value':'Fictional issue'}}},{'id':'task-2','title':'Private other task'}],sources=[],snapshot='test',fetched_at=now());s.add(row);s.flush();self.snapshot=row.id;s.add(TaskDockState(owner_id=self.actor.owner_id,active_id=row.id));s.commit()
        self.worker=self.client.post('/v1/workers',json={'name':'Synthetic Alex'}).json()['id'];self.pat=self.client.post('/v1/workers',json={'name':'Synthetic Pat'}).json()['id']
    def tearDown(self):self.portal.close();self.client.close()
    def enable(self):
        r=self.client.put('/v1/workers/settings',json={'enabled':True});self.assertEqual(r.status_code,200,r.text)
    def enroll(self,worker=None,portal=None):
        portal=portal or self.portal;r=self.client.post('/v1/workers/'+(worker or self.worker)+'/invitations');self.assertEqual(r.status_code,200,r.text)
        secret=r.json()['url'].split('#invite=')[1];r=portal.post('/worker/api/enroll',json={'invitation':secret});self.assertEqual(r.status_code,200,r.text);portal.headers['x-juno-csrf']=r.json()['csrf'];return secret
    def grant(self,worker=None):
        value={'worker_id':worker or self.worker,'task_id':'task-1','expected_snapshot_id':self.snapshot,'fields':['title','room'],'instructions':'Only synthetic work.'}
        r=self.client.post('/v1/workers/grants',json=value);self.assertEqual(r.status_code,201,r.text);return r.json()['id']
    def payload(self,grant=None,key='synthetic-key-123456'):
        return {'request_key':key,'kind':'task' if grant else 'unexpected','grant_id':grant,'work_date':str(now().astimezone(__import__('zoneinfo').ZoneInfo('America/Chicago')).date()),'text':'Synthetic troubleshooting complete.','status':'reported_complete','actual_minutes':25,'remaining_minutes':15,'blocker_state':'none','handoff':'Check fictional cable.'}
    def report(self,grant=None,key='synthetic-key-123456'):
        r=self.portal.post('/worker/api/reports',json=self.payload(grant,key));self.assertEqual(r.status_code,201,r.text);return r.json()['id']
    def test_disabled_default_and_certificate_gate(self):
        data=self.client.get('/v1/workers').json();self.assertFalse(data['enabled']);self.assertEqual(data['reports'],[])
        self.assertEqual(self.client.post('/v1/workers/'+self.worker+'/invitations').status_code,403)
        app=create_app(self.engine);c=TestClient(app);c.headers['Authorization']='Bearer '+self.token
        self.assertEqual(c.put('/v1/workers/settings',json={'enabled':True}).status_code,409);c.close()
        self.assertEqual(self.client.post('/v1/workers',json={'name':'Unknown staff'}).status_code,422)
    def test_role_and_transport_separation(self):
        self.enable();self.enroll()
        for path in ['/v1/workers','/v1/memories','/v1/host','/v1/cache','/v1/pair','/docs','/health']:
            self.assertEqual(self.portal.get(path).status_code,403,path)
        self.assertEqual(self.client.get('/worker').status_code,403)
        self.assertEqual(self.portal.get('/worker/api/me').status_code,200)
        with self.factory() as s:session=s.scalar(select(WorkerSession).where(WorkerSession.worker_id==self.worker));self.assertIsNotNone(session)
        raw=self.portal.cookies.get('__Host-juno-worker');self.assertEqual(self.client.get('/v1/memories',headers={'Authorization':'Bearer '+raw}).status_code,401)
        self.assertEqual(self.portal.get('/worker/api/me',headers={'Authorization':'Bearer '+self.token,'Cookie':''}).status_code,401)
        http=TestClient(WorkerBoundary(self.app),base_url='http://localhost',client=('127.0.0.1',1));self.assertEqual(http.get('/worker').status_code,403);http.close()
    def test_identity_task_owner_isolation_and_minimal_excerpt(self):
        self.enable();self.enroll();g=self.grant();items=self.portal.get('/worker/api/tasks').json()['items'];self.assertEqual(len(items),1);self.assertEqual(set(items[0]['excerpt']),{'title','room','instructions'});self.assertNotIn('Fictional issue',str(items))
        pg=self.grant(self.pat);self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(pg)).status_code,403)
        self.assertEqual(self.client.get('/v1/workers',headers={'Authorization':'Bearer '+self.other_token}).json()['workers'],[])
        self.assertEqual(self.client.post('/v1/workers/'+self.worker+'/revoke',headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
        self.assertEqual(self.portal.get('/worker/api/receipts').json()['items'],[])
        self.assertEqual(self.client.post('/v1/workers/grants',json={'worker_id':self.worker,'task_id':'task-2','expected_snapshot_id':self.snapshot,'fields':['contact']}).status_code,422)
        with self.factory() as s:
            s.add(PlanningState(owner_id=self.actor.owner_id,data={'workspace_id':'worker-test','tasks':[{'task_id':'task-1','room':'Juno confirmed room'}]},revision=1));s.commit()
        preview={'worker_id':self.worker,'task_id':'task-1','expected_snapshot_id':self.snapshot,'fields':['room']}
        self.assertEqual(self.client.post('/v1/workers/grants/preview',json=preview).json()['excerpt']['room'],'Juno confirmed room')
        with self.factory() as s:
            p=s.get(PlanningState,self.actor.owner_id);p.data={**p.data,'workspace_id':'other-workspace'};s.commit()
        self.assertEqual(self.client.post('/v1/workers/grants/preview',json=preview).json()['excerpt']['room'],'ARTS 121')

    def test_worker_network_is_ten_slash_eight_only(self):
        for address,expected in [('10.0.0.1',200),('10.3.66.50',200),('10.255.255.254',200),('192.168.1.20',403),('172.16.0.1',403),('8.8.8.8',403),('fc00::1',403),('fe80::1',403)]:
            with TestClient(WorkerBoundary(self.app),base_url='https://localhost',client=(address,51000)) as client:
                self.assertEqual(client.get('/worker',headers={'X-Forwarded-For':'10.3.66.50'}).status_code,expected,address)

    def test_one_use_expiry_and_revocation(self):
        self.enable();secret=self.enroll();self.assertEqual(self.portal.post('/worker/api/enroll',json={'invitation':secret}).status_code,401)
        self.client.post('/v1/workers/'+self.worker+'/revoke');self.assertEqual(self.portal.get('/worker/api/tasks').status_code,401)
        self.assertEqual(self.client.post('/v1/workers/'+self.worker+'/invitations').status_code,409)
        secret=self.enroll(self.pat)
        with self.factory() as s:
            row=s.scalar(select(WorkerSession).where(WorkerSession.worker_id==self.pat));row.expires_at=now()-timedelta(seconds=1);s.commit()
        self.assertEqual(self.portal.get('/worker/api/me').status_code,401)
    def test_csrf_size_rate_limits_and_safe_assets(self):
        self.enable();self.enroll()
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(),headers={'Origin':'https://evil.invalid'}).status_code,403)
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(),headers={'x-juno-csrf':'wrong'}).status_code,403)
        self.assertEqual(self.portal.post('/worker/api/reports',content='x'*33000).status_code,413)
        page=self.portal.get('/worker');self.assertEqual(page.status_code,200);self.assertIn("frame-ancestors 'none'",page.headers['content-security-policy']);self.assertEqual(page.headers['cache-control'],'no-store')
        js=self.portal.get('/worker/app.js').text;self.assertNotIn('innerHTML',js);self.assertNotIn('localStorage',js)
        for _ in range(65):r=self.portal.post('/worker/api/enroll',json={'invitation':'invalid'})
        self.assertEqual(r.status_code,429)
    def test_idempotent_retry_and_correction(self):
        self.enable();self.enroll();g=self.grant();identity=self.report(g)
        retry=self.portal.post('/worker/api/reports',json=self.payload(g));self.assertEqual(retry.json()['id'],identity);self.assertTrue(retry.json()['duplicate'])
        changed=self.payload(g);changed['text']='Different';self.assertEqual(self.portal.post('/worker/api/reports',json=changed).status_code,409)
        correction=self.payload(g,'correction-key-123456');correction['correction_of']=identity;correction['text']='Correction';r=self.portal.post('/worker/api/reports',json=correction);self.assertEqual(r.status_code,201)
        reports=self.client.get('/v1/workers').json()['reports'];self.assertEqual(len(reports),2);self.assertEqual(reports[0]['correction_of'],identity)
        attack=self.payload(None,'other-key-1234567');attack['correction_of']=identity;self.assertEqual(self.portal.post('/worker/api/reports',json=attack).status_code,409)
    def test_shift_unexpected_and_validation(self):
        self.enable();self.enroll();self.report()
        value=self.payload(None,'shift-key-12345678');value['kind']='shift';self.assertEqual(self.portal.post('/worker/api/reports',json=value).status_code,201)
        value['request_key']='invalid-key-12345';value['actual_minutes']=-1;self.assertEqual(self.portal.post('/worker/api/reports',json=value).status_code,422)
        self.assertEqual(len(self.portal.get('/worker/api/receipts').json()['items']),2)
    def test_grant_expiration_disable_and_policy_withdrawal(self):
        self.enable();self.enroll();g=self.grant();self.report(g)
        with self.factory() as s:restrict_copies(s,self.actor.owner_id,'http://127.0.0.1:18114','Synthetic withdrawal');s.commit()
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(g,'new-key-12345678')).status_code,403)
        report=self.client.get('/v1/workers').json()['reports'][0];self.assertEqual(report['shared_excerpt'],{});self.assertEqual(report['data']['text'],'Synthetic troubleshooting complete.')
        self.client.put('/v1/workers/settings',json={'enabled':False});self.enable();self.assertEqual(self.portal.get('/worker/api/me').status_code,401)
    def test_review_selective_apply_conflict_and_no_double_time(self):
        self.enable();self.enroll();g=self.grant();identity=self.report(g)
        value={'expected_revision':1,'expected_planning_revision':99,'fields':['actual_minutes']};self.assertEqual(self.client.post('/v1/workers/reports/'+identity+'/apply',json=value).status_code,409)
        value['expected_planning_revision']=0;r=self.client.post('/v1/workers/reports/'+identity+'/apply',json=value);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['revision'],2)
        plan=self.client.get('/v1/planning').json();self.assertEqual(plan['tasks'][0]['actual_minutes'],25);self.assertFalse(plan['tasks'][0]['independent'])
        value.update(expected_revision=2,expected_planning_revision=1);self.assertEqual(self.client.post('/v1/workers/reports/'+identity+'/apply',json=value).status_code,409)
        self.assertEqual(self.client.post('/v1/workers/reports/'+identity+'/review',json={'expected_revision':1,'outcome':'completion_verified'}).status_code,409)
        r=self.client.post('/v1/workers/reports/'+identity+'/review',json={'expected_revision':2,'outcome':'completion_verified','note':'Private synthetic supervisor note'});self.assertEqual(r.status_code,200)
        self.assertNotIn('Private synthetic supervisor note',str(self.portal.get('/worker/api/receipts').json()))
        self.assertEqual(self.client.delete('/v1/workers/reports/'+identity+'?expected_revision=3',headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
        self.assertEqual(self.client.delete('/v1/workers/reports/'+identity+'?expected_revision=2').status_code,409)
        self.assertEqual(self.client.delete('/v1/workers/reports/'+identity+'?expected_revision=3').status_code,204)
        self.assertEqual(self.portal.get('/worker/api/receipts').json()['items'],[])
        with self.factory() as s:self.assertEqual(len(s.get(TaskDockSnapshot,self.snapshot).items),2);self.assertEqual(s.get(TaskDockSnapshot,self.snapshot).items[0]['title'],'Synthetic repair')
    def test_reshare_replaces_old_grant_and_unknown_does_not_clear(self):
        self.enable();self.enroll();first=self.grant();second=self.grant()
        tasks=self.portal.get('/worker/api/tasks').json()['items'];self.assertEqual([t['id'] for t in tasks],[second])
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(first)).status_code,403)
        payload=self.payload(second);payload['blocker_state']='unknown';payload['remaining_minutes']=0
        identity=self.portal.post('/worker/api/reports',json=payload).json()['id']
        for field in ('blocker','minutes'):
            response=self.client.post('/v1/workers/reports/'+identity+'/apply',json={'expected_revision':1,'expected_planning_revision':0,'fields':[field]});self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.client.get('/v1/planning').json()['revision'],0)

    def repair_review(self,identity,revision=1,verified=True,complete=True,room="ARTS 121"):
        repair={'room':room,'equipment':'Synthetic printer','category':'printer','summary':'Repeated synthetic paper-feed repair','complete_effort':complete}
        r=self.client.post('/v1/workers/reports/'+identity+'/review',json={'expected_revision':revision,'outcome':'completion_verified' if verified else 'reviewed','repair':repair});self.assertEqual(r.status_code,200,r.text);return r.json()

    def test_reviewed_repair_history_calibrates_estimates_and_chat(self):
        self.enable();self.enroll()
        with self.factory() as s:
            task=s.get(TaskDockSnapshot,self.snapshot);task.items=[{**task.items[0],'title':'Synthetic printer problem'},task.items[1]];s.commit()
        for index,minutes in enumerate((60,90,120)):
            payload=self.payload(None,'history-key-000000'+str(index));payload['actual_minutes']=minutes
            identity=self.portal.post('/worker/api/reports',json=payload).json()['id'];self.repair_review(identity,room='A121' if index==1 else 'ARTS 121')
        history=self.client.get('/v1/workers/repair-history').json();self.assertEqual(history['reviewed_reports'],3);group=history['groups'][0];self.assertEqual(group['time_samples'],3);self.assertEqual(group['duration']['minimum'],65);self.assertEqual(group['duration']['maximum'],135)
        estimate=self.client.post('/v1/planning/estimate',json={'task_id':'task-1','model_assist':False}).json();self.assertEqual(estimate['source'],'verified repair reports');self.assertEqual(estimate['repair_samples'],3)
        from juno.companion import context_for,refs_current
        with self.factory() as s:
            context,refs=context_for(s,self.actor.owner_id,'What did we try on the printer?',[]);repair=next(c for c in context if c['source'].startswith('worker_history:'));self.assertEqual(len(repair['reports']),3);self.assertTrue(refs_current(s,self.actor.owner_id,refs))
        self.client.delete('/v1/workers/reports/'+identity+'?expected_revision=2')
        with self.factory() as s:self.assertFalse(refs_current(s,self.actor.owner_id,refs))
        self.assertEqual(self.client.get('/v1/workers/repair-history',headers={'Authorization':'Bearer '+self.other_token}).json()['groups'],[])

    def test_model_estimate_rechecks_history_after_a_changed_review(self):
        import json
        self.enable();self.enroll();ids=[]
        with self.factory() as s:
            snapshot=s.get(TaskDockSnapshot,self.snapshot);snapshot.items=[{**snapshot.items[0],'title':'Synthetic printer problem'},snapshot.items[1]];s.commit()
        for index in range(3):
            identity=self.report(None,'model-history-key-'+str(index));self.repair_review(identity);ids.append(identity)
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic'})
        outer=self
        class ChangedHistoryModel:
            def __init__(self,origin):pass
            def complete(self,messages,model):
                changed=outer.client.post('/v1/workers/reports/'+ids[0]+'/review',json={'expected_revision':2,'outcome':'reviewed','repair':None});outer.assertEqual(changed.status_code,200)
                return json.dumps({'minimum':10,'maximum':20,'reason':'Synthetic result','question':'Scope?'})
        with TestClient(create_app(self.engine,model_factory=ChangedHistoryModel)) as client:
            client.headers['Authorization']='Bearer '+self.token
            result=client.post('/v1/planning/estimate',json={'task_id':'task-1'})
            self.assertEqual(result.status_code,409,result.text)

    def test_repair_samples_exclude_partial_duplicate_current_and_corrected_work(self):
        self.enable();self.enroll();grant=self.grant()
        first=self.report(grant,'linked-history-0001');self.repair_review(first)
        second=self.report(grant,'linked-history-0002');self.repair_review(second)
        partial=self.report(None,'partial-history-001');self.repair_review(partial,complete=False)
        history=self.client.get('/v1/workers/repair-history').json();self.assertEqual(history['groups'][0]['time_samples'],1);self.assertIsNone(history['groups'][0]['duration'])
        from juno.repair_history import comparable
        with self.factory() as s:self.assertEqual(comparable(s,self.actor.owner_id,'printer','worker-test','task-1'),[])
        correction=self.payload(grant,'history-correction01');correction['correction_of']=second;identity=self.portal.post('/worker/api/reports',json=correction).json()['id']
        # The corrected report stops being used immediately; the new one waits for review.
        context=self.client.get('/v1/workers/repair-history').json();self.assertEqual(context['reviewed_reports'],2)
        self.repair_review(identity)
        self.assertEqual(self.client.get('/v1/workers/repair-history').json()['groups'][0]['time_samples'],1)
        cleared=self.client.post('/v1/workers/reports/'+identity+'/review',json={'expected_revision':2,'outcome':'reviewed','repair':None});self.assertEqual(cleared.status_code,200)
        self.assertEqual(cleared.json()['repair_context'],{})

    def test_reports_are_retained_indefinitely(self):
        self.enable();self.enroll();identity=self.report()
        with self.factory() as s:row=s.get(WorkerReport,identity);row.submitted_at=now()-timedelta(days=3650);s.commit()
        data=self.client.get('/v1/workers').json();self.assertEqual(len(data['reports']),1);self.assertEqual(len(data['workers']),2);self.assertEqual(data['retention_days'],0)
        self.assertEqual(len(self.portal.get('/worker/api/receipts').json()['items']),1)



    def assignment(self,owner,channels=None):
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot)
            row.info={**row.info,'sharing':{'channels':channels or ['title','assignment','description','dates','custom_fields','priority'],'planning_fields':['room','issue_description','equipment','blockers']}}
            row.items=[{**row.items[0],'owner':owner,'description':'Fictional full instructions','custom_values':{'asset':'test asset'},'planning_details':{**row.items[0]['planning_details'],'equipment':{'state':'provided','value':'Synthetic printer'},'blockers':{'state':'none'}}},row.items[1]]
            s.commit()

    def test_taskdock_assignment_controls_access_and_stale_submission(self):
        self.enable();self.enroll();self.assignment('Synthetic Alex')
        items=self.portal.get('/worker/api/tasks').json()['items'];self.assertEqual(len(items),1)
        grant=items[0];self.assertEqual(grant['mode'],'assigned');self.assertIsNone(grant['expires_at'])
        self.assertEqual(grant['excerpt']['description'],'Fictional full instructions')
        self.assertEqual(grant['excerpt']['equipment'],'Synthetic printer');self.assertEqual(grant['excerpt']['blockers'],'Explicitly none')
        report=self.report(grant['id'])
        self.assignment('Synthetic Pat')
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(grant['id'],'after-reassign-123456')).status_code,403)
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])
        self.assertEqual(self.client.get('/v1/workers/reports/'+report).status_code,200)
        self.enroll(self.pat);items=self.portal.get('/worker/api/tasks').json()['items'];self.assertEqual(len(items),1)
        self.assertNotEqual(items[0]['id'],grant['id'])
        self.assertEqual(self.client.post('/v1/workers/grants/'+items[0]['id']+'/revoke').status_code,409)

    def test_one_time_stable_identity_mapping_and_owner_isolation(self):
        self.enable();self.enroll();self.assignment({'id':'student-42','name':'Synthetic Alex','email':'alex@example.invalid'})
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])
        overview=self.client.get('/v1/workers').json();key=overview['assignment_options'][0]['key'];self.assertEqual(__import__('json').loads(key),['worker-test','id:student-42'])
        path='/v1/workers/'+self.worker+'/assignment'
        self.assertEqual(self.client.put(path,json={'key':key},headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
        self.assertEqual(self.client.put(path,json={'key':'id:missing'}).status_code,409)
        self.assertEqual(self.client.put(path,json={'key':key}).status_code,200)
        self.assertEqual(len(self.portal.get('/worker/api/tasks').json()['items']),1)
        self.assertEqual(self.client.put('/v1/workers/'+self.pat+'/assignment',json={'key':key}).status_code,409)
        self.assertEqual(self.client.put(path,json={'key':''}).status_code,200)
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])

    def test_assignment_scope_and_ambiguous_names_fail_closed(self):
        self.enable();self.enroll();self.assignment('Synthetic Alex',channels=['title'])
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])
        self.assignment('Synthetic Alex')
        with self.factory() as s:
            s.add(Worker(owner_id=self.actor.owner_id,name='synthetic alex'));s.commit()
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])

    def test_complete_details_dynamic_but_legacy_shares_remain_limited(self):
        self.enable();self.enroll();self.assignment('No registered worker')
        value={'worker_id':self.worker,'task_id':'task-1','expected_snapshot_id':self.snapshot,'include_all':True}
        preview=self.client.post('/v1/workers/grants/preview',json=value);self.assertEqual(preview.status_code,200,preview.text)
        self.assertIn('custom_values',preview.json()['excerpt'])
        r=self.client.post('/v1/workers/grants',json=value);self.assertEqual(r.status_code,201,r.text)
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot);row.items=[{**row.items[0],'description':'Updated instructions','secret_provider_token':'Never share'},row.items[1]];s.commit()
        excerpt=self.portal.get('/worker/api/tasks').json()['items'][0]['excerpt']
        self.assertEqual(excerpt['description'],'Updated instructions');self.assertNotIn('secret_provider_token',excerpt)
        self.assignment('No registered worker',channels=['title'])
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])

    def test_assignment_mapping_is_workspace_bound_and_missing_task_revokes(self):
        self.enable();self.enroll();self.assignment({'id':'student-42','name':'Synthetic Alex'})
        key=self.client.get('/v1/workers').json()['assignment_options'][0]['key']
        self.client.put('/v1/workers/'+self.worker+'/assignment',json={'key':key})
        grant=self.portal.get('/worker/api/tasks').json()['items'][0]['id']
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot);row.info={**row.info,'workspace_id':'another-workspace'};s.commit()
        self.assertEqual(self.portal.get('/worker/api/tasks').json()['items'],[])
        with self.factory() as s:
            row=s.get(TaskDockSnapshot,self.snapshot);row.info={**row.info,'workspace_id':'worker-test'};row.items=[];s.commit()
        self.assertEqual(self.portal.post('/worker/api/reports',json=self.payload(grant)).status_code,403)
