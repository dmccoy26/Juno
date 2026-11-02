"""Real isolated TLS listener: trust is temporary per client, never installed in macOS."""
import json,os,socket,ssl,tempfile,unittest,urllib.request,urllib.error,http.cookiejar
from fastapi.testclient import TestClient
from juno.auth import provision
from juno.models import ScheduleState,now
from zoneinfo import ZoneInfo
from pathlib import Path
from juno.shared_host import HostManager
from juno.worker_host import WorkerHostManager
from juno.api import create_app
import test_memory_api as memory_tests


@unittest.skipUnless(os.environ.get('JUNO_TEST_ADMIN_URL'),'Set JUNO_TEST_ADMIN_URL for isolated PostgreSQL tests')
class WorkerHostTests(unittest.TestCase):
    setUpClass=classmethod(memory_tests.MemoryTests.setUpClass.__func__)
    tearDownClass=classmethod(memory_tests.MemoryTests.tearDownClass.__func__)
    def test_certificate_gate_and_actual_https_worker_only_listener(self):
        with tempfile.TemporaryDirectory(prefix='juno-worker-tls-') as temp:
            root=Path(temp);pair=HostManager(root);cert,key=pair.certificate()
            manager=WorkerHostManager(root);self.assertFalse(manager.readiness()['ready'])
            with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
            value={'address':f'https://localhost:{port}','certificate':str(cert),'private_key':str(key),'ca_bundle':str(cert)}
            manager.config_path.write_text(json.dumps(value));self.assertTrue(manager.readiness()['ready'],manager.readiness())
            value['address']=f'https://wrong.invalid:{port}';manager.config_path.write_text(json.dumps(value));self.assertFalse(manager.readiness()['ready'])
            value['address']=f'https://localhost:{port}';manager.config_path.write_text(json.dumps(value));key.chmod(0o644);self.assertFalse(manager.readiness()['ready']);key.chmod(0o600)
            manager.app=create_app(self.engine,worker_manager=manager)
            try:
                manager.start();self.assertTrue(manager.status()['running'])
                context=ssl.create_default_context(cafile=str(cert));address=f'https://localhost:{port}'
                with urllib.request.urlopen(address+'/worker',context=context,timeout=5) as response:self.assertIn('Worker check-in',response.read().decode());self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
                for path in ('/v1/workers','/v1/pair','/v1/memories','/docs'):
                    with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(address+path,context=context,timeout=5)
                    self.assertEqual(caught.exception.code,403);caught.exception.close()
                with self.assertRaises(urllib.error.URLError):urllib.request.urlopen(address+'/worker',context=ssl.create_default_context(),timeout=5)
                with self.factory() as session:
                    owner,token=provision(session,'Synthetic worker TLS owner');session.add(ScheduleState(owner_id=owner.owner_id,data={'people':[{'name':'Synthetic TLS worker'}]},revision=1));session.commit()
                with TestClient(manager.app) as control:
                    control.headers['Authorization']='Bearer '+token
                    self.assertEqual(control.put('/v1/workers/settings',json={'enabled':True}).status_code,200)
                    worker=control.post('/v1/workers',json={'name':'Synthetic TLS worker'}).json()['id']
                    invitation=control.post('/v1/workers/'+worker+'/invitations').json()['url'].split('#invite=')[1]
                    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(jar))
                    def post(path,body,csrf=''):
                        request=urllib.request.Request(address+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':address,'X-Juno-CSRF':csrf})
                        return opener.open(request,timeout=5)
                    with post('/worker/api/enroll',{'invitation':invitation}) as response:
                        cookie=response.headers['Set-Cookie'];self.assertIn('Secure',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=strict',cookie);csrf=json.loads(response.read())['csrf']
                    body={'request_key':'synthetic-tls-report-001','kind':'unexpected','work_date':str(now().astimezone(ZoneInfo('America/Chicago')).date()),'text':'Synthetic real TLS report'}
                    with post('/worker/api/reports',body,csrf) as response:self.assertTrue(json.loads(response.read())['received'])
                    self.assertEqual(len(control.get('/v1/workers').json()['reports']),1)
                    self.assertEqual(control.put('/v1/workers/settings',json={'enabled':False}).status_code,200)
                    self.assertFalse(manager.status()['running'])

            finally:manager.close()
            self.assertFalse(manager.status()['running'])

if __name__=='__main__':unittest.main()
