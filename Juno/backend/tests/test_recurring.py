"""Calendar and isolated API checks; never create real TaskDock tasks."""
from datetime import date, datetime, timezone
from uuid import uuid4
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from juno.recurring import RoutineInput, preview, creation_at
from juno.shared_host import LANBoundary
from test_memory_api import MemoryTests


class RoutineCalendarTests(unittest.TestCase):
    def rule(self, **values):
        return RoutineInput(title='Fictional checks', start_date='2030-01-07', **values)

    def test_week_anchor_interval_end_and_due(self):
        value = self.rule(frequency='weekly', interval=2, weekdays=[0, 2], end_date='2030-01-22', due_offset_days=2)
        dates = preview(value, date(2030, 1, 7))
        self.assertEqual([r['occurrence_date'] for r in dates], ['2030-01-07', '2030-01-09', '2030-01-21'])
        self.assertEqual(dates[-1]['due_date'], '2030-01-23')

    def test_month_end_and_ordinal_are_explicit(self):
        value = self.rule(frequency='monthly', month_day=31)
        self.assertEqual([r['occurrence_date'] for r in preview(value, date(2030, 2, 1), 2)], ['2030-03-31', '2030-05-31'])
        value.month_end = 'last_day'
        self.assertEqual(preview(value, date(2030, 2, 1), 1)[0]['occurrence_date'], '2030-02-28')
        value = self.rule(frequency='ordinal', ordinal=-1, weekday=4)
        self.assertEqual(preview(value, date(2030, 2, 1), 1)[0]['occurrence_date'], '2030-02-22')

    def test_dst_nonexistent_time_and_first_fold(self):
        value = self.rule(creation_time='02:30')
        spring = creation_at(value, date(2026, 3, 8))
        self.assertEqual(spring.hour, 3); self.assertEqual(spring.minute, 0)
        value.creation_time = '01:30'
        fall = creation_at(value, date(2026, 11, 1))
        self.assertEqual(fall.astimezone(timezone.utc), datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc))

    def test_invalid_inputs_and_no_hidden_execution_fields(self):
        for values in [{'weekdays': []}, {'weekdays': [8]}, {'ordinal': 0}, {'creation_time': '9:00'},
                       {'creation_time': '09:00:30'}, {'end_date': '2029-01-01'}, {'enabled': True}, {'timezone': 'UTC'}]:
            with self.subTest(values=values), self.assertRaises(ValueError): self.rule(**values)

    def test_upcoming_preview_excludes_elapsed_creation_time_today(self):
        value = RoutineInput(title='Fictional checks', start_date='2026-11-18', weekdays=[2])
        with patch('juno.recurring.now', return_value=datetime(2026, 11, 18, 16, tzinfo=timezone.utc)):
            self.assertEqual(preview(value, count=1)[0]['occurrence_date'], '2026-11-25')


class RoutineAPITests(MemoryTests):
    def test_history_retire_and_restore_preserve_definitions(self):
        from uuid import uuid4
        body={'request_id':str(uuid4()),'title':'Fictional routine history','start_date':'2030-01-07'}
        created=self.client.post('/v1/recurring',json=body)
        self.assertEqual(created.status_code,201,created.text)
        row=created.json();path='/v1/recurring/'+row['id']
        retired=self.client.post(path+'/lifecycle',json={'expected_revision':row['revision'],'action':'retire'})
        self.assertEqual(retired.status_code,200,retired.text)
        self.assertEqual(retired.json()['status'],'retired');self.assertEqual(retired.json()['next_occurrences'],[])
        restored=self.client.post(path+'/lifecycle',json={'expected_revision':retired.json()['revision'],'action':'restore'})
        self.assertEqual(restored.status_code,200,restored.text)
        self.assertEqual(restored.json()['definition'],row['definition'])
        history=self.client.get(path+'/history').json()
        self.assertEqual([v['action'] for v in history['versions']],['restore','retire','created'])
        self.assertEqual(history['occurrences'],[])
        self.assertEqual(self.client.get(path+'/history',headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
        self.assertEqual(self.client.post(path+'/lifecycle',json={'expected_revision':1,'action':'retire'}).status_code,409)

    def payload(self):
        return dict(title='Fictional printer checks', start_date='2030-01-07', request_id=str(uuid4()))

    def test_idempotent_draft_creation_isolated_and_revision_checked(self):
        body = self.payload()
        first = self.client.post('/v1/recurring', json=body)
        self.assertEqual(first.status_code, 201, first.text)
        row = first.json()
        self.assertEqual(row['status'], 'draft')
        self.assertEqual(self.client.post('/v1/recurring', json=body).json(), row)
        self.assertEqual(self.client.post('/v1/recurring', json={**body, 'title': 'Changed payload'}).status_code, 409)
        state = self.client.get('/v1/recurring').json()
        self.assertFalse(state['execution_available']); self.assertEqual(len(state['items']), 1)
        auth = {'Authorization': 'Bearer ' + self.other_token}
        self.assertEqual(self.client.get('/v1/recurring', headers=auth).json()['items'], [])
        edit = {k: v for k, v in body.items() if k != 'request_id'} | {'expected_revision': 1}
        self.assertEqual(self.client.put('/v1/recurring/' + row['id'], json=edit, headers=auth).status_code, 404)
        self.assertEqual(self.client.put('/v1/recurring/' + row['id'], json=edit).json()['revision'], 2)
        self.assertEqual(self.client.put('/v1/recurring/' + row['id'], json=edit).status_code, 409)
        cache = self.client.get('/v1/cache').json()
        self.assertTrue(any(p['path'] == '/v1/recurring' for p in cache['pages']))

    def test_lan_clients_read_but_cannot_create_or_preview_routines(self):
        with TestClient(LANBoundary(self.app), client=('10.12.1.2', 12345)) as remote:
            auth = {'Authorization': 'Bearer ' + self.token}
            self.assertEqual(remote.get('/v1/recurring', headers=auth).status_code, 200)
            self.assertEqual(remote.post('/v1/recurring', headers=auth, json=self.payload()).status_code, 403)
            self.assertEqual(remote.post('/v1/recurring/preview', headers=auth, json={}).status_code, 403)

    def test_validation_does_not_echo_private_title(self):
        response = self.client.post('/v1/recurring', json={'title': 'Private fictional note', 'enabled': True})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('Private fictional note', response.text)

    def test_schema_downgrade_refuses_saved_routine_loss(self):
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        self.assertEqual(self.client.post('/v1/recurring', json=self.payload()).status_code, 201)
        config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
        with self.engine.connect() as connection:
            config.attributes['connection'] = connection
            with self.assertRaisesRegex(RuntimeError, 'automatic data loss'):
                command.downgrade(config, '0017_chat_message_order')
            connection.rollback()
        self.assertTrue(self.client.get('/v1/recurring').json()['items'])
