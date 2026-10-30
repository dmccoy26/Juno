import SwiftUI

struct RecurringSchedule: Codable, Identifiable {
    var id = UUID().uuidString; var kind = "work"; var name = ""; var location = ""
    var start_date = "2026-08-24"; var end_date = "2026-12-10"
    var days = [0,1,2,3,4]; var start_time = "09:00"; var end_time = "17:00"; var timezone = "America/Chicago"
}
struct StaffSchedule: Codable, Identifiable {
    var name = ""; var status = "tentative"; var weekly_limit_minutes = 1200; var desired_minutes: Int?; var notes = ""
    var id: String { name }
}
struct DailyScheduleException: Codable, Identifiable {
    var id = UUID().uuidString; var kind = "room"; var name = ""; var day = integrationDay(0)
    var closed = true; var start_time: String? = "09:00"; var end_time: String? = "17:00"; var note = ""
}
struct PlanningReservation: Codable, Identifiable {
    var id: String; var task_id: String; var workspace_id: String; var room: String; var employee: String
    var start: String; var end: String; var uses_owner: Bool
}
struct ScheduleRecord: Codable {
    var revision: Int; var rules: [RecurringSchedule]; var people: [StaffSchedule]; var exceptions: [DailyScheduleException]; var reservations: [PlanningReservation]
    var reservation_notice: String?
}
struct AvailabilityPerson: Decodable, Identifiable { var name: String; var status: String; var id: String { name } }
struct RepairWindow: Decodable, Identifiable {
    var start: String; var end: String; var proposed_end: String; var available_minutes: Int
    var id: String { start + end }
}
struct AvailabilityRecord: Decodable {
    var day: String; var revision: Int; var rooms: [String]; var people: [AvailabilityPerson]
    var windows: [RepairWindow]; var warnings: [String]; var source_notices: [String]; var notice: String
}
struct TaskEstimate: Decodable { var minimum: Int; var maximum: Int; var source: String; var reason: String; var question: String; var notice: String; var model_notice: String? }

func scheduleKind(_ text: String) -> String { ["work":"My work hours","room":"Building access","staff_available":"Staff shift","classroom_busy":"Classroom occupied"][text] ?? text }

func scheduleDate(_ text: String) -> String {
    guard let date = providerDate(text) else { return text }
    let f = DateFormatter(); f.timeZone = TimeZone(identifier:"America/Chicago"); f.dateFormat = "EEE MMM d, h:mm a"; return f.string(from:date)
}

