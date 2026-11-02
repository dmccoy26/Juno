"""Dedicated browser surface: no owner/pairing routes and no generated trust bypass."""
from collections import OrderedDict, deque
from pathlib import Path
import ipaddress
from hashlib import sha256
import json
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit
from starlette.responses import JSONResponse


class WorkerBoundary:
    def __init__(self, app):
        self.app=app
        self.attempts=OrderedDict()

    async def __call__(self,scope,receive,send):
        if scope['type']=='lifespan':return await self.app(scope,receive,send)
        if scope['type']!='http':return
        path=scope['path'];method=scope['method']
        headers={k.decode().lower():v.decode() for k,v in scope.get('headers',[])}
        async def reject(code,message):
            await JSONResponse({'detail':message},status_code=code,headers={'Cache-Control':'no-store'})(scope,receive,send)
        allowed=(method=='GET' and path in {'/worker','/worker/app.js','/worker/style.css','/worker/api/me','/worker/api/tasks','/worker/api/receipts'} or method=='POST' and path in {'/worker/api/enroll','/worker/api/sign-out','/worker/api/reports'})
        if not allowed:return await reject(403,'This is the limited worker portal.')
        if scope.get('scheme')!='https':return await reject(403,'Use the approved HTTPS worker address.')
        try:
            ip=ipaddress.ip_address((scope.get('client') or ('',))[0])
            if not (ip.is_loopback or (ip.version==4 and ip in ipaddress.ip_network('10.0.0.0/8'))):return await reject(403,'Worker access is restricted to the 10.0.0.0/8 network.')
        except ValueError:return await reject(403,'Worker access is restricted to the 10.0.0.0/8 network.')
        if method=='POST':
            host=headers.get('host','');origin=headers.get('origin','')
            if origin!='https://'+host or headers.get('sec-fetch-site','same-origin') not in {'same-origin','none'}:return await reject(403,'Open this form from the worker portal itself.')
            address=(scope.get('client') or ('',))[0];stamp=time.monotonic()
            while self.attempts and next(iter(self.attempts.values()))[-1]<stamp-60:self.attempts.popitem(last=False)
            bucket=self.attempts.pop(address,deque());bucket=deque(t for t in bucket if t>stamp-60)
            if len(bucket)>=60:
                self.attempts[address]=bucket;return await reject(429,'Too many requests. Wait a minute and try again.')
            bucket.append(stamp);self.attempts[address]=bucket
            while len(self.attempts)>4096:self.attempts.popitem(last=False)
            body=b''
            while True:
                part=await receive()
                if part['type']=='http.disconnect':return
                body+=part.get('body',b'')
                if len(body)>32768:return await reject(413,'This update is too large.')
                if not part.get('more_body',False):break
            original=receive
            delivered=False
            async def buffered():
                nonlocal delivered
                if not delivered:delivered=True;return {'type':'http.request','body':body,'more_body':False}
                return await original()
            receive=buffered
        scope['juno_worker']=True
        await self.app(scope,receive,send)


