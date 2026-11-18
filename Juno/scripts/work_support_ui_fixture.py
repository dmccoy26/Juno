"""Serve an isolated owner workspace for the native Mission 17 walkthrough.

Keep this process running only for the walkthrough. It deletes its random test
PostgreSQL database on normal shutdown. Never loads the installed app state.
"""
from pathlib import Path
import os,sys,json,socket,signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend/tests'))
from test_memory_api import MemoryTests
from juno.auth import provision
from juno.api import create_app
import uvicorn
root=Path(__file__).resolve().parents[1]
MemoryTests.setUpClass()
try:
    with MemoryTests.factory() as s:
        actor,token=provision(s,'Synthetic Mission 17 walkthrough');s.commit()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    folder=root/'.local/mission17-ui';folder.mkdir(exist_ok=True)
    path=folder/'fixture.json';path.write_text(json.dumps({'url':f'http://127.0.0.1:{port}','token':token}));path.chmod(0o600)
    print('Disposable Mission 17 native fixture ready on a random loopback port.',flush=True)
    uvicorn.run(create_app(MemoryTests.engine),host='127.0.0.1',port=port,log_level='critical',access_log=False)
finally:
    MemoryTests.tearDownClass()
