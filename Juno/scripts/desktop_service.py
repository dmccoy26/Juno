"""Private local-development service owned by the native Juno application.

Handshake is sent only through the application's private stdout pipe.
Never run this helper in a terminal: the handshake contains a temporary token.
"""
import fcntl
import json
import os
import plistlib
import tarfile
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
    from juno.workspace_guard import read_identity, validate_owner, pin_identity
    previous = read_identity(state)
    pg = Path(os.environ.get('JUNO_POSTGRES_BIN', '/opt/homebrew/opt/postgresql@17/bin')) / 'pg_ctl'
    data = state / 'postgres/data'
    was_running = data.exists() and subprocess.run(
        [str(pg), '-D', str(data), 'status'], stdout=subprocess.DEVNULL).returncode == 0
    engine = None
    actor_id = None
    host_manager = None
    worker_manager = None
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
        # Back up on every release change, including updates without migrations.
        info = ROOT.parent.parent / 'Info.plist'
        release = (plistlib.loads(info.read_bytes()).get('JunoReleaseVersion', 'development')
                   if info.exists() else json.loads((ROOT/'packaging/release.json').read_text())['version'])
        receipt = state/'last-successful-release.json'
        last_release = json.loads(receipt.read_text()).get('release') if receipt.exists() else None
        if inspect(engine).has_table('alembic_version'):
            with engine.connect() as connection:
                installed = connection.scalar(text('SELECT version_num FROM alembic_version'))
            if installed != expected or last_release != release:
                backups = state/'backups'; backups.mkdir(mode=0o700, exist_ok=True)
                backup = backups/(time.strftime('%Y%m%d-%H%M%S')+'-'+str(time.time_ns())+'-before-update.dump')
                subprocess.run([str(pg.parent/'pg_dump'), '-h', str(state/'postgres/socket'), '-U', 'juno',
                                '-d', 'juno_dev', '-Fc', '-f', str(backup)], check=True, stdout=sys.stderr)
                backup.chmod(0o600)
                subprocess.run([str(pg.parent/'pg_restore'), '--list', str(backup)], check=True, stdout=subprocess.DEVNULL)
                # Preserve identity, pinned TLS and hosting configuration beside the DB dump.
                archive = backup.with_suffix('.settings.tar.gz')
                fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as output, tarfile.open(fileobj=output, mode='w:gz') as bundle:
                    for name in ('desktop-owner.json', 'workspace-identity.json', 'last-successful-release.json', 'shared-host', 'worker-portal'):
                        if (state/name).exists(): bundle.add(state/name, arcname=name)
                with tarfile.open(archive, 'r:gz') as bundle: bundle.getmembers()

        command.upgrade(config, 'head')
        factory = sessions(engine)
        saved = state / 'desktop-owner.json'
        with factory() as session:
            from juno.models import Owner
            from sqlalchemy import select
            validate_owner(previous, session.scalars(select(Owner.id)))
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
            pin_identity(state, actor.owner_id)
            release_temp = receipt.with_suffix('.tmp')
            fd = os.open(release_temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as output: json.dump({'release': release}, output)
            release_temp.replace(receipt)
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(128)
        host, port = listener.getsockname()
        from juno.shared_host import HostManager
        host_manager = HostManager(state)
        from sqlalchemy import select
        from juno.worker_host import WorkerHostManager
        from juno.models import WorkerPortal
        worker_manager = WorkerHostManager(state)
        app = create_app(engine, host_manager=host_manager, worker_manager=worker_manager)
        worker_manager.app = app
        with factory() as session:
            restart_workers = session.scalar(select(WorkerPortal.owner_id).where(WorkerPortal.enabled.is_(True))) is not None
        if restart_workers:
            try: worker_manager.start()
            except Exception: worker_manager.error = "Worker HTTPS could not restart. Check its approved certificate and network configuration."
        host_manager.app = app
        if host_manager.config.get('enabled'):
            try: host_manager.set_enabled(True)
            except Exception: host_manager.error = 'Shared hosting could not restart. Check the network host screen.'
        server = uvicorn.Server(uvicorn.Config(app, access_log=False, log_level='warning', proxy_headers=False))
        print(json.dumps({'url': f'http://{host}:{port}', 'token': token}), flush=True)
        server.run(sockets=[listener])
    finally:
        if worker_manager is not None: worker_manager.close()
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
        from juno.workspace_guard import WorkspaceError
        message = str(error) if isinstance(error, WorkspaceError) else 'Local service could not start. See the development log.'
        print(json.dumps({'error': message}), flush=True)
        print(f'Juno helper stopped: {type(error).__name__}', file=sys.stderr)
        sys.exit(1)
