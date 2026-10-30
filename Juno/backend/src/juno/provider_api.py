"""Local-only native connection operations; normalized dated evidence is the only shared output."""
from datetime import timedelta
from typing import Literal
from uuid import uuid4
import json
from fastapi import Depends,HTTPException,Request,APIRouter
from fastapi.responses import HTMLResponse,RedirectResponse
from pydantic import BaseModel,ConfigDict,Field,SecretStr
from sqlalchemy import select
from .models import IntegrationSnapshot,now
from .integrations_api import snapshot_view,check_evidence_size
from .providers import readers
from .providers.http import ReadError
from .providers.oauth import OAuthManager,SCOPES

Provider=Literal['gmail','google_calendar','google_tasks','google_chat','slack','smartsheet','outlook_calendar']
class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Credential(Strict):token:SecretStr
class Selection(Strict):
    resources:list[str]=Field(default_factory=list,max_length=10)
    query:str=Field(default='in:inbox is:unread',max_length=500)
    start:str=Field(default='',max_length=10)
    end:str=Field(default='',max_length=10)
    timezone:str=Field(default='America/Chicago',max_length=100)
    include_threads:bool=True
    reviewed_account:str | None=Field(default=None,pattern=r'^[0-9a-f]{64}$')
class Refresh(Credential):
    selection:Selection
    expected_id:str | None=Field(default=None,max_length=36)
class OAuthSettings(Strict):
    provider:Provider
    client_id:str=Field(max_length=300)
    client_secret:SecretStr=SecretStr('')
    tenant:str=Field(default='organizations',max_length=150)
class Renew(OAuthSettings):refresh_token:SecretStr
class Disconnect(Strict):expected_id:str | None=Field(default=None,max_length=36)


def local_native(request:Request):
    if request.scope.get('juno_lan') or request.headers.get('origin') or not request.client or request.client.host not in ('127.0.0.1','::1'):
        raise HTTPException(403,'Connection administration is available only in native Juno on the work Mac.')