class WorkerHostManager:
    """IT provisions config/certificate files; the UI cannot replace certificate trust."""
    def __init__(self,state):
        self.root=Path(state)/'worker-portal';self.root.mkdir(mode=0o700,parents=True,exist_ok=True);self.root.chmod(0o700)
        self.config_path=self.root/'https.json';self.app=None;self.server=None;self.thread=None;self.error=None
        self.lock=threading.Lock();self.loaded_fingerprint=None

    def readiness(self):
        if not self.config_path.exists():return {'ready':False,'address':'','reason':'IT must configure a browser-trusted hostname, certificate and private key in worker-portal/https.json. No worker access is enabled.'}
        try:
            data=json.loads(self.config_path.read_text());address=data['address'];u=urlsplit(address)
            if u.scheme!='https' or not u.hostname or u.username or u.password or u.path not in ('','/') or u.query or u.fragment:raise ValueError()
            port=u.port or 443
            if not 1024<=port<=65535:raise ValueError()
            cert=Path(data['certificate']);key=Path(data['private_key'])
            if not cert.is_absolute() or not key.is_absolute() or not cert.is_file() or not key.is_file() or key.stat().st_mode&0o077:raise ValueError()
            import ssl
            server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server_context.load_cert_chain(cert,key)
            client_context=ssl.create_default_context(cafile=data.get('ca_bundle'))
            # Verify the complete chain, dates and hostname entirely in memory.
            # macOS's bundled LibreSSL CLI lacks verify_hostname; no network probe
            # or global trust modification is needed here.
            client_in,client_out,server_in,server_out=[ssl.MemoryBIO() for _ in range(4)]
            client=client_context.wrap_bio(client_in,client_out,server_side=False,server_hostname=u.hostname)
            server=server_context.wrap_bio(server_in,server_out,server_side=True)
            complete=[False,False]
            for _ in range(50):
                for index,tls in enumerate((client,server)):
                    if not complete[index]:
                        try:tls.do_handshake();complete[index]=True
                        except ssl.SSLWantReadError:pass
                data_out=client_out.read()
                if data_out:server_in.write(data_out)
                data_out=server_out.read()
                if data_out:client_in.write(data_out)
                if all(complete):break
            if not all(complete):raise ValueError()
            return {'ready':True,'address':address.rstrip('/'),'reason':'Certificate chain/hostname checked on this Mac. Each worker browser still needs institutional trust and network testing.'}
        except (KeyError,ValueError,OSError,subprocess.SubprocessError):return {'ready':False,'address':'','reason':'Worker HTTPS configuration is invalid or certificate trust/hostname verification failed. Ask IT to check it; do not bypass browser warnings.'}

    def material_fingerprint(self):
        try:
            raw=self.config_path.read_bytes();data=json.loads(raw);parts=[raw,Path(data['certificate']).read_bytes(),Path(data['private_key']).read_bytes()]
            if data.get('ca_bundle'):parts.append(Path(data['ca_bundle']).read_bytes())
            return sha256(b'\0'.join(parts)).digest()
        except (OSError,ValueError,KeyError):return None

    def status(self):
        ready=self.readiness()
        if self.thread and self.thread.is_alive() and self.loaded_fingerprint!=self.material_fingerprint():ready={'ready':False,'address':'','reason':'Worker HTTPS files changed. Disable worker access, then enable it again to load the approved configuration.'}
        return {**ready,'running':bool(self.server and self.server.started and self.thread and self.thread.is_alive()),'error':self.error}

    def start(self):
        with self.lock:
            state=self.readiness()
            if not state['ready']:raise RuntimeError(state['reason'])
            if self.thread and self.thread.is_alive():
                if self.loaded_fingerprint!=self.material_fingerprint():raise RuntimeError('Restart worker HTTPS after configuration changes.')
                return
            self.error=None
            self.loaded_fingerprint=self.material_fingerprint()
            data=json.loads(self.config_path.read_text());u=urlsplit(data['address']);listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try:
                try:bind_address=str(ipaddress.IPv4Address(u.hostname))
                except ipaddress.AddressValueError:bind_address='0.0.0.0'
                listener.bind((bind_address,u.port or 443));listener.listen(64)
                import uvicorn
                self.server=uvicorn.Server(uvicorn.Config(WorkerBoundary(self.app),access_log=False,log_level='critical',proxy_headers=False,timeout_keep_alive=2,timeout_graceful_shutdown=2,ssl_certfile=data['certificate'],ssl_keyfile=data['private_key']))
                self.thread=threading.Thread(target=lambda:self.server.run(sockets=[listener]),daemon=True);self.thread.start()
                for _ in range(100):
                    if self.server.started:return
                    if not self.thread.is_alive():break
                    time.sleep(.02)
                raise RuntimeError('Worker HTTPS listener did not start.')
            except Exception:
                if self.server:self.server.should_exit=True
                listener.close();raise

    def close(self):
        if self.server:self.server.should_exit=True
        if self.thread:
            self.thread.join(5)
            if self.thread.is_alive() and self.server:
                self.server.force_exit=True
                self.thread.join(3)
