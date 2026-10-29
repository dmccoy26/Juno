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


def launch(app, state, log, wrapped=False):
    resources=app/'Contents/Resources'
    env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','TMPDIR','LANG')}
    env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1',
               JUNO_DATA_ROOT=str(state), JUNO_POSTGRES_BIN=str(resources/'runtime/postgres/bin'))
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
                process,second=launch(relocated,state,log)
                url=second['url']
                api(url,token,'/v1/memories',expected=401)
                token=second['token']
                assert api(url,token,path)['text']==edit['text']
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
            finally:
                if process is not None:
                    process.terminate();process.wait(timeout=15)
        result={'package':package.name,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),
                'status':'passed','checks':checks,'host_architecture':os.uname().machine,
                'host_macos': subprocess.check_output(['sw_vers','-productVersion'],text=True).strip(),
                'limits':['not installed on the actual M5 laptop yet', 'no Developer ID signature or notarization',
                          'no cross-device synchronization or model/chat connection']}
        report.write_text(json.dumps(result,indent=2)+'\n')
        for check in checks: print('PASS '+check)
        print('Report: '+str(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    verify(args.package.resolve(),args.report.resolve())
