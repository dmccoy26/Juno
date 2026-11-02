import threading
import unittest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
import test_memory_api as memory_tests
from juno.api import create_app
from juno.auth import provision
from juno.local_model import ModelError, validate_origin
from juno.models import Message


class FakeModel:
    calls = []
    failure = False
    entered = None
    release = None
    def __init__(self, base_url): pass
    def models(self): return ['synthetic-model']
    def complete(self, messages, model):
        self.calls.append(messages)
        if self.entered: self.entered.set(); self.release.wait(5)
        if self.failure: raise ModelError('Synthetic model unavailable.')
        return 'Synthetic answer based on current context.'


class CompanionTests(memory_tests.MemoryTests):
    # Reuse the isolated PostgreSQL harness, not its individual test methods.
    def setUp(self):
        super().setUp()
        self.client.close()
        FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.app=create_app(self.engine, model_factory=FakeModel)
        self.client=TestClient(self.app)
        self.client.headers['Authorization']='Bearer '+self.token
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic-model'})
        self.conv=self.client.post('/v1/conversations',json={'title':'Synthetic work chat'}).json()['id']
        self.path='/v1/conversations/'+self.conv+'/messages'

    def turn(self, text='What should I do next?', request_id=None, **extra):
        return self.client.post(self.path,json={'text':text,'request_id':request_id or str(uuid.uuid4()),**extra})

    def test_chat_persistence_idempotency_and_owner_boundary(self):
        request=str(uuid.uuid4())
        first=self.turn(request_id=request)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()['status'],'complete')
        self.assertEqual(first.json()['model_name'],'synthetic-model')
        self.assertEqual(self.turn(request_id=request).json()['id'], first.json()['id'])
        self.assertEqual(len(FakeModel.calls),1)
        with TestClient(create_app(self.engine,model_factory=FakeModel)) as second:
            second.headers['Authorization']='Bearer '+self.second_token
            self.assertEqual(len(second.get(self.path).json()['items']),2)
            second.headers['Authorization']='Bearer '+self.other_token
            self.assertEqual(second.get(self.path).status_code,404)
            self.assertEqual(second.post(self.path,json={'text':'Unauthorized','request_id':str(uuid.uuid4())}).status_code,404)

    def test_remember_request_never_claims_or_performs_a_model_save(self):
        before = self.client.get('/v1/memories').json()['items']
        request = str(uuid.uuid4())
        reply = self.turn('Can you remember that the fictional cutter is model TEST-42?', request_id=request)
        self.assertEqual(reply.status_code, 200, reply.text)
        self.assertIn('has not been saved', reply.json()['text'])
        self.assertEqual(reply.json()['model_name'], 'Juno memory review')
        self.assertEqual(FakeModel.calls, [])
        self.assertEqual(self.client.get('/v1/memories').json()['items'], before)
        self.assertEqual(self.turn('Can you remember that the fictional cutter is model TEST-42?', request_id=request).json()['id'], reply.json()['id'])
        saved = self.client.post('/v1/memories', json={'text':'The fictional cutter is model TEST-42.', 'source':'Reviewed chat', 'confidence':'confirmed'})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(self.client.get('/v1/memories/'+saved.json()['id']).json()['text'], 'The fictional cutter is model TEST-42.')

    def test_memory_review_needs_no_model_but_recall_is_normal_chat(self):
        from juno.models import ModelConnection
        from juno.companion import memory_request
        self.assertIsNone(memory_request('Do you remember that fictional cutter?'))
        self.assertIsNone(memory_request('Remember when we fixed the printer?'))
        self.assertEqual(memory_request('Please remember this: Fictional note'), 'Fictional note')
        self.assertEqual(memory_request('Hi Juno, can you remember this? Fictional note'), 'Fictional note')
        self.assertIsNone(memory_request('Hey Juno, do you remember that printer?'))
        with self.factory() as session:
            connection = session.get(ModelConnection, self.actor.owner_id)
            session.delete(connection);session.commit()
        self.assertEqual(self.turn('Remember this: Fictional note').status_code, 200)
        self.assertEqual(self.turn('Do you remember that fictional cutter?').status_code, 503)

    def test_delete_conversation_removes_messages_but_preserves_memory_and_owner_isolation(self):
        self.turn('Fictional conversation to delete')
        saved = self.client.post('/v1/memories',json={'text':'Independent fictional memory','source':'manual:test','confidence':'confirmed'}).json()
        diary = self.client.post('/v1/check-ins',json={'local_date':'2026-10-30'}).json()
        self.client.headers['Authorization'] = 'Bearer '+self.other_token
        self.assertEqual(self.client.delete('/v1/conversations/'+self.conv).status_code,404)
        self.client.headers['Authorization'] = 'Bearer '+self.token
        self.assertEqual(self.client.delete('/v1/conversations/'+self.conv).status_code,200)
        self.assertEqual(self.client.get(self.path).status_code,404)
        self.assertNotIn(self.conv,[r['id'] for r in self.client.get('/v1/conversations').json()['items']])
        self.assertEqual(self.client.get('/v1/memories/'+saved['id']).status_code,200)
        self.assertEqual(self.client.get('/v1/check-ins/by-date/2026-10-30').json()['id'],diary['id'])
        with self.factory() as session:
            self.assertIsNone(session.scalar(select(Message).where(Message.conversation_id==self.conv)))
        self.assertEqual(self.client.delete('/v1/conversations/'+self.conv).status_code,404)

    def test_delete_pending_conversation_is_rejected(self):
        with self.factory() as session:
            session.add(Message(conversation_id=self.conv,role='assistant',text='',request_id=str(uuid.uuid4()),status='pending',meeting_mode=True))
            session.commit()
        self.assertEqual(self.client.delete('/v1/conversations/'+self.conv).status_code,409)
        self.assertEqual(self.client.get(self.path).status_code,200)

    def test_message_memory_badge_survives_edit_and_disappears_after_memory_delete(self):
        self.turn('Fictional original note')
        user=next(m for m in self.client.get(self.path).json()['items'] if m['role']=='user')
        value={'text':'Reviewed fictional fact','source':'Chat review','confidence':'confirmed','source_message_id':user['id']}
        saved=self.client.post('/v1/memories',json=value)
        self.assertEqual(saved.status_code,201,saved.text);memory=saved.json()
        def badge():return next(m for m in self.client.get(self.path).json()['items'] if m['id']==user['id'])['saved_memory_id']
        self.assertEqual(badge(),memory['id'])
        changed=self.client.put('/v1/memories/'+memory['id'],json={'text':'Corrected fictional fact','source':'Corrected source','confidence':'confirmed','expected_revision':1})
        self.assertEqual(changed.status_code,200,changed.text)
        self.assertEqual(changed.json()['source_message_id'],user['id'])
        self.assertEqual(badge(),memory['id'])
        exported=self.client.get('/v1/cache').json()
        self.assertIn(memory['id'],str(exported))
        self.assertEqual(self.client.post('/v1/memories',json={**value,'text':'Another fact from same message'}).status_code,409)
        self.assertEqual(self.client.delete('/v1/memories/'+memory['id']+'?expected_revision=2').status_code,204)
        self.assertIsNone(badge())

    def test_message_memory_origin_is_owner_scoped_and_chat_delete_keeps_memory(self):
        self.turn('Fictional note to save')
        user=next(m for m in self.client.get(self.path).json()['items'] if m['role']=='user')
        value={'text':'Independent reviewed note','source':'Chat','confidence':'confirmed','source_message_id':user['id']}
        self.client.headers['Authorization']='Bearer '+self.other_token
        self.assertEqual(self.client.post('/v1/memories',json=value).status_code,404)
        self.client.headers['Authorization']='Bearer '+self.token
        memory=self.client.post('/v1/memories',json=value).json()
        self.assertEqual(self.client.delete('/v1/conversations/'+self.conv).status_code,200)
        kept=self.client.get('/v1/memories/'+memory['id'])
        self.assertEqual(kept.status_code,200,kept.text)
        self.assertIsNone(kept.json()['source_message_id'])

    def test_legacy_badge_uses_exact_memory_content_not_model_prose(self):
        self.turn('A fictional exact note')
        def badge():return next(m for m in self.client.get(self.path).json()['items'] if m['role']=='user')['saved_memory_id']
        self.assertIsNone(badge())
        saved=self.client.post('/v1/memories',json={'text':'A fictional exact note','source':'Legacy manual','confidence':'confirmed'}).json()
        self.assertEqual(badge(),saved['id'])

    def test_memory_origin_upgrade_backfills_only_unambiguous_exact_owner_matches(self):
        from pathlib import Path
        from alembic import command
        from alembic.config import Config
        exact='Exact fictional note '+str(uuid.uuid4())
        ambiguous='Repeated fictional note '+str(uuid.uuid4())
        self.turn(exact)
        original=next(m for m in self.client.get(self.path).json()['items'] if m['role']=='user')
        def save(text):return self.client.post('/v1/memories',json={'text':text,'source':'Legacy','confidence':'confirmed'}).json()
        first=save(exact)
        self.turn(ambiguous);self.turn(ambiguous)
        repeated=save(ambiguous)
        self.client.headers['Authorization']='Bearer '+self.other_token
        foreign=save(exact)
        self.client.headers['Authorization']='Bearer '+self.token
        cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
        with self.engine.connect() as connection:
            cfg.attributes['connection']=connection
            command.downgrade(cfg,'0007_schedules')
            command.upgrade(cfg,'head')
        self.assertEqual(self.client.get('/v1/memories/'+first['id']).json()['source_message_id'],original['id'])
        self.assertIsNone(self.client.get('/v1/memories/'+repeated['id']).json()['source_message_id'])
        self.client.headers['Authorization']='Bearer '+self.other_token
        self.assertIsNone(self.client.get('/v1/memories/'+foreign['id']).json()['source_message_id'])

    def test_failed_turn_can_retry_without_duplicate_user_message(self):
        request=str(uuid.uuid4());FakeModel.failure=True
        self.assertEqual(self.turn(request_id=request).json()['status'],'failed')
        FakeModel.failure=False
        self.assertEqual(self.turn(request_id=request).json()['status'],'complete')
        self.assertEqual(len(self.client.get(self.path).json()['items']),2)
        self.assertEqual(self.turn(text='Changed text',request_id=request).status_code,409)

    def test_memory_correction_and_deletion_invalidate_derived_replies(self):
        memory=self.create()
        self.turn('When does the print lab open?')
        self.assertIn(self.value['text'], str(FakeModel.calls[-1]))
        response=self.client.put('/v1/memories/'+memory['id'],json={**self.value,'text':'Synthetic lab opens at noon.','expected_revision':1})
        self.assertEqual(response.status_code,200)
        history=self.client.get(self.path).json()['items']
        self.assertEqual(history[-1]['status'],'invalidated')
        self.turn('When does it open now?')
        self.assertNotIn(self.value['text'],str(FakeModel.calls[-1]))
        self.assertIn('Synthetic lab opens at noon.',str(FakeModel.calls[-1]))
        self.client.delete('/v1/memories/'+memory['id'],params={'expected_revision':2})
        self.turn('What can you remember?')
        self.assertNotIn('Synthetic lab opens at noon.',str(FakeModel.calls[-1]))

    def test_inflight_reply_is_not_published_after_memory_changes(self):
        memory=self.create();FakeModel.entered=threading.Event();FakeModel.release=threading.Event()
        result=[]
        worker=threading.Thread(target=lambda:result.append(self.turn()))
        worker.start();self.assertTrue(FakeModel.entered.wait(3))
        with TestClient(self.app) as other:
            other.headers['Authorization']='Bearer '+self.second_token
            other.delete('/v1/memories/'+memory['id'],params={'expected_revision':1})
        FakeModel.release.set();worker.join(timeout=5)
        self.assertEqual(result[0].json()['status'],'failed')
        self.assertNotIn('Synthetic answer',str(self.client.get(self.path).json()))

    def test_meeting_mode_changes_prompt_and_is_recorded(self):
        response=self.turn(meeting_mode=True)
        self.assertTrue(response.json()['meeting_mode'])
        self.assertIn('No flirting',FakeModel.calls[-1][0]['content'])

    def test_remote_endpoints_rejected_before_model_use(self):
        for value in ['https://example.com/v1','http://192.168.1.2:1234/v1','http://user:secret@localhost:1234/v1']:
            with self.assertRaises(ValueError): validate_origin(value)
            response=self.client.put('/v1/model',json={'base_url':value,'model':'synthetic'})
            self.assertEqual(response.status_code,422)

    def test_checkin_resumes_confirms_and_enters_context(self):
        day={'local_date':'2026-10-29'}
        row=self.client.post('/v1/check-ins',json=day).json()
        self.assertEqual(row['next_key'],'completed')
        path='/v1/check-ins/'+row['id']
        for key,text in [('completed','Synthetic repair finished.'),('interruptions',''),('blockers','Waiting for a fictional part.'),('employee_work','Unknown.'),('tomorrow','Investigate the sample issue.')]:
            old=row['revision']
            row=self.client.put(path+'/answer',json={'key':key,'text':text,'expected_revision':old}).json()
            self.assertEqual(row['revision'],old+1)
        resumed=self.client.post('/v1/check-ins',json=day).json()
        self.assertEqual(resumed['id'],row['id']);self.assertIsNone(row['next_key'])
        self.assertEqual(resumed['status'],'draft')
        diary=self.client.put(path+'/diary',json={'text':row['diary_text'],'expected_revision':row['revision'],'confirm':True}).json()
        self.assertEqual(diary['status'],'confirmed')
        self.turn('What did I finish?')
        self.assertIn('Synthetic repair finished.',str(FakeModel.calls[-1]))
        self.assertEqual(self.client.put(path+'/diary',json={'text':'Changed diary','expected_revision':row['revision'],'confirm':True}).status_code,409)
        edited=self.client.put(path+'/diary',json={'text':'Corrected fictional diary.','expected_revision':diary['revision'],'confirm':True})
        self.assertEqual(edited.status_code,200)
        self.assertEqual(self.client.get(self.path).json()['items'][-1]['status'],'invalidated')

    def test_checkin_other_owner_and_early_confirmation_rejected(self):
        row=self.client.post('/v1/check-ins',json={'local_date':'2026-10-28'}).json()
        path='/v1/check-ins/'+row['id']
        body={'text':'Premature','expected_revision':1,'confirm':True}
        self.assertEqual(self.client.put(path+'/diary',json=body).status_code,409)
        self.assertEqual(self.client.put(path+'/diary',json=body,headers={'Authorization':'Bearer '+self.other_token}).status_code,404)


# Avoid running inherited cases twice while preserving the fixture implementation.
for name in list(vars(memory_tests.MemoryTests)):
    if name.startswith('test_') and name not in CompanionTests.__dict__:
        setattr(CompanionTests,name,None)
