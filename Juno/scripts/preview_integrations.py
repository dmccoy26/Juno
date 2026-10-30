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
        listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        fixture=ProviderFixture()
        provider_app=create_app(case.engine,provider_transport=fixture)
        with TestClient(provider_app,base_url='http://127.0.0.1:18123',client=('127.0.0.1',50000)) as local:
            local.headers['Authorization']='Bearer '+case.token
            for provider in ('gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar'):
                response=local.post('/v1/providers/'+provider+'/refresh',json={'token':TOKEN,'selection':config(provider)})
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
'''.replace('PORT',str(port)).replace('TOKEN',json.dumps(case.token)).replace('value.section = "Evidence"','value.section = "Connections"' if '--connections' in sys.argv else 'value.section = "Evidence"'))
        (folder/'QA.swift').chmod(0o600)
        subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-O','-target','arm64-apple-macosx13.5',str(folder/'Juno.swift'),*[str(ROOT/'desktop'/n) for n in ['Companion.swift','TaskDock.swift','Shared.swift','Integrations.swift','Connections.swift']],str(folder/'QA.swift'),'-o',str(app/'Contents/MacOS/Juno')],check=True)
        print(app,flush=True)
        while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        if server:server.should_exit=True;worker.join(10)
        case.tearDown();MemoryTests.tearDownClass()
if __name__=='__main__':main()
