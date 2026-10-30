import SwiftUI

struct RecurringSchedule: Codable, Identifiable {
    var id = UUID().uuidString; var kind = "work"; var name = ""; var location = ""
    var start_date = integrationDay(0); var end_date = integrationDay(0)
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

func scheduleTime(_ text: String) -> String {
    let parts = text.split(separator:":")
    guard parts.count == 2, let hour = Int(parts[0]), let minute = Int(parts[1]), (0...23).contains(hour), (0...59).contains(minute) else { return text }
    return "\(hour % 12 == 0 ? 12 : hour % 12):" + String(format:"%02d",minute) + (hour < 12 ? " AM" : " PM")
}

struct ScheduleTimeField: View {
    let title: String
    @Binding var value: String
    private var formatter: DateFormatter {
        let f = DateFormatter(); f.locale = Locale(identifier:"en_US_POSIX"); f.timeZone = TimeZone(identifier:"America/Chicago"); f.dateFormat = "HH:mm"; return f
    }
    var body: some View {
        DatePicker(title,selection:Binding(get:{formatter.date(from:value) ?? Date()},set:{value = formatter.string(from:$0)}),displayedComponents:.hourAndMinute)
            .environment(\.locale,Locale(identifier:"en_US"))
            .environment(\.timeZone,TimeZone(identifier:"America/Chicago")!)
    }
}

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
    @State private var scheduleView = "Week by person"
    @State private var comparisonDate = Date()
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
                    Picker("Schedule view", selection:$scheduleView) {
                        Text("By person").tag("Week by person")
                        Text("By room").tag("Week by room")
                        Text("Room + person").tag("Compare")
                        Text("List & edit").tag("List & edit")
                    }.pickerStyle(.segmented).frame(maxWidth:600)
                    if scheduleView != "List & edit" {
                        if scheduleView == "Compare" {
                            HStack {
                                DatePicker("Compare date",selection:$comparisonDate,displayedComponents:.date)
                                    .environment(\.timeZone,TimeZone(identifier:"America/Chicago")!)
                                Button("Previous day") { moveComparisonDay(-1) }
                                Button("Today") { comparisonDate = Date() }
                                Button("Next day") { moveComparisonDay(1) }
                            }
                            ScrollView(.horizontal) { HStack(alignment:.top,spacing:12) {
                                ScheduleWeekView(record:record,byRoom:true,comparisonDate:comparisonDate).frame(width:400,alignment:.leading)
                                Divider()
                                ScheduleWeekView(record:record,byRoom:false,comparisonDate:comparisonDate).frame(width:400,alignment:.leading)
                            } }
                        } else {
                            ScheduleWeekView(record:record, byRoom:scheduleView == "Week by room").id(scheduleView)
                        }
                        Button("Edit schedules and people") { scheduleView = "List & edit" }
                    } else {
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
                                HStack { VStack(alignment:.leading) { Text(scheduleKind(r.kind) + ": " + (r.kind == "classroom_busy" ? r.location + " — " + r.name : r.name.isEmpty ? "My normal work" : r.name)).font(.headline);Text(r.days.sorted().map { weekdays[$0] }.joined(separator:", ") + "  " + scheduleTime(r.start_time) + "–" + scheduleTime(r.end_time));Text(r.start_date + " through " + r.end_date + " • " + r.timezone).font(.caption).foregroundStyle(.secondary) };Spacer();Button("Edit") { rule = r;ruleEditor = true };Button("Remove rule") { self.record?.rules.removeAll { $0.id == r.id };dirty = true } }
                            }
                            Button("Add recurring schedule") { rule = RecurringSchedule();ruleEditor = true }
                            Text("A recurring rule replaces older imported availability for the same room/person. Imported classroom occupancy remains effective unless you add a replacement classroom rule or a specific no-classes exception.").font(.caption)
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                    }
                    GroupBox("Daily exceptions") {
                        VStack(alignment:.leading,spacing:10) {
                            ForEach(record.exceptions) { e in
                                HStack { Text(e.day + " • " + scheduleKind(e.kind) + " • " + e.name + " • " + (e.closed ? "unavailable / no classes" : scheduleTime(e.start_time ?? "") + "–" + scheduleTime(e.end_time ?? "")));Spacer();Button("Edit") { exception = e;exceptionEditor = true };Button("Remove exception") { self.record?.exceptions.removeAll { $0.id == e.id };dirty = true } }
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
                }
            }.padding(24).disabled(busy)
        }.task { comparisonDate = Date(); await load() }
        .onChange(of:scheduleView) { _ in comparisonDate = Date() }
        .sheet(isPresented:$ruleEditor) { ruleForm }
        .sheet(isPresented:$personEditor) { personForm }
        .sheet(isPresented:$exceptionEditor) { exceptionForm }
    }
    private func moveComparisonDay(_ amount: Int) {
        var calendar = Calendar(identifier:.gregorian)
        calendar.timeZone = TimeZone(identifier:"America/Chicago")!
        comparisonDate = calendar.date(byAdding:.day,value:amount,to:comparisonDate)!
    }
    private var ruleForm: some View {
        VStack(alignment:.leading,spacing:12) {
            Text("Recurring schedule").font(.title2.bold())
            Picker("Kind",selection:$rule.kind) { Text("My work hours").tag("work");Text("Building access").tag("room");Text("Classroom occupied").tag("classroom_busy");Text("Staff shift").tag("staff_available") }
            TextField("Room, employee or course name",text:$rule.name)
            if rule.kind == "classroom_busy" { TextField("Room location",text:$rule.location) }
            HStack { TextField("First date YYYY-MM-DD",text:$rule.start_date);TextField("Last date YYYY-MM-DD",text:$rule.end_date) }
            HStack { ForEach(0..<7,id:\.self) { d in Toggle(weekdays[d],isOn:Binding(get:{rule.days.contains(d)},set:{ yes in if yes { rule.days.append(d) } else { rule.days.removeAll { $0 == d } } })).toggleStyle(.checkbox) } }
            HStack { ScheduleTimeField(title:"Start",value:$rule.start_time);ScheduleTimeField(title:"End",value:$rule.end_time) }
            TextField("Timezone",text:$rule.timezone)
            Text("Local times, including the final schedule date. Saving remains subject to validation.").font(.caption)
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
            if !exception.closed { HStack { ScheduleTimeField(title:"Replacement start",value:Binding(get:{exception.start_time ?? ""},set:{exception.start_time = $0}));ScheduleTimeField(title:"Replacement end",value:Binding(get:{exception.end_time ?? ""},set:{exception.end_time = $0})) } }
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
        }.task { day = integrationDay(0); if !store.offline { await find() } }
    }
}

