"""Exercise the actual installer payload after relocation with bundled runtimes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import selectors
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def run(*args):
    subprocess.run([str(a) for a in args], check=True, stdout=subprocess.DEVNULL)


def check_payload(app):
    info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
    assert info.get('JunoPackaged') is True
    assert 'JunoProjectRoot' not in info
    resources = app/'Contents/Resources'
    reference = resources/'runtime/postgres/share/proj/proj.db'
    forbidden = []
    binaries = []
    for path in app.rglob('*'):
        if path.is_symlink():
            assert path.resolve().is_relative_to(app.resolve()), 'External symlink in payload'
        if not path.is_file(): continue
        if path.name in ('.env', 'desktop-owner.json') or (path.suffix in ('.db','.sqlite','.sqlite3') and path != reference):
            forbidden.append(str(path.relative_to(app)))
        if not path.is_symlink():
            with path.open('rb') as stream: magic=stream.read(4)
            if magic in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbf'):
                binaries.append(path)
    assert not forbidden, 'Private data entered payload: '+repr(forbidden)
    linked = subprocess.check_output(['otool','-L',*map(str,binaries)], text=True)
    for line in linked.splitlines():
        if line.startswith('\t'):
            dep = line.strip().split(' (')[0]
            assert not dep.startswith(('/opt/', '/Users/', '/usr/local/', '/Library/Frameworks/')), 'External dynamic dependency: '+dep
    run('codesign','--verify','--deep','--strict',app)
    return len(binaries)


def api(url, token, path, *, method='GET', body=None, expected=200):
    headers={'Authorization':'Bearer '+token} if token else {}
    data = json.dumps(body).encode() if body is not None else None
    if data: headers['Content-Type']='application/json'
    req=urllib.request.Request(url+path,headers=headers,data=data,method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            status=response.status; raw=response.read()
    except urllib.error.HTTPError as error:
        status=error.code; raw=error.read()
    assert status==expected, f'{method} {path.split("?")[0]} returned {status}, expected {expected}'
    return json.loads(raw) if raw else None


def local_environment(app, state):
    resources=app/'Contents/Resources'
    env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','TMPDIR','LANG')}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1',
               JUNO_DATA_ROOT=str(state), JUNO_POSTGRES_BIN=str(resources/'runtime/postgres/bin'))
    return env


def launch(app, state, log, wrapped=False):
    resources=app/'Contents/Resources'
    env=local_environment(app,state)
    command=[str(resources/'runtime/python/bin/python3'), str(resources/'app/scripts/desktop_service.py')]
    if wrapped:
        wrapper = 'import subprocess,sys; p=subprocess.Popen(sys.argv[1:],stdout=subprocess.PIPE,text=True); print(p.stdout.readline().strip(),flush=True); p.wait()'
        command=[command[0], '-c', wrapper, *command]
    process=subprocess.Popen(command,
                             stdout=subprocess.PIPE,stderr=log,env=env,cwd=state.parent)
    select=selectors.DefaultSelector();select.register(process.stdout, selectors.EVENT_READ)
    if not select.select(40):
        process.terminate();process.wait(timeout=10)
        raise RuntimeError('Bundled service startup timed out')
    hello=json.loads(process.stdout.readline())
    select.close()
    if 'token' not in hello:
        process.wait(timeout=10)
        raise RuntimeError('Bundled service failed; inspect verification log')
    for _ in range(60):
        try:
            api(hello['url'],hello['token'],'/v1/memories')
            return process,hello
        except (urllib.error.URLError,ConnectionError): time.sleep(.1)
    process.terminate();process.wait(timeout=10)
    raise RuntimeError('Bundled API did not become ready')


def stop(process, app, state):
    process.terminate(); process.wait(timeout=15)
    status=subprocess.run([str(app/'Contents/Resources/runtime/postgres/bin/pg_ctl'),'-D',str(state/'postgres/data'),'status'],
                          stdout=subprocess.DEVNULL).returncode
    assert status != 0, 'Owned PostgreSQL did not stop'



def verify_taskdock_cache(url, token):
    """Disposable strict local API fixture; never reads an installed TaskDock workspace."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from urllib.parse import urlsplit, parse_qs
    import secrets
    fixture=json.loads((Path(__file__).resolve().parents[1]/'backend/tests/fixtures/taskdock-v1.json').read_text())
    pairing=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.headers.get('Authorization') != 'Bearer '+pairing:
                self.send_error(401);return
            path=urlsplit(self.path).path
            if path=='/integrations/juno/v1/info': result=fixture['info']
            elif path=='/integrations/juno/v1/sources': result=fixture['sources']
            elif path=='/workspace/tasks':
                query=parse_qs(urlsplit(self.path).query)
                assert query['parents_only']==['false'] and query['include_completed']==['true']
                result={**fixture['tasks'],'limit':500}
            else:self.send_error(403);return
            raw=json.dumps(result).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    worker=Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        body={'base_url':'http://127.0.0.1:'+str(server.server_port),'token':pairing}
        review=api(url,token,'/v1/taskdock/refresh',method='POST',body=body)
        assert review['review_required'] is True
        body.update(reviewed_workspace_id=review['info']['workspace_id'],reviewed_device_id=review['info']['device_id'])
        snapshot=api(url,token,'/v1/taskdock/refresh',method='POST',body=body)['snapshot']
        assert snapshot['items']==fixture['tasks']['items']
        assert snapshot['sources']==fixture['sources']['items']
        assert pairing not in json.dumps(snapshot)
    finally:
        server.shutdown();server.server_close();worker.join(3)
    api(url,token,'/v1/taskdock/refresh',method='POST',body={**body,'expected_snapshot_id':snapshot['id']},expected=502)
    kept=api(url,token,'/v1/taskdock')['snapshot']
    assert kept['id']==snapshot['id'] and kept['stale'] is True
    return snapshot['id']



