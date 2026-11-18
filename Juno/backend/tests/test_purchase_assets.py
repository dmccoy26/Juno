"""Exact reviewed purchase/equipment references never establish financial or repair status."""
import json
from datetime import datetime,timezone,timedelta
from copy import deepcopy
import test_memory_api as memory
from juno.models import IntegrationSnapshot,OperationalState,now
from test_purchasing import PurchasingParseTests

class PurchaseAssetTests(memory.MemoryTests):
 def setUp(self):
  super().setUp()
  self.purchase=self.client.post('/v1/purchasing/import',json={'content':json.dumps([PurchasingParseTests().sample()]),'observed_at':datetime.now(timezone.utc).isoformat()}).json()
  with self.factory() as s:
   b=IntegrationSnapshot(owner_id=self.actor.owner_id,kind='beacon',origin='http://localhost:12108',items=[{'id':'alert1','asset_id':'asset1','item':'Fictional printer','location':'Fixture room'},{'id':'alert2','asset_id':'asset1','item':'Fictional printer'}],details={'instance_id':'fixture-instance','generated_at':now().isoformat()},fetched_at=now());s.add(b);s.commit()
 def state(self):return self.client.get('/v1/purchasing').json()
 def body(self,**extra):
  state=self.state()
  return {'expense_id':'fictional-charge','snapshot_id':self.purchase['id'],'asset_id':'asset1','expected_revision':state['links_revision'],'beacon_snapshot_id':state['beacon_snapshot_id'],'beacon_instance':state['beacon_instance'],**extra}
 def test_link_exact_scope_history_and_remove_preserve_other_data(self):
  self.assertEqual(len(self.state()['asset_choices']),1)
  body=self.body()
  for changes in [{'asset_id':'wrong'},{'beacon_instance':'other'},{'beacon_snapshot_id':'changed'},{'snapshot_id':'changed'}]:
   self.assertEqual(self.client.post('/v1/purchasing/asset-link',json={**body,**changes}).status_code,409)
  self.assertEqual(self.client.post('/v1/purchasing/asset-link',json=body,headers={'Authorization':'Bearer '+self.other_token}).status_code,409)
  result=self.client.post('/v1/purchasing/asset-link',json=body);self.assertEqual(result.status_code,200,result.text)
  self.assertTrue(result.json()['asset_links'][0]['active'])
  self.assertEqual(self.client.post('/v1/purchasing/asset-link',json=body).status_code,409)
  removed=self.client.post('/v1/purchasing/asset-unlink',json=self.body());self.assertEqual(removed.status_code,200,removed.text);self.assertEqual(removed.json()['asset_links'],[])
  with self.factory() as s:
   row=s.get(OperationalState,self.actor.owner_id);self.assertEqual(len(row.data['purchasing_asset_history']),2)
   self.assertEqual(s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon')).items[0]['item'],'Fictional printer')
 def test_changed_expense_stale_missing_and_reused_instance_invalidate_link(self):
  result=self.client.post('/v1/purchasing/asset-link',json=self.body());self.assertEqual(result.status_code,200,result.text)
  with self.factory() as s:
   b=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));b.details={**b.details,'instance_id':'new-instance'};s.commit()
  self.assertFalse(self.state()['asset_links'][0]['active']);self.assertIsNone(self.state()['asset_links'][0]['asset_title'])
  with self.factory() as s:
   b=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));b.fetched_at=now()-timedelta(days=2);s.commit()
  self.assertEqual(self.state()['asset_choices'],[])
  self.assertEqual(self.client.post('/v1/purchasing/asset-link',json=self.body()).status_code,409)
  self.assertEqual(self.client.post('/v1/purchasing/asset-unlink',json=self.body()).status_code,200)

 def test_lan_equipment_review_requires_paired_device(self):
  from fastapi.testclient import TestClient
  from juno.api import create_app
  from juno.shared_host import LANBoundary
  with TestClient(LANBoundary(create_app(self.engine)),client=('10.1.2.3',50000)) as client:
   self.assertEqual(client.post('/v1/purchasing/asset-link',json=self.body()).status_code,401)
   client.headers['Authorization']='Bearer '+self.second_token
   self.assertEqual(client.post('/v1/purchasing/asset-link',json=self.body()).status_code,200)
   self.assertEqual(client.post('/v1/purchasing/import',json={}).status_code,403)