// A dated overview of saved schedule facts. Feasibility remains the Plan API's job.
struct ScheduleWeekItem: Identifiable {
    var id: String; var time: String; var title: String; var detail: String; var kind: String
    var order: String
}

struct ScheduleWeekView: View {
    let record: ScheduleRecord
    let byRoom: Bool
    var comparisonDate: Date? = nil
    @State private var selected = ""
    @State private var anchor = Date()
    private var calendar: Calendar {
        var c = Calendar(identifier:.gregorian)
        c.timeZone = TimeZone(identifier:"America/Chicago")!
        c.firstWeekday = 2
        return c
    }
    private var week: [Date] {
        let start = calendar.startOfDay(for:anchor)
        let offset = (calendar.component(.weekday,from:start) + 5) % 7
        let monday = calendar.date(byAdding:.day,value:-offset,to:start)!
        return (0..<7).map { calendar.date(byAdding:.day,value:$0,to:monday)! }
    }
    private var displayedDates: [Date] { comparisonDate.map { [calendar.startOfDay(for:$0)] } ?? week }
    private func format(_ date: Date, _ pattern: String) -> String {
        let f = DateFormatter(); f.calendar = calendar; f.timeZone = calendar.timeZone
        f.locale = Locale(identifier:"en_US"); f.dateFormat = pattern
        return f.string(from:date)
    }
    private var choices: [String] {
        if byRoom {
            return Array(Set(record.rules.compactMap { r -> String? in
                r.kind == "room" ? r.name : r.kind == "classroom_busy" ? r.location : nil
            } + record.reservations.map(\.room) + record.exceptions.filter { ["room","classroom_busy"].contains($0.kind) }.map(\.name))).filter { !$0.isEmpty }.sorted()
        }
        return ["My work"] + Array(Set(record.people.map(\.name) + record.rules.filter { $0.kind == "staff_available" }.map(\.name))).filter { !$0.isEmpty && $0 != "My work" }.sorted()
    }
    private var selection: String { choices.contains(selected) ? selected : choices.first ?? "" }
    private func matching(_ kind: String, _ name: String, _ location: String = "") -> Bool {
        if byRoom { return kind == "room" && name == selection || kind == "classroom_busy" && location == selection }
        return selection == "My work" ? kind == "work" : kind == "staff_available" && name == selection
    }
    private func items(_ date: Date) -> [ScheduleWeekItem] {
        let day = format(date,"yyyy-MM-dd")
        let weekday = (calendar.component(.weekday,from:date) + 5) % 7
        let exceptions = record.exceptions.filter { e in
            e.day == day && (byRoom ? ["room","classroom_busy"].contains(e.kind) && e.name == selection : matching(e.kind,e.name))
        }
        var result = record.rules.filter { r in
            matching(r.kind,r.name,r.location) && r.start_date <= day && day <= r.end_date && r.days.contains(weekday)
                && !exceptions.contains { $0.kind == r.kind }
        }.map { r in
            ScheduleWeekItem(id:r.id,time:scheduleTime(r.start_time) + "–" + scheduleTime(r.end_time),title:scheduleKind(r.kind),detail:r.kind == "classroom_busy" ? r.name : r.timezone,kind:r.kind,order:r.start_time)
        }
        result += exceptions.map { e in
            ScheduleWeekItem(id:e.id,time:e.closed ? "All day" : scheduleTime(e.start_time ?? "") + "–" + scheduleTime(e.end_time ?? ""),title:e.closed ? (e.kind == "classroom_busy" ? "No classes" : "Unavailable / closed") : scheduleKind(e.kind),detail:e.note,kind:"exception",order:e.start_time ?? "00:00")
        }
        result += record.reservations.compactMap { r -> ScheduleWeekItem? in
            guard let start = providerDate(r.start), let end = providerDate(r.end),
                  (byRoom ? r.room == selection : selection == "My work" ? r.employee.isEmpty || r.uses_owner : r.employee == selection),
                  start < calendar.date(byAdding:.day,value:1,to:date)!, end > date else { return nil }
            return ScheduleWeekItem(id:r.id,time:format(start,"h:mm a") + "–" + format(end,"h:mm a"),title:"Planning hold",detail:byRoom ? (r.employee.isEmpty ? "My work" : r.employee) : r.room,kind:"hold",order:format(start,"HH:mm"))
        }
        return result.sorted { $0.order == $1.order ? $0.id < $1.id : $0.order < $1.order }
    }
    private func color(_ kind: String) -> Color {
        switch kind { case "classroom_busy":return .orange;case "hold":return .purple;case "exception":return .red;default:return .blue }
    }
    var body: some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {
                Picker(byRoom ? "Room" : "Person",selection:Binding(get:{selection},set:{selected = $0})) {
                    ForEach(choices,id:\.self) { Text($0).tag($0) }
                }.frame(maxWidth:320)
                Spacer()
                if comparisonDate == nil {
                Button("Previous week") { anchor = calendar.date(byAdding:.day,value:-7,to:anchor)! }
                Button("This week") { anchor = Date() }
                Button("Next week") { anchor = calendar.date(byAdding:.day,value:7,to:anchor)! }
                }
            }
            if comparisonDate == nil {
            DatePicker("Week containing",selection:$anchor,displayedComponents:.date).environment(\.timeZone,calendar.timeZone)
            Text(format(week[0],"MMM d") + " – " + format(week[6],"MMM d, yyyy") + " • America/Chicago").font(.headline)
            } else {
                Text(format(comparisonDate!,"EEEE MMM d, yyyy") + " • America/Chicago").font(.headline)
            }
            if !byRoom, let p = record.people.first(where: { $0.name == selection }) {
                Text(p.name + " • " + p.status + " • funded limit " + String(p.weekly_limit_minutes / 60) + "h/week").font(.headline)
                if !p.notes.isEmpty { Text(p.notes).foregroundStyle(.secondary) }
                if p.status != "active" { Text("Availability is unconfirmed; this person is excluded from confirmed capacity.").foregroundStyle(.orange) }
            }
            Text(byRoom ? "Blue: building access • Orange: classes (unavailable) • Purple: local holds • Red: daily exceptions" : "Blue: work hours • Purple: local holds • Red: daily exceptions").font(.caption)
            ScrollView(.horizontal) {
                HStack(alignment:.top,spacing:8) {
                    ForEach(displayedDates,id:\.self) { date in
                        VStack(alignment:.leading,spacing:8) {
                            Text(format(date,"EEE MMM d")).font(.headline)
                            let entries = items(date)
                            if entries.isEmpty { Text("No saved hours or events").font(.caption).foregroundStyle(.secondary) }
                            ForEach(entries) { item in
                                VStack(alignment:.leading,spacing:4) {
                                    Text(item.time).font(.headline).monospacedDigit()
                                    Text(item.title).font(.subheadline.bold())
                                    if !item.detail.isEmpty { Text(item.detail).font(.caption) }
                                }.frame(maxWidth:.infinity,alignment:.leading).padding(8)
                                    .background(color(item.kind).opacity(0.12)).overlay(alignment:.leading) { Rectangle().fill(color(item.kind)).frame(width:3) }
                                    .accessibilityElement(children:.combine)
                            }
                            Spacer(minLength:0)
                        }.padding(10).frame(width:comparisonDate == nil ? 170 : nil,alignment:.topLeading).frame(maxWidth:comparisonDate == nil ? nil : .infinity).frame(minHeight:230,alignment:.topLeading)
                            .background(Color.secondary.opacity(0.05)).clipShape(RoundedRectangle(cornerRadius:8))
                    }
                }.padding(.bottom,4)
            }
            Text("This overview shows saved schedules, not confirmed free time. Meetings, closures, capability and task blockers still need review. Use Plan to find a possible repair window.").font(.caption).foregroundStyle(.secondary)
            if let notice = record.reservation_notice, !notice.isEmpty { Text(notice).foregroundStyle(.orange) }
            if choices.isEmpty { Text("Add room schedules in List & edit to start this view.").foregroundStyle(.secondary) }
        }.onAppear { anchor = Date() }
    }
}