def verify_integrations(url,token):
    """Exercise all new readers using only supplied fictional files and an isolated HTTP fixture."""
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from threading import Thread
    fixtures=Path(__file__).resolve().parents[1]/'backend/tests/fixtures'
    identities={}
    for kind,name in [('calendar','calendar.ics'),('schedules','semester-schedule.csv'),('beacon','beacon-alerts.json')]:
        body={'kind':kind,'content':(fixtures/name).read_text(),'label':name,'start':'2026-10-26','end':'2026-11-17','timezone':'America/Chicago'}
        result=api(url,token,'/v1/integrations/import',method='POST',body=body)
        identities[kind]=result['id']
        if kind=='calendar':
            assert result['count']==5 and result['details']['busy_days'][0]['busy_minutes']==90
            api(url,token,'/v1/integrations/import',method='POST',body={**body,'expected_id':result['id'],'content':body['content'].replace('FREQ=WEEKLY','FREQ=SECONDLY')},expected=422)
        if kind=='schedules':assert result['count']==12 and all(d['busy_minutes']==60 for d in result['details']['busy_days'])
    feed=json.loads((fixtures/'beacon-alerts.json').read_text());calls=[]
    secret='synthetic-packaged-beacon-key'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            assert self.path=='/api/alerts' and self.headers.get('Authorization')=='Bearer '+secret
            calls.append(self.path);payload=feed if len(calls)==1 else {**feed,'complete':False}
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps(payload).encode())
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);worker=Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        body={'base_url':'http://127.0.0.1:'+str(server.server_port),'token':secret,'expected_id':identities['beacon']}
        result=api(url,token,'/v1/integrations/beacon/refresh',method='POST',body=body);identities['beacon']=result['id']
        api(url,token,'/v1/integrations/beacon/refresh',method='POST',body={**body,'expected_id':result['id']},expected=502)
        saved=api(url,token,'/v1/integrations')
        assert len(saved['items'])==3 and secret not in json.dumps(saved)
        assert next(r for r in saved['items'] if r['kind']=='beacon')['id']==identities['beacon']
        pages=api(url,token,'/v1/cache')['pages']
        assert len(next(p['body'] for p in pages if p['path']=='/v1/integrations')['items'])==3
    finally:server.shutdown();server.server_close();worker.join(3)
    return identities


def verify_shared_host(url, token, state):
    import ssl
    from urllib.parse import urlsplit
    status=api(url,token,'/v1/host',method='PUT',body={'enabled':True})
    invitation=api(url,token,'/v1/host/invitations',method='POST')
    certificate=state/'shared-host/certificate.pem'
    assert hashlib.sha256(ssl.PEM_cert_to_DER_cert(certificate.read_text())).hexdigest()==invitation['certificate_sha256']
    context=ssl.create_default_context(cafile=str(certificate))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=context))
    address='https://localhost:'+str(urlsplit(status['address']).port)
    def tls(path,device_token='',body=None,expected=200):
        request=urllib.request.Request(address+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+device_token,'Content-Type':'application/json'},method='POST' if body is not None else 'GET')
        try:
            with opener.open(request,timeout=10) as response:code=response.status;raw=response.read()
        except urllib.error.HTTPError as error:code=error.code;raw=error.read();error.close()
        assert code==expected,'Unexpected shared-host result'
        return json.loads(raw)
    paired=tls('/v1/pair',body={'invitation':invitation['invitation'],'label':'Synthetic packaged laptop'})
    tls('/v1/pair',body={'invitation':invitation['invitation'],'label':'Denied replay'},expected=401)
    exported=tls('/v1/cache',paired['token'])
    assert exported['owner_id']==paired['owner_id']
    assert paired['token'] not in json.dumps(exported)
    operation={'operation_id':'00000000-0000-0000-0000-000000000099','kind':'memory.create','body':{'text':'Synthetic packaged offline memory','source':'verification:shared','confidence':'confirmed'}}
    assert len(tls('/v1/integrations',paired['token'])['items'])==3
    first=tls('/v1/offline-operations',paired['token'],operation)
    assert tls('/v1/offline-operations',paired['token'],operation)==first
    tls('/v1/host',paired['token'],expected=403)
    api(url,token,'/v1/host/devices/'+paired['device_id'],method='DELETE')
    tls('/v1/cache',paired['token'],expected=401)
    api(url,token,'/v1/host',method='PUT',body={'enabled':False})


