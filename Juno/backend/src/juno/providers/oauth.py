"""Desktop PKCE authorization. Only bounded in-memory pending secrets; persistent credentials belong in native Keychain."""
import base64
import hashlib
import secrets
import re
import threading
import time
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
from .http import ReadError,request_json,validate_request
from .readers import GOOGLE

SCOPES={
 'gmail':['openid','email','https://www.googleapis.com/auth/gmail.readonly'],
 'google_calendar':['openid','email','https://www.googleapis.com/auth/calendar.calendarlist.readonly','https://www.googleapis.com/auth/calendar.events.readonly'],
 'google_tasks':['openid','email','https://www.googleapis.com/auth/tasks.readonly'],
 'google_chat':['openid','email','https://www.googleapis.com/auth/chat.spaces.readonly','https://www.googleapis.com/auth/chat.messages.readonly'],
 'outlook_calendar':['offline_access','User.Read','Calendars.Read'],
}


def client_settings(provider,client_id,client_secret='',tenant='organizations'):
    if provider not in SCOPES:raise ReadError('This provider uses a manually supplied token, not desktop OAuth.',422)
    if not isinstance(client_id,str) or not 3<=len(client_id)<=300 or not re.fullmatch(r'[A-Za-z0-9._:-]+',client_id):raise ReadError('Enter the registered desktop/public OAuth client ID.',422)
    if provider in GOOGLE and not client_id.endswith('.apps.googleusercontent.com'):raise ReadError('Use a Google Desktop app OAuth client ID ending in .apps.googleusercontent.com.',422)
    if len(client_secret)>2000 or any(ord(c)<32 for c in client_secret):raise ReadError('The OAuth client secret is invalid.',422)
    if not isinstance(tenant,str) or not re.fullmatch(r'(?:common|organizations|consumers|[A-Za-z0-9.-]{1,150})',tenant):raise ReadError('Enter an approved Microsoft tenant ID/domain or organizations/common/consumers.',422)
    return {'provider':provider,'client_id':client_id,'client_secret':client_secret if provider in GOOGLE else '', 'tenant':tenant}


def token_result(provider,data,require_refresh=False):
    if not isinstance(data,dict) or not isinstance(data.get('access_token'),str) or not data['access_token'] or str(data.get('token_type','')).lower()!='bearer':raise ReadError('The provider did not return a usable bearer token. Sign in again.',401)
    if len(data['access_token'])>16384 or any(c.isspace() or ord(c)<32 for c in data['access_token']):raise ReadError('The provider returned an invalid bearer token.',401)
    refresh=data.get('refresh_token')
    if (refresh is not None and (not isinstance(refresh,str) or not refresh or len(refresh)>16384)) or (require_refresh and not refresh):raise ReadError('The provider did not grant renewable offline access. Sign in again and approve the requested read access.',401)
    try:
        expires=int(data.get('expires_in',3600))
        if not 1<=expires<=604800:raise ValueError()
    except (ValueError,TypeError):raise ReadError('The provider returned an invalid token lifetime.',401) from None
    scope=data.get('scope')
    if scope is not None:
        if not isinstance(scope,str):raise ReadError('The provider returned invalid scope information.',401)
        aliases={'email':'https://www.googleapis.com/auth/userinfo.email'}
        actual={aliases.get(s,s.removeprefix('https://graph.microsoft.com/')) for s in scope.split()}
        required={aliases.get(s,s) for s in SCOPES[provider] if s!='offline_access'}
        if not required<=actual:raise ReadError('Not all requested read permissions were approved. Sign in again.',401)
    return {'access_token':data['access_token'],'refresh_token':refresh,'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=expires)).isoformat(),
        'scope':scope or ' '.join(SCOPES[provider]),'token_type':'Bearer'}


