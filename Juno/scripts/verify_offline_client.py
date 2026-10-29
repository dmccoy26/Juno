"""Compile and exercise the exact native cache/queue code with isolated fictional data."""
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
TEST=r'''
let profile = SharedProfile(address:"https://synthetic.local:8443",certificate_sha256:String(repeating:"a",count:64),owner_id:UUID().uuidString,device_id:"synthetic")
let copy = try OfflineCopy(profile:profile)
defer { try? FileManager.default.removeItem(at:copy.file) }
let questions = ["completed","interruptions","blockers","employee_work","tomorrow"].map { ["key":$0,"text":"Synthetic question"] }
let pages:[[String:Any]] = [
    ["path":"/v1/memories?q=&offset=0","body":["items":[[String:Any]](),"has_more":false]],
    ["path":"/v1/check-in-template","body":["questions":questions]],
    ["path":"/v1/conversations/test/messages","body":["items":[["id":"answer","role":"assistant","text":"Old synthetic reply","status":"complete"]],"has_more":false]]]
try copy.replace(JSONSerialization.data(withJSONObject:["version":1,"owner_id":profile.owner_id,"pages":pages]),owner:profile.owner_id)
let created = try copy.perform("/v1/memories",method:"POST",body:["text":"Synthetic offline memory","source":"manual:test","confidence":"confirmed"])
let memory = try JSONSerialization.jsonObject(with:created) as! [String:Any]
let identity = memory["id"] as! String
_ = try copy.perform("/v1/memories/"+identity,method:"PUT",body:["text":"Corrected offline memory","source":"manual:test","confidence":"confirmed","expected_revision":1])
guard copy.archive.pending.count == 2 else { fatalError("Queue lost an edit") }
let reopened = try OfflineCopy(profile:profile)
guard reopened.archive.pending.count == 2 else { fatalError("Queue did not survive restart") }
let first = reopened.archive.pending[0]
try reopened.acknowledge(first,result:JSONSerialization.data(withJSONObject:["id":"server-memory"]))
guard reopened.archive.pending.count == 1 && reopened.archive.pending[0].recordID == "server-memory" else { fatalError("Dependent ID mapping failed") }
let before = copy.archive.pending.count
do { _ = try copy.perform("/v1/memories/"+identity,method:"PUT",body:["text":"Wrong version","expected_revision":99]); fatalError("Conflict was overwritten") } catch is APIProblem {}
guard copy.archive.pending.count == before else { fatalError("Failed edit changed queue") }
let day = "2026-10-30"
let start = try JSONSerialization.jsonObject(with:copy.perform("/v1/check-ins",method:"POST",body:["local_date":day])) as! [String:Any]
let checkID = start["id"] as! String
var row = start
for key in ["completed","interruptions","blockers","employee_work","tomorrow"] {
    row = try JSONSerialization.jsonObject(with:copy.perform("/v1/check-ins/"+checkID+"/answer",method:"PUT",body:["key":key,"text":"Fictional answer","expected_revision":row["revision"]!])) as! [String:Any]
}
row = try JSONSerialization.jsonObject(with:copy.perform("/v1/check-ins/"+checkID+"/diary",method:"PUT",body:["text":"Fictional diary","confirm":true,"expected_revision":row["revision"]!])) as! [String:Any]
guard row["status"] as? String == "confirmed" else { fatalError("Diary did not confirm offline") }
let final = try OfflineCopy(profile:profile)
guard final.archive.pending.count == 9 else { fatalError("Offline diary chain lost edits") }
let search = try JSONSerialization.jsonObject(with:final.read("/v1/memories?q=Corrected&offset=0")) as! [String:Any]
guard (search["items"] as! [[String:Any]]).count == 1 else { fatalError("Offline search failed") }
let replies = String(data:try final.read("/v1/conversations/test/messages"),encoding:.utf8)!
guard !replies.contains("Old synthetic reply") else { fatalError("Stale reply leaked after offline edit") }
let permissions = try FileManager.default.attributesOfItem(atPath:final.file.path)[.posixPermissions] as! NSNumber
guard permissions.intValue == 0o600 else { fatalError("Offline file permissions invalid") }
print("PASS native offline memory edits, diary chain, restart, dependency mapping, conflict retention, local search, stale-reply removal and private file permissions")
'''