def install(app,db,device,lock_owner,transport=None,oauth_manager=None):
    oauth=oauth_manager or OAuthManager(transport=transport);app.state.provider_oauth=oauth
    router=APIRouter(prefix='/v1/providers',dependencies=[Depends(local_native)])
    def owned(session,owner,kind):return session.scalar(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==owner,IntegrationSnapshot.kind==kind).execution_options(populate_existing=True))
    def check(row,expected):
        if (row.id if row else None)!=expected:raise HTTPException(409,'This source changed. Reload before replacing its saved copy.')
    def failure(error):
        headers={'Retry-After':str(error.retry_after)} if error.retry_after else None
        raise HTTPException(error.status,str(error),headers=headers) from None
    def failed(session,actor,kind,expected,error):
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,kind)
        if row and row.id==expected:
            from .companion import invalidate_context
            invalidate_context(session,actor.owner_id,'integration:'+kind)
            row.error=str(error)[:500]
            if error.status in (401,403,404):
                row.id=str(uuid4())  # Fence reads that began before authorization was denied.
                row.details={**row.details,'active':False,'connection_notice':'Authorization/resource needs review; historical evidence is retained but excluded from new model context.'}
            session.commit()

    @router.get('/catalog')
    def catalog(actor=Depends(device)):
        return {'providers':[{'id':p,'method':'oauth' if p in SCOPES else 'token','scopes':SCOPES.get(p,[])} for p in readers.PROVIDERS],
            'notice':'Direct provider connections are separate from TaskDock. No upstream credentials are imported. Live access waits for your credentials, explicit resource selection and consent.'}

    @router.get('/state')
    def connection_state(actor=Depends(device),session=Depends(db)):
        rows=session.scalars(select(IntegrationSnapshot).where(IntegrationSnapshot.owner_id==actor.owner_id)).all()
        return {'items':[{k:v for k,v in snapshot_view(row).items() if k!='items'} for row in rows]}

    @router.post('/{provider}/discover')
    def discover(provider:Provider,value:Credential,actor=Depends(device)):
        try:return readers.discover(provider,value.token.get_secret_value(),transport)
        except ReadError as error:failure(error)
        except Exception:failure(ReadError('Provider discovery could not be validated. Private diagnostics were withheld.'))

    @router.post('/{provider}/refresh')
    def refresh(provider:Provider,value:Refresh,actor=Depends(device),session=Depends(db)):
        row=owned(session,actor.owner_id,provider);check(row,value.expected_id);session.commit()
        try:result=readers.read(provider,value.token.get_secret_value(),value.selection.model_dump(),transport)
        except ReadError as error:failed(session,actor,provider,value.expected_id,error);failure(error)
        except Exception:
            error=ReadError('The provider response could not be validated. The previous copy has been retained; private diagnostics were withheld.')
            failed(session,actor,provider,value.expected_id,error);failure(error)
        if result['review_required']:return result
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,provider);check(row,value.expected_id)
        check_evidence_size(session,actor.owner_id,provider,result['items'],result['details'])
        from .companion import invalidate_context
        if row:invalidate_context(session,actor.owner_id,'integration:'+provider)
        else:row=IntegrationSnapshot(owner_id=actor.owner_id,kind=provider);session.add(row)
        row.id=str(uuid4());row.origin='Direct '+provider.replace('_',' ')+' · '+result['account']['label'];row.items=result['items'];row.details=result['details'];row.fetched_at=now();row.error=None
        session.commit()
        return {'review_required':False,'snapshot':snapshot_view(row)}

    @router.post('/{provider}/disconnect')
    def disconnect(provider:Provider,value:Disconnect,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id);row=owned(session,actor.owner_id,provider);check(row,value.expected_id)
        if row:
            from .companion import invalidate_context
            invalidate_context(session,actor.owner_id,'integration:'+provider)
            row.id=str(uuid4())  # An older in-flight refresh must not undo an explicit disconnect.
            row.details={**row.details,'active':False,'connection_notice':'Disconnected on the work Mac; this historical copy is excluded from new model context.'}
            row.error='Disconnected. This dated copy is retained until you remove it.';session.commit()
        return {'disconnected':True,'notice':'Forget the credential in native Juno Keychain setup. No upstream authorization or data was changed.'}

    @router.post('/oauth/start')
    def start(value:OAuthSettings,request:Request,actor=Depends(device)):
        if request.url.hostname not in ('127.0.0.1','localhost'):raise HTTPException(422,'The private loopback callback address is invalid.')
        try:return oauth.start(actor.owner_id,actor.id,value.provider,value.client_id,value.client_secret.get_secret_value(),value.tenant,request.url.port or 80)
        except ReadError as error:failure(error)

    @router.post('/oauth/renew')
    def renew(value:Renew,actor=Depends(device)):
        try:return oauth.refresh(value.provider,value.client_id,value.client_secret.get_secret_value(),value.tenant,value.refresh_token.get_secret_value())
        except ReadError as error:failure(error)

    @router.get('/oauth/session/{state}')
    def poll(state:str,actor=Depends(device)):
        try:return oauth.poll(state,actor.owner_id,actor.id)
        except ReadError as error:failure(error)
    @router.post('/oauth/session/{state}/ack')
    def acknowledge(state:str,actor=Depends(device)):
        try:oauth.acknowledge(state,actor.owner_id,actor.id);return {'acknowledged':True}
        except ReadError as error:failure(error)
    @router.delete('/oauth/session/{state}')
    def cancel(state:str,actor=Depends(device)):
        try:oauth.cancel(state,actor.owner_id,actor.id);return {'cancelled':True}
        except ReadError as error:failure(error)
    app.include_router(router)

    @app.get('/v1/providers/oauth/callback/{family}',dependencies=[Depends(local_native)])
    def callback(family:Literal['google','microsoft'],state:str='',code:str | None=None,error:str | None=None):
        try:oauth.callback(family,state,code,denied=error is not None)
        except ReadError as issue:failure(issue)
        return RedirectResponse('/v1/providers/oauth/return',status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    @app.get('/v1/providers/oauth/return',dependencies=[Depends(local_native)])
    def returned():
        return HTMLResponse('<!doctype html><meta charset="utf-8"><title>Return to Juno</title><h1>Return to Juno</h1><p>Your authorization response was received. Juno will show whether sign-in completed. You can close this page.</p>',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'"})

    @app.middleware('http')
    async def connection_privacy(request,call_next):
        response=await call_next(request)
        if request.url.path.startswith('/v1/providers'):response.headers['Cache-Control']='no-store'
        return response
