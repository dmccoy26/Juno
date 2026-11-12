from datetime import datetime, timezone
from unittest.mock import patch

import test_daily_brief as daily
from juno.models import IntegrationSnapshot


class ChairsDraftTests(daily.DailyBriefTests):
    def test_recipient_edits_and_routing(self):
        path = '/v1/planning/chairs-draft/2030-01-07'
        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        self.snapshot(lambda tasks: tasks + [
            {'id': 'stacker', 'title': 'Sorin stacker'},
            {'id': 'theater', 'title': 'A140M03 check-in'},
            {'id': 'toner', 'title': 'Holy Cross 203 toner'},
            {'id': 'scanner', 'title': 'Flextight scanner'},
        ])
        with patch('juno.chairs_report.now', return_value=cutoff):
            response = self.client.post(path + '/prepare', json={})
            self.assertEqual(response.status_code, 200, response.text)
            emails = response.json()['emails']
            for key, title in [('lwr', 'Sorin stacker'), ('visu', 'Flextight scanner'),
                               ('performing', 'A140M03 check-in')]:
                self.assertEqual([recipient for recipient, mail in emails.items() if title in mail['body']], [key])
            self.assertFalse(any('Holy Cross 203 toner' in mail['body'] for mail in emails.values()))
            edit = {'recipient': 'visu', 'subject': emails['visu']['subject'],
                    'body': 'Reviewed Visual Studies email', 'expected_revision': 1}
            saved = self.client.put(path, json=edit).json()['emails']
            self.assertEqual(saved['visu']['body'], edit['body'])
            self.assertEqual(saved['lwr'], emails['lwr'])
            self.assertEqual(saved['performing'], emails['performing'])

    def test_weekly_draft_uses_three_sources_and_preserves_reviewed_edits(self):
        path = '/v1/planning/chairs-draft/2030-01-07'
        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        self.snapshot(lambda tasks: tasks + [
            {'id': 'closed', 'title': 'Fictional print driver', 'completed_at': '2030-01-09T18:00:00Z'},
            {'id': 'test', 'title': 'Test fictional task'},
        ])
        with self.factory() as session:
            session.add_all([
                IntegrationSnapshot(owner_id=self.actor.owner_id, kind='beacon', origin='Fictional',
                                    fetched_at=cutoff, details={'generated_at': cutoff.isoformat()},
                                    items=[{'id': 'alert', 'item': 'Fictional copier', 'problem': 'Paper jam',
                                            'issue_state': 'open'}]),
                IntegrationSnapshot(owner_id=self.actor.owner_id, kind='smartsheet', origin='Fictional',
                                    fetched_at=cutoff,
                                    details={'completion_archive': {'sheet_id': '1001', 'completion_date_column': 'Closed Date'}},
                                    items=[{'id': 'archive', 'title': 'Fictional lab repair',
                                            'archive_completed_on': '2030-01-09', 'provider_ids': {'sheet_id': '1001'}}]),
            ])
            session.commit()
        with patch('juno.chairs_report.now', return_value=cutoff):
            response = self.client.post(path + '/prepare', json={})
            self.assertEqual(response.status_code, 200, response.text)
            draft = response.json()
            for entry in ('Fictional classroom repair', 'Fictional print driver',
                          'Fictional copier', 'Fictional lab repair'):
                self.assertIn('• ' + entry, draft['body'])
            self.assertNotIn('Test fictional task', draft['body'])
            self.assertIn('Jan 4–Jan 10', draft['subject'])
            edited = {'subject': draft['subject'], 'body': 'Reviewed wording', 'expected_revision': draft['revision']}
            self.assertEqual(self.client.put(path, json=edited).status_code, 200)
            self.assertEqual(self.client.post(path + '/prepare', json={}).json()['body'], 'Reviewed wording')
            self.assertEqual(self.client.put(path, json=edited | {'body': 'Competing edit'}).status_code, 409)
            self.assertFalse(self.client.get(path, headers={'Authorization': 'Bearer ' + self.other_token}).json()['exists'])
