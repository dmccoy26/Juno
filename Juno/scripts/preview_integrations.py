"""Isolated native QA backed by disposable PostgreSQL and fictional integration records.
Run with JUNO_TEST_ADMIN_URL and the project venv; close with Ctrl-C after UI inspection.
"""
import json, os, plistlib, uuid, socket, subprocess, sys, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_memory_api import MemoryTests
from test_integrations import ICS,CSV,FEED
from juno.api import create_app
import uvicorn
from test_providers import ProviderFixture,config,TOKEN
from fastapi.testclient import TestClient


def main():
    MemoryTests.setUpClass();case=MemoryTests();server=None
    try:
        case.setUp()
        for kind,content in [('calendar',ICS),('schedules',CSV),('beacon',json.dumps(FEED))]:
            response=case.client.post('/v1/integrations/import',json={'kind':kind,'content':content,'label':'fictional-'+kind,'start':'2026-10-26','end':'2026-11-17','timezone':'America/Chicago'})
            assert response.status_code==200,response.text
        if '--planning' in sys.argv or '--schedules' in sys.argv:
            from juno.models import TaskDockSnapshot, TaskDockState, now
            from datetime import datetime,timedelta,time as daytime
            from zoneinfo import ZoneInfo
            with case.factory() as session:
                snap=TaskDockSnapshot(owner_id=case.actor.owner_id,origin='http://localhost:8100',
                    info={'workspace_id':'fictional','definitions':{}},items=[
                        {'id':'fictional-dean','title':'Fictional Dean briefing','behavior':'open'},
                        {'id':'fictional-room','title':'Fictional classroom repair','behavior':'open'}],
                    sources=[],snapshot='fictional',fetched_at=now())
                session.add(snap);session.flush();session.add(TaskDockState(owner_id=case.actor.owner_id,active_id=snap.id));session.commit()
            today=now().astimezone(ZoneInfo('America/Chicago')).date()
            windows=[]
            for i in range(1,6):
                a=datetime.combine(today+timedelta(days=i),daytime(9),ZoneInfo('America/Chicago'))
                windows.append({'kind':'work','start':a.isoformat(),'end':(a+timedelta(hours=8)).isoformat()})
            response=case.client.put('/v1/planning',json={'expected_revision':0,'workspace_id':'fictional','reserve_minutes':240,'windows':windows,'tasks':[
                {'task_id':'fictional-dean','minutes':45,'dean':True},
                {'task_id':'fictional-room','minutes':90,'operational':True,'blocker':'Awaiting fictional parts','next_action':'Check delivery','next_check':str(today+timedelta(days=2))}]})
            assert response.status_code==200,response.text
        if '--schedules' in sys.argv:
            rules=[]
            for kind,name,location,a,b,days in [
                ('work','','','09:00','17:00',[0,1,2,3,4]),
                ('room','Example Room','','08:00','18:00',[0,1,2,3,4]),
                ('staff_available','Fictional Tech','','09:00','12:00',[0,2,4]),
                ('staff_available','Fictional Candidate','','09:00','12:00',[0,2,4])]:
                rules.append({'kind':kind,'name':name,'location':location,'start_date':'2026-10-26','end_date':'2026-12-10','days':days,'start_time':a,'end_time':b})
            response=case.client.put('/v1/schedules',json={'expected_revision':0,'rules':rules,'people':[
                {'name':'Fictional Tech','status':'active','weekly_limit_minutes':1200},
                {'name':'Fictional Candidate','status':'candidate','weekly_limit_minutes':1200}], 'exceptions':[]})
            assert response.status_code==200,response.text
        listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        fixture=ProviderFixture()
        provider_app=create_app(case.engine,provider_transport=fixture)
        with TestClient(provider_app,base_url='http://127.0.0.1:18123',client=('127.0.0.1',50000)) as local:
            local.headers['Authorization']='Bearer '+case.token
            for provider in ('gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar'):
                response=local.post('/v1/providers/'+provider+'/refresh',json={'token':TOKEN,'selection':config(provider)})
                assert response.status_code==200,response.text
            if '--empty-status' in sys.argv:
                row=next(r for r in local.get('/v1/providers/state').json()['items'] if r['kind']=='google_tasks')
                response=local.delete('/v1/integrations/google_tasks',params={'expected_id':row['id']})
                assert response.status_code==200,response.text
        server=uvicorn.Server(uvicorn.Config(provider_app,log_level='error',access_log=False))
        worker=threading.Thread(target=lambda:server.run(sockets=[listener]),daemon=True);worker.start()
        folder=Path(tempfile.mkdtemp(prefix='juno-evidence-ui-'));folder.chmod(0o700)
        app=folder/'Juno Evidence QA.app';(app/'Contents/MacOS').mkdir(parents=True)
        (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.dmccoy.juno.evidence.qa.'+uuid.uuid4().hex,'CFBundleName':'Juno Evidence QA','CFBundleExecutable':'Juno','CFBundlePackageType':'APPL','LSMinimumSystemVersion':'13.5'}))
        source=(ROOT/'desktop/Juno.swift').read_text().split('@main\nstruct JunoApplication',1)[0]
        (folder/'Juno.swift').write_text(source)
        (folder/'QA.swift').write_text('''import SwiftUI
@main struct EvidenceQA: App {
    @StateObject var store: JunoStore
    init() {
        let value = JunoStore()
        value.endpoint = URL(string:"http://127.0.0.1:PORT")!;value.localEndpoint = value.endpoint
        value.token = TOKEN;value.localToken = value.token;value.status = "Isolated QA · Fictional records";value.section = "Evidence"
        _store = StateObject(wrappedValue:value)
    }
    var body: some Scene {
        WindowGroup("Juno Evidence QA · Fictional data") {
            RootView(store:store).frame(width:1100,height:850)
        }
    }
}
'''.replace('PORT',str(port)).replace('TOKEN',json.dumps(case.token)).replace('value.section = "Evidence"','value.section = "Schedules"' if '--schedules' in sys.argv else 'value.section = "Plan"' if '--planning' in sys.argv else 'value.section = "Connections"' if '--connections' in sys.argv else 'value.section = "Evidence"'))
        (folder/'QA.swift').chmod(0o600)
        subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-O','-target','arm64-apple-macosx13.5',str(folder/'Juno.swift'),*[str(ROOT/'desktop'/n) for n in ['Companion.swift','TaskDock.swift','Shared.swift','Integrations.swift','Connections.swift','Planning.swift','Schedules.swift']],str(folder/'QA.swift'),'-o',str(app/'Contents/MacOS/Juno')],check=True)
        print(app,flush=True)
        while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        if server:server.should_exit=True;worker.join(10)
        case.tearDown();MemoryTests.tearDownClass()
if __name__=='__main__':main()
