"""Verify Juno's reader against an extracted TaskDock app, using disposable data only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SMOKE = r'''
import json, os, socket, threading, time, secrets
from pathlib import Path
from urllib.request import Request, urlopen
import uvicorn
from unified_tasks.main import create_app
from juno.taskdock import TaskDockReader, TaskDockError
admin_token = secrets.token_urlsafe(32)
os.environ['UNIFIED_API_TOKEN'] = admin_token
app = create_app(Path.cwd()/'student-test.db', mode='disabled')
sock = socket.socket(); sock.bind(('127.0.0.1', 0))
origin = 'http://127.0.0.1:' + str(sock.getsockname()[1])
server = uvicorn.Server(uvicorn.Config(app, log_level='critical', access_log=False))
worker = threading.Thread(target=lambda:server.run(sockets=[sock]), daemon=True); worker.start()
for _ in range(100):
    if server.started: break
    time.sleep(.05)
assert server.started

def admin(path, body=None, method='POST'):
    request=Request(origin+path, data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+admin_token,'Content-Type':'application/json'}, method=method)
    with urlopen(request, timeout=10) as response:
        raw=response.read()
        return json.loads(raw) if raw else None

try:
    admin('/workspace/integrations/juno', {'enabled':True}, 'PUT')
    token=admin('/workspace/integrations/juno/token')['token']
    parent=admin('/workspace/tasks', {'title':'Student Test — Classroom repair','subtasks':[{'title':'Student Test — Check cable'}]})
    admin('/workspace/tasks/'+parent['id']+'/updates', {'body':'Student Test — Awaiting fictional part.'})
    reader=TaskDockReader(origin,token)
    first=reader.fetch()
    assert first.info['api_version']=='1' and first.info['taskdock']['build']==13
    assert len(first.items)==2
    assert any(r.get('parent_id')==parent['id'] for r in first.items)
    assert any('fictional part' in r.get('body','') for r in reader.history(parent['id'],'updates'))
    assert reader.history(parent['id'],'activity')
    admin('/workspace/integrations/juno/token', method='DELETE')
    try:reader.fetch()
    except TaskDockError as error:assert error.status==401
    else:raise AssertionError('Revoked token accepted')
finally:
    server.should_exit=True;worker.join(10);sock.close()
assert not worker.is_alive()
print(json.dumps({'synthetic_only':True,'taskdock_build':13,'real_loopback_http':True,
    'discovery':True,'native_tasks_and_subtasks':True,'updates_and_activity':True,'revocation_no_fallback':True}))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    resources=args.app.resolve()/'Contents/Resources'
    env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','TMPDIR','LANG')}
    with tempfile.TemporaryDirectory(prefix='juno-taskdock-synthetic-') as folder:
        env.update(PATH='/usr/bin:/bin:/usr/sbin:/sbin',TASKDOCK_DATA_ROOT=folder,
            PYTHONPATH=os.pathsep.join([str(resources/'app/api'),str(resources/'app/scripts'),str(ROOT/'backend/src')]),
            PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
        result=subprocess.run([str(resources/'runtime/python/bin/python3'),'-c',SMOKE],
            cwd=folder,env=env,capture_output=True,text=True,timeout=60)
        if result.returncode:
            # Only this disposable fixture is used; errors must never contain pairing values.
            raise RuntimeError('Disposable TaskDock connector smoke failed. '+result.stderr[-1500:])
        report=json.loads(result.stdout)
    print(json.dumps(report,indent=2))
    if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