class OAuthManager:
    def __init__(self,transport=None,clock=time.monotonic):self.transport=transport;self.clock=clock;self.flows={};self.lock=threading.RLock();self.timer=None
    def sweep(self):
        with self.lock:
            self.cleanup();self.timer=None
            if self.flows:self.schedule_cleanup()
    def schedule_cleanup(self):
        if self.timer is None:
            self.timer=threading.Timer(30,self.sweep);self.timer.daemon=True;self.timer.start()
    def cleanup(self):
        for key in list(self.flows):
            if self.flows[key]['expires']<=self.clock():self.flows.pop(key,None)
    def start(self,owner,device,provider,client_id,client_secret,tenant,port):
        config=client_settings(provider,client_id,client_secret,tenant)
        if type(port) is not int or not 1<=port<=65535:raise ReadError('The private loopback callback is unavailable.',422)
        family='google' if provider in GOOGLE else 'microsoft'
        redirect=('http://127.0.0.1:' if family=='google' else 'http://localhost:')+str(port)+'/v1/providers/oauth/callback/'+family
        state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        params={'client_id':client_id,'response_type':'code','redirect_uri':redirect,'scope':' '.join(SCOPES[provider]),'state':state,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'consent select_account' if family=='google' else 'select_account'}
        if family=='google':params.update(access_type='offline',include_granted_scopes='false');base='https://accounts.google.com/o/oauth2/v2/auth'
        else:base='https://login.microsoftonline.com/'+tenant+'/oauth2/v2.0/authorize';params['response_mode']='query'
        with self.lock:
            self.cleanup()
            for key,value in list(self.flows.items()):
                if (value['owner'],value['device'],value['provider'])==(owner,device,provider):self.flows.pop(key)
            if len(self.flows)>=50:raise ReadError('Too many pending authorizations. Finish or cancel another sign-in.',429,60)
            self.flows[state]={**config,'owner':owner,'device':device,'family':family,'verifier':verifier,'redirect':redirect,'expires':self.clock()+600,'phase':'waiting'}
            self.schedule_cleanup()
        return {'flow_id':state,'authorization_url':base+'?'+urlencode(params),'redirect_uri':redirect,'scopes':SCOPES[provider],'expires_in':600}
    def exchange(self,config,fields,require_refresh=False):
        provider=config['provider'];url='https://oauth2.googleapis.com/token' if provider in GOOGLE else 'https://login.microsoftonline.com/'+config['tenant']+'/oauth2/v2.0/token'
        body={'client_id':config['client_id'],**fields}
        if config['client_secret']:body['client_secret']=config['client_secret']
        if provider=='outlook_calendar' and fields.get('grant_type')=='refresh_token':body['scope']=' '.join(SCOPES[provider])
        raw=urlencode(body).encode();headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'}
        validate_request('POST',url)
        data=self.transport('POST',url,headers,raw) if self.transport else request_json('POST',url,headers,raw,timeout=15)
        return token_result(provider,data,require_refresh)
    def callback(self,family,state,code=None,denied=False):
        with self.lock:
            value=self.flows.get(state)
            if not value or value['expires']<=self.clock():self.flows.pop(state,None);raise ReadError('Authorization expired or is invalid. Return to Juno and start again.',410)
            if value['family']!=family or value['phase']!='waiting':raise ReadError('This authorization response does not match a waiting Juno sign-in.',409)
            if denied:
                value.pop('verifier',None);value.pop('client_secret',None)
                value['phase']='failed';value['error']='Sign-in was cancelled or permission was denied.';return
            if not isinstance(code,str) or not 8<=len(code)<=4096:raise ReadError('The authorization response is invalid.',422)
            value['phase']='exchanging';config=dict(value)
        try:result=self.exchange(config,{'grant_type':'authorization_code','code':code,'redirect_uri':config['redirect'],'code_verifier':config['verifier']},require_refresh=True)
        except ReadError as error:
            with self.lock:
                if state in self.flows:
                    self.flows[state].pop('verifier',None);self.flows[state].pop('client_secret',None)
                    self.flows[state].update(phase='failed',error=str(error))
            return
        except Exception:
            with self.lock:
                if state in self.flows:
                    self.flows[state].pop('verifier',None);self.flows[state].pop('client_secret',None)
                    self.flows[state].update(phase='failed',error='Authorization could not be completed. Sign in again; private provider details were withheld.')
            return
        with self.lock:
            if state in self.flows and self.flows[state]['expires']>self.clock():
                # Drop verifier/client secret as soon as exchange is done; native polling still needs delivery acknowledgment.
                self.flows[state]={k:v for k,v in self.flows[state].items() if k not in ('verifier','client_secret')}
                self.flows[state].update(phase='complete',tokens=result)
    def owned(self,state,owner,device):
        value=self.flows.get(state)
        if not value or (value['owner'],value['device'])!=(owner,device):raise ReadError('Authorization session not found.',404)
        if value['expires']<=self.clock():self.flows.pop(state,None);raise ReadError('Authorization expired. Start sign-in again.',410)
        return value
    def poll(self,state,owner,device):
        with self.lock:
            value=self.owned(state,owner,device)
            return {'phase':value['phase'],'provider':value['provider'],**({'tokens':value['tokens']} if value['phase']=='complete' else {}),**({'error':value['error']} if value.get('error') else {})}
    def acknowledge(self,state,owner,device):
        with self.lock:
            value=self.owned(state,owner,device)
            if value['phase']!='complete':raise ReadError('Authorization is not ready for delivery acknowledgment.',409)
            self.flows.pop(state,None)
    def cancel(self,state,owner,device):
        with self.lock:self.owned(state,owner,device);self.flows.pop(state,None)
    def refresh(self,provider,client_id,client_secret,tenant,refresh_token):
        config=client_settings(provider,client_id,client_secret,tenant)
        if not isinstance(refresh_token,str) or not refresh_token or len(refresh_token)>16384:raise ReadError('Sign in again to obtain renewable authorization.',401)
        try:return self.exchange(config,{'grant_type':'refresh_token','refresh_token':refresh_token})
        except ReadError as error:
            if error.status==429:raise
            raise ReadError('Authorization could not be renewed. Sign in again; the previous source copy is retained.',401) from None