def verify(package, report):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='juno-verify-', dir='/tmp') as temporary:
        root=Path(temporary)
        expanded=root/'expanded'
        run('pkgutil','--expand-full',package,expanded)
        apps=list(expanded.glob('**/Payload/Applications/Juno.app'))
        assert len(apps)==1, 'Installer payload did not contain exactly one Juno.app'
        assert 'Quit Juno' in next(expanded.glob('**/Scripts/preinstall')).read_text()
        checks.append('installer expands with expected app and non-destructive preinstall guard')
        relocated=root/'Relocated Juno.app'
        shutil.copytree(apps[0],relocated,symlinks=True)
        count=check_payload(relocated)
        checks.append(f'payload seals, internal symlinks and {count} Mach-O dependency checks')
        state=root/'state'
        hostdir=state/'shared-host';hostdir.mkdir(parents=True,mode=0o700)
        (hostdir/'settings.json').write_text(json.dumps({'enabled':False,'port':0}))
        (hostdir/'settings.json').chmod(0o600)
        process=None
        logpath=report.with_suffix('.log')
        with logpath.open('w') as log:
            try:
                process,hello=launch(relocated,state,log)
                url,token=hello['url'],hello['token']
                assert api(url,token,'/v1/memories')['items']==[], 'Payload was not clean'
                api(url,'','/v1/memories',expected=401)
                value=dict(text='Synthetic portable installer memory',source='verification:installer',confidence='confirmed')
                row=api(url,token,'/v1/memories',method='POST',body=value,expected=201)
                path='/v1/memories/'+row['id']
                edit={**value,'text':'Synthetic portable memory corrected','expected_revision':1}
                updated=api(url,token,path,method='PUT',body=edit)
                assert updated['revision']==2
                api(url,token,path,method='PUT',body=edit,expected=409)
                stop(process,relocated,state);process=None
                checks.append('fresh isolated startup, authentication, create/edit and stale-edit conflict')
                # The check-in is useful even with no configured model/server.
                process,hello=launch(relocated,state,log)
                url,token=hello['url'],hello['token']
                assert api(url,token,'/v1/model')['configured'] is False
                conv=api(url,token,'/v1/conversations',method='POST',body={'title':'Synthetic portable chat'},expected=201)
                api(url,token,'/v1/conversations/'+conv['id']+'/messages',method='POST',
                    body={'text':'Synthetic unsent message','request_id':'00000000-0000-0000-0000-000000000001'},expected=503)
                assert api(url,token,'/v1/conversations/'+conv['id']+'/messages')['items']==[]
                diary=api(url,token,'/v1/check-ins',method='POST',body={'local_date':'2026-10-29'})
                for question in diary['questions']:
                    diary=api(url,token,'/v1/check-ins/'+diary['id']+'/answer',method='PUT',
                        body={'key':question['key'],'text':'Synthetic installer check-in answer.','expected_revision':diary['revision']})
                diary=api(url,token,'/v1/check-ins/'+diary['id']+'/diary',method='PUT',
                    body={'text':diary['diary_text'],'expected_revision':diary['revision'],'confirm':True})
                assert diary['status']=='confirmed'
                taskdock_snapshot_id=verify_taskdock_cache(url,token)
                integration_ids=verify_integrations(url,token)
                verify_shared_host(url,token,state)
                checks.append("packaged Beacon HTTP reader, calendar recurrence/DST/overlap, semester CSV, error retention and offline export")
                checks.append('packaged TLS pairing, one-use invitations, offline-operation idempotency, administration scope and device revocation')
                checks.append('packaged TaskDock identity review, dated snapshot, provider freshness and outage retention')
                stop(process,relocated,state);process=None
                checks.append('offline check-in/diary and explicit unconfigured-model behavior')

                process,second=launch(relocated,state,log)
                url=second['url']
                api(url,token,'/v1/memories',expected=401)
                token=second['token']
                assert api(url,token,'/v1/taskdock')['snapshot']['id']==taskdock_snapshot_id
                checks.append('TaskDock snapshot persists across packaged service restart')
                assert {r['kind']:r['id'] for r in api(url,token,'/v1/integrations')['items']}==integration_ids
                for kind,identity in integration_ids.items():api(url,token,'/v1/integrations/'+kind+'?expected_id='+identity,method='DELETE')
                assert api(url,token,'/v1/integrations')['items']==[]
                checks.append('integration snapshots persist across restart and can be removed without provider writes')
                assert api(url,token,path)['text']==edit['text']
                assert api(url,token,'/v1/check-ins',method='POST',body={'local_date':'2026-10-29'})['status']=='confirmed'
                api(url,token,path+'?expected_revision=2',method='DELETE',expected=204)
                api(url,token,path,expected=404)
                api(url,token,'/v1/memories',method='POST',body=value,expected=409)
                stop(process,relocated,state);process=None
                checks.append('relaunch persistence, credential rotation, deletion/suppression and clean shutdown')
                process,third=launch(relocated,state,log,wrapped=True)
                process.kill();process.wait(timeout=10);process=None
                for attempt in range(100):
                    status=subprocess.run([str(relocated/'Contents/Resources/runtime/postgres/bin/pg_ctl'),'-D',str(state/'postgres/data'),'status'],stdout=subprocess.DEVNULL).returncode
                    if status != 0: break
                    time.sleep(.1)
                else: raise RuntimeError('Parent-loss cleanup left PostgreSQL running')
                checks.append('application parent-loss watchdog stops its owned database')
                run('codesign','--verify','--deep','--strict',relocated)
                checks.append('application resources unchanged after execution')
                legacy=root/'legacy-state'
                env=local_environment(relocated,legacy)
                resources=relocated/'Contents/Resources'
                python=resources/'runtime/python/bin/python3'
                helper=resources/'app/scripts/dev_database.py'
                subprocess.run([str(python),str(helper),'start'],env=env,check=True,stdout=log,stderr=log)
                env['JUNO_DATABASE_URL']=subprocess.check_output([str(python),str(helper),'url'],env=env,text=True).strip()
                seed = """import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/backend/src')
from alembic import command
from alembic.config import Config
from juno.database import engine_for,sessions
from juno.auth import provision
from juno.models import Memory
command.upgrade(Config(sys.argv[1]+'/backend/alembic.ini'),'0001_memory')
with sessions(engine_for())() as session:
 actor,token=provision(session,'Synthetic legacy owner')
 session.add(Memory(owner_id=actor.owner_id,text='Legacy synthetic memory survives upgrade.',source='verification:legacy',confidence='confirmed',fingerprint='a'*64))
 session.commit()
 Path(sys.argv[2]+'/desktop-owner.json').write_text(json.dumps({'owner_id':actor.owner_id,'device_id':actor.id}))
"""
                subprocess.run([str(python),'-c',seed,str(resources/'app'),str(legacy)],env=env,check=True,stdout=log,stderr=log)
                subprocess.run([str(python),str(helper),'stop'],env=env,check=True,stdout=log,stderr=log)
                process,upgraded=launch(relocated,legacy,log)
                legacy_rows=api(upgraded['url'],upgraded['token'],'/v1/memories')['items']
                assert any(r['text']=='Legacy synthetic memory survives upgrade.' for r in legacy_rows)
                backups=list((legacy/'backups').glob('*.dump'))
                assert len(backups)==1, 'Upgrade did not create a backup'
                run(resources/'runtime/postgres/bin/pg_restore','--list',backups[0])
                stop(process,relocated,legacy);process=None
                checks.append('schema-1 upgrade with readable pre-migration backup and preserved memory')

            finally:
                if process is not None:
                    process.terminate();process.wait(timeout=15)
        result={'package':package.name,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
                'status':'passed','checks':checks,'host_architecture':os.uname().machine,
                'host_macos': subprocess.check_output(['sw_vers','-productVersion'],text=True).strip(),
                'limits':['not installed on the actual M5 laptop yet', 'no Developer ID signature or notarization',
                          'actual two-Mac/network acceptance pending; host must remain awake with Juno open']}
        report.write_text(json.dumps(result,indent=2)+'\n')
        for check in checks: print('PASS '+check)
        print('Report: '+str(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    verify(args.package.resolve(),args.report.resolve())
