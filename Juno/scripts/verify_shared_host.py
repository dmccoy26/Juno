"""Real native pinned-TLS pairing, offline queue/restart and reconnection with disposable data."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend/src'))
SWIFT=r'''
struct APIProblem: Error { let message:String; let status:Int }
let mode = CommandLine.arguments[1]
let file = URL(fileURLWithPath:CommandLine.arguments[2])
let config = try JSONSerialization.jsonObject(with:Data(contentsOf:file)) as! [String:Any]
let address = config["address"] as! String
let profile = SharedProfile(address:address,certificate_sha256:config["pin"] as! String,owner_id:config["owner"] as! String,device_id:"synthetic-test")
let copy = try OfflineCopy(profile:profile)
let endpoint = try validatedHost(address)
let good = PinnedHostSession(profile.certificate_sha256).session()
defer { good.invalidateAndCancel() }
func call(_ session:URLSession,_ path:String,_ method:String = "GET",_ token:String = "",_ body:[String:Any]? = nil) throws -> Data {
    var request = URLRequest(url:URL(string:path,relativeTo:endpoint)!.absoluteURL);request.httpMethod = method;request.timeoutInterval = 8
    request.setValue("Bearer "+token,forHTTPHeaderField:"Authorization")
    if let body { request.httpBody = try JSONSerialization.data(withJSONObject:body);request.setValue("application/json",forHTTPHeaderField:"Content-Type") }
    let ready = DispatchSemaphore(value:0)
    var value:Data?;var failure:Error?
    session.dataTask(with:request) { data,response,error in
        if let error { failure = error }
        else if let response = response as? HTTPURLResponse, (200..<300).contains(response.statusCode) { value = data }
        else { failure = APIProblem(message:"Synthetic HTTP failure",status:(response as? HTTPURLResponse)?.statusCode ?? 0) }
        ready.signal()
    }.resume()
    guard ready.wait(timeout:.now()+12) == .success else { throw APIProblem(message:"Synthetic network timeout",status:0) }
    if let failure { throw failure };return value!
}
if mode == "online" {
    let bad = PinnedHostSession(String(repeating:"0",count:64)).session()
    defer { bad.invalidateAndCancel() }
    do { _ = try call(bad,"/v1/pair","POST","",["invitation":config["invitation"]!,"label":"Wrong identity"]); fatalError("Wrong certificate accepted") } catch {}
    let paired = try JSONSerialization.jsonObject(with:call(good,"/v1/pair","POST","",["invitation":config["invitation"]!,"label":"Synthetic native laptop"])) as! [String:Any]
    guard paired["owner_id"] as? String == profile.owner_id else { fatalError("Wrong owner") }
    let token = paired["token"] as! String
    try SharedKeychain.save(token,origin:address)
    try copy.replace(call(good,"/v1/cache","GET",token),owner:profile.owner_id)
    print("PASS exact-certificate TLS pairing, wrong-certificate rejection, Keychain credential and owner-scoped offline copy")
} else if mode == "offline" {
    let token = try SharedKeychain.read(address)!
    do { _ = try call(good,"/v1/cache","GET",token);fatalError("Host should be stopped") } catch {}
    _ = try copy.perform("/v1/memories",method:"POST",body:["text":"Synthetic laptop memory","source":"manual:offline-native-test","confidence":"confirmed"])
    let data = try copy.perform("/v1/check-ins",method:"POST",body:["local_date":"2026-10-30"])
    var row = try JSONSerialization.jsonObject(with:data) as! [String:Any]
    let id = row["id"] as! String
    for key in ["completed","interruptions","blockers","employee_work","tomorrow"] {
        row = try JSONSerialization.jsonObject(with:copy.perform("/v1/check-ins/"+id+"/answer",method:"PUT",body:["key":key,"text":"Synthetic native offline entry","expected_revision":row["revision"]!])) as! [String:Any]
    }
    _ = try copy.perform("/v1/check-ins/"+id+"/diary",method:"PUT",body:["text":"Synthetic native offline diary","confirm":true,"expected_revision":row["revision"]!])
    guard copy.archive.pending.count == 8 else { fatalError("Queue incomplete") }
    print("PASS actual host outage with native offline memory and diary writes persisted locally")
} else if mode == "sync" {
    let token = try SharedKeychain.read(address)!
    guard copy.archive.pending.count == 8 else { fatalError("Offline queue did not survive process restart") }
    while let edit = copy.archive.pending.first {
        var body:[String:Any] = ["operation_id":edit.id,"kind":edit.kind,"body":try JSONSerialization.jsonObject(with:edit.body)]
        if let id = edit.recordID { body["record_id"] = id }
        let result = try call(good,"/v1/offline-operations","POST",token,body)
        let retry = try call(good,"/v1/offline-operations","POST",token,body)
        guard (try JSONSerialization.jsonObject(with:result) as! NSDictionary).isEqual(to:try JSONSerialization.jsonObject(with:retry) as! [AnyHashable:Any]) else { fatalError("Retry duplicated or changed an operation") }
        try copy.acknowledge(edit,result:result)
    }
    try copy.replace(call(good,"/v1/cache","GET",token),owner:profile.owner_id)
    let rows = copy.objects("/v1/memories")
    guard rows.count == 1 && rows[0]["text"] as? String == "Synthetic laptop memory" else { fatalError("Memory synchronization failed") }
    let diary = String(data:try copy.read("/v1/check-ins/by-date/2026-10-30"),encoding:.utf8)!
    guard diary.contains("Synthetic native offline diary") else { fatalError("Diary synchronization failed") }
    print("PASS process restart, dependent-ID mapping, idempotent retries and complete offline memory/diary synchronization")
} else if mode == "cleanup" {
    try? SharedKeychain.forget(address);try? FileManager.default.removeItem(at:copy.file)
}
'''


def main():
    from sqlalchemy import create_engine,text
    from alembic import command
    from alembic.config import Config
    from juno.api import create_app
    from juno.auth import provision,digest
    from juno.database import engine_for,sessions
    from juno.models import PairingInvitation,now
    from juno.shared_host import HostManager
    from datetime import timedelta
    admin=engine_for(os.environ['JUNO_TEST_ADMIN_URL']).execution_options(isolation_level='AUTOCOMMIT')
    name='juno_native_test_'+uuid.uuid4().hex
    with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
    engine=create_engine(admin.url.set(database=name),hide_parameters=True)
    manager=None
    try:
        with engine.connect() as connection:
            config=Config(str(ROOT/'backend/alembic.ini'));config.attributes['connection']=connection;command.upgrade(config,'head')
        with sessions(engine)() as session:
            actor,_=provision(session,'Synthetic native host');owner=actor.owner_id
            code=secrets.token_urlsafe(48)
            session.add(PairingInvitation(token_hash=digest(code),owner_id=owner,expires_at=now()+timedelta(minutes=15),used=False));session.commit()
        with tempfile.TemporaryDirectory(prefix='juno-native-host-check-') as folder:
            temp=Path(folder);manager=HostManager(temp);manager.config['port']=0
            app=create_app(engine,host_manager=manager);manager.app=app;manager.set_enabled(True)
            invitation=manager.invitation_info()
            pairing={'address':'https://127.0.0.1:'+str(manager.config['port']),'pin':invitation['certificate_sha256'],'owner':owner,'invitation':code}
            settings=temp/'pair.json';settings.write_text(json.dumps(pairing));settings.chmod(0o600)
            native=(ROOT/'desktop/Shared.swift').read_text().split('extension JunoStore {',1)[0]
            (temp/'main.swift').write_text(native+'\n'+SWIFT)
            program=temp/'native-check'
            subprocess.run(['xcrun','swiftc','-swift-version','5',str(temp/'main.swift'),'-o',str(program)],check=True,capture_output=True)
            def phase(mode):subprocess.run([str(program),mode,str(settings)],check=True,timeout=60)
            try:
                phase('online');manager.close();phase('offline');manager.set_enabled(True);phase('sync')
            finally:
                subprocess.run([str(program),'cleanup',str(settings)],check=False,timeout=20)
                manager.close()
    finally:
        if manager:manager.close()
        engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()

if __name__=='__main__':main()
