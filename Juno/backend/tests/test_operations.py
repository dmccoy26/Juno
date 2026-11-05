"""Fictional two-source operational evidence; no production connections or writes."""
from datetime import timedelta
import uuid
from sqlalchemy import select
from fastapi.testclient import TestClient
from juno.models import IntegrationSnapshot,TaskDockSnapshot,TaskDockState,OperationalState,DeanDraft,now
from juno.api import create_app
from juno.integrations import beacon_feed,IntegrationError
from juno.operations import relative_link
import test_planning as planning_tests


class OperationsTests(planning_tests.PlanningTests):
    def setUp(self):
        super().setUp()
        self.feed={'schema_version':1,'complete':True,'generated_at':now().isoformat(),'total':1,'rows':[{'id':'alert-1','category':'Printer','item':'Synthetic printer','location':'ARTS 121','problem':'Paper feed problem','action':'Inspect rollers','observed_at':now().isoformat(),'source':'weekly-check','evidence':'RECORDED','url':'/beacon/printers'}]}
        rows,details=beacon_feed(self.feed)
        with self.factory() as s:
            s.add(IntegrationSnapshot(owner_id=self.actor.owner_id,kind='beacon',origin='http://127.0.0.1:12108',items=rows,details=details,fetched_at=now()));s.commit()

    def operations(self):
        r=self.client.get('/v1/operations');self.assertEqual(r.status_code,200,r.text);return r.json()

    def link(self,task='dean',expected=200):
        state=self.operations();r=self.client.post('/v1/operations/links',json={'expected_revision':state['revision'],'basis_token':state['basis_token'],'alert_id':'alert-1','task_id':task,'rationale':'Reviewed exact fictional records'})
        self.assertEqual(r.status_code,expected,r.text);return r.json()

    def change_alert(self,**changes):
        with self.factory() as s:
            row=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));row.items=[{**row.items[0],**changes}];s.commit()

    def test_no_name_matching_and_each_claim_has_resolvable_evidence(self):
        value=self.operations();self.assertEqual(value['cards'][0]['relationship'],'unmatched')
        self.assertFalse(value['cards'][0]['tasks']);self.assertIsNone(value['cards'][0]['asset_id'])
        linked=self.link();card=linked['cards'][0];self.assertEqual(card['relationship'],'reviewed_ids')
        evidence={r['id'] for r in linked['evidence']}
        self.assertTrue(all(set(claim['evidence_ids'])<=evidence for claim in card['claims']))
        self.assertEqual(next(e for e in linked['evidence'] if e['app']=='Beacon')['source_link'],'/beacon/printers')
        self.assertIn('operations',self.client.get('/v1/planning/daily-brief?day=2030-01-06').json())

    def test_completed_task_and_failed_verification_do_not_establish_recovery(self):
        value=self.link('done');card=value['cards'][0]
        self.assertEqual(card['verification_state'],'unknown')
        self.assertTrue(card['tasks'][0]['completed']);self.assertIn('recovery is not established',str(card['claims']))
        self.change_alert(verification_state='failed');card=self.operations()['cards'][0]
        self.assertTrue(any('failed verification' in x for x in card['conflicts']))

    def test_authority_contradiction_and_stale_sources_block_unreviewed_repair(self):
        self.link();self.change_alert(decision_authority='department_lead',service_impact='unavailable')
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True}])
        t=self.plan()['tasks'][0];self.assertFalse(t['actionable']);self.assertIn('department-lead',str(t['missing']))
        self.assertIn('unavailable',str(t['operational_reasons']))
        with self.factory() as s:
            snap=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id));snap.items=[{**snap.items[0],'planning_details':{'room':{'state':'provided','value':'TRUS 108'}}},*snap.items[1:]]
            beacon=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));beacon.fetched_at=now()-timedelta(days=2);s.commit()
        card=self.operations()['cards'][0];self.assertTrue(card['stale']);self.assertIn('disagree',str(card['conflicts']))

    def test_permissions_workspace_switch_and_owner_isolation_do_not_disclose_old_content(self):
        self.link()
        other=self.client.get('/v1/operations',headers={'Authorization':'Bearer '+self.other_token}).json();self.assertFalse(other['cards']);self.assertFalse(other['links'])
        with self.factory() as s:
            snap=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id));snap.info={**snap.info,'workspace_id':'different'};s.commit()
        self.assertFalse(self.operations()['cards'][0]['tasks'])
        with self.factory() as s:
            snap=s.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==self.actor.owner_id));snap.info={**snap.info,'workspace_id':'fictional','sharing_restricted':True};s.commit()
        value=self.operations();self.assertFalse(value['task_choices']);self.assertNotIn('Fictional Dean request',str(value))

    def test_source_change_rejects_link_and_lost_records_are_explicit(self):
        state=self.operations()
        with self.factory() as s:
            beacon=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));beacon.id=str(uuid.uuid4());s.commit()
        r=self.client.post('/v1/operations/links',json={'expected_revision':0,'basis_token':state['basis_token'],'alert_id':'alert-1','task_id':'dean'})
        self.assertEqual(r.status_code,409)
        self.link()
        with self.factory() as s:s.delete(s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon')));s.commit()
        value=self.operations();self.assertFalse(value['cards']);self.assertIn('unavailable',str(value['notices']))

    def test_feedback_replays_once_and_conflicting_payload_is_rejected(self):
        self.save(tasks=[{'task_id':'dean','minutes':30,'dean':True}]);state=self.operations()
        payload={'expected_revision':state['revision'],'basis_token':state['basis_token'],'operation_id':str(uuid.uuid4()),'task_id':'dean','planning_day':'2030-01-07','outcome':'accepted','rationale':'Chosen proposal'}
        before=self.client.get('/v1/planning').json()
        one=self.client.post('/v1/operations/feedback',json=payload);self.assertEqual(one.status_code,200,one.text)
        two=self.client.post('/v1/operations/feedback',json=payload);self.assertEqual(two.status_code,200);self.assertTrue(two.json()['replayed'])
        self.assertEqual(len(self.operations()['feedback']),1)
        self.assertEqual(self.client.get('/v1/planning').json(),before)
        self.assertEqual(self.client.post('/v1/operations/feedback',json={**payload,'rationale':'Different'}).status_code,409)

    def test_feedback_missing_information_and_invalid_reschedule_are_rejected(self):
        state=self.operations();body={'expected_revision':0,'basis_token':state['basis_token'],'operation_id':str(uuid.uuid4()),'task_id':'dean','planning_day':'2030-01-07','outcome':'accepted'}
        self.assertEqual(self.client.post('/v1/operations/feedback',json=body).status_code,409)
        self.assertEqual(self.client.post('/v1/operations/feedback',json={**body,'outcome':'rescheduled'}).status_code,422)
        body={**body,'outcome':'rescheduled','reschedule_day':'2030-01-09'}
        self.assertEqual(self.client.post('/v1/operations/feedback',json=body).status_code,200)

    def test_allocation_does_not_double_book_owner_and_keeps_alternatives_distinct(self):
        self.save(tasks=[{'task_id':'dean','minutes':60,'dean':True},{'task_id':'room','minutes':60}])
        plan=self.plan();blocks=plan['allocation_proposal']['blocks'];self.assertEqual(len(blocks),2)
        self.assertGreaterEqual(blocks[1]['start'],blocks[0]['end'])
        self.assertEqual(len(plan['tasks']),2)
        self.assertEqual(self.client.get('/v1/planning').json()['revision'],1)

    def test_weekly_refresh_flags_beacon_change_without_overwriting_saved_writing(self):
        draft=self.client.get('/v1/planning/weekly?day=2030-01-06').json();self.assertIn('Decisions and meeting agenda',draft['text'])
        path='/v1/planning/weekly-draft/2030-01-06';r=self.client.put(path,json={'operation_id':str(uuid.uuid4()),'expected_revision':0,'text':'My unchanged reviewed draft','basis':draft['basis']});self.assertEqual(r.status_code,200,r.text)
        with self.factory() as s:
            b=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));b.id=str(uuid.uuid4());s.commit()
        saved=self.client.get(path).json();self.assertTrue(saved['sources_changed']);self.assertEqual(saved['text'],'My unchanged reviewed draft')

    def test_procedures_use_only_authorized_current_records_and_flag_changed_versions(self):
        self.add_source('slack',[{'id':'procedure-1','title':'Fictional instructions','text':'Reference only: inspect equipment.'}])
        view=self.client.get('/v1/operations/procedures').json();choice=view['choices'][0]
        r=self.client.post('/v1/operations/procedures',json={'expected_revision':0,**{k:choice[k] for k in ('kind','snapshot_id','record_id')},'label':'Inspection reference'});self.assertEqual(r.status_code,200,r.text)
        self.assertTrue(r.json()['items'][0]['available'])
        with self.factory() as s:
            source=s.get(IntegrationSnapshot,(self.actor.owner_id,'slack'));source.id=str(uuid.uuid4());source.items=[];s.commit()
        reference=self.client.get('/v1/operations/procedures').json()['items'][0]
        self.assertTrue(reference['changed']);self.assertFalse(reference['available']);self.assertIsNone(reference['text'])
        self.assertFalse(self.client.get('/v1/operations/procedures',headers={'Authorization':'Bearer '+self.other_token}).json()['items'])

    def test_optional_contract_extensions_are_validated_and_arbitrary_links_not_followed(self):
        feed={**self.feed,'rows':[{**self.feed['rows'][0],'asset_id':'asset-1','issue_id':'issue-1','record_version':'v2','verification_state':'verified_recovered','decision_authority':'none'}]}
        rows,_=beacon_feed(feed);self.assertEqual(rows[0]['asset_id'],'asset-1');self.assertEqual(rows[0]['verification_state'],'verified_recovered')
        for bad in ('javascript:alert(1)','//evil.invalid/a','https://evil.invalid/a','/path\\escape','/path\n'):
            self.assertIsNone(relative_link(bad))
        feed['rows'][0]['decision_authority']='guessed policy'
        with self.assertRaises(IntegrationError):beacon_feed(feed)

    def test_reviewed_link_removal_invalidates_model_context_and_is_revision_fenced(self):
        from juno.companion import context_for,refs_current
        linked=self.link()
        with self.factory() as s:
            context,refs=context_for(s,self.actor.owner_id,'How is the printer?',[])
            self.assertTrue(any(r['source'].startswith('operations:') for r in context));self.assertTrue(refs_current(s,self.actor.owner_id,refs))
        r=self.client.delete('/v1/operations/links/alert-1',params={'expected_revision':0});self.assertEqual(r.status_code,409)
        r=self.client.delete('/v1/operations/links/alert-1',params={'expected_revision':linked['revision']});self.assertEqual(r.status_code,200)
        with self.factory() as s:self.assertFalse(refs_current(s,self.actor.owner_id,refs))
        self.assertFalse(self.operations()['cards'][0]['tasks'])

    def test_coordinated_staff_proposal_respects_weekly_limit_and_room_contention(self):
        from datetime import datetime,timezone
        from juno.planning import allocate_proposal
        a=datetime(2030,1,7,15,tzinfo=timezone.utc);b=a+timedelta(hours=5)
        rows=[{'task_id':str(i),'title':'Synthetic '+str(i),'employee':'Alex','room':'ARTS 121','estimate_minutes':60,'actionable':True,'supervision':False} for i in range(3)]
        state={'people':[{'name':'Alex','weekly_limit_minutes':90,'desired_minutes':None}],'reservations':[]}
        result=allocate_proposal(rows,{str(i):[(a,b)] for i in range(3)},480,state)
        self.assertEqual(len(result['blocks']),1);self.assertEqual(len(result['unplaced']),2)
        rows[1]['employee']='Other';state['people'].append({'name':'Other','weekly_limit_minutes':120,'desired_minutes':None})
        result=allocate_proposal(rows,{str(i):[(a,b)] for i in range(3)},480,state)
        self.assertEqual(len(result['blocks']),2);self.assertGreaterEqual(result['blocks'][1]['start'],result['blocks'][0]['end'])

    def test_additive_migration_preserves_prior_records_and_downgrades_only_new_table(self):
        from alembic import command
        from alembic.config import Config
        from pathlib import Path
        from sqlalchemy import inspect,text
        cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
        with self.engine.connect() as c:
            before=c.execute(text('select id,owner_id,items from taskdock_snapshots order by id')).fetchall()
            cfg.attributes['connection']=c
            command.downgrade(cfg,'0012_daily_planning')
            self.assertNotIn('operational_state',inspect(c).get_table_names())
            command.upgrade(cfg,'head')
            after=c.execute(text('select id,owner_id,items from taskdock_snapshots order by id')).fetchall()
            self.assertEqual(before,after);self.assertIn('operational_state',inspect(c).get_table_names())

    def test_missing_schedules_do_not_produce_allocation_or_coverage_claim(self):
        self.data['windows']=[];self.save(tasks=[{'task_id':'dean','minutes':30}])
        plan=self.plan();self.assertFalse(plan['allocation_proposal']['blocks'])
        self.assertIn('No staffing coverage gap is inferred',str(self.operations()['notices']))

    def test_metadata_is_owner_scoped_and_reads_do_not_create_records(self):
        value=self.operations();self.assertEqual(value['revision'],0)
        with self.factory() as s:self.assertIsNone(s.get(OperationalState,self.actor.owner_id))
        self.assertEqual(self.client.get('/v1/operations',headers={'Authorization':'Bearer invalid'}).status_code,401)
        self.link()
        with TestClient(create_app(self.engine)) as client:
            client.headers['Authorization']='Bearer '+self.token
            self.assertEqual(client.get('/v1/operations').json()['cards'][0]['relationship'],'reviewed_ids')

    def test_verified_recovery_needs_matching_asset_and_current_verification_record(self):
        self.change_alert(verification_state='verified_recovered',asset_id='asset-1')
        self.assertEqual(self.operations()['cards'][0]['verification_state'],'unknown')
        self.change_alert(verification_record={'asset_id':'asset-1','record_id':'verification-1','actor_id':'technician-1','method':'Physical feed test','observed_at':now().isoformat()})
        self.assertEqual(self.operations()['cards'][0]['verification_state'],'verified_recovered')
        self.change_alert(verification_record={'asset_id':'different','record_id':'verification-1','actor_id':'technician-1','method':'Physical feed test','observed_at':now().isoformat()})
        self.assertEqual(self.operations()['cards'][0]['verification_state'],'unknown')

    def test_beacon_origin_change_does_not_reuse_reviewed_relationship(self):
        self.link()
        with self.factory() as s:
            source=s.get(IntegrationSnapshot,(self.actor.owner_id,'beacon'));source.origin='Imported file: another-instance.json';s.commit()
        self.assertFalse(self.operations()['cards'][0]['tasks'])

    def test_paired_reads_are_allowed_but_metadata_writes_and_worker_access_are_not(self):
        from juno.shared_host import LANBoundary
        with TestClient(LANBoundary(self.app),client=('10.20.30.40',50000)) as lan:
            lan.headers['Authorization']='Bearer '+self.token
            self.assertEqual(lan.get('/v1/operations').status_code,200)
            self.assertEqual(lan.get('/v1/operations/procedures').status_code,200)
            self.assertEqual(lan.post('/v1/operations/links',json={}).status_code,403)
            self.assertEqual(lan.post('/v1/operations/feedback',json={}).status_code,403)
        with TestClient(LANBoundary(self.app),client=('8.8.8.8',50000)) as public:
            public.headers['Authorization']='Bearer '+self.token
            self.assertEqual(public.get('/v1/operations').status_code,403)

    def test_procedure_identity_cannot_follow_record_ids_into_a_different_account(self):
        self.add_source('slack',[{'id':'same-id','text':'Original reference'}],account={'id':'original-account'})
        view=self.client.get('/v1/operations/procedures').json();choice=view['choices'][0]
        body={'expected_revision':0,**{k:choice[k] for k in ('kind','snapshot_id','record_id')},'label':'Reference'}
        self.assertEqual(self.client.post('/v1/operations/procedures',json=body).status_code,200)
        with self.factory() as s:
            row=s.get(IntegrationSnapshot,(self.actor.owner_id,'slack'));row.id=str(uuid.uuid4());row.details={**row.details,'account':{'id':'different-account'}};row.items=[{'id':'same-id','text':'Other account content'}];s.commit()
        value=self.client.get('/v1/operations/procedures').json();self.assertFalse(value['items'][0]['available']);self.assertNotIn('Other account content',str(value['items']))
        r=self.client.post('/v1/operations/procedures/remove',json={'expected_revision':value['revision'],'kind':'slack','record_id':'same-id'});self.assertEqual(r.status_code,200);self.assertFalse(r.json()['items'])

    def test_concurrent_relationship_saves_are_fenced(self):
        from concurrent.futures import ThreadPoolExecutor
        state=self.operations();body={'expected_revision':0,'basis_token':state['basis_token'],'alert_id':'alert-1','task_id':'dean'}
        def submit(task):
            with TestClient(create_app(self.engine)) as client:
                client.headers['Authorization']='Bearer '+self.token
                return client.post('/v1/operations/links',json={**body,'task_id':task}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(submit,['dean','room']))
        self.assertEqual(sorted(codes),[200,409])
        self.assertEqual(len(self.operations()['links']),1)
