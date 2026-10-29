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
    host_manager = None
    try:
        subprocess.run([sys.executable, str(ROOT / 'scripts/dev_database.py'), 'start'],
                       check=True, stdout=sys.stderr)
        url = subprocess.check_output([sys.executable, str(ROOT / 'scripts/dev_database.py'), 'url'], text=True).strip()
        os.environ['JUNO_DATABASE_URL'] = url
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from sqlalchemy import inspect, text
        from juno.auth import provision
        from juno.database import engine_for, sessions
        from juno.models import Device, Message
        from juno.api import create_app
        import uvicorn
        engine = engine_for(url)
        config = Config(str(ROOT / 'backend/alembic.ini'))
        expected = ScriptDirectory.from_config(config).get_current_head()
        if inspect(engine).has_table('alembic_version'):
            with engine.connect() as connection:
                installed = connection.scalar(text('SELECT version_num FROM alembic_version'))
            if installed != expected:
                backups = state/'backups'; backups.mkdir(mode=0o700, exist_ok=True)
                backup = backups/(time.strftime('%Y%m%d-%H%M%S')+'-before-'+expected+'.dump')
                subprocess.run([str(pg.parent/'pg_dump'), '-h', str(state/'postgres/socket'), '-U', 'juno',
                                '-d', 'juno_dev', '-Fc', '-f', str(backup)], check=True, stdout=sys.stderr)
                backup.chmod(0o600)
                subprocess.run([str(pg.parent/'pg_restore'), '--list', str(backup)], check=True, stdout=subprocess.DEVNULL)
        command.upgrade(config, 'head')
        factory = sessions(engine)
        saved = state / 'desktop-owner.json'
        previous = json.loads(saved.read_text()) if saved.exists() else {}
        with factory() as session:
            # This helper owns the exclusive local service lock. Pending replies
            # from a previous process cannot still be running after a restart.
            from sqlalchemy import update
            session.execute(update(Message).where(Message.status == 'pending').values(
                status='failed', text='This reply was interrupted. You can retry it.', context_refs={}))
            old = session.get(Device, previous['device_id']) if previous.get('device_id') else None
            if old is not None:
                old.revoked = True
            actor, token = provision(session, 'Juno on this Mac', previous.get('owner_id'))
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
        from juno.shared_host import HostManager
        host_manager = HostManager(state)
        app = create_app(engine, host_manager=host_manager)
        host_manager.app = app
        if host_manager.config.get('enabled'):
            try: host_manager.set_enabled(True)
            except Exception: host_manager.error = 'Shared hosting could not restart. Check the network host screen.'
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False))
        print(json.dumps({'url': f'http://{host}:{port}', 'token': token}), flush=True)
        server.run(sockets=[listener])
    finally:
        if host_manager is not None: host_manager.close()
        if engine is not None and actor_id is not None:
            from juno.database import sessions
            from juno.models import Device
            with sessions(engine)() as session:
                actor = session.get(Device, actor_id)
                if actor:
                    actor.revoked = True
                    session.commit()
        if engine is not None:
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
