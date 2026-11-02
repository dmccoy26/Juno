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
let durable = try OfflineCopy(profile:profile)
guard durable.resolved[identity] == "server-memory", durable.objects("/v1/memories").first?["id"] as? String == "server-memory" else { fatalError("Acknowledged identity lost across restart/export failure") }
let movedProfile = SharedProfile(address:"https://10.22.33.44:8443",certificate_sha256:profile.certificate_sha256,owner_id:profile.owner_id,device_id:"replacement")
guard try OfflineCopy(profile:movedProfile).file == durable.file else { fatalError("Changed IP stranded the queue") }
let conflicting = durable.archive.pending[0]
try durable.block(conflicting,status:409,message:"Synthetic conflict")
guard try OfflineCopy(profile:profile).archive.block?.operationID == conflicting.id else { fatalError("Conflict did not survive restart") }
try durable.resolve(conflicting,current:["id":"server-memory","revision":7,"text":"Host version"],keepLaptop:true)
guard (try JSONSerialization.jsonObject(with:durable.archive.pending[0].body) as! [String:Any])["expected_revision"] as? Int == 7, durable.archive.pending[0].id != conflicting.id else { fatalError("Conflict was not safely rebased with a fresh operation identity") }
durable.clear()
let revoked = try OfflineCopy(profile:profile)
guard revoked.archive.pages.isEmpty, revoked.archive.pending.count == 1 else { fatalError("Revocation deleted durable unsynchronized work") }
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
let queued = final.archive.pending[0]
let unrelatedCount = final.archive.pending.filter { $0.kind.hasPrefix("checkin.") }.count
try final.block(queued,status:404,message:"Deleted on host")
try final.recoverMemory(queued)
guard final.archive.pending.filter({$0.kind.hasPrefix("checkin.")}).count == unrelatedCount,
      final.archive.pending.last?.kind == "memory.create" else { fatalError("Recovery lost unrelated diary edits") }
