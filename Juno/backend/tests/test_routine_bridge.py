"""Real HTTP bridge against disposable TaskDock SQLite and Juno PostgreSQL."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from juno.models import RoutineOccurrenceRecord, RecurringRoutine
from test_memory_api import MemoryTests

TASKDOCK=Path(os.environ.get('JUNO_TASKDOCK_CHECKOUT',str(Path(__file__).resolve().parents[3]/'TaskDock'))).expanduser()
PYTHON=Path(os.environ.get('JUNO_TASKDOCK_PYTHON',str(TASKDOCK/'.venv/bin/python'))).expanduser()

class RoutineBridgeTests(MemoryTests):
    def setUp(self):
        super().setUp()
        if not TASKDOCK.exists() or not PYTHON.exists():self.skipTest('Set JUNO_TASKDOCK_CHECKOUT and JUNO_TASKDOCK_PYTHON for the optional real-HTTP bridge tests')
        self.tmp=tempfile.TemporaryDirectory(prefix='juno-taskdock-bridge-')
        self.addCleanup(self.tmp.cleanup)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        self.base=f'http://127.0.0.1:{port}'
        env={**os.environ,'PYTHONPATH':str(TASKDOCK/'api'),'UNIFIED_API_TOKEN':'synthetic-owner-only','TASKDOCK_DATA_ROOT':self.tmp.name}
        script="from unified_tasks.main import create_app; import uvicorn, os; os.environ['UNIFIED_API_TOKEN']='synthetic-owner-only'; uvicorn.run(create_app(%r,mode='disabled'),host='127.0.0.1',port=%d,log_level='critical')"%(str(Path(self.tmp.name)/'tasks.db'),port)
        self.server=subprocess.Popen([str(PYTHON),'-c',script],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        self.addCleanup(self.stop_server)
        self.remote=httpx.Client(base_url=self.base,headers={'Authorization':'Bearer synthetic-owner-only'},trust_env=False,timeout=10)
        self.addCleanup(self.remote.close)
        for attempt in range(100):
            try:
                response=self.remote.get('/workspace/integrations/juno/writes')
                if response.status_code==200:break
            except httpx.TransportError:pass
            if self.server.poll() is not None:self.fail(self.server.stderr.read().decode()[-3000:])
            time.sleep(.05)
        else:self.fail('Disposable TaskDock did not become ready: '+str(response.status_code)+' '+response.text[:500])
        state=self.remote.get('/workspace/integrations/juno/writes').json()
        target={k:state[k] for k in ('instance_id','workspace_id')}
        column=self.remote.post('/workspace/integrations/juno/writes/columns',json={**target,'operation_id':str(uuid4()),'name':'Juno','approved':True})
        self.assertEqual(column.status_code,200,column.text)
        grant=self.remote.post('/workspace/integrations/juno/writes/grants',json={**target,'column_id':column.json()['column_id'],'allowed_assignees':[],'approved':True})
        self.assertEqual(grant.status_code,200,grant.text)
        self.grant=grant.json()
        self.credential={'base_url':self.base,'token':self.grant['token']}
        self.client.close();self.client=TestClient(self.app,client=('127.0.0.1',49000))
        self.client.headers['Authorization']='Bearer '+self.token

    def stop_server(self):
        self.server.terminate()
        try:self.server.wait(timeout=5)
        except subprocess.TimeoutExpired:self.server.kill();self.server.wait()
        self.server.stderr.close()

    def connect(self):
        probe=self.client.post('/v1/recurring/probe',json=self.credential)
        self.assertEqual(probe.status_code,200,probe.text)
        info=probe.json()
        state=self.client.get('/v1/recurring/connection').json()
        r=self.client.post('/v1/recurring/connection',json={**self.credential,'expected_revision':state['revision'],
            'expected_scope':{k:info[k] for k in ('instance_id','workspace_id','column_id','grant_id','owner_id')},'approved':True})
        self.assertEqual(r.status_code,200,r.text)

    def routine(self, future=True):
        # Future schedule review, then advance both application clocks to that date.
        self.at=datetime.now(timezone.utc)+timedelta(days=2 if future else 0)
        day=self.at.astimezone(__import__('zoneinfo').ZoneInfo('America/Chicago')).date()
        r=self.client.post('/v1/recurring',json={'request_id':str(uuid4()),'title':'Synthetic integration check',
            'description':'Disposable test only','frequency':'daily','start_date':str(day),'end_date':str(day),'creation_time':'00:00'})
        self.assertEqual(r.status_code,201,r.text)
        return r.json()

    def decision(self,row):
        return {**self.credential,'expected_revision':row['revision'],'expected_updated_at':row['updated_at']}

    def approve(self,row):
        preview=self.client.post('/v1/recurring/'+row['id']+'/approval-preview',json=self.decision(row))
        self.assertEqual(preview.status_code,200,preview.text)
        denied=self.client.post('/v1/recurring/'+row['id']+'/activate',json=self.decision(row))
        self.assertEqual(denied.status_code,409,denied.text)
        r=self.remote.post('/workspace/integrations/juno/writes/previews/'+preview.json()['preview_id']+'/approve',json={'approved':True,'routine':True})
        self.assertEqual(r.status_code,200,r.text)
        r=self.client.post('/v1/recurring/'+row['id']+'/activate',json=self.decision(row))
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def tick(self):
        # TaskDock uses its own clock: patch its due check through a small clock
        # offset is deliberately avoided. Dates are adjusted to today below.
        with patch('juno.routine_api.now',return_value=self.at):
            return self.client.post('/v1/recurring/tick',json=self.credential)

    def test_review_due_creation_and_duplicate_readback(self):
        self.connect();row=self.approve(self.routine())
        # Delivery before remote due time must fail closed, not create early.
        r=self.tick();self.assertEqual(r.status_code,200,r.text)
        with self.factory() as s:
            saved=s.scalar(select(RoutineOccurrenceRecord).where(RoutineOccurrenceRecord.routine_id==row['id']))
            self.assertIsNotNone(saved)
            self.assertIsNone(saved.task_id)
        # No real tasks may appear before the approved occurrence date.
        result=self.remote.get('/workspace/tasks').json()
        self.assertNotIn('Synthetic integration check',str(result))

    def test_revoked_grant_pauses_and_browser_administration_is_blocked(self):
        self.connect();row=self.approve(self.routine())
        self.assertEqual(self.remote.delete('/workspace/integrations/juno/writes/grants/'+self.grant['grant_id']).status_code,200)
        r=self.tick();self.assertEqual(r.status_code,403,r.text)
        with self.factory() as s:self.assertEqual(s.get(RecurringRoutine,row['id']).status,'paused')
        self.assertFalse(self.client.get('/v1/recurring/connection').json()['connection']['enabled'])
        self.assertEqual(self.client.post('/v1/recurring/probe',json=self.credential,headers={'Origin':'https://untrusted.example'}).status_code,403)

    def test_due_creation_and_replayed_tick_keep_one_task(self):
        self.connect();row=self.approve(self.routine(future=False))
        # Activation is now; advance the host tick just after activation.
        self.at=datetime.now(timezone.utc)+timedelta(seconds=2)
        first=self.tick();self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()['items'][0]['status'],'created',first.text)
        second=self.tick();self.assertEqual(second.status_code,200,second.text)
        with self.factory() as session:
            rows=session.scalars(select(RoutineOccurrenceRecord).where(RoutineOccurrenceRecord.routine_id==row['id'])).all()
            self.assertEqual(len(rows),1);self.assertIsNotNone(rows[0].task_id)
        from sqlite3 import connect
        from contextlib import closing
        with closing(connect(str(Path(self.tmp.name)/'tasks.db'))) as db:
            self.assertEqual(db.execute('select count(*) from workspace_native').fetchone()[0],1)

    def test_lost_http_reply_reconciles_committed_occurrence(self):
        from juno.routine_writer import Writer
        self.connect();row=self.approve(self.routine(future=False))
        self.at=datetime.now(timezone.utc)+timedelta(seconds=2)
        original=Writer.request
        lost=[False]
        def request(writer,method,path,body=None):
            result=original(writer,method,path,body)
            if method=='POST' and path=='/tasks' and not lost[0]:
                lost[0]=True
                raise TimeoutError('Synthetic lost HTTP reply after TaskDock committed')
            return result
        with patch.object(Writer,'request',request):
            first=self.tick()
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()['items'][0]['status'],'unknown',first.text)
        second=self.tick();self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(second.json()['items'][0]['status'],'created',second.text)
        from sqlite3 import connect
        from contextlib import closing
        with closing(connect(str(Path(self.tmp.name)/'tasks.db'))) as db:
            self.assertEqual(db.execute('select count(*) from workspace_native').fetchone()[0],1)
