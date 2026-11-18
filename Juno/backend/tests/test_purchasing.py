from datetime import datetime, timezone
import json
import unittest
from juno.purchasing import parse
from test_memory_api import MemoryTests


class PurchasingParseTests(unittest.TestCase):
    def sample(self):
        return {'expense_id':'fictional-charge', 'merchant':'Fictional supply', 'amount':'-18.14',
                'currency':'USD', 'date':'2030-01-07', 'status':'review',
                'attachment':'/private/do-not-import', 'report_url':'https://invalid/?token=secret'}

    def test_helper_plan_preserves_credit_and_strips_paths(self):
        row = self.sample()
        result = parse(json.dumps({'expenses':[row], 'skipped_emails':['private message path']}))
        self.assertEqual(result[0]['amount'], '-18.14')
        self.assertNotIn('attachment', result[0]); self.assertNotIn('report_url', result[0])
        self.assertNotIn('private', json.dumps(result))

    def test_unknown_is_not_missing_and_bad_numbers_are_rejected(self):
        row = self.sample(); row['id'] = row.pop('expense_id'); row.pop('status')
        self.assertEqual(parse(json.dumps([row]))[0]['status'], 'not_checked')
        for amount in ['NaN','Infinity','1.001','10000001']:
            with self.subTest(amount=amount), self.assertRaises(ValueError): parse(json.dumps([{**row,'amount':amount}]))
        with self.assertRaises(ValueError): parse(json.dumps([row,row]))


class PurchasingAPITests(MemoryTests):
    def test_explicit_link_checks_workspace_and_changed_expense(self):
        from juno.models import TaskDockSnapshot, TaskDockState, OperationalState, now
        from juno.operations import saved
        body = {'content':json.dumps([PurchasingParseTests().sample()]), 'observed_at':datetime.now(timezone.utc).isoformat()}
        purchase = self.client.post('/v1/purchasing/import', json=body).json()
        with self.factory() as session:
            snapshot = TaskDockSnapshot(owner_id=self.actor.owner_id,origin='Fictional',info={'workspace_id':'fixture-workspace'},items=[{'id':'fixture-task','title':'ARTS 121 fictional part'}],sources=[],snapshot='fixture',fetched_at=now())
            session.add(snapshot);session.flush();session.add(TaskDockState(owner_id=self.actor.owner_id,active_id=snapshot.id));session.commit()
        request = {'expense_id':'fictional-charge','snapshot_id':purchase['id'],'task_id':'fixture-task','workspace_id':'fixture-workspace','expected_revision':0}
        self.assertEqual(self.client.post('/v1/purchasing/link',json={**request,'workspace_id':'wrong'}).status_code,409)
        self.assertEqual(self.client.post('/v1/purchasing/link',json=request,headers={'Authorization':'Bearer '+self.other_token}).status_code,409)
        linked = self.client.post('/v1/purchasing/link',json=request)
        self.assertEqual(linked.status_code,200,linked.text)
        self.assertTrue(linked.json()['links'][0]['active'])
        self.assertEqual(self.client.post('/v1/purchasing/link',json=request).json()['links_revision'],linked.json()['links_revision'])
        changed = PurchasingParseTests().sample();changed['amount']='89.12'
        replaced = self.client.post('/v1/purchasing/import',json={**body,'expected_id':purchase['id'],'content':json.dumps([changed])})
        self.assertEqual(replaced.status_code,200,replaced.text)
        self.assertFalse(replaced.json()['links'][0]['active'])
        self.assertIsNone(replaced.json()['links'][0]['task_title'])
        self.assertEqual(self.client.post('/v1/purchasing/link',json=request).status_code,409)
        removed = self.client.post('/v1/purchasing/unlink',json={**request,'expected_revision':linked.json()['links_revision']})
        self.assertEqual(removed.status_code,200,removed.text)
        self.assertEqual(removed.json()['links'],[])
        with self.factory() as session:
            _, data = saved(session,self.actor.owner_id)
            self.assertEqual(len(data['purchasing_link_history']),2)

    def test_import_is_reviewed_cas_scoped_and_cached(self):
        sample = PurchasingParseTests().sample()
        body = {'content':json.dumps({'expenses':[sample]}), 'observed_at':datetime.now(timezone.utc).isoformat()}
        response = self.client.post('/v1/purchasing/preview', json=body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get('/v1/purchasing').json()['items'], [])
        saved = self.client.post('/v1/purchasing/import', json=body)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.client.post('/v1/purchasing/import', json=body).status_code, 409)
        other = {'Authorization':'Bearer ' + self.other_token}
        self.assertEqual(self.client.get('/v1/purchasing', headers=other).json()['items'], [])
        self.assertTrue(any(p['path']=='/v1/purchasing' for p in self.client.get('/v1/cache').json()['pages']))
        self.assertNotIn('do-not-import', saved.text); self.assertNotIn('token=secret', saved.text)
