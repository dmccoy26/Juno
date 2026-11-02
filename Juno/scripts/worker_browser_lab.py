"""Synthetic browser fixture ONLY. Loopback HTTP adapter; never bundled or a deployment option.

Requires an isolated prepare_native_lab.py state. Uses a fake host solely to exercise
forms in a browser without installing certificate trust. This does not verify HTTPS
browser acceptance. Production WorkerBoundary still requires HTTPS and secure cookies.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend/src'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('state',type=Path);parser.add_argument('--port',type=int,default=18125);args=parser.parse_args()
    state=args.state.resolve()
    if state.parent.parent!=ROOT/'.local' or not state.parent.name.startswith('native-lab-') or state.name!='state':raise SystemExit('Only a named isolated native-lab state is allowed.')
    if json.loads((state/'shared-host/settings.json').read_text()).get('enabled'):raise SystemExit('Lab hosting must be disabled.')
    from juno.database import engine_for,sessions
    from juno.auth import provision
    from juno.api import create_app
    from juno.worker_host import WorkerBoundary
    from juno.models import Owner,Device,Worker,WorkerPortal,WorkerGrant,WorkerInvitation,WorkerSession,now
    from sqlalchemy import select
    from fastapi.testclient import TestClient
    from urllib.parse import urlsplit
    import uvicorn
    engine=engine_for('postgresql+psycopg://juno@/juno_dev?host='+str(state/'postgres/socket'));factory=sessions(engine)
    identity=json.loads((state/'desktop-owner.json').read_text())
    with factory() as session:
        owner=session.get(Owner,identity['owner_id'])
        if not owner or not owner.label.startswith('Student Test'):raise SystemExit('Synthetic owner required.')
        actor,token=provision(session,'Student Test worker browser fixture',owner.id);actor_id=actor.id;session.commit()
    class FakeHost:
        running=True
        def readiness(self):return {'ready':True,'address':f'http://localhost:{args.port}','reason':'Synthetic loopback fixture; not production HTTPS.'}
        def status(self):return {**self.readiness(),'running':self.running,'error':None}
        def start(self):self.running=True
        def close(self):self.running=False
    app=create_app(engine,worker_manager=FakeHost());client=TestClient(app);client.headers['Authorization']='Bearer '+token
    try:
        overview=client.get('/v1/workers').json();worker=next((w for w in overview['workers'] if w['name']=='Student Test Alex' and w['active']),None)
        if not worker:
            response=client.post('/v1/workers',json={'name':'Student Test Alex'});response.raise_for_status();worker=response.json()
        response=client.put('/v1/workers/settings',json={'enabled':True});response.raise_for_status()
        task=client.get('/v1/taskdock').json()['snapshot'];response=client.post('/v1/workers/grants',json={'worker_id':worker['id'],'task_id':'student-test-0','expected_snapshot_id':task['id'],'fields':['title','room','issue_description'],'instructions':'Synthetic browser exercise only.'});response.raise_for_status()
        response=client.post('/v1/workers/'+worker['id']+'/invitations');response.raise_for_status()
        (state.parent/'worker-browser-invitation.json').write_text(json.dumps(response.json()));(state.parent/'worker-browser-invitation.json').chmod(0o600)
        boundary=WorkerBoundary(app)
        class LoopbackFixture:
            async def __call__(self,scope,receive,send):
                if scope['type']=='lifespan':return await app(scope,receive,send)
                # Test adapter only, not reachable from LAN. The production ASGI
                # boundary, session, CSRF, grant and receipt implementations run unchanged.
                scope=dict(scope);scope['scheme']='https';headers=[]
                for key,value in scope['headers']:
                    if key==b'origin' and value==f'http://localhost:{args.port}'.encode():value=f'https://localhost:{args.port}'.encode()
                    if key==b'cookie':value=value.replace(b'juno-worker-lab=',b'__Host-juno-worker=')
                    headers.append((key,value))
                scope['headers']=headers
                async def synthetic_cookie(message):
                    if message['type']=='http.response.start':
                        message=dict(message);message['headers']=[(k,v.replace(b'; Secure',b'').replace(b'__Host-juno-worker=',b'juno-worker-lab=')) if k.lower()==b'set-cookie' else (k,v) for k,v in message.get('headers',[])]
                    await send(message)
                await boundary(scope,receive,synthetic_cookie)
        print(f'Synthetic worker browser fixture: http://localhost:{args.port}/worker; private invitation saved in the lab folder. Not a real HTTPS acceptance test.',flush=True)
        uvicorn.run(LoopbackFixture(),host='127.0.0.1',port=args.port,access_log=False,log_level='error',proxy_headers=False)
    finally:
        client.close()
        with factory() as session:
            session.get(Device,actor_id).revoked=True
            # The disposable fixture cannot leave active invitations/sessions behind.
            from sqlalchemy import delete
            ids=select(Worker.id).where(Worker.owner_id==identity['owner_id'])
            session.execute(delete(WorkerSession).where(WorkerSession.worker_id.in_(ids)));session.execute(delete(WorkerInvitation).where(WorkerInvitation.worker_id.in_(ids)));settings=session.get(WorkerPortal,identity['owner_id'])
            if settings:settings.enabled=False
            session.commit()
        engine.dispose()


if __name__=='__main__':main()
