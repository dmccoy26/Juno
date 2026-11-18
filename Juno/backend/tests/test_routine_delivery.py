"""Disposable ledger + explicit fake remote; never a live TaskDock writer."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import copy
import threading
from uuid import uuid4
from sqlalchemy import select
from juno.models import RecurringRoutine, RoutineOccurrenceRecord as Occurrence
from juno.recurring import RoutineInput, retain_rule
from juno.routine_delivery import Lookup, plan_due, deliver, release_deferred
from test_memory_api import MemoryTests


class FakeRemote:
    def __init__(self, scope, backing=None):
        self.scope=scope;self.records=backing if backing is not None else {};self.lock=threading.RLock()
        self.calls=0;self.lookups=0;self.timeout_once=False;self.revoked=False
        self.entered=None;self.proceed=None
    def key(self,scope,routine,period): return (scope['owner_id'],scope['instance_id'],scope['workspace_id'],routine,period)
    def lookup(self,scope,operation,routine,period):
        self.lookups+=1
        if self.entered:
            self.entered.set();assert self.proceed.wait(5);self.entered=None
        if self.revoked or scope!=self.scope: return Lookup('denied')
        with self.lock:
            return Lookup('found',copy.deepcopy(self.records[self.key(scope,routine,period)])) if self.key(scope,routine,period) in self.records else Lookup('absent')
    def create(self,scope,operation,payload):
        if self.revoked or scope!=self.scope: raise PermissionError()
        with self.lock:
            self.calls+=1;key=self.key(scope,payload['routine_id'],payload['occurrence_key'])
            if key not in self.records:
                self.records[key]={'scope':copy.deepcopy(scope),'operation_id':operation,'routine_id':payload['routine_id'],'occurrence_key':payload['occurrence_key'],'task_id':str(uuid4())}
            if self.timeout_once:
                self.timeout_once=False;raise TimeoutError('Fictional response loss after commit')
            return Lookup('found',copy.deepcopy(self.records[key]))


class RoutineDeliveryTests(MemoryTests):
    at=datetime(2030,1,7,16,tzinfo=timezone.utc)
    def routine(self, **overrides):
        scope={'owner_id':self.actor.owner_id,'instance_id':'fictional-instance','workspace_id':'fictional-workspace','column_id':'fictional-juno'}
        definition=RoutineInput(title='Fictional recurring check',frequency='daily',start_date=date(2030,1,7),creation_time='09:00',**overrides).model_dump(mode='json')
        with self.factory() as session:
            row=RecurringRoutine(owner_id=self.actor.owner_id,definition=definition,status='active',revision=1,
                target_scope=scope,activated_at=self.at-timedelta(hours=1),updated_at=self.at)
            session.add(row);retain_rule(session,row,'fictional_activation');session.commit();identity=row.id
        return identity,scope
    def rows(self, identity):
        with self.factory() as session:
            return session.scalars(select(Occurrence).where(Occurrence.routine_id==identity).order_by(Occurrence.local_date)).all()
    def test_disabled_drafts_and_owner_scope(self):
        identity,scope=self.routine()
        with self.factory() as session:
            session.get(RecurringRoutine,identity).status='draft';session.commit()
        self.assertEqual(plan_due(self.factory,self.actor.owner_id,identity,self.at)['state'],'not_active')
        self.assertEqual(self.rows(identity),[])
        self.assertEqual(deliver(self.factory,self.actor.owner_id,'missing',None,self.at),'disabled')
        self.assertEqual(plan_due(self.factory,self.other.owner_id,identity,self.at)['state'],'not_active')
    def test_lost_receipt_restart_and_pre_delivery_restore(self):
        identity,scope=self.routine();owner=self.actor.owner_id
        self.assertEqual(plan_due(self.factory,owner,identity,self.at)['planned'],1)
        self.assertEqual(plan_due(self.factory,owner,identity,self.at)['planned'],0)
        row=self.rows(identity)[0];remote=FakeRemote(scope);remote.timeout_once=True
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'unknown')
        restarted=FakeRemote(scope,remote.records)
        self.assertEqual(deliver(self.factory,owner,row.id,restarted,self.at),'created')
        self.assertEqual(remote.calls,1);self.assertEqual(restarted.calls,0)
        task=self.rows(identity)[0].task_id
        # Simulate restoring the saved local pending row from a pre-delivery backup.
        with self.factory() as session:
            saved=session.get(Occurrence,row.id);saved.status='planned';saved.task_id=None;session.commit()
        self.assertEqual(deliver(self.factory,owner,row.id,restarted,self.at),'created')
        self.assertEqual(self.rows(identity)[0].task_id,task)
        self.assertEqual(len(remote.records),1);self.assertEqual(restarted.calls,0)
    def test_concurrent_host_claim_and_replayed_ticks(self):
        identity,scope=self.routine();owner=self.actor.owner_id
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:plan_due(self.factory,owner,identity,self.at),range(2)))
        self.assertEqual(sum(result['planned'] for result in results),1)
        row=self.rows(identity)[0];remote=FakeRemote(scope)
        remote.entered=threading.Event();remote.proceed=threading.Event()
        entered,proceed=remote.entered,remote.proceed
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(deliver,self.factory,owner,row.id,remote,self.at)
            self.assertTrue(entered.wait(5))
            self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'leased')
            proceed.set();self.assertEqual(first.result(timeout=5),'created')
        self.assertEqual(remote.calls,1);self.assertEqual(len(remote.records),1)
    def test_manual_changes_absence_deletion_and_revocation(self):
        identity,scope=self.routine();owner=self.actor.owner_id
        plan_due(self.factory,owner,identity,self.at);row=self.rows(identity)[0];remote=FakeRemote(scope)
        self.assertEqual(deliver(self.factory,self.other.owner_id,row.id,remote,self.at),'not_found')
        self.assertEqual(remote.lookups,0)
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'created')
        receipt=next(iter(remote.records.values()));receipt['actual_column_id']='human-moved-column';receipt['human_title']='Human edited title'
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'created')
        self.assertEqual(remote.calls,1)
        backup=copy.deepcopy(remote.records);remote.records.clear()
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'unknown')
        self.assertEqual(remote.calls,1)  # A known task is never recreated on absence.
        remote.records.update(backup);next(iter(remote.records.values()))['deleted']=True
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'cancelled')
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'cancelled')
        self.assertEqual(remote.calls,1)
        later=self.at+timedelta(days=1);plan_due(self.factory,owner,identity,later)
        second=self.rows(identity)[1];remote.revoked=True
        self.assertEqual(deliver(self.factory,owner,second.id,remote,later),'failed')
        with self.factory() as session:self.assertEqual(session.get(RecurringRoutine,identity).status,'paused')
        self.assertEqual(plan_due(self.factory,owner,identity,later+timedelta(days=1))['state'],'not_active')
    def test_wrong_receipt_scope_is_conflict_and_never_retried(self):
        identity,scope=self.routine();owner=self.actor.owner_id;plan_due(self.factory,owner,identity,self.at)
        row=self.rows(identity)[0];remote=FakeRemote(scope)
        original=remote.create
        def wrong(*args):
            result=original(*args);result.receipt['scope']['workspace_id']='wrong';return result
        remote.create=wrong
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'conflict')
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'conflict')
        self.assertIsNone(self.rows(identity)[0].task_id);self.assertEqual(remote.calls,1)
    def test_repeated_dst_hour_uses_absolute_creation_time(self):
        from zoneinfo import ZoneInfo
        zone=ZoneInfo('America/Chicago')
        identity,_=self.routine();owner=self.actor.owner_id
        with self.factory() as session:
            routine=session.get(RecurringRoutine,identity)
            routine.definition={**routine.definition,'start_date':'2030-11-03','creation_time':'01:30'}
            routine.activated_at=datetime(2030,11,3,0,0,tzinfo=zone);routine.revision+=1
            retain_rule(session,routine,'edited');session.commit()
        second_hour=datetime(2030,11,3,1,15,tzinfo=zone,fold=1)
        self.assertEqual(plan_due(self.factory,owner,identity,second_hour)['planned'],1)
        self.assertEqual(plan_due(self.factory,owner,identity,second_hour+timedelta(hours=1))['planned'],0)
        with self.assertRaises(ValueError):plan_due(self.factory,owner,identity,self.at.replace(year=2200))

    def test_non_boolean_completion_receipt_is_not_completion(self):
        identity,scope=self.routine();owner=self.actor.owner_id;plan_due(self.factory,owner,identity,self.at)
        row=self.rows(identity)[0];remote=FakeRemote(scope);original=remote.create
        def malformed(*args):
            result=original(*args);result.receipt['completed']='false';return result
        remote.create=malformed
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'conflict')
        self.assertIsNone(self.rows(identity)[0].task_id)

    def test_two_routines_share_a_date_without_identity_collision(self):
        first,scope=self.routine();second,_=self.routine();owner=self.actor.owner_id
        remote=FakeRemote(scope)
        for identity in (first,second):
            plan_due(self.factory,owner,identity,self.at)
            self.assertEqual(deliver(self.factory,owner,self.rows(identity)[0].id,remote,self.at),'created')
        self.assertEqual(len(remote.records),2)
        self.assertNotEqual(self.rows(first)[0].task_id,self.rows(second)[0].task_id)

    def test_expired_claim_reconciles_and_pause_never_creates(self):
        identity,scope=self.routine();owner=self.actor.owner_id;plan_due(self.factory,owner,identity,self.at)
        row=self.rows(identity)[0];remote=FakeRemote(scope)
        remote.create(scope,row.operation_id,row.payload)
        with self.factory() as session:
            record=session.get(Occurrence,row.id);record.status='in_flight';record.lease_id=str(uuid4());record.lease_expires=self.at-timedelta(seconds=1)
            session.commit()
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'created')
        self.assertEqual(remote.calls,1)
        later=self.at+timedelta(days=1);plan_due(self.factory,owner,identity,later)
        waiting=self.rows(identity)[1]
        with self.factory() as session:
            session.get(RecurringRoutine,identity).status='paused'
            record=session.get(Occurrence,waiting.id);record.status='planned';session.commit()
        self.assertEqual(deliver(self.factory,owner,waiting.id,remote,later),'not_active')
        self.assertEqual(remote.calls,1)

    def test_changed_stored_payload_conflicts_before_remote_request(self):
        identity,scope=self.routine();owner=self.actor.owner_id;plan_due(self.factory,owner,identity,self.at)
        row=self.rows(identity)[0];remote=FakeRemote(scope)
        with self.factory() as session:
            record=session.get(Occurrence,row.id);record.payload={**record.payload,'title':'Unreviewed replacement'};session.commit()
        self.assertEqual(deliver(self.factory,owner,row.id,remote,self.at),'conflict')
        self.assertEqual(remote.lookups,0);self.assertEqual(remote.calls,0)

    def test_missed_run_policies_and_bounded_cursor(self):
        for policy,counts in [('latest',{'skipped':2,'planned':1}),('all',{'planned':1,'deferred':2}),('skip',{'skipped':2,'planned':1})]:
            identity,_=self.routine(missed_policy=policy)
            end=self.at+timedelta(days=2)
            first=plan_due(self.factory,self.actor.owner_id,identity,end,limit=1)
            self.assertTrue(first['more_due'])
            while plan_due(self.factory,self.actor.owner_id,identity,end,limit=1)['more_due']: pass
            actual={state:sum(row.status==state for row in self.rows(identity)) for state in counts}
            self.assertEqual(actual,counts)
    def test_deferred_work_uses_original_policy_after_rule_edit(self):
        identity,scope=self.routine(missed_policy='all');owner=self.actor.owner_id
        end=self.at+timedelta(days=2);plan_due(self.factory,owner,identity,end)
        rows=self.rows(identity)
        with self.factory() as session:
            first=session.get(Occurrence,rows[0].id);first.status='completed'
            routine=session.get(RecurringRoutine,identity);routine.definition={**routine.definition,'missed_policy':'skip'};routine.revision+=1
            retain_rule(session,routine,'edited');session.commit()
        self.assertEqual(release_deferred(self.factory,owner,identity,end),1)
        self.assertEqual([row.status for row in self.rows(identity)],['completed','planned','deferred'])
    def test_monthly_rule_edit_keeps_existing_period_identity(self):
        # Build monthly explicitly to avoid passing frequency twice.
        identity,scope=self.routine();owner=self.actor.owner_id
        with self.factory() as session:
            routine=session.get(RecurringRoutine,identity);routine.definition={**routine.definition,'frequency':'monthly','month_day':7};routine.revision+=1
            retain_rule(session,routine,'edited');session.commit()
        plan_due(self.factory,owner,identity,self.at);first=self.rows(identity)[0]
        with self.factory() as session:
            session.get(Occurrence,first.id).status='completed'
            routine=session.get(RecurringRoutine,identity);routine.definition={**routine.definition,'month_day':8};routine.revision+=1
            retain_rule(session,routine,'edited');session.commit()
        self.assertEqual(plan_due(self.factory,owner,identity,self.at+timedelta(days=1))['planned'],0)
        self.assertEqual(len(self.rows(identity)),1)
        self.assertEqual(self.rows(identity)[0].period_key,'month:2030-01')
