"""Private local-development service owned by the native Juno application.

Handshake is sent only through the application's private stdout pipe.
Never run this helper in a terminal: the handshake contains a temporary token.
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/src'))


def main():
    if sys.stdout.isatty():
        raise RuntimeError('Launch this helper through Juno.app.')
    def terminate(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    parent = os.getppid()
    def watch_parent():
        while os.getppid() == parent:
            time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=watch_parent, daemon=True).start()
    state = Path(os.environ.get('JUNO_DATA_ROOT', str(ROOT / '.local')))
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    lock = (state / 'desktop.lock').open('w')
    for attempt in range(100):
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if attempt == 99:
                raise RuntimeError('Another Juno service is still running.')
            time.sleep(.1)
    os.chmod(state / 'desktop.lock', 0o600)
    pg = Path(os.environ.get('JUNO_POSTGRES_BIN', '/opt/homebrew/opt/postgresql@17/bin')) / 'pg_ctl'
    data = state / 'postgres/data'
    was_running = data.exists() and subprocess.run(
        [str(pg), '-D', str(data), 'status'], stdout=subprocess.DEVNULL).returncode == 0
    engine = None
    actor_id = None
    try:
        subprocess.run([sys.executable, str(ROOT / 'scripts/dev_database.py'), 'start'],
                       check=True, stdout=sys.stderr)
        url = subprocess.check_output([sys.executable, str(ROOT / 'scripts/dev_database.py'), 'url'], text=True).strip()
        os.environ['JUNO_DATABASE_URL'] = url
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(ROOT / 'backend/alembic.ini')), 'head')
        from juno.auth import provision
        from juno.database import engine_for, sessions
        from juno.models import Device
        from juno.api import create_app
        import uvicorn
        engine = engine_for(url)
        factory = sessions(engine)
        saved = state / 'desktop-owner.json'
        previous = json.loads(saved.read_text()) if saved.exists() else {}
        with factory() as session:
            old = session.get(Device, previous['device_id']) if previous.get('device_id') else None
            if old is not None:
                old.revoked = True
            actor, token = provision(session, 'Juno native development app', previous.get('owner_id'))
            actor_id = actor.id
            session.commit()
            temporary = saved.with_suffix('.tmp')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as out:
                json.dump({'owner_id': actor.owner_id, 'device_id': actor.id}, out)
            temporary.replace(saved)
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        host, port = listener.getsockname()
        server = uvicorn.Server(uvicorn.Config(create_app(engine), access_log=False, log_level='warning'))
        print(json.dumps({'url': f'http://{host}:{port}', 'token': token}), flush=True)
        server.run(sockets=[listener])
    finally:
        if engine is not None and actor_id is not None:
            from juno.database import sessions
            from juno.models import Device
            with sessions(engine)() as session:
                actor = session.get(Device, actor_id)
                if actor:
                    actor.revoked = True
                    session.commit()
            engine.dispose()
        if not was_running and data.exists():
            subprocess.run([str(pg), '-D', str(data), '-m', 'fast', 'stop'],
                           stdout=sys.stderr, stderr=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No URLs, request bodies, credentials or raw database errors on stdout.
        print(json.dumps({'error': 'Local service could not start. See the development log.'}), flush=True)
        print(f'Juno helper stopped: {type(error).__name__}', file=sys.stderr)
        sys.exit(1)
