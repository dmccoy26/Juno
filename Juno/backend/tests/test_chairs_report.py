from datetime import datetime, timezone
from unittest.mock import patch

import test_daily_brief as daily
from juno.local_model import LocalModel, ModelError
from juno.models import IntegrationSnapshot, ModelConnection


class ChairsDraftTests(daily.DailyBriefTests):
    def test_missing_archive_attribution(self):
        self.check_archive_attribution('missing')

    def test_archive_attribution_requires_routed_records(self):
        self.check_archive_attribution('matching')

    def test_inactive_archive_attribution(self):
        self.check_archive_attribution('inactive')

    def check_archive_attribution(self, case):
        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        with self.factory() as session:
            session.add(ModelConnection(owner_id=self.actor.owner_id,
                                        base_url='http://127.0.0.1:1234/v1', model='fixture'))
            if case != 'missing':
                session.add(IntegrationSnapshot(
                    owner_id=self.actor.owner_id, kind='smartsheet', origin='Fictional',
                    fetched_at=cutoff, details={'active': case != 'inactive', 'completion_archive': {
                        'sheet_id': '1001', 'completion_date_column': 'Closed Date'}},
                    items=[
                        {'id': 'dated', 'title': 'Flextight lamp replacement',
                         'archive_completed_on': '2030-01-09', 'provider_ids': {'sheet_id': '1001'}},
                        {'id': 'modified', 'title': 'Flextight cable replacement',
                         'notes': 'Status: Completed\nModified: 2030-01-09T18:00:00Z',
                         'provider_ids': {'sheet_id': '1001'}},
                        {'id': 'old', 'title': 'Sorin tray repair',
                         'archive_completed_on': '2030-01-01', 'provider_ids': {'sheet_id': '1001'}},
                    ]))
            session.commit()

        def compose(_client, messages, _model):
            evidence = messages[1]['content']
            self.assertNotIn('Flextight', evidence)
            self.assertNotIn('Smartsheet', evidence)
            if evidence.startswith('Visual Studies'):
                return 'Howdy Alex,\n\nI checked the Smartsheet archive.\n\n-Dan'
            return evidence.split('\n\n', 1)[1]

        with patch('juno.chairs_report.now', return_value=cutoff), patch.object(LocalModel, 'compose_email', compose):
            response = self.client.post('/v1/planning/chairs-draft/2030-01-07/prepare', json={})
        self.assertEqual(response.status_code, 200, response.text)
        emails = response.json()['emails']
        visu = emails['visu']
        self.assertEqual(visu['composition'], 'fallback')
        self.assertNotIn('I checked', visu['body'])
        self.assertNotIn('Last updated', visu['body'])
        if case == 'matching':
            self.assertIn('The saved Smartsheet archive records these closures.', visu['body'])
            self.assertIn('Flextight lamp replacement', visu['body'])
            self.assertIn('Flextight cable replacement', visu['body'])
            self.assertTrue(any('Last updated' in note for note in visu['coverage']))
            self.assertNotIn('no updates', visu['body'])
        else:
            self.assertNotIn('archive', visu['body'].casefold())
        for key in ('lwr', 'performing'):
            self.assertEqual(emails[key]['composition'], 'lm_studio')
            self.assertNotIn('archive', emails[key]['body'].casefold())
            self.assertNotIn('Sorin tray repair', emails[key]['body'])

    def test_records_model_outcome_for_each_recipient(self):
        with self.factory() as session:
            session.add(ModelConnection(owner_id=self.actor.owner_id, base_url='http://127.0.0.1:1234/v1', model='fixture'))
            session.commit()

        def compose(_client, _model, _subject, evidence, recipient):
            if recipient == 'visu':
                raise ModelError('Fictional model failure')
            return evidence

        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        with patch('juno.chairs_report.now', return_value=cutoff), patch('juno.chairs_report.write_email', side_effect=compose):
            response = self.client.post('/v1/planning/chairs-draft/2030-01-07/prepare', json={})
        self.assertEqual(response.status_code, 200, response.text)
        saved = self.client.get('/v1/planning/chairs-draft/2030-01-07').json()['emails']
        self.assertEqual({key: mail['composition'] for key, mail in saved.items()},
                         {'lwr': 'lm_studio', 'visu': 'fallback', 'performing': 'lm_studio'})
        self.assertTrue(any('LM Studio' in note for note in saved['visu']['coverage']))

    def test_recipient_edits_and_routing(self):
        path = '/v1/planning/chairs-draft/2030-01-07'
        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        self.snapshot(lambda tasks: tasks + [
            {'id': 'stacker', 'title': 'Sorin stacker'},
            {'id': 'theater', 'title': 'A140M03 check-in'},
            {'id': 'toner', 'title': 'Holy Cross 203 toner'},
            {'id': 'tray', 'title': 'Holy Cross 326 tray'},
            {'id': 'scanner', 'title': 'Flextight scanner'},
        ])
        with patch('juno.chairs_report.now', return_value=cutoff):
            response = self.client.post(path + '/prepare', json={})
            self.assertEqual(response.status_code, 200, response.text)
            draft = response.json()
            emails = draft['emails']
            for key, title in [('lwr', 'Sorin stacker'), ('visu', 'Flextight scanner'),
                               ('performing', 'A140M03 check-in')]:
                self.assertEqual([recipient for recipient, mail in emails.items() if title in mail['body']], [key])
            for key, name in [('lwr', 'Amy'), ('visu', 'Alex'), ('performing', 'Kathryn')]:
                self.assertTrue(emails[key]['body'].startswith(f'Howdy {name},\n'))
                self.assertEqual(emails[key]['composition'], 'built_in')
            for mail in [draft, *emails.values()]:
                self.assertTrue(mail['body'].endswith('\n-Dan'))
                self.assertNotIn('Holy Cross 203 toner', mail['body'])
                self.assertNotIn('Holy Cross 326 tray', mail['body'])
            edit = {'recipient': 'visu', 'subject': emails['visu']['subject'],
                    'body': 'Reviewed Visual Studies email', 'expected_revision': 1}
            saved = self.client.put(path, json=edit).json()['emails']
            self.assertEqual(saved['visu']['body'], edit['body'])
            self.assertEqual(saved['visu']['composition'], 'built_in')
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
                                            'archive_completed_on': '2030-01-09', 'provider_ids': {'sheet_id': '1001'}},
                                           {'id': 'updated', 'title': 'Flextight fixture archive update',
                                            'notes': 'Status: Completed\nModified: 2030-01-09T18:00:00Z',
                                            'provider_ids': {'sheet_id': '1001'}}]),
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
            visu = draft['emails']['visu']
            self.assertIn('The archive also lists these items as completed. Flextight fixture archive update.', visu['body'])
            self.assertNotIn('Jan 9 at', visu['body'])
            self.assertTrue(any('Last updated Jan 9 at 12:00 PM Central' in note for note in visu['coverage']))
            self.assertNotIn('Flextight fixture archive update', draft['emails']['lwr']['body'])
            edited = {'subject': draft['subject'], 'body': 'Reviewed wording', 'expected_revision': draft['revision']}
            self.assertEqual(self.client.put(path, json=edited).status_code, 200)
            self.assertEqual(self.client.post(path + '/prepare', json={}).json()['body'], 'Reviewed wording')
            self.assertEqual(self.client.put(path, json=edited | {'body': 'Competing edit'}).status_code, 409)
            self.assertFalse(self.client.get(path, headers={'Authorization': 'Bearer ' + self.other_token}).json()['exists'])