let recovered = final.archive.pending.last!
try final.block(recovered,status:409,message:"Synthetic duplicate")
try final.resolve(recovered,current:nil,keepLaptop:false)
guard final.archive.pending.count == unrelatedCount, final.archive.block == nil else { fatalError("Scoped discard lost unrelated work") }
let legacy = try JSONSerialization.data(withJSONObject:["savedAt":0,"pages":[String:String]()])
guard try JSONDecoder().decode(OfflineArchive.self,from:legacy).pending.isEmpty else { fatalError("Old cache format cannot upgrade") }
try final.discardAll()
_ = try final.perform("/v1/memories",method:"POST",body:["text":"Must disappear after an invalidated receipt","source":"synthetic-receipt","confidence":"confirmed"])
let invalidatedEdit = final.archive.pending.last!
try final.acknowledge(invalidatedEdit,result:JSONSerialization.data(withJSONObject:["id":"invalidated-server-id","invalidated":true]))
guard final.archive.pending.isEmpty, !String(data:try final.read("/v1/memories"),encoding:.utf8)!.contains("Must disappear") else { fatalError("Invalidated acknowledgment exposed stale canonical text") }
let badgeProfile = SharedProfile(address:"https://synthetic.local:8443",certificate_sha256:String(repeating:"a",count:64),owner_id:UUID().uuidString,device_id:"badges")
let badgeCopy = try OfflineCopy(profile:badgeProfile)
defer { try? FileManager.default.removeItem(at:badgeCopy.file) }
let origin = "00000000-0000-0000-0000-000000000001"
let badgePages:[[String:Any]] = [["path":"/v1/memories","body":["items":[[String:Any]](),"has_more":false]],["path":"/v1/conversations/badge/messages","body":["items":[["id":origin,"role":"user","text":"Synthetic origin","status":"complete"]],"has_more":false]]]
try badgeCopy.replace(JSONSerialization.data(withJSONObject:["version":1,"owner_id":badgeProfile.owner_id,"pages":badgePages]),owner:badgeProfile.owner_id)
let badgeCreated = try JSONSerialization.jsonObject(with:badgeCopy.perform("/v1/memories",method:"POST",body:["text":"Reviewed fact","source":"Chat","confidence":"confirmed","source_message_id":origin])) as! [String:Any]
let badgeID = badgeCreated["id"] as! String
precondition(badgeCopy.objects("/v1/conversations/badge/messages").first?["saved_memory_id"] as? String == badgeID)
let badgeRestart = try OfflineCopy(profile:badgeProfile)
precondition(badgeRestart.objects("/v1/conversations/badge/messages").first?["saved_memory_id"] as? String == badgeID)
try badgeRestart.acknowledge(badgeRestart.archive.pending[0],result:JSONSerialization.data(withJSONObject:["id":"server-badge-memory"]))
precondition(badgeRestart.objects("/v1/conversations/badge/messages").first?["saved_memory_id"] as? String == "server-badge-memory")
_ = try badgeRestart.perform("/v1/memories/server-badge-memory",method:"PUT",body:["text":"Corrected fact","source":"Updated","confidence":"confirmed","expected_revision":1])
precondition(badgeRestart.objects("/v1/conversations/badge/messages").first?["saved_memory_id"] as? String == "server-badge-memory")
_ = try badgeRestart.perform("/v1/memories/server-badge-memory",method:"DELETE",body:["expected_revision":2])
precondition(badgeRestart.objects("/v1/conversations/badge/messages").first?["saved_memory_id"] == nil)
print("PASS offline saved-memory badge create/restart/remap/correction/deletion")
print("PASS native offline memory edits, diary chain, restart, dependency mapping, conflict retention, local search, stale-reply removal and private file permissions")
'''

STORE_TEST=r'''
import Foundation
@main struct OfflineStoreCheck {
    @MainActor static func main() async throws {
        guard pairingFailure(URLError(.cannotFindHost)).contains("IP address"), pairingFailure(URLError(.cannotConnectToHost)).contains("8443"), pairingFailure(APIProblem(message:"Expired invitation",status:401)) == "Expired invitation" else { fatalError("Pairing diagnostics lost the failure reason") }
        let profile = SharedProfile(address:"https://synthetic-unreachable.local:8443",certificate_sha256:String(repeating:"a",count:64),owner_id:UUID().uuidString,device_id:"synthetic")
        let copy = try OfflineCopy(profile:profile)
        defer { try? FileManager.default.removeItem(at:copy.file) }
        let questions = ["completed","interruptions","blockers","employee_work","tomorrow"].map { ["key":$0,"text":"Synthetic question"] }
        try copy.replace(JSONSerialization.data(withJSONObject:["version":1,"owner_id":profile.owner_id,"pages":[["path":"/v1/memories?offset=0","body":["items":[[String:Any]](),"has_more":false]],["path":"/v1/check-in-template","body":["questions":questions]]]]),owner:profile.owner_id)
        let store = JunoStore()
        store.chatDraft = "Synthetic unsent draft"
        store.prepareChat("Synthetic planning question")
        precondition(store.chatDraft == "Synthetic unsent draft" && store.proposedChatDraft == "Synthetic planning question")
        store.proposedChatDraft = nil;store.chatDraft = ""
        store.prepareChat("Synthetic planning question")
        precondition(store.chatDraft == "Synthetic planning question" && store.section == "Chat")
        store.chatDraft = ""; store.sharedProfile = profile;store.endpoint = try validatedHost(profile.address);store.token = "synthetic-never-transmitted";store.offlineCopy = copy;store.offline = true
        do { _ = try await store.request("/v1/memories?offset=0");fatalError("Missing pinned session used another connection") } catch is APIProblem {}
        store.hostSession = PinnedHostSession(profile.certificate_sha256).session()
        defer { store.hostSession?.invalidateAndCancel() }
        store.chatDraft = "Remember that the fictional cutter is TEST-42"
        store.sendChat()
        precondition(store.memoryReviewText == "the fictional cutter is TEST-42" && !store.chatSending)
        precondition(store.pendingEdits.isEmpty, "Review intent must not save before confirmation")
        store.memoryReviewText = nil;store.memoryReviewOriginal = nil;store.chatDraft = ""
        do { try await store.deleteConversation("synthetic-conversation");fatalError("Offline deletion must require connection") } catch is APIProblem {}
        precondition(store.pendingEdits.isEmpty, "Offline chat deletion must not queue")
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
        subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-target','arm64-apple-macosx13.5',str(path/'Juno.swift'),str(ROOT/'desktop/Companion.swift'),str(ROOT/'desktop/TaskDock.swift'),str(ROOT/'desktop/Shared.swift'),str(ROOT/'desktop/Integrations.swift'),str(ROOT/'desktop/Connections.swift'),str(ROOT/'desktop/Planning.swift'),str(ROOT/'desktop/Schedules.swift'),str(path/'StoreCheck.swift'),'-o',str(path/'store-check')],check=True)
        subprocess.run([str(path/'store-check')],check=True,timeout=20)

if __name__=='__main__':main()
