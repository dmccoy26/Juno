import SwiftUI

struct PlanningWindow: Codable, Identifiable {
    var kind = "work"; var name = ""; var start: String; var end: String
    var id: String { kind + name + start + end }
}
struct PlanningFacts: Codable {
    var task_id: String
    var minutes: Int? = nil; var actual_minutes: Int? = nil
    var dean = false; var operational = false
    var room = ""; var employee = ""; var capability = ""; var independent = false; var supervision: Bool? = false
    var blocker = ""; var waiting_on = ""; var next_action = ""; var next_check: String? = nil; var resume = ""
}
struct PlanningRecord: Codable {
    var revision: Int; var workspace_id: String?; var reserve_minutes: Int; var priority_choice: String; var priority_choice_date: String?; var windows: [PlanningWindow]; var tasks: [PlanningFacts]
}
struct PlanningRequestField: Decodable, Identifiable {
    var key: String; var label: String; var state: String; var value: String?
    var origin: String?; var updated_at: String?; var source_updated_at: String?; var review_conflict: Bool?; var taskdock_flag: String?
    var id: String { key }
    var display: String { state == "none" ? "Explicitly none" : state == "provided" ? value ?? "Unknown" : "Not supplied / unknown" }
}
struct PlanningRequestQuestion: Decodable, Identifiable {
    var key: String; var label: String; var question: String
    var id: String { key }
}
struct PlanningTask: Decodable, Identifiable {
    var task_id: String; var title: String; var estimate_minutes: Int; var estimate_confirmed: Bool
    var estimate_reason: String; var missing: [String]; var actionable: Bool; var reason: String
    var blocker: String; var next_action: String; var next_check: String?; var resume: String; var employee: String
    var room: String; var room_hint: String?
    var request_fields: [PlanningRequestField]?; var request_questions: [PlanningRequestQuestion]?
    var due_date: String?; var priority_label: String?; var taskdock_saved_at: String?; var request_scope_notice: String?
    func requestField(_ key: String) -> PlanningRequestField? { request_fields?.first { $0.key == key } }
    var roomSummary: String {
        if !room.isEmpty { return room + " (confirmed in Juno)" }
        if let field = requestField("room") { return field.display }
        return room_hint.map { $0 + " (title suggestion; unconfirmed)" } ?? "Unknown"
    }
    var id: String { task_id }
}
struct StaffPlanningLoad: Decodable, Identifiable {
    var employee: String; var reported_assignment_minutes: Int; var unknown_estimates: Int; var blocked_tasks: Int; var available_minutes: Int?; var notice: String
    var id: String { employee }
}
struct PlanningResult: Decodable {
    var staff_loads: [StaffPlanningLoad]
    var capacity_minutes: Int; var free_minutes: Int; var reserve_minutes: Int
    var question: String?; var recommended_task_id: String?; var tasks: [PlanningTask]; var notices: [String]; var notice: String
}
struct WeeklyPlanningDraft: Decodable { var text: String; var notices: [String] }

func planningInputIssue(estimate: String,actual: String,check: String) -> String? {
    let e = estimate.trimmingCharacters(in:.whitespacesAndNewlines),a = actual.trimmingCharacters(in:.whitespacesAndNewlines)
    if !e.isEmpty && (Int(e) == nil || !(5...2400).contains(Int(e)!)) { return "Use an estimate of 5–2,400 minutes, or leave it blank if unknown." }
    if !a.isEmpty && (Int(a) == nil || !(0...10000).contains(Int(a)!)) { return "Use actual minutes from 0–10,000, or leave them blank." }
    if !check.isEmpty {
        let f = DateFormatter();f.locale = Locale(identifier:"en_US_POSIX");f.timeZone = TimeZone(identifier:"America/Chicago");f.dateFormat = "yyyy-MM-dd";f.isLenient = false
        guard let date = f.date(from:check),f.string(from:date) == check else { return "Use YYYY-MM-DD for the next blocker check, or leave it blank." }
    }
    return nil
}

