"""Synthetic feeds, recurrence edge cases and real owner-scoped database boundaries."""
import json
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select
import test_memory_api as memory_tests
from juno.api import create_app
from juno.models import IntegrationSnapshot
from juno.integrations import BeaconReader, IntegrationError, calendar_events, schedule_events, busy_summary, beacon_feed
from juno.shared_host import LANBoundary
from test_companion import FakeModel

from pathlib import Path
FIXTURES=Path(__file__).parent/'fixtures'
FEED=json.loads((FIXTURES/'beacon-alerts.json').read_text())
ICS=(FIXTURES/'calendar.ics').read_text()
CSV=(FIXTURES/'semester-schedule.csv').read_text()

class ReaderTests(unittest.TestCase):
    def test_recurrence_exception_dst_cancellation_transparency_and_overlap(self):
        rows,details=calendar_events(ICS,'2026-10-26','2026-11-17','America/Chicago')
        meetings=[r for r in rows if 'meeting' in r['title']]
        self.assertEqual(len(meetings),4)
        self.assertIn('2026-10-26T14:00:00+00:00',[r['start'] for r in rows])
        self.assertIn('2026-11-09T17:00:00+00:00',[r['start'] for r in rows])
        self.assertIn('2026-11-16T15:00:00+00:00',[r['start'] for r in rows])
        self.assertFalse(any('Cancelled' in r['title'] for r in rows))
        summary=busy_summary(rows,'2026-10-26','2026-11-17','America/Chicago')
        self.assertEqual(summary[0]['busy_minutes'],90)
        self.assertFalse(any(r['date']=='2026-11-02' for r in summary))
        self.assertEqual(details['timezone'],'America/Chicago')

    def test_all_day_exclusive_end_and_floating_time(self):
        content='BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:day\nDTSTART;VALUE=DATE:20261029\nDTEND;VALUE=DATE:20261030\nSUMMARY:Fictional day\nEND:VEVENT\nBEGIN:VEVENT\nUID:float\nDTSTART:20261030T090000\nDTEND:20261030T100000\nEND:VEVENT\nEND:VCALENDAR\n'
        rows,_=calendar_events(content,'2026-10-29','2026-10-31','America/Chicago')
        self.assertEqual(len(rows),2)
        self.assertTrue(rows[0]['all_day']);self.assertEqual(rows[1]['start'],'2026-10-30T14:00:00+00:00')
        self.assertEqual(busy_summary(rows,'2026-10-29','2026-10-31','America/Chicago')[0]['busy_minutes'],1440)
        with self.assertRaises(IntegrationError):calendar_events(content.replace('20261030T090000','20261101T013000'),'2026-10-29','2026-11-03','America/Chicago')

    def test_unsupported_dense_rules_duplicates_and_invalid_windows_fail_closed(self):
        for content in [ICS.replace('FREQ=WEEKLY','FREQ=SECONDLY'),ICS.replace('UID:overlap','UID:transparent'),ICS.replace('DTSTART:20261026T143000Z','DTSTART;TZID=Made/Up:20261026T143000')]:
            with self.assertRaises(IntegrationError):calendar_events(content,'2026-10-26','2026-11-17','America/Chicago')
        for start,end,zone in [('2026-10-29','2026-10-29','America/Chicago'),('2026-01-01','2028-01-01','America/Chicago'),('2026-10-29','2026-11-01','Unknown/Zone')]:
            with self.assertRaises(IntegrationError):calendar_events(ICS,start,end,zone)

    def test_semester_rows_preserve_occupancy_and_staff_semantics_across_dst(self):
        rows,_=schedule_events(CSV,'2026-10-26','2026-11-17','America/Chicago')
        self.assertEqual(len(rows),12)
        self.assertEqual(sum(r['busy'] for r in rows),4)
        self.assertEqual({r['busy_minutes'] for r in busy_summary(rows,'2026-10-26','2026-11-17','America/Chicago')},{60})
        self.assertIn('2026-11-16T15:00:00+00:00',[r['start'] for r in rows if r['kind']=='classroom_busy'])
        for bad in [CSV.replace('MO,09:00,10:00','MO,10:00,09:00'),CSV+CSV.splitlines()[1]+'\n',CSV.replace('MO,','ZZ,'),CSV.replace('America/Chicago','Unknown/Zone')]:
            with self.assertRaises(IntegrationError):schedule_events(bad,'2026-10-26','2026-11-17','America/Chicago')

    def test_beacon_completeness_duplicates_nullable_observation_and_unknown_fields(self):
        rows,_=beacon_feed(FEED)
        self.assertEqual(rows[0]['observed_at'],'')
        for bad in [{**FEED,'complete':False},{**FEED,'total':2},{**FEED,'rows':FEED['rows']*2,'total':2},{**FEED,'generated_at':'unknown'},{**FEED,'rows':[{'id':'missing-fields'}]}]:
            with self.assertRaises(IntegrationError):beacon_feed(bad)
        extra={**FEED,'rows':[{**FEED['rows'][0],'api_key':'synthetic-excluded','url':'https://example.invalid/never-follow'}]}
        self.assertNotIn('synthetic-excluded',json.dumps(beacon_feed(extra)))

    def test_beacon_transport_fixed_get_no_redirect_and_sanitized_errors(self):
        calls=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append((self.path,self.headers.get('Authorization')))
                if len(calls)==1:
                    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(FEED).encode())
                else:
                    self.send_response(302);self.send_header('Location','http://127.0.0.1:1/do-not-follow');self.end_headers()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            reader=BeaconReader('http://127.0.0.1:'+str(server.server_port),'synthetic-key')
            self.assertEqual(len(reader.fetch()[0]),1)
            with self.assertRaisesRegex(IntegrationError,'302'):reader.fetch()
            self.assertEqual(calls,[('/api/alerts','Bearer synthetic-key')]*2)
        finally:server.shutdown();server.server_close();worker.join()
        for origin in ['http://10.3.66.50:12108','http://user:secret@localhost:12108','http://localhost:12108/path','http://localhost:12108?token=secret','https://example.com']:
            with self.assertRaises(IntegrationError):BeaconReader(origin,'synthetic-key')


