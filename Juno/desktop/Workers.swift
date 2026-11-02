import SwiftUI

func workerShareSearchText(_ task:TaskDockTask,confirmedRoom:String="")->String {
    let values=[task.title,confirmedRoom,task.planningText("room") ?? "",task.planningText("equipment") ?? "",task.text("parent_title") ?? "",task.text("description") ?? "",task.text("status_name") ?? task.text("behavior") ?? "",task.text("owner") ?? "",task.id]
    let text=values.joined(separator:" ")
    let aliases=[("ARTS 121","A121 ARTS121 ARTS 121"),("ARTS 140","A140 ARTS140 ARTS 140"),("LIBR 115","LIB115 LIBR115 LIBRARY115 LIBR 115"),("MOOD 301","MH301 MOOD301 MOODY301 MOOD 301"),("TRUS 108","TH108 TRUS108 TRUSTEE108 TRUS 108")]
    let rooms=aliases.filter{scheduleTitleMentionsRoom(text,$0.0)}.map{$0.1}.joined(separator:" ")
    return (text+" "+rooms).folding(options:[.caseInsensitive,.diacriticInsensitive],locale:Locale(identifier:"en_US_POSIX"))
}
func workerShareMatches(_ task:TaskDockTask,query:String,confirmedRoom:String="")->Bool {
    let words=query.folding(options:[.caseInsensitive,.diacriticInsensitive],locale:Locale(identifier:"en_US_POSIX")).split(whereSeparator:{$0.isWhitespace})
    let text=workerShareSearchText(task,confirmedRoom:confirmedRoom)
    return words.allSatisfy{text.contains($0)}
}

func workerDetailKeys(_ excerpt:[String:String])->[String]{
    let first=["title","room","equipment","issue_description","requested_outcome","description","owner","priority","due_date","status_name","behavior","blockers","dependencies","troubleshooting","instructions"]
    return first.filter{excerpt[$0] != nil}+excerpt.keys.filter{!first.contains($0)}.sorted()
}
func workerDetailLabel(_ key:String)->String{
    if key=="owner"{return "Assigned to"};if key=="behavior"{return "Status"};if key=="impact"{return "Operational impact"}
    return key.replacingOccurrences(of:"_",with:" ").capitalized
}

struct WorkerTaskChooser:View {
    let tasks:[TaskDockTask]
    let rooms:[String:String]
    @Binding var selected:String
    @State private var search=""
    @FocusState private var searching:Bool
    private var matches:[TaskDockTask]{tasks.filter{workerShareMatches($0,query:search,confirmedRoom:rooms[$0.id] ?? "")}}
    private func detail(_ task:TaskDockTask)->String {
        var parts:[String]=[]
        let room=rooms[task.id] ?? task.planningText("room") ?? ""
        if !room.isEmpty{parts.append(room)}
        if let status=task.text("status_name") ?? task.text("behavior"),!status.isEmpty{parts.append(status.replacingOccurrences(of:"_",with:" "))}
        if let date=task.text("due_date"),!date.isEmpty{parts.append("Due "+date)}
        if let parent=task.text("parent_title"),!parent.isEmpty{parts.append("Under "+parent)}
        parts.append("Ref "+String(task.id.suffix(8)))
        return parts.joined(separator:" · ")
    }
    var body:some View {
        VStack(alignment:.leading,spacing:8){
            HStack{TextField("Search tasks by title, room, equipment or parent",text:$search).textFieldStyle(.roundedBorder).focused($searching).accessibilityLabel("Search tasks to share");if !search.isEmpty{Button("Clear search"){search="";searching=true}}}
            Text("\(matches.count) of \(tasks.count) tasks").font(.caption).foregroundStyle(.secondary)
            List(selection:Binding<String?>(get:{selected.isEmpty ? nil:selected},set:{selected=$0 ?? ""})){
                ForEach(matches){task in VStack(alignment:.leading,spacing:4){Text(task.title).lineLimit(2);Text(detail(task)).font(.caption).foregroundStyle(.secondary).lineLimit(2)}.padding(.vertical,4).tag(task.id)
                }
            }.frame(height:180).accessibilityLabel("Matching tasks to share")
            if matches.isEmpty{Text("No tasks match. Try fewer words or clear the search.").font(.callout).foregroundStyle(.secondary)}
            if let task=tasks.first(where:{$0.id==selected}){VStack(alignment:.leading,spacing:4){Text("Selected: "+task.title).font(.headline);Text(detail(task)).font(.caption).foregroundStyle(.secondary);if !matches.contains(where:{$0.id==selected}){Text("Your selected task is outside this search. It stays selected until you choose another task.").font(.caption)}}.textSelection(.enabled)}else{Text("Choose a task from the results.").font(.callout).foregroundStyle(.secondary)}
        }.onAppear{searching=true}
    }
}

