"""Opt-in TLS LAN host. Only the local app can administer paired devices."""
from datetime import timedelta
import ipaddress
import json
from pathlib import Path
import secrets
import re
import socket
import ssl
import subprocess
import threading
import time
from urllib.parse import urlsplit
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from .auth import digest, provision
from .models import Device, PairingInvitation, now


def network_identity():
    try:
        name=subprocess.check_output(['/usr/sbin/scutil','--get','LocalHostName'],text=True,stderr=subprocess.DEVNULL).strip()+'.local'
    except (OSError,subprocess.CalledProcessError):name=socket.gethostname()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}',name):name='localhost'
    addresses=[]
    # Prefer the wired interface; use actual local addresses, never external discovery.
    for interface in ('en0','en1','en2'):
        try:
            value=subprocess.check_output(['/usr/sbin/ipconfig','getifaddr',interface],text=True,stderr=subprocess.DEVNULL).strip()
            ip=ipaddress.ip_address(value)
            if ip.version==4 and ip.is_private and not ip.is_loopback and value not in addresses:addresses.append(value)
        except (OSError,ValueError,subprocess.CalledProcessError):pass
    return name,addresses


class LANBoundary:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        address = (scope.get('client') or ('',))[0]
        try:
            ip = ipaddress.ip_address(address)
            allowed = ip.is_loopback or any(ip in ipaddress.ip_network(n) for n in
                (('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16') if ip.version == 4 else ('fc00::/7','fe80::/10')))
        except ValueError: allowed = False
        path, method = scope['path'], scope['method']
        permitted = (path == '/v1/pair' and method == 'POST' or
            path in {'/','/v1/cache','/v1/ping','/v1/integrations'} and method == 'GET' or path in {'/v1/offline-operations','/v1/offline-review'} and method == 'POST' or
            path.startswith('/v1/memories') and method in {'GET','POST','PUT','DELETE'} or
            path.startswith('/v1/conversations') and method in {'GET','POST'} or
            path.startswith('/v1/check-ins') and method in {'GET','POST','PUT'} or
            path == '/v1/taskdock' and method == 'GET' or
            path.startswith('/v1/taskdock/snapshots') and method == 'GET' or
            path == '/v1/taskdock/history' and method == 'GET' or
            path == '/v1/planning' and method in {'GET','PUT'} or
            path in {'/v1/planning/next','/v1/planning/weekly','/v1/planning/check-in'} and method == 'GET' or
            path == '/v1/model' and method == 'GET')
        if not allowed or not permitted:
            from starlette.responses import JSONResponse
            return await JSONResponse({'detail':'This operation is not available through the shared host.'},status_code=403)(scope,receive,send)
        scope['juno_lan'] = True
        return await self.app(scope,receive,send)


class HostManager:
    def __init__(self, state):
        self.root = Path(state)/'shared-host'
        self.root.mkdir(parents=True,mode=0o700,exist_ok=True);self.root.chmod(0o700)
        self.config_path = self.root/'settings.json'
        self.config = json.loads(self.config_path.read_text()) if self.config_path.exists() else {'enabled':False,'port':8443}
        self.server = self.worker = None
        self.lock = threading.Lock()
        self.app = None
        self.error = None

    def certificate(self):
        cert,key = self.root/'certificate.pem',self.root/'private-key.pem'
        if cert.exists()!=key.exists():raise RuntimeError('The shared host certificate is incomplete; restore it before restarting.')
        if not cert.exists():
            # No shell interpolation; private key never leaves the host state directory.
            config = self.root/'openssl.cnf'
            name,addresses=network_identity()
            sans=','.join(dict.fromkeys(['DNS:localhost','DNS:'+name,'IP:127.0.0.1',*['IP:'+a for a in addresses]]))
            config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN='+name+'\n[ext]\nsubjectAltName='+sans+'\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\nextendedKeyUsage=serverAuth\n')
            subprocess.run(['/usr/bin/openssl','req','-x509','-newkey','rsa:3072','-nodes','-days','365',
                '-keyout',str(key),'-out',str(cert),'-config',str(config)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            config.unlink()
            key.chmod(0o600);cert.chmod(0o600)
        return cert,key

    def status(self):
        name,addresses=network_identity()
        destination=addresses[0] if addresses else name
        running=bool(self.server and self.worker and self.worker.is_alive() and self.server.started)
        return {'enabled':running,'address':f'https://{destination}:{self.config["port"]}',
            'error':self.error,'availability':'Available while Juno is open and this Mac is awake.'}

    def set_enabled(self, enabled):
        with self.lock:
            self.error=None
            if enabled and not (self.worker and self.worker.is_alive()):
                cert,key=self.certificate()
                listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                try: listener.bind(('0.0.0.0',self.config['port']));listener.listen(128)
                except OSError:
                    listener.close();raise RuntimeError('The shared-host port is already in use.') from None
                if self.config['port']==0:self.config['port']=listener.getsockname()[1]
                import uvicorn
                self.server=uvicorn.Server(uvicorn.Config(LANBoundary(self.app),access_log=False,log_level='critical',
                    ssl_certfile=str(cert),ssl_keyfile=str(key),proxy_headers=False))
                self.worker=threading.Thread(target=lambda:self.server.run(sockets=[listener]),daemon=True)
                self.worker.start()
                for _ in range(100):
                    if self.server.started: break
                    if not self.worker.is_alive(): break
                    time.sleep(.02)
                if not self.server.started:
                    self.server.should_exit=True;listener.close()
                    raise RuntimeError('The encrypted shared host could not start.')
            if not enabled and self.server:
                self.server.should_exit=True
                if self.worker:self.worker.join(10)
            self.config['enabled']=enabled
            temporary=self.config_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.config));temporary.chmod(0o600);temporary.replace(self.config_path)
        return self.status()

    def invitation_info(self):
        cert,_=self.certificate()
        der=ssl.PEM_cert_to_DER_cert(cert.read_text())
        from hashlib import sha256
        return {'version':1,'address':self.status()['address'],
                'certificate_sha256':sha256(der).hexdigest()}

    def close(self):
        if self.server:self.server.should_exit=True
        if self.worker:self.worker.join(10)


class HostInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled: bool


class PairInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    invitation: SecretStr
    label: str = Field(min_length=1,max_length=200)


def install(app,db,device,lock_owner,manager):
    def local(request:Request):
        if request.scope.get('juno_lan'):raise HTTPException(403,'Host administration is local only.')

    @app.get('/')
    def landing():
        return {'service':'Juno shared host','transport':'HTTPS','authentication':'Pair through Juno Computers to access work records.'}

    @app.get('/v1/ping')
    def ping(actor=Depends(device)):
        return {'owner_id':actor.owner_id,'time':now()}

    @app.get('/v1/host',dependencies=[Depends(local)])
    def status(actor=Depends(device)):
        return manager.status() if manager else {'enabled':False,'address':'','error':None,'availability':'Host unavailable in this service.'}

    @app.put('/v1/host',dependencies=[Depends(local)])
    def enable(value:HostInput,actor=Depends(device)):
        if manager is None:raise HTTPException(503,'Host management is unavailable.')
        try:return manager.set_enabled(value.enabled)
        except (RuntimeError,OSError,subprocess.SubprocessError):raise HTTPException(503,'The encrypted shared host could not start. Check the port and certificate.') from None

    @app.post('/v1/host/invitations',dependencies=[Depends(local)])
    def invitation(actor=Depends(device),session=Depends(db)):
        if manager is None or not manager.status()['enabled']:raise HTTPException(409,'Enable hosting before inviting a device.')
        lock_owner(session,actor.owner_id)
        # Keep only one outstanding invitation for this owner.
        from sqlalchemy import update
        session.execute(update(PairingInvitation).where(PairingInvitation.owner_id==actor.owner_id,PairingInvitation.used.is_(False)).values(used=True))
        code=secrets.token_urlsafe(48);expires=now()+timedelta(minutes=15)
        session.add(PairingInvitation(token_hash=digest(code),owner_id=actor.owner_id,expires_at=expires,used=False));session.commit()
        return {**manager.invitation_info(),'invitation':code,'expires_at':expires}

    @app.post('/v1/pair')
    def pair(value:PairInput,request:Request,session=Depends(db)):
        # This endpoint works only on the TLS LAN surface, not a local-port guess.
        if not request.scope.get('juno_lan'):raise HTTPException(403,'Use the encrypted host to pair.')
        secret=value.invitation.get_secret_value()
        if not 40<=len(secret)<=256:raise HTTPException(401,'Invitation expired or is invalid.')
        row=session.scalar(select(PairingInvitation).where(PairingInvitation.token_hash==digest(secret)).with_for_update())
        if row is None or row.used or row.expires_at<=now():raise HTTPException(401,'Invitation expired or is invalid.')
        row.used=True
        actor,token=provision(session,value.label,row.owner_id);session.commit()
        return {'token':token,'device_id':actor.id,'owner_id':actor.owner_id}

    @app.get('/v1/host/devices',dependencies=[Depends(local)])
    def devices(actor=Depends(device),session=Depends(db)):
        rows=session.scalars(select(Device).where(Device.owner_id==actor.owner_id,Device.revoked.is_(False))).all()
        return {'items':[{'id':r.id,'label':r.label,'current':r.id==actor.id} for r in rows]}

    @app.delete('/v1/host/devices/{identity}',dependencies=[Depends(local)])
    def revoke(identity:str,actor=Depends(device),session=Depends(db)):
        lock_owner(session,actor.owner_id)
        row=session.scalar(select(Device).where(Device.id==identity,Device.owner_id==actor.owner_id))
        if row is None:raise HTTPException(404,'Device not found.')
        if row.id==actor.id:raise HTTPException(409,'Cannot revoke the active local app.')
        row.revoked=True;session.commit()
        return {'revoked':True}
