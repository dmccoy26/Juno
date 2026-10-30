"""Actual TaskDock/Juno bridge with disposable records and loopback HTTP; no installed app data."""
import argparse,json,os,socket,subprocess,sys,tempfile,time
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_memory_api import MemoryTests
from juno.taskdock import TaskDockReader,TaskDockError
CHILD=r'''
import json,os,sys
from pathlib import Path
from fastapi.testclient import TestClient
from unified_tasks import environment
environment.load_environment=lambda root=None:None
from unified_tasks.main import create_app
from unified_tasks.db import connect
import uvicorn
folder=Path(sys.argv[1]);app=create_app(folder/'synthetic.db',mode='disabled')
with TestClient(app) as client:
    client.headers['Authorization']='Bearer synthetic-bridge-admin'
    client.put('/workspace/integrations/juno',json={'enabled':True})
    token=client.post('/workspace/integrations/juno/token').json()['token']
    client.post('/workspace/tasks',json={'title':'Synthetic bridge task'})
    with connect(folder/'synthetic.db') as db:
        for n in range(501):
            db.execute("INSERT INTO notebook_notes VALUES (?,?,?,0,1,'2026-10-29T12:00:00Z','2026-10-29T12:00:00Z')",('synthetic-'+str(n),'Synthetic note '+str(n),'Synthetic notebook body'))
        db.execute("INSERT INTO notebook_notes VALUES ('archived','Synthetic archived note','Never export',1,1,'2026-10-29T12:00:00Z','2026-10-29T12:00:00Z')")
    state=folder/'token.json';state.write_text(json.dumps({'token':token}));state.chmod(0o600)
uvicorn.run(app,host='127.0.0.1',port=int(sys.argv[2]),log_level='error',access_log=False)
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--taskdock',required=True,type=Path);p.add_argument('--python',required=True,type=Path);p.add_argument('--report',type=Path);args=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='juno-bridge-check-') as temp:
        folder=Path(temp);folder.chmod(0o700)
        with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        env={k:v for k,v in os.environ.items() if not k.startswith(('UNIFIED_','TASKDOCK_','PYTHON'))};env['PYTHONPATH']=str(args.taskdock.resolve()/'api');env['UNIFIED_API_TOKEN']='synthetic-bridge-admin'
        with (folder/'server.log').open('w') as log:
            child=subprocess.Popen([str(args.python),'-c',CHILD,temp,str(port)],cwd=args.taskdock,env=env,stdout=log,stderr=log)
            case=None
            try:
                base='http://127.0.0.1:'+str(port)
                from urllib.request import Request,urlopen
                deadline=time.monotonic()+30;token=None
                while time.monotonic()<deadline:
                    if child.poll() is not None:raise RuntimeError('Disposable TaskDock failed: '+(folder/'server.log').read_text()[-4000:])
                    try:
                        token=json.loads((folder/'token.json').read_text())['token'];reader=TaskDockReader(base,token);reader.discover();break
                    except (OSError,ValueError,TaskDockError):time.sleep(.1)
                else:raise RuntimeError('Disposable TaskDock did not become ready.')
                assert len(reader.fetch().items)==1
                assert reader.catalog()['grants']==[]
                try:reader.evidence(['notes']);raise AssertionError('Old task-only credential gained note access')
                except TaskDockError as error:assert error.status==403
                def grants(kinds):
                    req=Request(base+'/workspace/integrations/juno',data=json.dumps({'enabled':True,'grants':kinds}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer synthetic-bridge-admin'},method='PUT')
                    with urlopen(req) as response:assert response.status==200
                grants(['notes']);data=reader.evidence(['notes']);assert len(data['items'])==501
                assert all(x['id']!='note:archived' for x in data['items'])
                MemoryTests.setUpClass();case=MemoryTests();case.setUp()
                body={'base_url':base,'token':token,'kinds':['notes']}
                review=case.client.post('/v1/taskdock/evidence',json=body);assert review.status_code==200,review.text
                assert review.json()['review_required']
                info=review.json()['catalog']['info'];body.update(reviewed_workspace_id=info['workspace_id'],reviewed_device_id=info['device_id'])
                saved=case.client.post('/v1/taskdock/evidence',json=body);assert saved.status_code==200,saved.text
                snapshot=saved.json()['snapshot'];assert snapshot['count']==501
                assert token not in case.client.get('/v1/cache').text
                assert case.client.get('/v1/integrations',headers={'Authorization':'Bearer '+case.other_token}).json()['items']==[]
                assert case.client.post('/v1/taskdock/evidence',json=body).status_code==409
                grants([]);body['expected_id']=snapshot['id'];assert case.client.post('/v1/taskdock/evidence',json=body).status_code==403
                retained=case.client.get('/v1/integrations').json()['items'][0];assert retained['id']!=snapshot['id'] and retained['details']['active'] is False
                assert retained['items']==snapshot['items'] and datetime.fromisoformat(retained['fetched_at'])==datetime.fromisoformat(snapshot['fetched_at'])
                report={'taskdock_build':info['taskdock']['build'],'actual_http_bridge':True,'task_only_backward_compatibility':True,'explicit_grants':True,'paged_notes':501,'owner_isolation':True,'credential_excluded_from_cache':True,'revocation_retains_inactive_copy':True,'synthetic_only':True}
                print(json.dumps(report,indent=2))
                if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')
            finally:
                if case:case.tearDown();MemoryTests.tearDownClass()
                child.terminate();child.wait(timeout=10)
if __name__=='__main__':main()