struct WorkerIdentity:Decodable,Identifiable { var id:String;var name:String;var active:Bool;var assignment_keys:[String]? }
struct WorkerHostStatus:Decodable { var ready:Bool;var running:Bool;var address:String;var reason:String;var error:String? }
struct WorkerGrantRecord:Decodable,Identifiable { var id:String;var worker_id:String;var task_id:String;var excerpt:[String:String];var active:Bool;var expires_at:String?;var mode:String? }
struct WorkerReportData:Decodable { var kind:String;var work_date:String;var text:String;var status:String;var actual_minutes:Int?;var remaining_minutes:Int?;var blocker_state:String;var blocker:String;var next_action:String;var handoff:String;var location:String }
struct WorkerReportRecord:Decodable,Identifiable {
    var id:String;var worker_id:String;var worker_name:String;var grant_id:String?;var task_id:String?;var workspace_id:String?;var shared_excerpt:[String:String];var grant_active:Bool;var correction_of:String?;var data:WorkerReportData;var review:String;var review_note:String;var revision:Int;var applied:[String:TaskJSON];var repair_context:[String:TaskJSON];var submitted_at:String
    var title:String { shared_excerpt["title"] ?? (data.kind == "shift" ? "End-of-shift check-in" : data.kind == "unexpected" ? "Unexpected work" : "Task update") }
}
struct WorkerAssignee:Decodable,Identifiable {var key:String;var label:String;var id:String{key}}
struct WorkerOverview:Decodable {var assignment_options:[WorkerAssignee]?; var enabled:Bool;var retention_days:Int;var host:WorkerHostStatus;var people:[String];var workers:[WorkerIdentity];var reports:[WorkerReportRecord];var has_more:Bool;var grants:[WorkerGrantRecord];var more_grants:Bool }
struct WorkerLink:Decodable { var url:String;var expires_at:String }
struct WorkerGrantPreview:Decodable { var excerpt:[String:String];var worker_name:String;var workspace_id:String;var source_saved_at:String }
struct WorkerReceiptPage:Decodable { var items:[WorkerReportRecord];var has_more:Bool }
struct RepairDuration:Decodable {var minimum:Int;var maximum:Int;var samples:Int}
struct RepairEvidence:Decodable,Identifiable {var id:String;var work_date:String;var summary:String;var review:String}
struct RepairGroup:Decodable,Identifiable {var id:String;var room:String;var equipment:String;var category:String;var reports:Int;var distinct_repair_records:Int;var verified_repairs:Int;var duration:RepairDuration?;var time_samples:Int;var latest_work_date:String;var suggestion:String;var evidence:[RepairEvidence]}
struct RepairHistory:Decodable {var groups:[RepairGroup];var reviewed_reports:Int;var limited:Bool;var limit:Int;var notice:String}
struct WorkerSheet:Identifiable { let id=UUID();var kind:String;var report:WorkerReportRecord? }