STORE_TEST=r'''
import Foundation
@main struct OfflineStoreCheck {
    @MainActor static func main() async throws {
        let profile = SharedProfile(address:"https://synthetic-unreachable.local:8443",certificate_sha256:String(repeating:"a",count:64),owner_id:UUID().uuidString,device_id:"synthetic")
        let copy = try OfflineCopy(profile:profile)
        defer { try? FileManager.default.removeItem(at:copy.file) }
        let questions = ["completed","interruptions","blockers","employee_work","tomorrow"].map { ["key":$0,"text":"Synthetic question"] }
        try copy.replace(JSONSerialization.data(withJSONObject:["version":1,"owner_id":profile.owner_id,"pages":[["path":"/v1/memories?offset=0","body":["items":[[String:Any]](),"has_more":false]],["path":"/v1/check-in-template","body":["questions":questions]]]]),owner:profile.owner_id)
        let store = JunoStore(); store.sharedProfile = profile;store.endpoint = try validatedHost(profile.address);store.token = "synthetic-never-transmitted";store.offlineCopy = copy;store.offline = true
        do { _ = try await store.request("/v1/memories?offset=0");fatalError("Missing pinned session used another connection") } catch is APIProblem {}
        store.hostSession = PinnedHostSession(profile.certificate_sha256).session()
        defer { store.hostSession?.invalidateAndCancel() }
        let began = Date()
        _ = try await store.request("/v1/memories?q=&offset=0")
        let created = try await store.request("/v1/memories",method:"POST",body:["text":"Synthetic immediate offline save","source":"manual:test","confidence":"confirmed"])
        let row = try JSONSerialization.jsonObject(with:created) as! [String:Any]
        let id = row["id"] as! String
        _ = try await store.request("/v1/memories/"+id,method:"PUT",body:["text":"Synthetic corrected offline save","source":"manual:test","confidence":"confirmed","expected_revision":1])
        _ = try await store.request("/v1/memories/"+id+"?expected_revision=2",method:"DELETE")
        _ = try await store.request("/v1/check-ins",method:"POST",body:["local_date":"2026-10-30"])
        guard Date().timeIntervalSince(began) < 2 else { fatalError("Offline requests waited for the network") }
        guard store.pendingEdits.count == 4 else { fatalError("Store lost a queued mutation") }
        let list = try JSONSerialization.jsonObject(with:await store.request("/v1/memories?q=&offset=0")) as! [String:Any]
        guard (list["items"] as! [[String:Any]]).isEmpty else { fatalError("Offline delete did not update cached list") }
        print("PASS actual JunoStore offline reads/create/edit/delete/check-in save immediately without contacting a host")
    }
}
'''


def main():
    source=(ROOT/'desktop/Shared.swift').read_text().split('extension JunoStore {',1)[0]
    with tempfile.TemporaryDirectory(prefix='juno-offline-check-') as folder:
        path=Path(folder)
        (path/'main.swift').write_text(source+'\nstruct APIProblem: Error { let message:String; let status:Int }\n'+TEST)
        subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
        subprocess.run([str(path/'check')],check=True)
        (path/'Juno.swift').write_text((ROOT/'desktop/Juno.swift').read_text().split('@main\nstruct JunoApplication',1)[0])
        (path/'StoreCheck.swift').write_text(STORE_TEST)
        subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-target','arm64-apple-macosx13.5',str(path/'Juno.swift'),str(ROOT/'desktop/Companion.swift'),str(ROOT/'desktop/TaskDock.swift'),str(ROOT/'desktop/Shared.swift'),str(path/'StoreCheck.swift'),'-o',str(path/'store-check')],check=True)
        subprocess.run([str(path/'store-check')],check=True,timeout=20)

if __name__=='__main__':main()
