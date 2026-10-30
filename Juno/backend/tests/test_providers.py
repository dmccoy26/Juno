"""Fictional provider transports; no external account reads or OAuth consent."""
import base64
import json
import unittest
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
from fastapi.testclient import TestClient
import test_memory_api as memory_tests
from juno.api import create_app
from juno.providers.http import ReadError,validate_request,ProviderHTTP
from juno.providers.common import identity,PlainText
from juno.providers.readers import read,discover
from juno.providers.oauth import OAuthManager,SCOPES
from juno.shared_host import LANBoundary
from test_companion import FakeModel

TOKEN='synthetic-private-provider-token'
LEFT='2026-10-29';RIGHT='2026-11-02'

class ProviderFixture:
    def __init__(self):self.calls=[];self.bad_cursor=False;self.fail=False;self.sheet_changed=False;self.unsafe_next=False
    def __call__(self,method,url,headers,body):
        validate_request(method,url);self.calls.append((method,url,headers,body))
        if self.fail:raise ReadError('Synthetic provider unavailable',502)
        parts=urlsplit(url);query=parse_qs(parts.query);path=parts.path
        if parts.netloc=='openidconnect.googleapis.com':return {'sub':'synthetic-google-account','email':'student@example.invalid'}
        if parts.netloc=='gmail.googleapis.com':
            if path.endswith('/profile'):return {'emailAddress':'student@example.invalid'}
            if path.endswith('/messages'):return {'messages':[{'id':'synthetic-message','threadId':'synthetic-thread'}]}
            return {'id':'synthetic-message','threadId':'synthetic-thread','labelIds':['INBOX','UNREAD'],'internalDate':'1793271600000',
                    'payload':{'mimeType':'multipart/alternative','headers':[{'name':'Subject','value':'Synthetic printer issue'},{'name':'From','value':'Student Test <student@example.invalid>'}],
                        'parts':[{'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(b'Synthetic plain message body').decode()}},
                                 {'mimeType':'text/html','body':{'data':base64.urlsafe_b64encode(b'<script>hidden</script><p>HTML alternative</p>').decode()}},
                                 {'filename':'never-download.txt','mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(b'Attachment must stay omitted').decode()}}]}}
        if parts.netloc=='www.googleapis.com':
            if '/calendarList' in path:return {'items':[{'id':'primary','summary':'Synthetic calendar','accessRole':'owner'}]}
            return {'items':[{'id':'synthetic-event','summary':'Synthetic Dean meeting','start':{'dateTime':'2026-10-30T09:00:00-05:00'},'end':{'dateTime':'2026-10-30T10:00:00-05:00'},'description':'<p>Read this agenda</p><script>never run</script>'},
                {'id':'synthetic-cancel','status':'cancelled'},
                {'id':'synthetic-declined','attendees':[{'self':True,'responseStatus':'declined'}]},
                {'id':'synthetic-transparent','transparency':'transparent','start':{'date':'2026-10-31'},'end':{'date':'2026-11-01'}}]}
        if parts.netloc=='tasks.googleapis.com':
            if path.endswith('/lists'):return {'items':[{'id':'synthetic-list','title':'Synthetic list'}]}
            return {'items':[{'id':'synthetic-task','title':'Synthetic repair','notes':'Synthetic task notes','status':'needsAction','due':'2026-10-31T00:00:00Z'}],**({'nextPageToken':'repeat'} if self.bad_cursor else {})}
        if parts.netloc=='chat.googleapis.com':
            if path=='/v1/spaces':return {'spaces':[{'name':'spaces/SYNTHETIC','displayName':'Synthetic space'}]}
            return {'messages':[{'name':'spaces/SYNTHETIC/messages/message1','text':'Synthetic room issue','createTime':'2026-10-30T15:00:00Z','sender':{'name':'users/synthetic'},'thread':{'name':'spaces/SYNTHETIC/threads/thread1'}}]}
        if parts.netloc=='slack.com':
            if path.endswith('/auth.test'):return {'ok':True,'team_id':'TSYNTHETIC','user_id':'USYNTHETIC','team':'Synthetic team','user':'Student Test'}
            if path.endswith('/conversations.list'):return {'ok':True,'channels':[{'id':'CSYNTHETIC','name':'synthetic-channel'}],'response_metadata':{'next_cursor':''}}
            if path.endswith('/conversations.info'):return {'ok':True,'channel':{'id':'CSYNTHETIC','name':'synthetic-channel'}}
            stamp=str(datetime(2026,10,30,15,tzinfo=timezone.utc).timestamp())
            parent={'ts':stamp,'text':'Synthetic Slack parent','user':'USYNTHETIC','reply_count':1}
            reply={'ts':str(float(stamp)+60),'thread_ts':stamp,'text':'Synthetic Slack reply','user':'USYNTHETIC'}
            return {'ok':True,'messages':[parent,reply] if path.endswith('/conversations.replies') else [parent],'has_more':False,'response_metadata':{'next_cursor':''}}
        if parts.netloc=='api.smartsheet.com':
            if path.endswith('/users/me'):return {'id':1234,'email':'student@example.invalid'}
            if path=='/2.0/sheets':return {'data':[{'id':1001,'name':'Synthetic sheet'}],'pageNumber':1,'totalPages':1,'totalCount':1}
            return {'id':1001,'name':'Synthetic sheet','version':2 if self.sheet_changed and query.get('pageSize')==['1'] else 1,'totalRowCount':1,
                    'columns':[{'id':2001,'title':'Task name','primary':True},{'id':2002,'title':'Status'}],
                    'rows':[{'id':3001,'rowNumber':1,'cells':[{'columnId':2001,'value':'Synthetic sheet task'},{'columnId':2002,'displayValue':'Waiting for supplies'}]}]}
        if parts.netloc=='graph.microsoft.com':
            if path=='/v1.0/me':return {'id':'synthetic-ms-account','mail':'student@example.invalid'}
            if path=='/v1.0/me/calendars':return {'value':[{'id':'synthetic-ms-calendar','name':'Synthetic calendar'}]}
            return {'value':[{'id':'synthetic-ms-event','subject':'Synthetic MS meeting','start':{'dateTime':'2026-10-30T16:00:00.0000000','timeZone':'UTC'},'end':{'dateTime':'2026-10-30T17:00:00.0000000','timeZone':'UTC'},'body':{'contentType':'HTML','content':'<p>Synthetic agenda</p>'},'location':{'displayName':'Synthetic room'},'showAs':'busy'}],**({'@odata.nextLink':'https://example.invalid/steal'} if self.unsafe_next else {})}
        raise AssertionError('Unexpected synthetic request: '+method+' '+url)


def config(provider):
    account='synthetic-google-account' if provider in ('gmail','google_calendar','google_tasks','google_chat') else 'TSYNTHETIC:USYNTHETIC' if provider=='slack' else '1234' if provider=='smartsheet' else 'synthetic-ms-account'
    resources={'gmail':[],'google_calendar':['primary'],'google_tasks':['synthetic-list'],'google_chat':['spaces/SYNTHETIC'],'slack':['CSYNTHETIC'],'smartsheet':['1001'],'outlook_calendar':['synthetic-ms-calendar']}[provider]
    return {'reviewed_account':identity(provider,account),'resources':resources,'start':LEFT,'end':RIGHT,'timezone':'America/Chicago','query':'in:inbox is:unread','include_threads':True}


class ProviderReaderTests(unittest.TestCase):
    def test_all_seven_readers_and_resource_discovery_are_get_only(self):
        for provider in ('gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar'):
            with self.subTest(provider=provider):
                fixture=ProviderFixture();found=discover(provider,TOKEN,fixture)
                self.assertEqual(found['account']['id'],config(provider)['reviewed_account'])
                result=read(provider,TOKEN,config(provider),fixture)
                self.assertFalse(result['review_required']);self.assertTrue(result['items']);self.assertTrue(result['details']['read_only'])
                self.assertTrue(all(c[0]=='GET' and c[2]['Authorization']=='Bearer '+TOKEN for c in fixture.calls))
                self.assertNotIn(TOKEN,json.dumps(result))
                self.assertTrue(result['details']['active'])
    def test_account_review_precedes_content_read(self):
        fixture=ProviderFixture();result=read('gmail',TOKEN,{**config('gmail'),'reviewed_account':None},fixture)
        self.assertTrue(result['review_required']);self.assertEqual(len(fixture.calls),1)
    def test_email_is_plain_text_unread_and_attachment_free(self):
        result=read('gmail',TOKEN,config('gmail'),ProviderFixture());row=result['items'][0]
        self.assertIn('Synthetic plain message body',row['notes']);self.assertNotIn('HTML alternative',row['notes']);self.assertNotIn('Attachment must',row['notes'])
        self.assertTrue(row['unread']);self.assertTrue(row['body_available'])
    def test_calendar_visibility_declines_cancellation_and_busy_time(self):
        result=read('google_calendar',TOKEN,config('google_calendar'),ProviderFixture())
        self.assertEqual(len(result['items']),2);self.assertNotIn('never run',str(result));self.assertEqual(result['details']['busy_days'][0]['busy_minutes'],60)
    def test_cursor_version_and_nextlink_failures_keep_complete_reads(self):
        fixture=ProviderFixture();fixture.bad_cursor=True
        with self.assertRaises(ReadError):read('google_tasks',TOKEN,config('google_tasks'),fixture)
        fixture=ProviderFixture();fixture.sheet_changed=True
        with self.assertRaises(ReadError):read('smartsheet',TOKEN,config('smartsheet'),fixture)
        fixture=ProviderFixture();fixture.unsafe_next=True
        with self.assertRaises(ReadError):read('outlook_calendar',TOKEN,config('outlook_calendar'),fixture)
    def test_fixed_destinations_deny_writes_token_leaks_and_arbitrary_urls(self):
        for method,url in [('POST','https://gmail.googleapis.com/gmail/v1/users/me/messages/send'),('GET','https://example.invalid/'),('GET','http://slack.com/api/auth.test'),('GET','https://token@slack.com/api/auth.test'),('GET','https://slack.com/api/chat.postMessage'),('POST','https://example.invalid/token')]:
            with self.assertRaises(ReadError):validate_request(method,url)
        with self.assertRaises(ReadError):ProviderHTTP(TOKEN,lambda *a:{'echo':TOKEN}).get('https://slack.com','/api/auth.test')


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.tick=0
        def transport(method,url,headers,body):
            self.calls.append((method,url,parse_qs(body.decode())))
            return {'access_token':'synthetic-oauth-access','refresh_token':'synthetic-oauth-refresh','expires_in':3600,'token_type':'Bearer','scope':' '.join(SCOPES['gmail'])}
        self.manager=OAuthManager(transport,clock=lambda:self.tick)
    def start(self):return self.manager.start('owner','device','gmail','synthetic.apps.googleusercontent.com','synthetic-client-secret','organizations',18123)
    def test_pkce_state_single_callback_delivery_ack_and_owner_isolation(self):
        started=self.start();state=started['flow_id'];query=parse_qs(urlsplit(started['authorization_url']).query)
        self.assertEqual(query['code_challenge_method'],['S256']);self.assertNotIn('code_verifier',query)
        self.assertEqual(query['redirect_uri'],['http://127.0.0.1:18123/v1/providers/oauth/callback/google'])
        self.assertEqual(self.manager.poll(state,'owner','device')['phase'],'waiting')
        with self.assertRaises(ReadError):self.manager.poll(state,'other','device')
        with self.assertRaises(ReadError):self.manager.callback('microsoft',state,'synthetic-code')
        self.manager.callback('google',state,'synthetic-code')
        delivered=self.manager.poll(state,'owner','device');self.assertEqual(delivered['phase'],'complete')
        self.assertEqual(delivered,self.manager.poll(state,'owner','device'))
        self.assertIn('code_verifier',self.calls[0][2]);self.assertEqual(self.calls[0][1],'https://oauth2.googleapis.com/token')
        with self.assertRaises(ReadError):self.manager.callback('google',state,'synthetic-code')
        self.manager.acknowledge(state,'owner','device')
        with self.assertRaises(ReadError):self.manager.poll(state,'owner','device')
    def test_expiry_denial_cancel_and_missing_refresh(self):
        state=self.start()['flow_id'];self.tick=601
        with self.assertRaises(ReadError):self.manager.callback('google',state,'synthetic-code')
        state=self.start()['flow_id'];self.manager.callback('google',state,denied=True)
        self.assertEqual(self.manager.poll(state,'owner','device')['phase'],'failed')
        self.manager.cancel(state,'owner','device')
        self.manager.transport=lambda *a:{'access_token':'synthetic-access','token_type':'Bearer','scope':' '.join(SCOPES['gmail'])}
        state=self.start()['flow_id'];self.manager.callback('google',state,'synthetic-code')
        self.assertEqual(self.manager.poll(state,'owner','device')['phase'],'failed')
    def test_renewal_and_minimal_scope_rejection(self):
        result=self.manager.refresh('gmail','synthetic.apps.googleusercontent.com','','organizations','synthetic-refresh')
        self.assertTrue(result['refresh_token']);self.assertEqual(self.calls[0][2]['grant_type'],['refresh_token'])
        self.manager.transport=lambda *a:{'access_token':'synthetic-access','refresh_token':'synthetic-refresh','token_type':'Bearer','scope':'openid email'}
        state=self.start()['flow_id'];self.manager.callback('google',state,'synthetic-code')
        self.assertEqual(self.manager.poll(state,'owner','device')['phase'],'failed')


class ProviderAPITests(memory_tests.MemoryTests):
    def setUp(self):
        super().setUp();self.client.close();self.fixture=ProviderFixture();FakeModel.calls=[];FakeModel.failure=False;FakeModel.entered=None;FakeModel.release=None
        self.app=create_app(self.engine,model_factory=FakeModel,provider_transport=self.fixture)
        self.client=TestClient(self.app,base_url='http://127.0.0.1:18123',client=('127.0.0.1',50000));self.client.headers['Authorization']='Bearer '+self.token
    def refresh(self,provider='gmail',expected=None):return self.client.post('/v1/providers/'+provider+'/refresh',json={'token':TOKEN,'selection':config(provider),'expected_id':expected})
    def test_owner_cache_context_disconnection_and_error_retention(self):
        first=self.refresh();self.assertEqual(first.status_code,200,first.text);row=first.json()['snapshot'];ident=row['id']
        self.assertEqual(self.client.get('/v1/integrations',headers={'Authorization':'Bearer '+self.other_token}).json()['items'],[])
        self.assertNotIn(TOKEN,self.client.get('/v1/cache').text)
        self.assertIn('Synthetic printer issue',self.client.get('/v1/cache').text)
        self.fixture.fail=True;self.assertEqual(self.refresh(expected=ident).status_code,502)
        saved=self.client.get('/v1/integrations').json()['items'][0];self.assertEqual(saved['id'],ident);self.assertTrue(saved['error'])
        self.fixture.fail=False
        self.client.put('/v1/model',json={'base_url':'http://127.0.0.1:1234/v1','model':'synthetic-model'})
        conv=self.client.post('/v1/conversations',json={'title':'Synthetic provider chat'}).json()['id'];path='/v1/conversations/'+conv+'/messages'
        import uuid
        self.client.post(path,json={'request_id':str(uuid.uuid4()),'text':'What printer issue?'})
        self.assertIn('Synthetic plain message body',str(FakeModel.calls[-1]))
        self.assertEqual(self.client.post('/v1/providers/gmail/disconnect',json={'expected_id':ident}).status_code,200)
        self.assertEqual(self.client.get(path).json()['items'][-1]['status'],'invalidated')
        self.client.post(path,json={'request_id':str(uuid.uuid4()),'text':'What printer issue now?'})
        self.assertNotIn('Synthetic plain message body',str(FakeModel.calls[-1]))
        self.assertTrue(self.client.get('/v1/integrations').json()['items'])
    def test_lan_origin_and_invalid_secret_input_boundaries(self):
        for path in ['/v1/providers/catalog','/v1/providers/gmail/discover','/v1/providers/oauth/start']:
            method='GET' if path.endswith('catalog') else 'POST'
            self.assertEqual(self.client.request(method,path,headers={'Origin':'https://example.invalid'},json={}).status_code,403)
        with TestClient(LANBoundary(self.app),client=('192.168.1.9',50000)) as lan:
            lan.headers['Authorization']='Bearer '+self.token
            self.assertEqual(lan.get('/v1/providers/catalog').status_code,403)
            self.assertEqual(lan.post('/v1/providers/gmail/refresh',json={}).status_code,403)
            self.assertEqual(lan.get('/v1/providers/oauth/return').status_code,403)
        invalid=self.client.post('/v1/providers/gmail/discover',json={'token':TOKEN,'extra':'private-input'})
        self.assertEqual(invalid.status_code,422);self.assertNotIn(TOKEN,invalid.text);self.assertNotIn('private-input',invalid.text)

    def test_local_oauth_callback_delivery_renewal_and_ack_routes(self):
        calls=[]
        def exchange(method,url,headers,body):
            calls.append((method,url,parse_qs(body.decode())))
            return {'access_token':'synthetic-oauth-access','refresh_token':'synthetic-rotated-refresh','token_type':'Bearer','expires_in':3600,'scope':' '.join(SCOPES['gmail'])}
        manager=OAuthManager(exchange)
        app=create_app(self.engine,oauth_manager=manager)
        with TestClient(app,base_url='http://127.0.0.1:18123',client=('127.0.0.1',50000)) as client:
            client.headers['Authorization']='Bearer '+self.token
            settings={'provider':'gmail','client_id':'synthetic.apps.googleusercontent.com','client_secret':'synthetic-secret'}
            started=client.post('/v1/providers/oauth/start',json=settings)
            self.assertEqual(started.status_code,200,started.text);state=started.json()['flow_id']
            path='/v1/providers/oauth/session/'+state
            self.assertEqual(client.get(path,headers={'Authorization':'Bearer '+self.other_token}).status_code,404)
            self.assertEqual(client.get(path).json()['phase'],'waiting')
            # Browser callback has no device bearer; state plus loopback binds it to the initiating native session.
            response=client.get('/v1/providers/oauth/callback/google',params={'state':state,'code':'synthetic-code'},headers={'Authorization':''},follow_redirects=False)
            self.assertEqual(response.status_code,303);self.assertEqual(response.headers['location'],'/v1/providers/oauth/return')
            self.assertEqual(response.headers['cache-control'],'no-store');self.assertNotIn('synthetic-code',response.text)
            delivered=client.get(path);self.assertEqual(delivered.json()['tokens']['refresh_token'],'synthetic-rotated-refresh')
            self.assertEqual(delivered.headers['cache-control'],'no-store')
            self.assertEqual(client.get(path).json(),delivered.json())
            self.assertNotIn('synthetic-oauth-access',client.get('/v1/cache').text)
            self.assertEqual(client.post(path+'/ack').status_code,200);self.assertEqual(client.get(path).status_code,404)
            renewed=client.post('/v1/providers/oauth/renew',json={**settings,'refresh_token':'synthetic-previous-refresh'})
            self.assertEqual(renewed.status_code,200,renewed.text);self.assertEqual(calls[-1][2]['grant_type'],['refresh_token'])
            self.assertEqual(client.get('/v1/providers/state').json()['items'],[])
            self.assertEqual(client.get('/v1/providers/oauth/return',headers={'Authorization':''}).status_code,200)
            self.assertEqual(client.get('/v1/providers/oauth/return',headers={'Origin':'https://example.invalid'}).status_code,403)
            cancelled=client.post('/v1/providers/oauth/start',json=settings).json()['flow_id']
            self.assertEqual(client.delete('/v1/providers/oauth/session/'+cancelled).status_code,200)
            self.assertEqual(client.get('/v1/providers/oauth/callback/google',params={'state':cancelled,'code':'synthetic-code'}).status_code,410)

    def test_rate_limit_and_revocation_preserve_copy_without_secret_diagnostics(self):
        row=self.refresh().json()['snapshot'];ident=row['id']
        def limited(*args):raise ReadError('The provider is rate limiting this connection.',429,123)
        self.app.state.provider_oauth.transport=limited
        # create_app captures the read transport; construct another instance for controlled failure.
        for status in (429,401):
            def broken(*args):raise ReadError('Synthetic authorization/read failure',status,123 if status==429 else None)
            with TestClient(create_app(self.engine,provider_transport=broken),base_url='http://127.0.0.1:18123',client=('127.0.0.1',50000)) as client:
                client.headers['Authorization']='Bearer '+self.token
                response=client.post('/v1/providers/gmail/refresh',json={'token':TOKEN,'selection':config('gmail'),'expected_id':ident})
                self.assertEqual(response.status_code,status)
                if status==429:self.assertEqual(response.headers['retry-after'],'123')
                saved=client.get('/v1/integrations').json()['items'][0]
                self.assertEqual(saved['id'],ident);self.assertTrue(saved['items'])
                if status==401:self.assertFalse(saved['details']['active'])
                self.assertNotIn(TOKEN,response.text)

    def test_combined_source_limit_rejects_without_replacing_previous_copy(self):
        from unittest.mock import patch
        first=self.refresh().json()['snapshot']
        with patch('juno.integrations_api.EVIDENCE_BYTES',100):
            response=self.refresh(expected=first['id'])
            self.assertEqual(response.status_code,413)
        self.assertEqual(self.client.get('/v1/integrations').json()['items'][0]['id'],first['id'])

for name in list(vars(memory_tests.MemoryTests)):
    if name.startswith('test_') and name not in ProviderAPITests.__dict__:setattr(ProviderAPITests,name,None)
