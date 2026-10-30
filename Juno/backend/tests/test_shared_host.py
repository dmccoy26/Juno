from datetime import timedelta
import json
from pathlib import Path
import tempfile
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
import test_memory_api as memory_tests
from juno.api import create_app
from juno.auth import digest
from juno.models import Memory, OfflineOperation, PairingInvitation, now
from juno.shared_host import LANBoundary, HostManager


class FakeHost:
    def status(self):return {'enabled':True,'address':'https://synthetic.local:8443','error':None,'availability':'Synthetic host.'}
    def invitation_info(self):return {'version':1,'address':'https://synthetic.local:8443','certificate_sha256':'a'*64}


class SharedHostTests(memory_tests.MemoryTests):
    def setUp(self):
        super().setUp();self.client.close()
        self.app=create_app(self.engine,host_manager=FakeHost())
        self.client=TestClient(self.app);self.client.headers['Authorization']='Bearer '+self.token
        self.lan=TestClient(LANBoundary(self.app),client=('192.168.1.9',50000))

    def tearDown(self):self.lan.close();super().tearDown()

    def invitation(self):
        response=self.client.post('/v1/host/invitations')
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['invitation']

    def paired(self):
        code=self.invitation()
        response=self.lan.post('/v1/pair',json={'invitation':code,'label':'Synthetic laptop'})
        self.assertEqual(response.status_code,200,response.text)
        data=response.json();self.lan.headers['Authorization']='Bearer '+data['token']
        return data

    def operation(self,kind,body,record_id=None,operation_id=None):
        return self.lan.post('/v1/offline-operations',json={'operation_id':operation_id or str(uuid.uuid4()),'kind':kind,'record_id':record_id,'body':body})

    def test_single_use_expiring_invitation_and_device_revocation(self):
        code=self.invitation()
        with self.factory() as s:
            row=s.get(PairingInvitation,digest(code));self.assertNotIn(code,str(vars(row)))
        payload={'invitation':code,'label':'Synthetic laptop'}
        paired=self.lan.post('/v1/pair',json=payload).json()
        self.assertEqual(self.lan.post('/v1/pair',json=payload).status_code,401)
        self.lan.headers['Authorization']='Bearer '+paired['token']
        self.assertEqual(self.lan.get('/v1/memories').status_code,200)
        self.assertEqual(self.client.delete('/v1/host/devices/'+paired['device_id']).status_code,200)
        self.assertEqual(self.lan.get('/v1/cache').status_code,401)
        code=self.invitation()
        with self.factory() as s:s.get(PairingInvitation,digest(code)).expires_at=now()-timedelta(seconds=1);s.commit()
        self.assertEqual(self.lan.post('/v1/pair',json={'invitation':code,'label':'Expired'}).status_code,401)

    def test_replacement_invitation_owner_scope_and_host_administration_boundary(self):
        first=self.invitation();second=self.invitation()
        self.assertEqual(self.lan.post('/v1/pair',json={'invitation':first,'label':'Old'}).status_code,401)
        result=self.lan.post('/v1/pair',json={'invitation':second,'label':'Synthetic'}).json()
        self.lan.headers['Authorization']='Bearer '+result['token']
        for method,path in [('GET','/v1/host'),('POST','/v1/host/invitations'),('PUT','/v1/model'),('POST','/v1/taskdock/refresh'),('GET','/docs')]:
            self.assertEqual(self.lan.request(method,path,json={}).status_code,403)
        self.assertEqual(self.client.delete('/v1/host/devices/'+result['device_id'],headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
        with TestClient(LANBoundary(self.app),client=('203.0.113.10',50000)) as external:
            self.assertEqual(external.get('/v1/cache',headers={'Authorization':'Bearer '+result['token']}).status_code,403)
        self.assertEqual(self.client.post('/v1/pair',json={'invitation':second,'label':'Wrong surface'}).status_code,403)

    def test_offline_memory_retry_is_atomic_idempotent_and_conflicts_preserve_server_record(self):
        self.paired();operation_id=str(uuid.uuid4())
        first=self.operation('memory.create',self.value,operation_id=operation_id)
        self.assertEqual(first.status_code,200,first.text);row=first.json()
        self.assertEqual(self.operation('memory.create',self.value,operation_id=operation_id).json(),row)
        self.assertEqual(self.operation('memory.create',{**self.value,'text':'Different'},operation_id=operation_id).status_code,409)
        edit={**self.value,'text':'Offline updated memory.','expected_revision':1}
        revised=self.operation('memory.edit',edit,row['id'])
        self.assertEqual(revised.json()['revision'],2)
        conflict=self.operation('memory.edit',{**edit,'text':'Conflicting version.'},row['id'])
        self.assertEqual(conflict.status_code,409)
        self.assertEqual(self.client.get('/v1/memories/'+row['id']).json()['text'],'Offline updated memory.')
        self.assertEqual(self.operation('memory.delete',{'expected_revision':2},row['id']).status_code,200)
        self.assertEqual(self.operation('memory.create',self.value).status_code,409)
        with self.factory() as s:
            receipts=s.scalars(select(OfflineOperation).where(OfflineOperation.owner_id==self.actor.owner_id)).all()
            self.assertEqual(len(receipts),3)
            self.assertNotIn('Offline updated memory.',json.dumps([r.result for r in receipts]))
            self.assertNotIn(self.value['text'],json.dumps([r.result for r in receipts]))

    def test_conflict_review_is_read_only_owner_scoped_and_revision_checked(self):
        self.paired();row=self.create()
        op={'operation_id':str(uuid.uuid4()),'kind':'memory.edit','record_id':row['id'],'body':{**self.value,'text':'Laptop version','expected_revision':1}}
        host=self.client.put('/v1/memories/'+row['id'],json={**self.value,'text':'Host version','expected_revision':1}).json()
        self.assertEqual(self.lan.post('/v1/offline-operations',json=op).status_code,409)
        review=self.lan.post('/v1/offline-review',json=op)
        self.assertEqual(review.status_code,200,review.text)
        self.assertEqual(review.json()['current']['text'],'Host version')
        other=self.client.post('/v1/offline-review',json=op,headers={'Authorization':'Bearer '+self.other_token})
        self.assertIsNone(other.json()['current'])
        self.assertEqual(self.client.get('/v1/memories/'+row['id']).json()['revision'],host['revision'])
        with self.factory() as session:self.assertEqual(session.scalars(select(OfflineOperation)).all(),[])
        op['operation_id']=str(uuid.uuid4());op['body']['expected_revision']=host['revision']
        self.assertEqual(self.lan.post('/v1/offline-operations',json=op).json()['text'],'Laptop version')
        self.client.delete('/v1/memories/'+row['id'],params={'expected_revision':3})
        self.assertIsNone(self.lan.post('/v1/offline-review',json=op).json()['current'])

    def test_offline_diary_chain_and_retries_do_not_duplicate_day(self):
        self.paired();start_id=str(uuid.uuid4())
        row=self.operation('checkin.start',{'local_date':'2026-10-30'},operation_id=start_id).json()
        self.assertEqual(self.operation('checkin.start',{'local_date':'2026-10-30'},operation_id=start_id).json()['id'],row['id'])
        for key in ['completed','interruptions','blockers','employee_work','tomorrow']:
            response=self.operation('checkin.answer',{'key':key,'text':'Synthetic offline answer','expected_revision':row['revision']},row['id'])
            self.assertEqual(response.status_code,200,response.text);row=response.json()
        confirmed=self.operation('checkin.diary',{'text':'Synthetic offline diary','confirm':True,'expected_revision':row['revision']},row['id'])
        self.assertEqual(confirmed.json()['status'],'confirmed')
        self.assertEqual(self.client.get('/v1/check-ins/by-date/2026-10-30').json()['diary_text'],'Synthetic offline diary')

    def test_cache_is_owner_scoped_complete_and_credential_free(self):
        paired=self.paired();self.create()
        self.client.post('/v1/check-ins',json={'local_date':'2026-10-30'})
        result=self.lan.get('/v1/cache')
        self.assertEqual(result.status_code,200,result.text)
        data=result.json();self.assertEqual(data['owner_id'],self.actor.owner_id)
        self.assertNotIn(paired['token'],result.text);self.assertNotIn(self.token,result.text)
        pages={p['path']:p['body'] for p in data['pages']}
        self.assertEqual(pages['/v1/memories?q=&offset=0']['items'][0]['text'],self.value['text'])
        self.assertIn('/v1/check-ins/by-date/2026-10-30',pages)
        other=self.client.get('/v1/cache',headers={'Authorization':'Bearer '+self.other_token}).json()
        self.assertNotIn(self.value['text'],json.dumps(other))

    def test_failed_offline_edit_does_not_commit_an_operation_or_audit(self):
        self.paired();row=self.create()
        response=self.operation('memory.edit',{**self.value,'expected_revision':999},row['id'])
        self.assertEqual(response.status_code,409)
        with self.factory() as s:self.assertEqual(s.scalars(select(OfflineOperation).where(OfflineOperation.owner_id==self.actor.owner_id)).all(),[])


for name in list(vars(memory_tests.MemoryTests)):
    if name.startswith('test_') and name not in SharedHostTests.__dict__:setattr(SharedHostTests,name,None)


class CertificateTests(__import__('unittest').TestCase):
    def test_advertised_ip_and_hostname_are_certificate_sans_and_persist(self):
        import ssl
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix='juno-certificate-test-') as folder, patch('juno.shared_host.network_identity',return_value=('synthetic-host.local',['10.22.33.44'])):
            manager=HostManager(folder)
            cert,key=manager.certificate()
            names=ssl._ssl._test_decode_cert(str(cert))['subjectAltName']
            for entry in [('DNS','synthetic-host.local'),('DNS','localhost'),('IP Address','127.0.0.1'),('IP Address','10.22.33.44')]:self.assertIn(entry,names)
            original=cert.read_bytes()
            self.assertEqual(manager.certificate()[0].read_bytes(),original)
            self.assertEqual(manager.status()['address'],'https://10.22.33.44:8443')
            self.assertEqual(key.stat().st_mode & 0o777,0o600)