class IntegrationAPITests(memory_tests.MemoryTests):
    def setUp(self):
        super().setUp();self.client.close();FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.app=create_app(self.engine,model_factory=FakeModel);self.client=TestClient(self.app);self.client.headers['Authorization']='Bearer '+self.token
    def import_source(self,kind='calendar',content=ICS,expected=None,headers=None):
        return self.client.post('/v1/integrations/import',json={'kind':kind,'content':content,'label':'synthetic.ics','start':'2026-10-26','end':'2026-11-17','timezone':'America/Chicago','expected_id':expected},headers=headers)

    def test_replace_error_retention_owner_cache_boundary_and_delete(self):
        first=self.import_source();self.assertEqual(first.status_code,200,first.text);identity=first.json()['id']
        self.assertEqual(self.import_source().status_code,409)
        bad=self.import_source(content=ICS.replace('FREQ=WEEKLY','FREQ=SECONDLY'),expected=identity)
        self.assertEqual(bad.status_code,422)
        state=self.client.get('/v1/integrations').json()['items'][0]
        self.assertEqual(state['id'],identity);self.assertEqual(state['count'],5);self.assertTrue(state['error'])
        self.assertEqual(self.client.get('/v1/integrations',headers={'Authorization':'Bearer '+self.other_token}).json()['items'],[])
        pages=self.client.get('/v1/cache').json()['pages']
        self.assertTrue(next(p['body'] for p in pages if p['path']=='/v1/integrations')['items'])
        with TestClient(LANBoundary(self.app),client=('192.168.1.9',55000)) as lan:
            lan.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(lan.get('/v1/integrations').status_code,200)
            for path in ['/v1/integrations/import','/v1/integrations/beacon/refresh']:
                self.assertEqual(lan.post(path,json={}).status_code,403)
        self.assertEqual(self.client.delete('/v1/integrations/calendar',params={'expected_id':identity},headers={'Authorization':'Bearer '+self.other_token}).status_code,409)
        self.assertEqual(self.client.delete('/v1/integrations/calendar',params={'expected_id':identity}).status_code,200)
        self.assertEqual(self.client.get('/v1/integrations').json()['items'],[])

    def test_context_is_dated_untrusted_bounded_and_invalidated_on_replace(self):
        first=self.import_source('beacon',json.dumps(FEED));self.assertEqual(first.status_code,200,first.text)
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic-model'})
        conv=self.client.post('/v1/conversations',json={'title':'Fictional integration chat'}).json()['id'];path='/v1/conversations/'+conv+'/messages'
        import uuid
        self.assertEqual(self.client.post(path,json={'request_id':str(uuid.uuid4()),'text':'What printer issue needs attention?'}).status_code,200)
        self.assertIn('Paper refill needed',str(FakeModel.calls[-1]));self.assertIn('untrusted',str(FakeModel.calls[-1]))
        self.assertEqual(self.client.delete('/v1/integrations/beacon',params={'expected_id':first.json()['id']}).status_code,200)
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')
        self.client.post(path,json={'request_id':str(uuid.uuid4()),'text':'What issue now?'})
        self.assertNotIn('Paper refill needed',str(FakeModel.calls[-1]))
        with self.factory() as session:self.assertEqual(session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==self.actor.owner_id)).all(),[])

    def test_inflight_reply_is_rejected_if_source_changes(self):
        first=self.import_source('beacon',json.dumps(FEED)).json()
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic-model'})
        conv=self.client.post('/v1/conversations',json={'title':'Fictional inflight test'}).json()['id'];path='/v1/conversations/'+conv+'/messages'
        FakeModel.entered=threading.Event();FakeModel.release=threading.Event();result=[]
        import uuid
        worker=threading.Thread(target=lambda:result.append(self.client.post(path,json={'request_id':str(uuid.uuid4()),'text':'What printer issue?'})))
        worker.start();self.assertTrue(FakeModel.entered.wait(3))
        with TestClient(self.app) as other:
            other.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(other.delete('/v1/integrations/beacon',params={'expected_id':first['id']}).status_code,200)
        FakeModel.release.set();worker.join(timeout=5)
        self.assertEqual(result[0].json()['status'],'failed')
        self.assertNotIn('Synthetic answer',self.client.get(path).text)

    def test_beacon_credentials_not_persisted_and_failure_keeps_snapshot(self):
        class Reader:
            origin='http://127.0.0.1:12108'
            failure=False
            def __init__(self,*args):pass
            def fetch(self):
                if self.failure:raise IntegrationError('Synthetic unavailable')
                return beacon_feed(FEED)
        with patch('juno.integrations_api.BeaconReader',Reader):
            # install's default factory is already bound: replace this app's route with a fresh injected app below.
            from juno import integrations_api
            original=integrations_api.install
            def injected(app,db,device,lock_owner):return original(app,db,device,lock_owner,beacon_factory=Reader)
            with patch('juno.integrations_api.install',injected):app=create_app(self.engine)
        with TestClient(app) as client:
            client.headers['Authorization']='Bearer '+self.token
            payload={'base_url':Reader.origin,'token':'synthetic-do-not-store'}
            first=client.post('/v1/integrations/beacon/refresh',json=payload)
            self.assertEqual(first.status_code,200,first.text);identity=first.json()['id']
            Reader.failure=True
            self.assertEqual(client.post('/v1/integrations/beacon/refresh',json={**payload,'expected_id':identity}).status_code,502)
            data=client.get('/v1/integrations').json()['items'][0]
            self.assertEqual(data['id'],identity);self.assertEqual(data['count'],1)
            self.assertNotIn('synthetic-do-not-store',client.get('/v1/cache').text)
            with self.factory() as session:self.assertNotIn('synthetic-do-not-store',str(vars(session.get(IntegrationSnapshot,(self.actor.owner_id,'beacon')))))

for name in list(vars(memory_tests.MemoryTests)):
    if name.startswith('test_') and name not in IntegrationAPITests.__dict__:setattr(IntegrationAPITests,name,None)