struct PlanningWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var record: PlanningRecord?
    @State private var plan: PlanningResult?
    @State private var issue: String?
    @State private var busy = false
    @State private var dirty = false
    @State private var day = Date()
    @State private var windowKind = "work"
    @State private var windowName = ""
    @State private var windowStart = Date()
    @State private var windowEnd = Date().addingTimeInterval(3600)
    @State private var selected: String?
    @State private var facts = PlanningFacts(task_id: "")
    @State private var estimate = ""
    @State private var actual = ""
    @State private var checkDate = ""
    @State private var weekly = ""
    @State private var estimateSuggestion: TaskEstimate?
    @State private var taskSearch = ""
    @State private var editorIssue: String?
    @State private var estimateTask: Task<Void,Never>?
    @State private var estimating = false
    @State private var taskFilter = "All issues"
    @State private var guided = false
    @State private var guideStep = 0
    private func dateString(_ date: Date) -> String {
        let f = DateFormatter(); f.timeZone = TimeZone(identifier: "America/Chicago"); f.dateFormat = "yyyy-MM-dd"; return f.string(from: date)
    }
    private func object<T: Encodable>(_ value: T) throws -> [String: Any] {
        try JSONSerialization.jsonObject(with: JSONEncoder().encode(value)) as! [String: Any]
    }
    private func load() async {
        plan = nil
        busy = true; defer { busy = false }
        do {
            let fresh = try await store.decode(PlanningRecord.self, "/v1/planning")
            record = fresh; dirty = false; selected = nil
            if store.offline { plan = nil; issue = "Saved planning facts are available offline. Reconnect to calculate recommendations or save planning changes. Diary and memory edits still work offline."; return }
            plan = try await store.decode(PlanningResult.self, "/v1/planning/next?day=" + dateString(day)); issue = nil
            if let wanted = store.planningTaskID, let task = plan?.tasks.first(where: { $0.id == wanted }) { choose(task); store.planningTaskID = nil }
        } catch { issue = (error as? APIProblem)?.message ?? "Could not load planning. Your changes remain here." }
    }
    private func save() async {
        guard let record else { return }
        busy = true; defer { busy = false }
        do {
            var body = try object(record); body.removeValue(forKey: "revision"); body["expected_revision"] = record.revision
            self.record = try await store.decode(PlanningRecord.self, "/v1/planning", method: "PUT", body: body)
            dirty = false
            plan = nil
            plan = try await store.decode(PlanningResult.self, "/v1/planning/next?day=" + dateString(day))
            issue = "Saved. Recommendations use these confirmed planning facts."
        } catch { issue = (error as? APIProblem)?.message ?? "Could not save planning. Your changes remain here." }
    }
    private func choose(_ task: PlanningTask, guidedMode: Bool = false) {
        guided = guidedMode;guideStep = 0
        selected = task.id
        editorIssue = nil
        estimateSuggestion = nil
        facts = record?.tasks.first { $0.task_id == task.id } ?? PlanningFacts(task_id: task.id)
        estimate = facts.minutes.map(String.init) ?? ""
        actual = facts.actual_minutes.map(String.init) ?? ""
        checkDate = facts.next_check ?? ""
    }
    private func applyFacts() -> Bool {
        if let problem = planningInputIssue(estimate:estimate,actual:actual,check:checkDate) { editorIssue = problem;return false }
        facts.minutes = Int(estimate.trimmingCharacters(in:.whitespacesAndNewlines))
        facts.actual_minutes = Int(actual.trimmingCharacters(in:.whitespacesAndNewlines));facts.next_check = checkDate.isEmpty ? nil : checkDate
        record?.tasks.removeAll { $0.task_id == facts.task_id }; record?.tasks.append(facts)
        dirty = true; issue = "Task planning details added to your draft. Save planning to use them."
        return true
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("What should I do next?").font(.title2.bold())
                Text("Confirm your work windows and task details. Juno checks constraints before suggesting a next task. TaskDock remains your task hub.").foregroundStyle(.secondary)
                HStack {
                    DatePicker("Seven days starting", selection: $day, displayedComponents: .date)
                    Button("Reload saved planning") { Task { await load() } }.disabled(busy || dirty)
                    Button("Save planning") { Task { await save() } }.disabled(busy || !dirty || store.offline)
                    if busy { ProgressView().controlSize(.small) }
                }
                if dirty { HStack { Text("Unsaved planning changes").foregroundStyle(.orange); Button("Discard draft and reload") { Task { await load() } } } }
                if let issue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                RepairWindowsView(store: store, tasks: plan?.tasks ?? [], workspace: record?.workspace_id)
                if let record {
                    DisclosureGroup("Legacy dated availability (\(record.windows.count) windows)") {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Times use this Mac’s timezone. Enter individual days, room access and staff availability. Missing hours mean unknown availability.").font(.caption)
                            HStack {
                                Text("Interruption reserve, minutes per seven days")
                                Stepper("\(record.reserve_minutes)", value: Binding(get: { self.record?.reserve_minutes ?? 240 }, set: { self.record?.reserve_minutes = $0; dirty = true }), in: 0...2400, step: 30)
                            }
                            ForEach(Array(record.windows.enumerated()), id: \.offset) { index, w in
                                HStack {
                                    Text("\(w.kind): \(w.name)  \(w.start) → \(w.end)").font(.caption).textSelection(.enabled)
                                    Spacer(); Button("Remove") { self.record?.windows.remove(at: index); dirty = true }
                                }
                            }
                            HStack {
                                Picker("Window", selection: $windowKind) { Text("My work").tag("work"); Text("Room access").tag("room"); Text("Staff available").tag("staff") }.frame(width: 220)
                                if windowKind != "work" { TextField("Exact room or employee name", text: $windowName) }
                            }
                            DatePicker("Start", selection: $windowStart)
                            DatePicker("End", selection: $windowEnd)
                            Button("Add confirmed window") {
                                guard windowEnd > windowStart, windowEnd.timeIntervalSince(windowStart) <= 86400, windowKind == "work" || !windowName.trimmingCharacters(in: .whitespaces).isEmpty else { issue = "Choose an end after the start, within 24 hours, and a room or employee name where required."; return }
                                let f = ISO8601DateFormatter()
                                self.record?.windows.append(PlanningWindow(kind: windowKind, name: windowName.trimmingCharacters(in: .whitespaces), start: f.string(from: windowStart), end: f.string(from: windowEnd)))
                                dirty = true
                            }.disabled(store.offline)
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(6)
                    }
                }
                if let plan, !dirty, !busy {
                    Text("\(plan.capacity_minutes) minutes to plan • \(plan.free_minutes) after recorded meetings • \(plan.reserve_minutes) reserved for interruptions").font(.headline)
                    if let question = plan.question { Text("Before I choose: " + question).font(.headline).foregroundStyle(.purple); Text("Discuss it in Chat, or confirm which priority should lead for this planning date.").font(.caption)
                        HStack {
                            ForEach(plan.tasks.filter { $0.reason == "Dean request" || $0.reason == "Teaching/operations need" }.prefix(4)) { task in
                                Button("Prioritize: " + task.title) { record?.priority_choice = task.id; record?.priority_choice_date = dateString(day); dirty = true }
                            }
                        } }
                    HStack {
                        TextField("Find an issue from TaskDock", text: $taskSearch).textFieldStyle(.roundedBorder)
                        Picker("Show",selection:$taskFilter) { Text("All issues").tag("All issues");Text("Needs details").tag("Needs details");Text("Blocked").tag("Blocked");Text("Ready to review").tag("Ready to review") }.frame(width:210)
                    }
                    Button("Refresh tasks in TaskDock connection") { store.section = "TaskDock" }
                    ForEach(plan.tasks.filter { (taskSearch.isEmpty || $0.title.localizedCaseInsensitiveContains(taskSearch)) && (taskFilter == "All issues" || taskFilter == "Needs details" && (!$0.missing.isEmpty || !($0.request_questions ?? []).isEmpty) || taskFilter == "Blocked" && !$0.blocker.isEmpty || taskFilter == "Ready to review" && $0.actionable) }) { task in
                        GroupBox {
                            VStack(alignment: .leading, spacing: 6) {
                                HStack { Text(task.title).font(.headline); if plan.recommended_task_id == task.id { Text("Suggested next").foregroundStyle(.green) }; Spacer(); Button("Discuss estimate") {
                                    store.chatDraft = "Help me estimate this task from the saved evidence: “" + task.title + "”. Give a range and explain the uncertainty. Ask one scope question if needed. Do not change my confirmed estimate; I will review and enter it in Plan."
                                    store.section = "Chat"
                                }; Button("Clarify with Juno") { choose(task,guidedMode:true) }; Button("Planning details") { choose(task) } }
                                PlanningRequestOverview(task:task) { question in
                                    store.chatDraft = "Help me clarify “" + task.title + "”. Start with this question: “" + question.question + "” Ask me one question at a time."
                                    store.section = "Chat"
                                }
                                Text("\(task.estimate_minutes) min • \(task.reason)")
                                Text(task.estimate_reason).font(.caption).foregroundStyle(.secondary)
                                if !task.missing.isEmpty { DisclosureGroup("\(task.missing.count) details to confirm") { ForEach(task.missing,id:\.self) { Text($0).font(.caption).foregroundStyle(.orange) } } }
                                if !task.next_action.isEmpty { Text("Unblock: " + task.next_action) }
                                if let check = task.next_check { Text("Next blocker check: " + check).font(.caption) }
                                if !task.resume.isEmpty { Text("Resume: " + task.resume) }
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                        ForEach(plan.staff_loads) { load in
                        GroupBox(load.employee + " — supplied workload") {
                            VStack(alignment: .leading) {
                                Text("\(load.reported_assignment_minutes) estimated assignment minutes • \(load.unknown_estimates) unestimated • \(load.blocked_tasks) blocked")
                                Text(load.available_minutes.map { "\($0) minutes of recorded availability" } ?? "Availability unknown")
                                Text(load.notice).font(.caption).foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    DisclosureGroup("Source details & limits") { VStack(alignment: .leading) { ForEach(plan.notices, id: \.self) { Text($0).font(.caption) }; Text(plan.notice).font(.caption) }.frame(maxWidth: .infinity, alignment: .leading) }
                }

                Divider()
                Text("End-of-day continuity").font(.headline)
                Text("Use Daily check-in for the five-question interview: accomplishments, interruptions, blockers, employee contributions and tomorrow. Aim for about 15 minutes; drafts survive interruptions.")
                Button("Open daily check-in") { store.section = "Check-in" }
                HStack {
                    Text("Dean update for the selected seven-day period").font(.headline)
                    Button("Prepare draft") {
                        Task {
                            busy = true; defer { busy = false }
                            do { let draft = try await store.decode(WeeklyPlanningDraft.self, "/v1/planning/weekly?day=" + dateString(day)); weekly = draft.text }
                            catch { issue = (error as? APIProblem)?.message ?? "Reconnect to prepare a weekly draft." }
                        }
                    }.disabled(busy || store.offline)
                }
                if !weekly.isEmpty {
                    TextEditor(text: $weekly).frame(minHeight: 220)
                    Text("Editable session draft. Copy it before leaving this screen; Juno does not send it.").font(.caption)
                    Button("Copy reviewed draft") { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(weekly, forType: .string) }
                }
            }.padding(24).disabled(busy)
        }.environment(\.locale,Locale(identifier:"en_US"))
        .task { day = Date(); await load() }
        .sheet(isPresented: Binding(get:{ selected != nil },set:{ if !$0 { selected = nil } }),onDismiss:{ estimateTask?.cancel();estimating = false }) {
            VStack(alignment:.leading,spacing:0) {
                HStack { VStack(alignment:.leading) { Text("Task planning details").font(.title2.bold());Text(plan?.tasks.first { $0.id == selected }?.title ?? "Review your task context").foregroundStyle(.secondary).lineLimit(2) };Spacer() }.padding(20)
                Divider()
                HStack { Text(guided ? "One question at a time" : "All task details").font(.caption).foregroundStyle(.secondary);Spacer();Button(guided ? "Show all fields" : "Guide me through this") { guided.toggle();guideStep = 0 } }.padding(.horizontal,20).padding(.vertical,8)
                ScrollView { if guided { guidedEditor.padding(20) } else { editor.padding(18) } }
                if let editorIssue { Text(editorIssue).foregroundStyle(.orange).padding(.horizontal,20).padding(.vertical,8) }
                Divider()
                HStack {
                    Button("Cancel",role:.cancel) { estimateTask?.cancel();estimating = false;selected = nil }.keyboardShortcut(.cancelAction)
                    Spacer()
                    if guided && guideStep > 0 { Button("Back") { guideStep -= 1 } }
                    if guided && guideStep < 5 { Button("Next") { guideStep += 1 } }
                    Button("Apply to draft") { if applyFacts() { estimateTask?.cancel();estimating = false;selected = nil } }.keyboardShortcut(.defaultAction).disabled(store.offline || estimating || (guided && guideStep < 5))
                }.padding(18)
            }.frame(width:700,height:620)
        }
        .onChange(of: day) { _ in if !dirty { Task { await load() } } }
    }
    private var guidedEditor: some View {
        VStack(alignment:.leading,spacing:16) {
            Text(guideStep < 5 ? "Question \(guideStep + 1) of 5" : "Review your answers").font(.caption).foregroundStyle(.secondary)
            switch guideStep {
            case 0:
                Text("How much working time might this take?").font(.title3.bold())
                TextField("Estimated minutes — leave blank if unknown",text:$estimate).textFieldStyle(.roundedBorder)
                Text("Use your best reviewed estimate. You can revise it later; blank stays unknown.").foregroundStyle(.secondary)
            case 1:
                Text("Which room needs the work?").font(.title3.bold())
                TextField("Room — leave blank if not room-related or unknown",text:$facts.room).textFieldStyle(.roundedBorder)
                if let hint = plan?.tasks.first(where: { $0.id == selected })?.room_hint { Button("Use suggested room: " + hint) { facts.room = hint };Text("Confirm that the suggested room is correct before applying it.").font(.caption) }
            case 2:
                Text("Who might handle this task?").font(.title3.bold())
                TextField("Possible employee — leave blank if not confirmed",text:$facts.employee).textFieldStyle(.roundedBorder)
                Text("This records a planning detail; it does not assign or notify anyone.").foregroundStyle(.secondary)
            case 3:
                Text("What support would that person need?").font(.title3.bold())
                TextField("Relevant experience or training",text:$facts.capability).textFieldStyle(.roundedBorder)
                Toggle("Confirmed able to work independently",isOn:$facts.independent)
                Toggle("Needs my supervision / collaboration",isOn:Binding(get:{facts.supervision ?? false},set:{facts.supervision = $0}))
                Text("Leave both unchecked when capability is unknown.").foregroundStyle(.secondary)
            case 4:
                Text("What could prevent this from getting done?").font(.title3.bold())
                TextField("Blocker — parts, approval, research or access",text:$facts.blocker).textFieldStyle(.roundedBorder)
                TextField("Waiting on whom or what?",text:$facts.waiting_on).textFieldStyle(.roundedBorder)
                TextField("Next step to unblock it",text:$facts.next_action).textFieldStyle(.roundedBorder)
                Text("Blank means nothing recorded; it does not confirm that there are no blockers.").foregroundStyle(.secondary)
            default:
                Text("Nothing has been saved yet.").font(.headline)
                Text("Estimate: " + (estimate.isEmpty ? "Unknown" : estimate + " minutes"))
                Text("Room: " + (facts.room.isEmpty ? "Not confirmed" : facts.room))
                Text("Person: " + (facts.employee.isEmpty ? "Not confirmed" : facts.employee))
                Text("Support: " + (facts.supervision == true ? "Supervision needed" : facts.independent ? "Confirmed independent" : "Not confirmed"))
                if !facts.capability.isEmpty { Text("Experience / training: " + facts.capability) }
                Text("Blocker: " + (facts.blocker.isEmpty ? "None recorded" : facts.blocker))
                if !facts.waiting_on.isEmpty { Text("Waiting on: " + facts.waiting_on) }
                if !facts.next_action.isEmpty { Text("Next action: " + facts.next_action) }
                Text("Apply adds these answers to your planning draft. Save planning on the main screen to persist them. Cancel leaves the existing draft untouched.").foregroundStyle(.secondary)
            }
        }.frame(maxWidth:.infinity,alignment:.leading)
    }

    private var editor: some View {
        GroupBox("Time & priority") {
            VStack(alignment: .leading, spacing: 10) {
                HStack { TextField("Estimate (minutes)", text: $estimate); TextField("Actual work (minutes, optional)", text: $actual) }
                Button("Suggest a duration range") {
                    let taskID = facts.task_id;estimating = true;editorIssue = nil
                    estimateTask = Task { defer { estimating = false };do {
                        let suggestion = try await store.decode(TaskEstimate.self,"/v1/planning/estimate",method:"POST",body:["task_id":taskID,"model_assist":true])
                        if !Task.isCancelled && selected == taskID { estimateSuggestion = suggestion }
                    } catch { if !Task.isCancelled && selected == taskID { editorIssue = (error as? APIProblem)?.message ?? "Could not estimate. Your saved duration is unchanged." } } }
                }.disabled(estimating || store.offline)
                if estimating { ProgressView("Estimating…").controlSize(.small) }
                if let suggestion = estimateSuggestion {
                    Text("\(suggestion.minimum)–\(suggestion.maximum) minutes • " + suggestion.source).font(.headline)
                    Text(suggestion.reason);if !suggestion.question.isEmpty { Text(suggestion.question).foregroundStyle(.purple) }
                    if let notice = suggestion.model_notice { Text(notice).font(.caption).foregroundStyle(.orange) }
                    Button("Use midpoint in this draft") { estimate = String((suggestion.minimum + suggestion.maximum)/2) }
                    Text(suggestion.notice).font(.caption)
                }
                Toggle("Dean request", isOn: $facts.dean)
                Toggle("Teaching or operations need", isOn: $facts.operational)
                Divider()
                Text("Room & person").font(.headline)
                TextField("Room needing confirmed access", text: $facts.room)
                if let hint = plan?.tasks.first(where: { $0.id == selected })?.room_hint { Button("Use suggested room: " + hint) { facts.room = hint } }
                TextField("Possible employee", text: $facts.employee)
                TextField("Confirmed relevant experience / capability", text: $facts.capability)
                Toggle("I confirm this employee can do this independently", isOn: $facts.independent)
                Toggle("Needs my supervision / collaboration", isOn: Binding(get:{facts.supervision ?? false},set:{facts.supervision = $0}))
                Divider()
                Text("Blockers & next steps").font(.headline)
                TextField("Blocker / dependency (parts, approval, bill, research…)", text: $facts.blocker)
                TextField("Waiting on whom or what?", text: $facts.waiting_on)
                TextField("Next unblocking action", text: $facts.next_action)
                TextField("Next check date, YYYY-MM-DD (optional)", text: $checkDate)
                TextField("Where we stopped and how to resume", text: $facts.resume)
                Button("Remove saved details from draft",role:.destructive) { record?.tasks.removeAll { $0.task_id == facts.task_id }; selected = nil; dirty = true }.disabled(store.offline)
                Text("Apply updates Juno’s draft only. Save planning on the main screen to persist changes.").font(.caption).foregroundStyle(.secondary)
            }.padding(6)
        }
    }
}


struct PlanningRequestOverview: View {
    let task: PlanningTask
    let clarify: (PlanningRequestQuestion) -> Void
    private func due(_ raw: String?) -> String {
        guard let raw, !raw.isEmpty else { return "Unknown / not supplied" }
        let day = String(raw.prefix(10));let parser = DateFormatter();parser.locale = Locale(identifier:"en_US_POSIX");parser.timeZone = TimeZone(identifier:"America/Chicago");parser.dateFormat = "yyyy-MM-dd";parser.isLenient = false
        guard let date = parser.date(from:day),parser.string(from:date) == day else { return raw }
        parser.dateFormat = "EEE, MMM d, yyyy";return parser.string(from:date)
    }
    var body: some View {
        VStack(alignment:.leading,spacing:8) {
            ViewThatFits(in:.horizontal) {
                HStack(alignment:.top,spacing:28) { location;priority }.frame(maxWidth:.infinity,alignment:.leading)
                VStack(alignment:.leading,spacing:8) { location;priority }
            }
            Text("Impact: " + (task.requestField("impact")?.display ?? "Unknown / not shared"))
            Text("Blockers: " + (task.blocker.isEmpty ? task.requestField("blockers")?.display ?? "None recorded; not confirmed clear" : task.blocker)).foregroundStyle(task.blocker.isEmpty ? Color.secondary : Color.orange)
            if let question = task.request_questions?.first {
                HStack(alignment:.top) {
                    VStack(alignment:.leading,spacing:3) {
                        Text("Next detail to clarify").font(.caption.bold()).foregroundStyle(.secondary)
                        Text(question.question)
                    }
                    Spacer()
                    Button("Discuss this detail") { clarify(question) }
                }.padding(10).background(Color.purple.opacity(0.08),in:RoundedRectangle(cornerRadius:8))
                Text("Opens a chat draft. Answers stay in chat; update TaskDock or save confirmed planning details to reuse them.").font(.caption).foregroundStyle(.secondary)
            }
            DisclosureGroup("Request details & source") {
                VStack(alignment:.leading,spacing:10) {
                    if let notice = task.request_scope_notice { Text(notice).font(.caption).foregroundStyle(.secondary) }
                    if let stamp = task.taskdock_saved_at { Text("TaskDock copy saved: " + scheduleDate(stamp)).font(.caption).foregroundStyle(.secondary) }
                    ForEach(task.request_fields ?? []) { field in
                        VStack(alignment:.leading,spacing:2) {
                            Text(field.label + ": " + field.display)
                            if let source = field.origin { Text("Source: " + source).font(.caption).foregroundStyle(.secondary) }
                            if let stamp = field.source_updated_at ?? field.updated_at { Text("Observed: " + scheduleDate(stamp)).font(.caption).foregroundStyle(.secondary) }
                            if field.review_conflict == true { Text("Conflicts with TaskDock’s blocked flag; review before planning.").font(.caption).foregroundStyle(.orange) }
                            if let flag = field.taskdock_flag { Text("TaskDock flag: " + flag).font(.caption).foregroundStyle(.orange) }
                        }
                    }
                    Text("These are request facts. Duration, capability, supervision and room access still need review.").font(.caption).foregroundStyle(.secondary)
                }.padding(.top,6).frame(maxWidth:.infinity,alignment:.leading)
            }
        }.textSelection(.enabled)
    }
    private var location: some View { Text("Room: " + task.roomSummary).frame(maxWidth:.infinity,alignment:.leading) }
    private var priority: some View { VStack(alignment:.leading,spacing:4) { Text("Priority: " + (task.priority_label ?? "Unknown"));Text("Due: " + due(task.due_date)) }.frame(maxWidth:.infinity,alignment:.leading) }
}
