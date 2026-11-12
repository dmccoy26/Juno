import json
import unittest
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
import test_daily_brief as daily_tests

from juno.dean_follow_up import extract
from juno.shared_host import LANBoundary


NOTES = """###From the Dean
-Attend Leadership Council on December 7
-Schedule a budget discussion before break
-Add the support document to SEEDS

### Zoom summary
-A separate suggestion from someone else
"""


class ExtractionTests(unittest.TestCase):
    def test_explicit_requests_work_without_a_model(self):
        result = extract(NOTES, date(2030, 1, 6), None, None)
        self.assertEqual([item.title for item in result.items], [
            'Attend Leadership Council on December 7',
            'Schedule a budget discussion before break',
            'Add the support document to SEEDS',
        ])

    def test_model_can_enrich_an_explicit_request_without_displacing_other_requests(self):
        class Model:
            def complete(self, messages, model):
                return json.dumps({'items': [
                    {'title': 'Attend Leadership Council', 'timing': 'December 7',
                     'quote': '-Attend Leadership Council on December 7'},
                    {'title': 'Extra item', 'quote': '-A separate suggestion from someone else'},
                ]})

        result = extract(NOTES, date(2030, 1, 6), ('http://localhost:1234/v1', 'example'), lambda _: Model())
        self.assertEqual(len(result.items), 3)
        self.assertEqual(result.items[0].timing, 'December 7')
        self.assertEqual(result.items[2].title, 'Add the support document to SEEDS')

    def test_model_quotes_must_come_from_the_notes(self):
        class Model:
            def complete(self, messages, model):
                return '{"items":[{"title":"Fabricated action","quote":"Fabricated request"}]}'

        with self.assertRaises(ValueError):
            extract('Reviewed the new plan.', date(2030, 1, 6),
                    ('http://localhost:1234/v1', 'example'), lambda _: Model())


class FollowUpTests(daily_tests.DailyBriefTests):
    path = '/v1/planning/dean-follow-up/2030-01-06'

    def test_review_is_owner_scoped_replay_safe_and_carries_into_plan_and_briefing(self):
        suggestion = self.client.post(self.path + '/extract', json={'notes': NOTES})
        self.assertEqual(suggestion.status_code, 200)
        self.assertEqual(self.client.get(self.path).json()['revision'], 0)
        items = [item | {'id': str(uuid4())} for item in suggestion.json()['items']]
        items[0].update(task_id='dean', workspace_id='fictional', waiting_on='Invitation')
        items[2]['closed'] = True
        payload = {'notes': NOTES, 'expected_revision': 0, 'items': items}
        invalid = payload | {'items': [items[0] | {'workspace_id': 'another-workspace'}]}
        self.assertEqual(self.client.put(self.path, json=invalid).status_code, 409)
        saved = self.client.put(self.path, json=payload)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.put(self.path, json=payload).json(), saved.json())
        self.assertEqual(self.client.put(self.path, json=payload | {'items': []}).status_code, 409)

        with TestClient(LANBoundary(self.app), client=('10.1.2.3', 50000)) as paired:
            paired.headers['Authorization'] = 'Bearer ' + self.second_token
            self.assertEqual(paired.get(self.path).json(), saved.json())
            self.assertTrue(any(page['path'] == self.path for page in paired.get('/v1/cache').json()['pages']))
            paired.headers['Authorization'] = 'Bearer ' + self.other_token
            self.assertEqual(paired.get(self.path).json()['revision'], 0)
            self.assertFalse(any(page['path'] == self.path for page in paired.get('/v1/cache').json()['pages']))

        plan = self.client.get('/v1/planning/next?day=2030-01-07').json()
        task = next(task for task in plan['tasks'] if task['task_id'] == 'dean')
        self.assertTrue(task['dean'])
        self.assertEqual(task['blocker'], 'Waiting on Invitation')
        weekly = '/v1/planning/weekly?day=2030-01-07'
        draft = self.client.get(weekly).json()['text']
        self.assertIn('• Attend Leadership Council on December 7', draft)
        self.assertIn('• Schedule a budget discussion before break', draft)
        self.assertNotIn('• Add the support document to SEEDS', draft)

        self.snapshot(lambda tasks: [
            task | {'source_completed': True} if task['id'] == 'dean' else task for task in tasks
        ])
        self.assertNotIn('• Attend Leadership Council on December 7', self.client.get(weekly).json()['text'])
