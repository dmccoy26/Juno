"""Integration tests use a fresh random PostgreSQL DB, never application data."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import unittest
import uuid

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from juno.api import create_app
from juno.auth import provision
from juno.database import engine_for, sessions
from juno.models import Audit, Device, Memory


@unittest.skipUnless(os.environ.get('JUNO_TEST_ADMIN_URL'), 'Set JUNO_TEST_ADMIN_URL for PostgreSQL integration tests')
class MemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = engine_for(os.environ['JUNO_TEST_ADMIN_URL']).execution_options(isolation_level='AUTOCOMMIT')
        cls.name = 'juno_test_' + uuid.uuid4().hex
        with cls.admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{cls.name}"'))
        cls.engine = create_engine(cls.admin.url.set(database=cls.name), hide_parameters=True)
        cfg = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
        with cls.engine.connect() as connection:
            cfg.attributes['connection'] = connection
            command.upgrade(cfg, 'head')
        cls.factory = sessions(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        with cls.admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{cls.name}" WITH (FORCE)'))
        cls.admin.dispose()

    def setUp(self):
        with self.factory() as session:
            self.actor, self.token = provision(session, 'Synthetic owner')
            self.other, self.other_token = provision(session, 'Other synthetic owner')
            self.second, self.second_token = provision(session, 'Second device', self.actor.owner_id)
            session.commit()
        self.app = create_app(self.engine)
        self.client = TestClient(self.app)
        self.client.headers['Authorization'] = 'Bearer ' + self.token
        self.value = dict(text='Synthetic print lab opens at nine.', source='manual:test', confidence='confirmed')

    def tearDown(self):
        self.client.close()

    def create(self):
        response = self.client.post('/v1/memories', json=self.value)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_migration_is_current_and_matches_models(self):
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext
        from juno.models import Base
        with self.engine.connect() as connection:
            self.assertEqual(compare_metadata(MigrationContext.configure(connection), Base.metadata), [])
            self.assertEqual(connection.scalar(text('SELECT version_num FROM alembic_version')), '0008_memory_origin')

    def test_missing_invalid_revoked_auth(self):
        for headers in [{}, {'Authorization': 'Bearer invalid'}]:
            with TestClient(self.app) as client:
                self.assertEqual(client.get('/v1/memories', headers=headers).status_code, 401)
        with self.factory() as session:
            session.get(Device, self.actor.id).revoked = True
            session.commit()
        self.assertEqual(self.client.get('/v1/memories').status_code, 401)

    def test_owner_isolation_for_every_operation(self):
        row = self.create()
        auth = {'Authorization': 'Bearer ' + self.other_token}
        self.assertEqual(self.client.get('/v1/memories', headers=auth).json()['items'], [])
        path = '/v1/memories/' + row['id']
        self.assertEqual(self.client.get(path, headers=auth).status_code, 404)
        self.assertEqual(self.client.put(path, headers=auth, json={**self.value, 'expected_revision': 1}).status_code, 404)
        self.assertEqual(self.client.delete(path, headers=auth, params={'expected_revision': 1}).status_code, 404)
        self.assertEqual(self.client.post('/v1/memories', json={**self.value, 'owner_id': self.other.owner_id}).status_code, 422)

    def test_correction_persists_across_device_and_restart(self):
        row = self.create()
        path = '/v1/memories/' + row['id']
        update = {**self.value, 'text': 'Synthetic print lab opens at ten.', 'expected_revision': 1}
        corrected = self.client.put(path, json=update)
        self.assertEqual(corrected.status_code, 200, corrected.text)
        self.assertEqual(corrected.json()['revision'], 2)
        with TestClient(create_app(self.engine)) as second:
            second.headers['Authorization'] = 'Bearer ' + self.second_token
            self.assertEqual(second.get(path).json()['text'], update['text'])
            self.assertEqual(second.get('/v1/memories', params={'q': 'nine'}).json()['items'], [])
        self.assertEqual(self.client.put(path, json=update).status_code, 409)
        self.assertEqual(self.client.post('/v1/memories', json=self.value).status_code, 409)

    def test_delete_removes_canonical_text_and_blocks_reimport(self):
        row = self.create()
        path = '/v1/memories/' + row['id']
        self.assertEqual(self.client.delete(path, params={'expected_revision': 99}).status_code, 409)
        self.assertEqual(self.client.delete(path, params={'expected_revision': 1}).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get('/v1/memories', params={'q': 'print lab'}).json()['items'], [])
        self.assertEqual(self.client.post('/v1/memories', json=self.value).status_code, 409)
        with self.factory() as session:
            self.assertIsNone(session.get(Memory, row['id']))
            events = session.scalars(select(Audit).where(Audit.record_id == row['id'])).all()
            self.assertEqual({e.action for e in events}, {'memory.created', 'memory.deleted'})
            self.assertNotIn('text', inspect(Audit).columns)

    def test_competing_edits_do_not_overwrite(self):
        row = self.create()
        def edit(number):
            with TestClient(create_app(self.engine)) as client:
                return client.put('/v1/memories/' + row['id'],
                    headers={'Authorization': 'Bearer ' + self.token},
                    json={**self.value, 'text': f'Synthetic concurrent edit {number}', 'expected_revision': 1}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(edit, [1, 2])), [200, 409])

    def test_search_treats_wildcards_literally_and_does_not_cache(self):
        self.create()
        response = self.client.get('/v1/memories', params={'q': '%'})
        self.assertEqual(response.json()['items'], [])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_duplicate_and_empty_memory_rejected(self):
        self.create()
        self.assertEqual(self.client.post('/v1/memories', json=self.value).status_code, 409)
        self.assertEqual(self.client.post('/v1/memories', json={**self.value, 'text': '  '}).status_code, 422)
