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
        with self.factory() as session:
            connection = session.get(ModelConnection, self.actor.owner_id)
            session.delete(connection);session.commit()
        self.assertEqual(self.turn('Remember this: Fictional note').status_code, 200)
        self.assertEqual(self.turn('Do you remember that fictional cutter?').status_code, 503)

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
