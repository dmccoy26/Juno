"""Prove additive-schema preservation and detect data changes in a disposable cluster."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend/src'))
from check_update_preservation import capture, compare


with tempfile.TemporaryDirectory(prefix='juno-preserve-', dir='/tmp') as temporary:
    state = Path(temporary)
    env = {**os.environ, 'JUNO_DATA_ROOT': str(state)}
    started = False
    try:
        subprocess.run([sys.executable, str(ROOT/'scripts/dev_database.py'), 'start'], env=env, check=True)
        started = True
        url = subprocess.check_output([sys.executable, str(ROOT/'scripts/dev_database.py'), 'url'], env=env, text=True).strip()
        from sqlalchemy import text
        from juno.database import engine_for, sessions
        from juno.auth import provision
        from alembic import command
        from alembic.config import Config
        engine = engine_for(url)
        config = Config(str(ROOT/'backend/alembic.ini'))
        with engine.connect() as connection:
            config.attributes['connection'] = connection
            command.upgrade(config, 'head')
        with sessions(engine)() as session:
            actor, _ = provision(session, 'Synthetic preservation fixture')
            session.commit()
            (state/'desktop-owner.json').write_text(json.dumps({'owner_id':actor.owner_id}))
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE preservation_fixture (id integer PRIMARY KEY, value text NOT NULL)'))
            connection.execute(text("INSERT INTO preservation_fixture VALUES (1,'Original synthetic value')"))
        before = capture(state)
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE preservation_fixture ADD COLUMN additive boolean NOT NULL DEFAULT false'))
        compare(before, capture(state, before['columns']))
        with engine.begin() as connection:
            connection.execute(text("UPDATE preservation_fixture SET value='Unexpected changed value'"))
        try:
            compare(before, capture(state, before['columns']))
        except ValueError as error:
            assert 'preservation_fixture' in str(error)
        else:
            raise AssertionError('Changed original work data passed preservation.')
        engine.dispose()
        print('PASS additive fields preserve every old field fingerprint; changed work data is rejected')
    finally:
        if started:
            subprocess.run([sys.executable, str(ROOT/'scripts/dev_database.py'), 'stop'], env=env, check=True)