struct WorkerWorkspace:View {
    @ObservedObject var store:JunoStore
    @State private var overview:WorkerOverview?
    @State private var repairHistory:RepairHistory?
    @State private var historyLimit=20
    @State private var includeRepair=false
    @State private var repairRoom=""
    @State private var repairEquipment=""
    @State private var repairCategory="other"
    @State private var repairSummary=""
    @State private var completeEffort=false
    @State private var snapshot:TaskDockSnapshot?
    @State private var sharingPlan:PlanningRecord?
    @State private var reports:[WorkerReportRecord]=[]
    @State private var selected:String?
    @State private var filter="unread"
    @State private var query=""
    @State private var busy=false
    @State private var issue:String?
    @State private var sheet:WorkerSheet?
    @State private var more=false
    @State private var person=""
    @State private var chosenWorker=""
    @State private var taskID=""
    @State private var instructions=""
    @State private var shareDays=7
    @State private var preview:WorkerGrantPreview?
    @State private var link:WorkerLink?
    @State private var reviewNote=""
    @State private var outcome="reviewed"
    @State private var plan:PlanningRecord?
    @State private var applyFields:Set<String>=[]
    @State private var retention=0
    @State private var confirmation:String?
    @State private var targetID=""
    private let applying=[("actual_minutes","Actual minutes (replace, never add)"),("minutes","Remaining estimate"),("blocker","Blocker"),("next_action","Next action"),("resume","Handoff / where to resume")]
    private var local:Bool { store.sharedProfile == nil && !store.offline }
    private func binding(_ set:Binding<Set<String>>,_ key:String)->Binding<Bool> { Binding(get:{set.wrappedValue.contains(key)},set:{v in if v {set.wrappedValue.insert(key)}else{set.wrappedValue.remove(key)}}) }
    private func perform(_ action:@escaping () async throws -> Void) { busy=true;issue=nil;Task { defer{busy=false};do {try await action()}catch {issue=(error as? APIProblem)?.message ?? "Could not complete this action. Your draft is still here."} } }
    private func load() async throws {
        let data=try await store.decode(WorkerOverview.self,"/v1/workers");overview=data;reports=data.reports;more=data.has_more;retention=data.retention_days
        snapshot=try await store.decode(TaskDockState.self,"/v1/taskdock").snapshot
        sharingPlan=try await store.decode(PlanningRecord.self,"/v1/planning")
        repairHistory=try await store.decode(RepairHistory.self,"/v1/workers/repair-history")
        if person.isEmpty {person=data.people.first ?? ""};if chosenWorker.isEmpty {chosenWorker=data.workers.first(where:{$0.active})?.id ?? ""}
    }
    private func openShare(){instructions="";preview=nil;link=nil;sheet=WorkerSheet(kind:"share")}
    private var assignedTaskGrants:[WorkerGrantRecord]{overview?.grants.filter{$0.active && $0.mode=="assigned" && $0.task_id==taskID} ?? []}
    private func consumeTask(){if let wanted=store.workerTaskID {taskID=wanted;store.workerTaskID=nil;if assignedTaskGrants.isEmpty{openShare()}else{link=nil;sheet=WorkerSheet(kind:"assigned")}}}
    private var shareRooms:[String:String]{
        guard let planning=sharingPlan,planning.workspace_id==snapshot?.info.workspace_id else{return [:]}
        return Dictionary(planning.tasks.filter{!$0.room.isEmpty}.map{($0.task_id,$0.room)},uniquingKeysWith:{first,_ in first})
    }
    private func grantBody()->[String:Any] { ["worker_id":chosenWorker,"task_id":taskID,"expected_snapshot_id":snapshot?.id ?? "","include_all":true,"instructions":instructions,"days":shareDays] }
    private func copy(_ value:String){NSPasteboard.general.clearContents();NSPasteboard.general.setString(value,forType:.string)}
    private var visible:[WorkerReportRecord] { reports.filter { r in (filter=="all" || r.review==filter) && (query.isEmpty || (r.worker_name+" "+r.title+" "+r.data.text+" "+r.data.location).localizedCaseInsensitiveContains(query)) } }
    var body:some View {
        Group {
            if !local { VStack(alignment:.leading,spacing:16){Text("Worker updates live on your work Mac").font(.title2.bold());Text("Create invitations and review reports on the hosting Mac. The laptop keeps its existing memory and diary cache; it does not host the worker portal.")}.padding(28).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading) }
            else { VStack(alignment:.leading,spacing:12){
                HStack {Text("Worker updates").font(.title2.bold());Spacer();Button("Reload inbox"){perform{try await load()}}.disabled(busy||sheet != nil)}
                Text("Workers report what happened. You decide what changes in the plan. TaskDock stays read-only.").foregroundStyle(.secondary)
                if let issue {Text(issue).foregroundStyle(.orange).textSelection(.enabled)}
                if let data=overview {
                    DisclosureGroup("Worker access · " + (data.enabled ? (data.host.running ? "Enabled" : "Unavailable") : "Disabled")) {
                        ScrollView { VStack(alignment:.leading,spacing:12){
                            Text(data.host.reason).font(.callout).foregroundStyle(.secondary).textSelection(.enabled)
                            if let error=data.host.error {Text(error).foregroundStyle(.orange)}
                            if !data.host.address.isEmpty {Text(data.host.address+"/worker").textSelection(.enabled);Button("Copy portal address"){copy(data.host.address+"/worker")}}
                            Text("Reports are kept indefinitely unless you explicitly delete them. Invitations and browser sessions still expire.").font(.callout)
                            Button(data.enabled ? "Disable worker access…" : "Enable worker access…"){confirmation=data.enabled ? "disable" : "enable"}.disabled(busy || (!data.enabled && !data.host.ready))
                            Text("Disabling access invalidates browser sessions and invitations. Your repair history and laptop pairing stay intact.").font(.caption).foregroundStyle(.secondary)
                            HStack {Picker("Saved schedule person",selection:$person){Text("Choose a person").tag("");ForEach(data.people,id:\.self){Text($0).tag($0)}};Button("Add portal identity"){perform{_ = try await store.request("/v1/workers",method:"POST",body:["name":person]);try await load()}}.disabled(person.isEmpty||busy)}
                            ForEach(data.workers){worker in HStack {Text(worker.name + (worker.active ? "" : " · revoked"));Spacer();if worker.active {Button("Create invitation…"){chosenWorker=worker.id;link=nil;sheet=WorkerSheet(kind:"invite")}.disabled(!data.enabled || !data.host.running||busy);Button("Revoke access…"){targetID=worker.id;confirmation="worker"}.disabled(busy)}}}
                            Text("Tasks assigned in TaskDock appear automatically after refresh for workers with a matching name. Match a different TaskDock name or email once below. Change task assignments in TaskDock.").font(.callout).foregroundStyle(.secondary)
                            ForEach(data.workers.filter{$0.active}){worker in
                                HStack {Text(worker.name);Picker("TaskDock identity",selection:Binding(get:{worker.assignment_keys?.first ?? ""},set:{key in perform{_ = try await store.request("/v1/workers/"+worker.id+"/assignment",method:"PUT",body:["key":key]);try await load()}})){
                                    Text("Match by exact name").tag("")
                                    ForEach(data.assignment_options ?? []){option in Text(option.label).tag(option.key)}
                                }.disabled(busy)}
                            }
                            Button("Request help on a task…"){openShare()}.disabled(data.workers.filter{$0.active}.isEmpty||snapshot==nil||busy)
                            DisclosureGroup("Shared tasks (latest 200)"){ForEach(data.grants){grant in HStack {VStack(alignment:.leading){Text(grant.excerpt["title"] ?? "Task excerpt withdrawn");Text((data.workers.first{$0.id==grant.worker_id}?.name ?? "Worker")+" · "+(grant.active ? (grant.mode=="assigned" ? "assigned in TaskDock" : "active until "+scheduleDate(grant.expires_at ?? "")) : "expired or revoked")).font(.caption)};Spacer();if grant.active {Button("Copy task link"){copy(data.host.address+"/worker#task="+grant.id)}.disabled(!data.enabled || !data.host.running);if grant.mode != "assigned"{Button("Revoke task…"){targetID=grant.id;confirmation="grant"}}}}};if data.more_grants {Text("Older grants are not listed here. Revoke the worker identity to withdraw all of their access.").font(.caption)}}
                        }.padding(.vertical,8) }.frame(maxHeight:260)
                    }
                }
                if let history=repairHistory {DisclosureGroup("Repair history & patterns · \(history.reviewed_reports) included reports") {
                    ScrollView {VStack(alignment:.leading,spacing:14){
                        Text(history.notice).font(.caption).foregroundStyle(.secondary)
                        if history.groups.isEmpty {Text("Include a task or unexpected-work report in repair history when reviewing it. Verified complete-repair times help calibrate future estimates.")}
                        ForEach(Array(history.groups.prefix(historyLimit))){group in
                            GroupBox((group.room.isEmpty ? group.equipment:group.room+(group.equipment.isEmpty ? "":" · "+group.equipment))+" · "+group.category){VStack(alignment:.leading,spacing:8){
                                Text("\(group.reports) reports · \(group.verified_repairs) verified repair records · latest "+group.latest_work_date)
                                if let duration=group.duration {Text("Comparable effort: \(duration.minimum)–\(duration.maximum) min · \(duration.samples) verified complete-effort samples")}else{Text("\(group.time_samples) verified complete-effort samples; at least 3 needed for a calibrated range.").foregroundStyle(.secondary)}
                                Text(group.suggestion).font(.callout)
                                DisclosureGroup("Supporting reports"){ForEach(group.evidence){evidence in Button(evidence.work_date+" · "+evidence.summary){perform{let report=try await store.decode(WorkerReportRecord.self,"/v1/workers/reports/"+evidence.id);if !reports.contains(where:{$0.id==report.id}){reports.append(report)};filter="all";query="";selected=report.id}}.buttonStyle(.link)}}
                            }.frame(maxWidth:.infinity,alignment:.leading)}
                        }
                        if history.groups.count>historyLimit {Button("Show more repair groups"){historyLimit+=20}}
                        if history.limited {Text("Analysis covers the latest \(history.limit) included reports. Older reports are still retained.").font(.caption)}
                    }}.frame(maxHeight:260)
                }}
                Divider()
                HSplitView {
                    VStack(alignment:.leading){TextField("Find worker, task or room",text:$query).textFieldStyle(.roundedBorder);Picker("Show",selection:$filter){Text("Unread").tag("unread");Text("Needs follow-up").tag("needs_follow_up");Text("All updates").tag("all")}
                        List(selection:$selected){ForEach(visible){r in VStack(alignment:.leading,spacing:4){Text(r.worker_name+" · "+r.title).lineLimit(2);Text(r.data.status.replacingOccurrences(of:"_",with:" ")+" · "+r.review.replacingOccurrences(of:"_",with:" ")).font(.caption);Text(scheduleDate(r.submitted_at)).font(.caption).foregroundStyle(.secondary)}.tag(r.id)}}
                        if more {Button("Load older updates"){perform{let page=try await store.decode(WorkerReceiptPage.self,"/v1/workers/reports?offset=\(reports.count)");reports+=page.items.filter{r in !reports.contains{$0.id==r.id}};more=page.has_more}}.disabled(busy)}
                    }.padding(8).frame(minWidth:240,idealWidth:300,maxWidth:360)
                    ScrollView {if let r=reports.first(where:{$0.id==selected}) {reportDetail(r)}else{VStack(alignment:.leading,spacing:12){Text(reports.isEmpty ? "No worker updates yet" : "Choose an update").font(.title3.bold());Text("Share a task or a worker invitation when approved HTTPS is ready. Reports arrive here for your review.").foregroundStyle(.secondary)}.padding(24).frame(maxWidth:.infinity,alignment:.leading)}}.frame(minWidth:400)
                }
            }.padding(20).disabled(busy && sheet == nil) }
        }.onAppear {if local {perform{try await load();consumeTask()}}}.onChange(of:store.section){key in if key=="Workers" && local && sheet==nil {perform{try await load();consumeTask()}}}.onChange(of:store.workerTaskID){_ in if local && overview != nil {consumeTask()}}
        .sheet(item:$sheet,onDismiss:{preview=nil;link=nil;issue=nil}){request in editor(request).id(request.id)}
        .alert(alertTitle,isPresented:Binding(get:{confirmation != nil},set:{if !$0{confirmation=nil}})) {
            Button("Cancel",role:.cancel){confirmation=nil}
            Button("Confirm"){let action=confirmation;confirmation=nil;perform{
                if action=="worker" {_ = try await store.request("/v1/workers/"+targetID+"/revoke",method:"POST",body:[:])}
                else if action=="grant" {_ = try await store.request("/v1/workers/grants/"+targetID+"/revoke",method:"POST",body:[:])}
                else if action=="delete",let r=reports.first(where:{$0.id==targetID}) {_ = try await store.request("/v1/workers/reports/"+r.id+"?expected_revision=\(r.revision)",method:"DELETE")}
                else {_ = try await store.request("/v1/workers/settings",method:"PUT",body:["enabled":action=="enable" ? true : action=="disable" ? false : overview?.enabled ?? false,"retention_days":retention])}
                try await load()
            }}
        } message:{Text(alertMessage)}
    }
    private var alertTitle:String {switch confirmation {case "enable":return "Enable worker access?";case "disable":return "Disable worker access?";case "worker":return "Revoke this worker’s access?";case "grant":return "Revoke this task share?";case "delete":return "Permanently delete this report?";default:return "Confirm change?"}}
    private var alertMessage:String {switch confirmation {case "enable":return "Opens only the dedicated HTTPS worker portal on the local network. Verify institutional certificate trust and worker browsers before sharing invitations. Juno must remain open and awake.";case "disable":return "All worker sessions and invitations stop working. Reports stay saved indefinitely. Your paired laptop is unchanged.";case "worker","grant":return "Access is withdrawn. Reports stay available for review. Already-viewed information cannot be remotely erased.";case "delete":return "This removes the retained report and its review history. Applied planning facts and old backups are not erased.";default:return "Saved reports remain until explicitly deleted."}}
    private func reportDetail(_ r:WorkerReportRecord)->some View {VStack(alignment:.leading,spacing:16){
        Text(r.title).font(.title2.bold());Text(r.worker_name+" · "+scheduleDate(r.submitted_at));Text("Work date: "+r.data.work_date+" · "+r.data.status.replacingOccurrences(of:"_",with:" ")).font(.headline)
        if let previous=r.correction_of {Text("Correction / follow-up to receipt "+previous).font(.caption)}
        Text(r.data.text).textSelection(.enabled)
        Text("Reported time: "+(r.data.actual_minutes.map{"\($0) minutes"} ?? "Unknown")+" · remaining: "+(r.data.remaining_minutes.map{"\($0) minutes"} ?? "Unknown"))
        Text("Blocker: "+(r.data.blocker_state=="none" ? "Explicitly none" : r.data.blocker_state=="reported" ? r.data.blocker : "Not supplied / unknown"))
        if !r.data.next_action.isEmpty {Text("Next: "+r.data.next_action)};if !r.data.handoff.isEmpty {Text("Handoff: "+r.data.handoff)};if !r.data.location.isEmpty {Text("Room / equipment: "+r.data.location)}
        Text("Review: "+r.review.replacingOccurrences(of:"_",with:" "));if !r.review_note.isEmpty{Text(r.review_note)}
        if !r.applied.isEmpty {Text("Applied fields: "+r.applied.keys.sorted().joined(separator:", ")).font(.caption)}
        DisclosureGroup("What was shared"){if r.shared_excerpt.isEmpty {Text("Task excerpt expired or withdrawn.")}else{ForEach(r.shared_excerpt.keys.sorted(),id:\.self){key in Text(key.replacingOccurrences(of:"_",with:" ")+": "+(r.shared_excerpt[key] ?? ""))}}}
        VStack(alignment:.leading,spacing:8){Button("Review update…"){prepareReview(r);sheet=WorkerSheet(kind:"review",report:r)};Button("Review planning changes…"){perform{plan=try await store.decode(PlanningRecord.self,"/v1/planning");applyFields=[];sheet=WorkerSheet(kind:"apply",report:r)}}.disabled(!r.grant_active||store.unsavedSections.contains("Plan"));Button("Copy TaskDock summary"){copy("Worker report — "+r.worker_name+"\n"+r.title+"\n"+r.data.work_date+" · "+r.data.status+"\n"+r.data.text+"\nBlockers: "+r.data.blocker_state+" "+r.data.blocker+"\nNext: "+r.data.next_action+"\nNot synchronized to TaskDock.")}}
        Text("Worker reports and verified completion are local annotations. TaskDock status is unchanged. Minutes replace a reviewed value; reconcile overlapping shift/task reports first.").font(.caption).foregroundStyle(.secondary)
        if store.unsavedSections.contains("Plan"){Text("Save or discard your existing Plan draft before applying a worker update.").foregroundStyle(.orange)}
        Button("Delete retained report…",role:.destructive){targetID=r.id;confirmation="delete"}.font(.caption)
    }.padding(24).frame(maxWidth:.infinity,alignment:.leading)}
    @ViewBuilder private func editor(_ request:WorkerSheet)->some View {
        VStack(alignment:.leading,spacing:16){
            Text(request.kind=="assigned" ? "Assigned in TaskDock" : request.kind=="share" ? "Request help on a task" : request.kind=="invite" ? "Invite a worker" : request.kind=="apply" ? "Review planning changes" : "Review worker update").font(.title2.bold())
            ScrollView { VStack(alignment:.leading,spacing:16) {
            if request.kind=="invite" {Text("Verify the recipient before sharing. This one-use invitation expires in 24 hours; the enrolled session lasts at most seven days. It grants worker-only access.");Text(overview?.workers.first{$0.id==chosenWorker}?.name ?? "Worker").font(.headline);if link==nil{Button("Create private invitation"){perform{link=try await store.decode(WorkerLink.self,"/v1/workers/"+chosenWorker+"/invitations",method:"POST",body:[:])}}}}
            else if request.kind=="assigned" {
                Text("These workers already have this task in their portal. Refresh TaskDock in Juno after changing an assignment there.").foregroundStyle(.secondary)
                ForEach(assignedTaskGrants){grant in
                    Text(overview?.workers.first{$0.id==grant.worker_id}?.name ?? "Worker").font(.headline)
                    Text(grant.excerpt["title"] ?? "Assigned task")
                    Button("Copy task link"){copy((overview?.host.address ?? "")+"/worker#task="+grant.id)}.disabled(overview?.host.running != true)
                }
                Button("Request help from another worker…"){openShare()}
            }
            else if request.kind=="share" {
                if let preview {Text("Task details shared with the worker").font(.headline);Text(preview.worker_name);ForEach(workerDetailKeys(preview.excerpt),id:\.self){key in Text(workerDetailLabel(key)+": "+(preview.excerpt[key].flatMap{$0.isEmpty ? nil: key.hasSuffix("_at") || key=="taskdock_copy_saved" ? scheduleDate($0):$0} ?? "Not supplied"))};Text("TaskDock copy saved: "+scheduleDate(preview.source_saved_at)).font(.caption)
                    if overview?.enabled != true || overview?.host.running != true {Text("Enable approved worker HTTPS in Worker access before creating this link.").font(.callout).foregroundStyle(.secondary)}
                    if link==nil {HStack{Button("Back to task"){self.preview=nil};Button("Create task link"){perform{link=try await store.decode(WorkerLink.self,"/v1/workers/grants",method:"POST",body:grantBody());try await load()}}.disabled(overview?.enabled != true || overview?.host.running != true)}}
                }else{
                    Picker("Worker",selection:$chosenWorker){Text("Choose worker").tag("");ForEach(overview?.workers.filter{$0.active} ?? []){Text($0.name).tag($0.id)}}
                    WorkerTaskChooser(tasks:snapshot?.items ?? [],rooms:shareRooms,selected:$taskID)
                    Text("Available TaskDock details are included automatically. Private supervisor notes stay private. Assigned tasks already appear for matched workers; use this to request help from another worker.").font(.callout).foregroundStyle(.secondary)
                    TextField("Instructions for this worker (optional)",text:$instructions).textFieldStyle(.roundedBorder);Stepper("Share for \(shareDays) days",value:$shareDays,in:1...30)

                }
            }else if let r=request.report {
                if request.kind=="apply" {
                    Text("Select values to save to Juno planning. Existing values are replaced, never added. Reconcile overlapping reports first. No TaskDock write.").foregroundStyle(.secondary)
                    ForEach(applying,id:\.0){key,label in if let value=proposed(r,key),r.applied[key]==nil {Toggle(isOn:binding($applyFields,key)){VStack(alignment:.leading){Text(label);Text("Current: "+currentValue(r,key)+" → Reported: "+value).font(.caption).foregroundStyle(.secondary)}}}}
                    Text("Reported completion does not change staffing, priority or TaskDock status.").font(.caption)
                    Button("Save selected planning changes"){perform{_ = try await store.request("/v1/workers/reports/"+r.id+"/apply",method:"POST",body:["expected_revision":r.revision,"expected_planning_revision":plan?.revision ?? -1,"fields":Array(applyFields).sorted()]);sheet=nil;try await load()}}.disabled(applyFields.isEmpty||busy)
                }else{
                    Text(r.worker_name+" · "+r.title);Picker("Outcome",selection:$outcome){Text("Reviewed").tag("reviewed");Text("Needs follow-up").tag("needs_follow_up");if r.data.status=="reported_complete"{Text("Completion verified by me").tag("completion_verified")};Text("Dismissed").tag("dismissed")};TextField("Private review note (optional)",text:$reviewNote).textFieldStyle(.roundedBorder)
                    if r.data.kind != "shift" {
                        Toggle("Use this report for repair history and future estimates",isOn:$includeRepair)
                        if includeRepair {
                            Text("Confirm the repair context. It remains your independent reviewed history even if a task share expires. Partial work will not be treated as a whole-repair time.").font(.caption).foregroundStyle(.secondary)
                            TextField("Confirmed room (or supply equipment)",text:$repairRoom).textFieldStyle(.roundedBorder)
                            TextField("Equipment / asset identifier",text:$repairEquipment).textFieldStyle(.roundedBorder)
                            Picker("Repair type",selection:$repairCategory){Text("Printer / cutter").tag("printer");Text("Network / offline computer").tag("offline computer");Text("Driver / display / input").tag("driver/display");Text("Other repair").tag("other")}
                            TextField("Repair / symptom summary",text:$repairSummary).textFieldStyle(.roundedBorder)
                            Toggle("Reported minutes cover the complete repair",isOn:$completeEffort).disabled(r.data.actual_minutes==nil)
                            Text("Time calibration also requires Completion verified by me. Unknown effort stays unknown.").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    Button("Save review"){perform{_ = try await store.request("/v1/workers/reports/"+r.id+"/review",method:"POST",body:reviewBody(r));sheet=nil;try await load()}}.disabled(busy || (includeRepair && (repairSummary.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty || (repairRoom.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty && repairEquipment.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty))))
                }
            }
            if let link {Text("Expires "+scheduleDate(link.expires_at)).font(.caption);Button("Copy private link"){copy(link.url)};Text("Share it yourself with the intended worker. Nothing has been sent.").font(.caption)}
            if let issue {Text(issue).foregroundStyle(.orange).textSelection(.enabled)}
            } }.frame(maxHeight:460)
            HStack{if request.kind=="share" && preview==nil{Button("Preview worker view"){perform{preview=try await store.decode(WorkerGrantPreview.self,"/v1/workers/grants/preview",method:"POST",body:grantBody())}}.disabled(chosenWorker.isEmpty || !(snapshot?.items.contains(where:{$0.id==taskID}) ?? false) || busy)};Spacer();Button(link==nil ? "Cancel" : "Done"){sheet=nil}.keyboardShortcut(.cancelAction).disabled(busy)}
        }.padding(26).frame(width:600).fixedSize(horizontal:false,vertical:true).disabled(busy).interactiveDismissDisabled(busy)
        .onAppear{store.unsavedSections.insert("worker review")}.onDisappear{store.unsavedSections.remove("worker review")}
    }
    private func repairText(_ r:WorkerReportRecord,_ key:String)->String {if case .string(let value)=r.repair_context[key]{return value};return ""}
    private func prepareReview(_ r:WorkerReportRecord){
        reviewNote=r.review_note;outcome=r.review=="unread" ? "reviewed":r.review
        repairRoom=repairText(r,"room");if repairRoom.isEmpty {repairRoom=r.shared_excerpt["room"] ?? r.data.location}
        repairEquipment=repairText(r,"equipment");repairCategory=repairText(r,"category");if repairCategory.isEmpty{repairCategory="other"}
        repairSummary=repairText(r,"summary");if repairSummary.isEmpty{repairSummary=String((r.shared_excerpt["title"] ?? r.data.text).prefix(500))}
        if case .bool(let value)=r.repair_context["complete_effort"]{completeEffort=value}else{completeEffort=false}
        includeRepair=r.data.kind != "shift" && (!r.repair_context.isEmpty || !repairRoom.isEmpty || !repairEquipment.isEmpty)
    }
    private func reviewBody(_ r:WorkerReportRecord)->[String:Any]{
        var body:[String:Any]=["expected_revision":r.revision,"outcome":outcome,"note":reviewNote]
        if includeRepair && r.data.kind != "shift"{body["repair"]=["room":repairRoom,"equipment":repairEquipment,"category":repairCategory,"summary":repairSummary,"complete_effort":completeEffort]}else{body["repair"]=NSNull()}
        return body
    }
    private func proposed(_ r:WorkerReportRecord,_ key:String)->String? {switch key {case "actual_minutes":return r.data.actual_minutes.map{String($0)};case "minutes":return r.data.remaining_minutes.flatMap{$0>=5 ? String($0):nil};case "blocker":return r.data.blocker_state=="none" ? "Explicitly no blocker" : r.data.blocker_state=="reported" ? r.data.blocker:nil;case "next_action":return r.data.next_action.isEmpty ? nil:r.data.next_action;default:return r.data.handoff.isEmpty ? nil:r.data.handoff}}
    private func currentValue(_ r:WorkerReportRecord,_ key:String)->String {guard let facts=plan?.tasks.first(where:{$0.task_id==r.task_id}) else{return "Not supplied"};switch key{case "actual_minutes":return facts.actual_minutes.map{String($0)} ?? "Unknown";case "minutes":return facts.minutes.map{String($0)} ?? "Unknown";case "blocker":return facts.blocker.isEmpty ? "None recorded":facts.blocker;case "next_action":return facts.next_action.isEmpty ? "None recorded":facts.next_action;default:return facts.resume.isEmpty ? "None recorded":facts.resume}}
}
