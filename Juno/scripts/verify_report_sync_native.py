"""Run the actual native Dean refresh/save and report-library refresh methods."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'desktop/Planning.swift').read_text()
policy=s[s.index('enum DeanRemoteRefreshAction:'):s.index('struct WeeklyPlanningDraft:')]
remote=s[s.index('    private func checkRemoteRevision()'):s.index('    private func prepare()',s.index('    private func checkRemoteRevision()'))].replace('private func','func')
retry=s[s.index('    private func retry()',s.index('struct WeeklyDeanEditor:')):s.index('    private func compare()',s.index('struct WeeklyDeanEditor:'))].replace('private func','func')
load=s[s.index('    private func load(older:'):s.index('\n}\nprivate struct ReportLibraryReader:')].replace('private func','func')
head=r'''
import Foundation
struct APIProblem:Error {var message:String;var status:Int}
struct Basis:Equatable {var value=1}
struct SavedDeanDraft {var owner_id="owner";var week_start="2030-01-07";var revision=5;var text="Local writing";var basis=Basis()}
struct DeanSaveReceipt {var revision:Int}
@MainActor final class Store {
 var connected=true,offline=false;var failure:APIProblem?;var reply=SavedDeanDraft(revision:8,text:"Other Mac writing");var writes=0;var ids:[String]=[];var onGet:(()->Void)?
 func decode<T>(_ type:T.Type,_ path:String,method:String="GET",body:[String:Any]?=nil)async throws->T {
  await Task.yield()
  if method=="PUT" {writes+=1;ids.append(body?["operation_id"] as? String ?? "")}
  if let failure {throw failure}
  if method=="PUT" {return DeanSaveReceipt(revision:8) as! T}
  onGet?();return reply as! T
 }
}
@MainActor final class Editor {
 var store=Store();var busy=false,checkingRemote=false,dirty=false,editing=false,showingHistory=false,presenting=false,showFresh=false,closeAfterSave=false
 var pending:[String:Any]?;var saved:SavedDeanDraft?=SavedDeanDraft();var basis:Basis?=Basis();var text="Local writing";var baseRevision=5;var newerRemoteRevision:Int?;var notice=""
 var saveDestination="the work Mac"
 var prepared:String?;var comparison:SavedDeanDraft?;var dayKey="2030-01-07";var recoveries=0;var dismissals=0
 var comparisonOpen:Bool {comparison != nil || showFresh}
 func recoverable(){recoveries+=1}
 func dismiss(){dismissals+=1}
'''
lib=r'''
struct ReportLibraryItem:Equatable {var id="dean:2030-01-07";var revision=5}
struct ReportLibraryPage {var owner_id="owner";var items=[ReportLibraryItem(revision:8)];var has_more=false;var next_offset=20}
@MainActor final class LibraryStore {
 var connected=true;var reply=ReportLibraryPage()
 func decode<T>(_ type:T.Type,_ path:String)async throws->T {reply as! T}
}
@MainActor final class Library {
 var store=LibraryStore();var loading=false,busy=false,more=false;var owner:String?="owner";var offset=20;var issue:String?;var selected:String?="dean:2030-01-07";var readVersion=UUID();var assignments=0
 var items=[ReportLibraryItem()] {didSet{assignments+=1}}
 var filtered:[ReportLibraryItem]{items}
'''
tests=r'''
@main struct Verify {
 @MainActor static func idle(_ editor:Editor)async {for _ in 0..<1000 {if !editor.busy{return};try? await Task.sleep(nanoseconds:1_000_000)};fatalError("Save did not finish")}
 @MainActor static func main()async {
  let clean=Editor();await clean.checkRemoteRevision();precondition(clean.text=="Other Mac writing" && clean.baseRevision==8)
  for kind in 0..<4 {
   let writing=Editor();writing.dirty=kind==0;writing.editing=kind==1;writing.comparison=kind==2 ? SavedDeanDraft() : nil
   if kind==3 {writing.store.onGet={writing.dirty=true;writing.text="Typing while the read was in flight"}}
   await writing.checkRemoteRevision()
   precondition(writing.baseRevision==5 && writing.text != "Other Mac writing" && writing.newerRemoteRevision==8)
  }
  let owner=Editor();owner.store.reply.owner_id="different-owner";await owner.checkRemoteRevision();precondition(owner.baseRevision==5 && owner.text=="Local writing")
  let stale=Editor();stale.store.reply.revision=4;await stale.checkRemoteRevision();precondition(stale.baseRevision==5)
  let offline=Editor();offline.store.offline=true;await offline.checkRemoteRevision();precondition(offline.baseRevision==5)
  let pending=Editor();pending.dirty=true;pending.pending=["operation_id":"same-save"];pending.store.failure=APIProblem(message:"Work Mac unavailable",status:0)
  pending.retry();await idle(pending);precondition(pending.pending != nil && pending.dirty && pending.notice.contains("Work Mac unavailable"))
  pending.store.failure=nil;pending.closeAfterSave=true;pending.retry();await idle(pending)
  precondition(pending.pending==nil && !pending.dirty && pending.baseRevision==8 && pending.dismissals==1 && pending.store.ids==["same-save","same-save"])
  let conflict=Editor();conflict.dirty=true;conflict.closeAfterSave=true;conflict.pending=["operation_id":"conflict"];conflict.store.failure=APIProblem(message:"Newer saved revision",status:409)
  conflict.retry();await idle(conflict);precondition(conflict.pending==nil && conflict.dirty && conflict.text=="Local writing" && conflict.dismissals==0 && conflict.notice.contains("Compare saved copy"))
  let reader=Library();let identity=reader.readVersion
  await reader.load(quiet:true);precondition(reader.items[0].revision==8 && reader.readVersion==identity && reader.selected=="dean:2030-01-07")
  let assignments=reader.assignments;await reader.load(quiet:true);precondition(reader.assignments==assignments && reader.readVersion==identity)
  await reader.load();precondition(reader.readVersion != identity)
  print("PASS actual native cross-Mac revision refresh, typing/owner/outage protection, durable save retry, save-and-close receipt, conflicts and quiet reader refresh")
 }
}
'''
with tempfile.TemporaryDirectory(prefix='juno-report-sync-') as tmp:
 p=Path(tmp);(p/'verify.swift').write_text(head+policy+remote+retry+'\n}\n'+lib+load+'\n}\n'+tests)
 subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5',str(p/'verify.swift'),'-o',str(p/'verify')],check=True)
 subprocess.run([str(p/'verify')],check=True)
