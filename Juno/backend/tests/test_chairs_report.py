from datetime import datetime, timezone
from unittest.mock import patch

import test_daily_brief as daily
from juno.local_model import LocalModel, ModelError
from juno.models import IntegrationSnapshot, ModelConnection, OperationalState


class ChairsDraftTests(daily.DailyBriefTests):
    def test_report_library_pages_weeks_scopes_owners_and_retains_legacy(self):
        from datetime import date, timedelta
        from juno.models import ChairsDraft, DeanDraft
        with self.factory() as session:
            for number in range(21):
                week = date(2026,11,16)-timedelta(weeks=number)
                session.add(ChairsDraft(owner_id=self.actor.owner_id,week_start=week,subject='Fictional legacy',body='Fictional body',coverage=[],emails={} if number==20 else {'visu':{'subject':'Fictional VISU','body':'Howdy Alex,\n\nFictional body.\n\n-Dan','coverage':[]}},revision=1))
            session.add(DeanDraft(owner_id=self.actor.owner_id,week_start=date(2026,11,16),text='Fictional talking points',basis={}))
            session.commit()
        first=self.client.get('/v1/reports/index?offset=0').json()
        self.assertTrue(first['has_more']);self.assertEqual(first['next_offset'],20)
        self.assertEqual(len({r['week'] for r in first['items']}),20)
        self.assertEqual(first['items'][0]['kind'],'dean')
        self.assertNotIn('body',first['items'][0])
        last=self.client.get('/v1/reports/index?offset=20').json()
        self.assertFalse(last['has_more']);self.assertEqual(last['items'][0]['audience'],'all')
        self.assertFalse(set(r['id'] for r in first['items']) & set(r['id'] for r in last['items']))
        self.assertEqual(self.client.get('/v1/reports/index',headers={'Authorization':'Bearer '+self.other_token}).json()['items'],[])
        pages=self.client.get('/v1/cache').json()['pages']
        self.assertEqual(next(p['body'] for p in pages if p['path']=='/v1/reports/index?offset=20'),last)

    def test_selected_evidence_preview_and_reviewed_save(self):
        week = '2030-01-07'
        path = '/v1/planning/chairs-draft/' + week
        self.snapshot(lambda tasks: tasks + [
            {'id':'scoped-lab','title':'ARTS 121 fictional cable replacement'},
            {'id':'dean-only','title':'Holy Cross 203 toner'},
        ])
        cutoff = datetime(2030, 1, 11, 15, tzinfo=timezone.utc)
        with self.factory() as session:
            session.add(IntegrationSnapshot(owner_id=self.actor.owner_id, kind='smartsheet', origin='Fictional archive', fetched_at=cutoff,
                details={'active':True, 'completion_archive':{'sheet_id':'1001', 'completion_date_column':'Closed'}},
                items=[{'id':'closure-fixture', 'title':'Flextight fictional lamp', 'archive_completed_on':'2030-01-09', 'provider_ids':{'sheet_id':'1001'}}]))
            session.commit()
        with patch('juno.chairs_report.now', return_value=cutoff):
            original = self.client.post(path + '/prepare', json={}).json()
            endpoint = '/v1/reports/chairs/' + week
            packet = self.client.get(endpoint + '/evidence?recipient=visu').json()
            ids = [item['id'] for item in packet['items']]
            self.assertIn('archive:1001:closure-fixture', ids)
            self.assertFalse(any('dean-only' in identity for identity in ids))
            payload = {'recipient':'visu','expected_revision':original['revision'], 'token':packet['token'], 'selected_ids':['archive:1001:closure-fixture']}
            preview = self.client.post(endpoint + '/preview', json=payload)
            self.assertEqual(preview.status_code, 200, preview.text)
            self.assertIn('Flextight fictional lamp', preview.json()['body'])
            self.assertNotIn('fictional cable replacement', preview.json()['body'])
            self.assertEqual(self.client.get(path).json(), original)
            bad = self.client.post(endpoint + '/preview', json={**payload,'selected_ids':['taskdock:student-test-workspace:dean-only']})
            self.assertEqual(bad.status_code, 422)
            self.assertEqual(self.client.get(endpoint + '/evidence?recipient=visu', headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
            proposal = preview.json()
            saved = self.client.put(path, json={'recipient':'visu','expected_revision':original['revision'], 'subject':proposal['subject'], 'body':proposal['body'],
                'evidence_selection':{'token':packet['token'],'selected_ids':payload['selected_ids']}})
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json()['emails']['lwr'], original['emails']['lwr'])
            self.assertEqual(saved.json()['emails']['visu']['composition'], 'reviewed_evidence')
            history = self.client.get('/v1/reports/chairs/' + week + '/history').json()['items']
            self.assertEqual(history[-1]['content']['emails']['visu']['body'], original['emails']['visu']['body'])
            self.snapshot(lambda tasks: [{**task, 'title':task.get('title','')+' changed'} if str(task['id'])=='scoped-lab' else task for task in tasks])
            stale = self.client.post(endpoint + '/preview', json={**payload,'expected_revision':saved.json()['revision']})
            self.assertEqual(stale.status_code,409)

    def test_history_style_and_review_are_recipient_scoped(self):
        path = '/v1/planning/chairs-draft/2030-01-07'
        with patch('juno.chairs_report.now', return_value=datetime(2030, 1, 11, 15, tzinfo=timezone.utc)):
            first = self.client.post(path + '/prepare', json={}).json()
        email = first['emails']['visu']
        middle = 'Keep this paragraph exactly: 17 ± 4.\nSecond line.\n\n'
        old_body = 'Dear Department Chair,\n\n' + middle + 'Thanks,\nDan'
        edit = self.client.put(path, json={'expected_revision':first['revision'], 'recipient':'visu', 'subject':email['subject'], 'body':old_body})
        self.assertEqual(edit.status_code, 200, edit.text)
        styled = self.client.post(path + '/style', json={'expected_revision':edit.json()['revision'], 'recipient':'visu'})
        self.assertEqual(styled.status_code, 200, styled.text)
        current = styled.json()
        self.assertEqual(current['emails']['visu']['body'], 'Howdy Alex,\n\n' + middle + '-Dan')
        self.assertEqual(current['emails']['lwr'], first['emails']['lwr'])
        history_path = '/v1/reports/chairs/2030-01-07/history'
        history = self.client.get(history_path).json()['items']
        self.assertEqual([r['revision'] for r in history], [3,2,1])
        self.assertEqual(history[1]['content']['emails']['visu']['body'], old_body)
        review_path = '/v1/reports/chairs/2030-01-07/review'
        marked = self.client.post(review_path, json={'expected_revision':3, 'audience':'visu'})
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertTrue(next(r for r in marked.json()['items'] if r['audience']=='visu')['reviewed'])
        current_body = current['emails']['visu']['body']
        self.client.put(path, json={'expected_revision':3, 'recipient':'visu', 'subject':email['subject'], 'body':current_body + '\nAnother reviewed fact.'})
        self.assertFalse(next(r for r in self.client.get(review_path).json()['items'] if r['audience']=='visu')['reviewed'])
        other = {'Authorization':'Bearer ' + self.other_token}
        self.assertEqual(self.client.get(history_path, headers=other).json()['items'], [])
        self.assertEqual(self.client.post(review_path, json={'expected_revision':4,'audience':'visu'}, headers=other).status_code, 404)

    def test_reviewed_addition_is_scoped_preserved_and_included_once(self):
        addition = 'Fictional VISU expense reports total $42.50 and remain pending external validation.'
        with self.factory() as session:
            session.add(OperationalState(owner_id=self.actor.owner_id, data={
                'weekly_report_updates': {
                    '2030-01-07': {'visu': [{'text': addition, 'source': 'Reviewed fictional statement'}]},
                    '2030-01-14': {'visu': [{'text': 'Other week', 'source': 'Fictional'}]},
                }}))
            session.commit()
        path = '/v1/planning/chairs-draft/2030-01-07'
        with patch('juno.chairs_report.now', return_value=datetime(2030, 1, 11, 15, tzinfo=timezone.utc)):
            response = self.client.post(path + '/prepare', json={})
            self.assertEqual(response.status_code, 200, response.text)
            draft = response.json()
            self.assertEqual(draft['emails']['visu']['body'].count(addition), 1)
            self.assertNotIn('no updates', draft['emails']['visu']['body'])
            self.assertNotIn('Other week', draft['emails']['visu']['body'])
            for key in ('lwr', 'performing'):
                self.assertNotIn(addition, draft['emails'][key]['body'])
            self.assertTrue(draft['emails']['visu']['body'].endswith('-Dan'))
            self.assertIn('Reviewed addition · Reviewed fictional statement', draft['emails']['visu']['coverage'])
            self.assertEqual(self.client.post(path + '/prepare', json={}).json(), draft)
            other = self.client.post(path + '/prepare', json={},
                                     headers={'Authorization': 'Bearer ' + self.other_token})
            self.assertNotIn(addition, other.text)

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


class ChairCompositionScopeTests(__import__('unittest').TestCase):
    def test_structured_shared_room_routes_without_guessing(self):
        from juno.chairs_routing import task_routes
        tasks = [{'id':'lab','title':'Generic cable repair','planning_details':{'room':{'state':'provided','value':'ARTS 121'}}},
                 {'id':'dean','title':'Generic toner follow-up','planning_details':{'room':{'state':'provided','value':'HCH203'}}},
                 {'id':'theater','title':'Generic projector follow-up','planning_details':{'room':{'state':'provided','value':'ARTS 140'}}},
                 {'id':'unknown','title':'Generic repair','planning_details':{'room':{'state':'unknown','value':'ARTS 121'}}}]
        self.assertEqual(task_routes(tasks, []), {'lab':'visu','dean':'dean','theater':'performing','unknown':None})

    def test_limited_evidence_rejects_broad_all_clear(self):
        from juno.chairs_report import write_email
        class Model:
            def complete(self, messages, model): return self.answer
        client = Model()
        evidence = "A fictional projector is waiting for a cable. No repair has been verified."
        for claim in [
            "No other new hardware failures, software issues, or maintenance alerts have been recorded.",
            "There are no additional issues this week.",
            "All other equipment is working normally.",
            "Existing tickets remain open pending parts.",
        ]:
            client.answer = 'Howdy Alex,\n\n' + claim + '\n\n-Dan'
            with self.subTest(claim=claim), self.assertRaises(ModelError):
                write_email(client, 'fixture', 'Fictional update', evidence, 'visu')
        client.answer = 'Howdy Alex,\n\nThe fictional projector is waiting for a cable. A repair has not been verified.\n\n-Dan'
        self.assertEqual(write_email(client, 'fixture', 'Fictional update', evidence, 'visu'), client.answer)
