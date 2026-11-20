"""Exercise the actual Swift automatic Dean method with isolated source adapters."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'desktop/Planning.swift').read_text()
method=source[source.index('    func prepareDeanMeeting(automatic:Bool) async {'):].split('\n}\n\nprivate struct DeanMeetingControls',1)[0]
schedule=source[source.index('struct DeanMeetingSchedule {'):source.index('struct ChairPreparationSchedule {')].replace('DeanMeetingSchedule','RealDeanMeetingSchedule')
harness=r'''
import Foundation
struct APIProblem:Error { var message:String;var status:Int=0 }
struct Basis { var meeting_window:String?;var dean_format:String? }
struct SavedDeanDraft { var owner_id=UUID().uuidString;var exists=false;var revision=0;var basis=Basis() }
struct DeanPrepareResult { var created:Bool;var review_notice:String?=nil }
struct TaskItem { var id:String;func text(_ key:String)->String? { nil } }
struct TaskInfo { var capabilities:[String:Bool]=[:] }
struct TaskCopy { var info=TaskInfo();var items:[TaskItem]=[];var origin="http://127.0.0.1:1";var id="fixture-task" }
struct BeaconCopy { var id="fixture-beacon" }
struct DeanMeetingSchedule {
    var meeting=Date().addingTimeInterval(3600);var previous=Date().addingTimeInterval(-604800);var key="fixture-week"
    init(now:Date) {}
    func due(at:Date)->Bool {true}
}
final class JunoStore {
    var deanPreparing=false,chairsPreparing=false,connected=true,offline=false,deanAutomatic=true
    var sharedProfile:String?;var deanHandledWeek:String?;var deanLastAttempt:Date?;var deanNotice=""
    var deanOverrideWeek="";var deanOverride:Date?;var draft=SavedDeanDraft()
    var calls:[String]=[];var payload:[String:Any]=[:];var failedSource:String?
    func decode<T>(_ type:T.Type,_ path:String,method:String="GET",body:[String:Any]?=nil) async throws->T {
        calls.append(method)
        if method=="GET" {return draft as! T}
        payload=body ?? [:];draft.exists=true;draft.revision+=1;draft.basis=Basis(meeting_window:"prepared",dean_format:"leadership-v1")
        return DeanPrepareResult(created:true) as! T
    }
    func mark(_ source:String)throws {calls.append(source);if failedSource==source {throw APIProblem(message:"Fixture outage")}}
    func refreshReportingTasks()async throws->(TaskCopy,String) {try mark("TaskDock");return(TaskCopy(),"fixture-key")}
    func refreshReportingBeacon()async throws->BeaconCopy {try mark("Beacon");return BeaconCopy()}
    func refreshCompletionArchive()async throws {try mark("Smartsheet")}
    func request(_ path:String,method:String,body:[String:Any])async throws->Data {Data()}
'''
tests=r'''
@main struct Verify {
    static func main()async {
        let fresh=JunoStore();await fresh.prepareDeanMeeting(automatic:true)
        precondition(fresh.calls==["GET","TaskDock","Beacon","Smartsheet","POST"])
        precondition(fresh.payload["allow_late"] as? Bool==false)
        let count=fresh.calls.count;await fresh.prepareDeanMeeting(automatic:true);precondition(fresh.calls.count==count)
        let notes=JunoStore();notes.draft.exists=true;notes.draft.revision=3
        await notes.prepareDeanMeeting(automatic:true)
        precondition(notes.calls==["GET","TaskDock","Beacon","Smartsheet","POST"])
        precondition(notes.payload["preserve_saved_revision"] as? Int==3)
        let edited=JunoStore();edited.draft.exists=true;edited.draft.basis=Basis(meeting_window:"saved",dean_format:"leadership-v1")
        await edited.prepareDeanMeeting(automatic:true);precondition(edited.calls==["GET"])
        let outage=JunoStore();outage.failedSource="TaskDock";await outage.prepareDeanMeeting(automatic:true)
        precondition(!outage.calls.contains("POST") && outage.deanHandledWeek==nil)
        let archive=JunoStore();archive.failedSource="Smartsheet";await archive.prepareDeanMeeting(automatic:true)
        precondition(archive.payload["archive_refresh_failed"] as? Bool==true)
        let paired=JunoStore();paired.sharedProfile="fixture";await paired.prepareDeanMeeting(automatic:true);precondition(paired.calls.isEmpty)
        let disconnected=JunoStore();disconnected.offline=true;await disconnected.prepareDeanMeeting(automatic:true);precondition(disconnected.calls.isEmpty)
        let disabled=JunoStore();disabled.deanAutomatic=false;await disabled.prepareDeanMeeting(automatic:true);precondition(disabled.calls.isEmpty)
        let formatter=ISO8601DateFormatter()
        let before=formatter.date(from:"2030-01-10T14:59:59Z")!,due=formatter.date(from:"2030-01-10T15:00:00Z")!,after=formatter.date(from:"2030-01-10T16:00:00Z")!
        let clock=RealDeanMeetingSchedule(now:due)
        precondition(!clock.due(at:before) && clock.due(at:due) && !clock.due(at:after) && clock.key=="2030-01-07")
        let summer=formatter.date(from:"2030-07-04T14:00:00Z")!
        precondition(RealDeanMeetingSchedule(now:summer).due(at:summer))
        print("PASS actual native automatic Dean sequence, note preservation, edited-draft protection, source failures, paired/offline gates and 9 AM Central schedule")
    }
}
'''
with tempfile.TemporaryDirectory(prefix='juno-dean-auto-') as tmp:
    p=Path(tmp);(p/'verify.swift').write_text(harness+method+'\n}\n'+schedule+tests)
    subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5',str(p/'verify.swift'),'-o',str(p/'verify')],check=True)
    subprocess.run([str(p/'verify')],check=True)