struct SchedulesWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var record: ScheduleRecord?
    @State private var busy = false; @State private var dirty = false; @State private var issue: String?
    @State private var rule = RecurringSchedule(); @State private var person = StaffSchedule(); @State private var exception = DailyScheduleException()
    @State private var ruleEditor = false; @State private var personEditor = false; @State private var exceptionEditor = false
    @State private var editingPersonName: String?
    @State private var limitHours = "20"; @State private var desiredHours = ""
    private let weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    private func load() async {
        busy = true; defer { busy = false }
        do { record = try await store.decode(ScheduleRecord.self,"/v1/schedules");dirty = false;issue = nil }
        catch { issue = (error as? APIProblem)?.message ?? "Could not load schedules." }
    }
    private func save() async {
        guard let record else { return };busy = true;defer { busy = false }
        do {
            let encoded = try JSONSerialization.jsonObject(with:JSONEncoder().encode(record)) as! [String:Any]
            self.record = try await store.decode(ScheduleRecord.self,"/v1/schedules",method:"PUT",body:["expected_revision":record.revision,"rules":encoded["rules"]!,"people":encoded["people"]!,"exceptions":encoded["exceptions"]!])
            dirty = false;issue = "Schedules saved. Review existing planning holds after any availability change."
        } catch { issue = (error as? APIProblem)?.message ?? "Could not save. Your draft remains here." }
    }
    var body: some View {
        ScrollView {
            VStack(alignment:.leading,spacing:16) {
                Text("Schedules & people").font(.title2.bold())
                Text("Recurring schedules, semester dates and daily exceptions. Building access excludes classes; staff shifts do not establish capability. All schedule times use the stated timezone.").foregroundStyle(.secondary)
                HStack {
                    Button("Reload saved schedules") { Task { await load() } }.disabled(dirty || busy)
                    Button("Save schedules") { Task { await save() } }.disabled(!dirty || busy || store.offline)
                    if dirty { Text("Unsaved changes").foregroundStyle(.orange);Button("Discard draft") { Task { await load() } } }
                    if busy { ProgressView().controlSize(.small) }
                }
                if store.offline { Text("Dated offline schedule copy. Reconnect to edit schedules or reserve work.").foregroundStyle(.orange) }
                if let issue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                if let record {
                    GroupBox("People and weekly limits") {
                        VStack(alignment:.leading,spacing:10) {
                            ForEach(record.people) { p in
                                HStack { VStack(alignment:.leading) { Text(p.name + " • " + p.status).font(.headline);Text("Funded limit: \(p.weekly_limit_minutes / 60) hours • agreed hours: " + (p.desired_minutes.map { "\($0 / 60)" } ?? "unknown"));Text(p.notes).font(.caption).foregroundStyle(.secondary) };Spacer();Button("Edit") { person = p;editingPersonName = p.name;limitHours = String(p.weekly_limit_minutes/60);desiredHours = p.desired_minutes.map { String($0/60) } ?? "";personEditor = true } }
                            }
                            Button("Add person / candidate") { person = StaffSchedule();editingPersonName = nil;limitHours = "20";desiredHours = "";personEditor = true }
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                    }
                    GroupBox("Recurring rules") {
                        VStack(alignment:.leading,spacing:10) {
                            ForEach(record.rules) { r in
                                HStack { VStack(alignment:.leading) { Text(scheduleKind(r.kind) + ": " + (r.kind == "classroom_busy" ? r.location + " — " + r.name : r.name.isEmpty ? "My normal work" : r.name)).font(.headline);Text(r.days.sorted().map { weekdays[$0] }.joined(separator:", ") + "  " + r.start_time + "–" + r.end_time);Text(r.start_date + " through " + r.end_date + " • " + r.timezone).font(.caption).foregroundStyle(.secondary) };Spacer();Button("Edit") { rule = r;ruleEditor = true };Button("Remove rule") { self.record?.rules.removeAll { $0.id == r.id };dirty = true } }
                            }
                            Button("Add recurring schedule") { rule = RecurringSchedule();ruleEditor = true }
                            Text("A recurring rule replaces older imported availability for the same room/person. Imported classroom occupancy remains effective unless you add a replacement classroom rule or a specific no-classes exception.").font(.caption)
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                    }
                    GroupBox("Daily exceptions") {
                        VStack(alignment:.leading,spacing:10) {
                            ForEach(record.exceptions) { e in
                                HStack { Text(e.day + " • " + scheduleKind(e.kind) + " • " + e.name + " • " + (e.closed ? "unavailable / no classes" : (e.start_time ?? "") + "–" + (e.end_time ?? "")));Spacer();Button("Edit") { exception = e;exceptionEditor = true };Button("Remove exception") { self.record?.exceptions.removeAll { $0.id == e.id };dirty = true } }
                            }
                            Button("Add closure / shift exception") { exception = DailyScheduleException();exceptionEditor = true }
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                    }
                    GroupBox("Local planning holds — no TaskDock changes") {
                        VStack(alignment:.leading,spacing:10) {
                            if let notice = record.reservation_notice, !notice.isEmpty { Text(notice).foregroundStyle(.orange) }
                            if record.reservations.isEmpty { Text("No planning holds. Find possible work windows in Plan.").foregroundStyle(.secondary) }
                            ForEach(record.reservations) { r in
                                HStack { VStack(alignment:.leading) { Text(r.room + " • " + (r.employee.isEmpty ? "My work" : r.employee));Text(scheduleDate(r.start) + " → " + scheduleDate(r.end)).font(.caption) };Spacer();Button("Release hold") {
                                    Task { busy = true;defer { busy = false };do { _ = try await store.request("/v1/schedules/reservations/"+r.id+"?expected_revision=\(record.revision)",method:"DELETE");await load() } catch { issue = (error as? APIProblem)?.message ?? "Could not release; refresh before retrying." } }
                                }.disabled(dirty || store.offline) }
                            }
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                    }
                }
            }.padding(24).disabled(busy)
        }.task { await load() }
        .sheet(isPresented:$ruleEditor) { ruleForm }
        .sheet(isPresented:$personEditor) { personForm }
        .sheet(isPresented:$exceptionEditor) { exceptionForm }
    }
    private var ruleForm: some View {
        VStack(alignment:.leading,spacing:12) {
            Text("Recurring schedule").font(.title2.bold())
            Picker("Kind",selection:$rule.kind) { Text("My work hours").tag("work");Text("Building access").tag("room");Text("Classroom occupied").tag("classroom_busy");Text("Staff shift").tag("staff_available") }
            TextField("Room, employee or course name",text:$rule.name)
            if rule.kind == "classroom_busy" { TextField("Room location",text:$rule.location) }
            HStack { TextField("First date YYYY-MM-DD",text:$rule.start_date);TextField("Last date YYYY-MM-DD",text:$rule.end_date) }
            HStack { ForEach(0..<7,id:\.self) { d in Toggle(weekdays[d],isOn:Binding(get:{rule.days.contains(d)},set:{ yes in if yes { rule.days.append(d) } else { rule.days.removeAll { $0 == d } } })).toggleStyle(.checkbox) } }
            HStack { TextField("Start HH:MM",text:$rule.start_time);TextField("End HH:MM",text:$rule.end_time) }
            TextField("Timezone",text:$rule.timezone)
            Text("24-hour local times, including the final semester date. Saving remains subject to validation.").font(.caption)
            HStack { Button("Cancel") { ruleEditor = false };Spacer();Button("Apply to draft") { record?.rules.removeAll { $0.id == rule.id };record?.rules.append(rule);dirty = true;ruleEditor = false }.disabled(store.offline || rule.days.isEmpty) }
        }.padding(24).frame(width:700)
    }
    private var personForm: some View {
        VStack(alignment:.leading,spacing:12) {
            Text("Person / hiring status").font(.title2.bold());TextField("Name",text:$person.name).disabled(editingPersonName != nil)
            Picker("Status",selection:$person.status) { Text("Active").tag("active");Text("Schedule unsettled").tag("tentative");Text("Candidate — not hired").tag("candidate") }
            TextField("Funded weekly limit, whole hours",text:$limitHours);TextField("Agreed hours, optional",text:$desiredHours);TextField("Notes / unresolved details",text:$person.notes)
            Text("Candidates and unsettled schedules are excluded from confirmed planning capacity. Funding does not imply agreed hours or independent capability.").font(.caption)
            HStack { Button("Cancel") { personEditor = false };Spacer();Button("Apply to draft") {
                guard let hours = Int(limitHours), (0...40).contains(hours), desiredHours.isEmpty || (Int(desiredHours) != nil && (0...hours).contains(Int(desiredHours)!)) else { issue = "Use whole hours from 0–40; agreed hours cannot exceed funding.";return }
                person.weekly_limit_minutes = hours*60;person.desired_minutes = Int(desiredHours).map { $0*60 }
                record?.people.removeAll { $0.name.caseInsensitiveCompare(person.name) == .orderedSame };record?.people.append(person);dirty = true;personEditor = false
            }.disabled(store.offline || person.name.trimmingCharacters(in:.whitespaces).isEmpty) }
        }.padding(24).frame(width:620)
    }
    private var exceptionForm: some View {
        VStack(alignment:.leading,spacing:12) {
            Text("Daily exception").font(.title2.bold())
            Picker("Kind",selection:$exception.kind) { Text("My hours").tag("work");Text("Building access").tag("room");Text("Staff shift").tag("staff_available");Text("Class occupancy").tag("classroom_busy") }
            TextField("Exact room or employee name",text:$exception.name);TextField("Date YYYY-MM-DD",text:$exception.day)
            Toggle(exception.kind == "classroom_busy" ? "No classes on this date" : "Unavailable / closed on this date",isOn:$exception.closed)
            if !exception.closed { HStack { TextField("Replacement start HH:MM",text:Binding(get:{exception.start_time ?? ""},set:{exception.start_time = $0}));TextField("Replacement end HH:MM",text:Binding(get:{exception.end_time ?? ""},set:{exception.end_time = $0})) } }
            TextField("Reason / note",text:$exception.note)
            Text("Exceptions use America/Chicago. A no-classes exception does not open a closed building.").font(.caption)
            HStack { Button("Cancel") { exceptionEditor = false };Spacer();Button("Apply to draft") { record?.exceptions.removeAll { $0.id == exception.id };record?.exceptions.append(exception);dirty = true;exceptionEditor = false }.disabled(store.offline) }
        }.padding(24).frame(width:650)
    }
}

struct RepairWindowsView: View {
    @ObservedObject var store: JunoStore
    var tasks: [PlanningTask]; var workspace: String?
    @State private var day = integrationDay(0);@State private var room = "";@State private var employee = "";@State private var minutes = "60";@State private var supervision = false
    @State private var data: AvailabilityRecord?;@State private var busy = false;@State private var issue: String?;@State private var taskID = ""
    @State private var rosterRooms: [String] = []; @State private var rosterPeople: [AvailabilityPerson] = []
    @State private var searched: String?
    private var signature: String { [day,room,employee,minutes,String(supervision)].joined(separator:"|") }
    private func find() async {
        let requestSignature = signature
        busy = true;data = nil;defer { busy = false }
        do {
            var parts = URLComponents();parts.path = "/v1/availability";parts.queryItems = [URLQueryItem(name:"day",value:day),URLQueryItem(name:"room",value:room),URLQueryItem(name:"employee",value:employee),URLQueryItem(name:"minutes",value:minutes),URLQueryItem(name:"supervision",value:supervision ? "true" : "false")]
            let result = try await store.decode(AvailabilityRecord.self,parts.string!);data = result;rosterRooms = result.rooms;rosterPeople = result.people;searched = requestSignature;issue = nil
        } catch { issue = (error as? APIProblem)?.message ?? "Could not find possible windows. Reconnect to the work Mac." }
    }
    var body: some View {
        GroupBox("When could we work on this?") {
            VStack(alignment:.leading,spacing:10) {
                HStack { TextField("Seven days starting YYYY-MM-DD",text:$day);TextField("Minutes needed",text:$minutes).frame(width:130) }
                HStack {
                    Picker("Room",selection:$room) { Text("Choose room").tag("");ForEach(rosterRooms,id:\.self) { Text($0).tag($0) } }
                    Picker("Who",selection:$employee) { Text("Me").tag("");ForEach(rosterPeople) { Text($0.name+" • "+$0.status).tag($0.name) } }
                }
                if !employee.isEmpty { Toggle("Needs my supervision / collaboration",isOn:$supervision) }
                HStack { Button("Find possible windows") { Task { await find() } }.disabled(busy || store.offline);Button("Manage schedules") { store.section = "Schedules" };if busy { ProgressView().controlSize(.small) } }
                if let issue { Text(issue).foregroundStyle(.orange) }
                if let data, signature == searched {
                    ForEach(data.warnings,id:\.self) { Text($0).foregroundStyle(.orange) }
                    if !room.isEmpty && data.windows.isEmpty { Text("No confirmed window fits. Review the duration, room/staff hours and blockers.").foregroundStyle(.secondary) }
                    Picker("Issue for a planning hold",selection:$taskID) { Text("Explore windows only").tag("");ForEach(tasks) { Text($0.title).tag($0.id) } }
                    Text("A hold requires saved task details: reviewed room, person, duration, prerequisites and capability/supervision. It changes only Juno’s plan.").font(.caption)
                    ForEach(data.windows.prefix(20)) { w in
                        HStack {
                            VStack(alignment:.leading) { Text(scheduleDate(w.start) + " → " + scheduleDate(w.proposed_end)).font(.headline);Text("Within a \(w.available_minutes)-minute opening").font(.caption) }
                            Spacer();Button("Reserve reviewed task") {
                                guard let workspace else { issue = "Connect TaskDock first.";return };busy = true
                                Task { defer { busy = false };do {
                                    _ = try await store.request("/v1/schedules/reservations",method:"POST",body:["expected_revision":data.revision,"task_id":taskID,"workspace_id":workspace,"room":room,"employee":employee,"start":w.start,"end":w.proposed_end]);await find();issue = "Planning hold saved in Juno. TaskDock was not changed."
                                } catch { issue = (error as? APIProblem)?.message ?? "Hold not confirmed. Refresh before retrying." } }
                            }.disabled(busy || taskID.isEmpty || store.offline)
                        }
                    }
                    Text(data.notice).font(.caption).foregroundStyle(.secondary)
                    DisclosureGroup("Source dates") { ForEach(data.source_notices,id:\.self) { Text($0).font(.caption) } }
                } else if searched != nil { Text("Inputs changed; find windows again before using a result.").font(.caption).foregroundStyle(.orange) }
            }.frame(maxWidth:.infinity,alignment:.leading).padding(6).disabled(busy)
        }.task { if !store.offline { await find() } }
    }
}
