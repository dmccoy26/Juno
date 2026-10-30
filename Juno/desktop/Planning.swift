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
struct PlanningTask: Decodable, Identifiable {
    var task_id: String; var title: String; var estimate_minutes: Int; var estimate_confirmed: Bool
    var estimate_reason: String; var missing: [String]; var actionable: Bool; var reason: String
    var blocker: String; var next_action: String; var next_check: String?; var resume: String; var employee: String
    var room: String; var room_hint: String?
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
    private func choose(_ task: PlanningTask) {
        selected = task.id
        estimateSuggestion = nil
        facts = record?.tasks.first { $0.task_id == task.id } ?? PlanningFacts(task_id: task.id)
        estimate = facts.minutes.map(String.init) ?? ""
        actual = facts.actual_minutes.map(String.init) ?? ""
        checkDate = facts.next_check ?? ""
    }
    private func applyFacts() {
        guard !estimate.isEmpty, let minutes = Int(estimate), (5...2400).contains(minutes),
              actual.isEmpty || (Int(actual) != nil && (0...10000).contains(Int(actual)!)) else {
            issue = "Enter an estimate of 5–2,400 minutes and optional actual minutes of 0–10,000."; return
        }
        if !checkDate.isEmpty {
            let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd"; formatter.isLenient = false
            guard let parsed = formatter.date(from: checkDate), formatter.string(from: parsed) == checkDate else { issue = "Use YYYY-MM-DD for the next blocker check, or leave it blank."; return }
        }
        facts.minutes = minutes; facts.actual_minutes = Int(actual); facts.next_check = checkDate.isEmpty ? nil : checkDate
        record?.tasks.removeAll { $0.task_id == facts.task_id }; record?.tasks.append(facts)
        dirty = true; issue = "Task planning details added to your draft. Save planning to use them."
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
                    TextField("Find an issue from TaskDock", text: $taskSearch)
                    Button("Refresh tasks in TaskDock connection") { store.section = "TaskDock" }
                    ForEach(plan.tasks.filter { taskSearch.isEmpty || $0.title.localizedCaseInsensitiveContains(taskSearch) }) { task in
                        GroupBox {
                            VStack(alignment: .leading, spacing: 6) {
                                HStack { Text(task.title).font(.headline); if plan.recommended_task_id == task.id { Text("Suggested next").foregroundStyle(.green) }; Spacer(); Button("Discuss estimate") {
                                    store.chatDraft = "Help me estimate this task from the saved evidence: “" + task.title + "”. Give a range and explain the uncertainty. Ask one scope question if needed. Do not change my confirmed estimate; I will review and enter it in Plan."
                                    store.section = "Chat"
                                }; Button("Planning details") { choose(task) } }
                                Text("\(task.estimate_minutes) min • \(task.reason)")
                                Text(task.estimate_reason).font(.caption).foregroundStyle(.secondary)
                                ForEach(task.missing, id: \.self) { Text($0).font(.caption).foregroundStyle(.orange) }
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
                    GroupBox("Source limits") { VStack(alignment: .leading) { ForEach(plan.notices, id: \.self) { Text($0).font(.caption) }; Text(plan.notice).font(.caption) }.frame(maxWidth: .infinity, alignment: .leading) }
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
        }.task { await load() }
        .sheet(isPresented: Binding(get:{ selected != nil },set:{ if !$0 { selected = nil } })) { ScrollView { editor }.padding(20).frame(width:760,height:760) }
        .onChange(of: day) { _ in if !dirty { Task { await load() } } }
    }
    private var editor: some View {
        GroupBox("Task planning details — your confirmed context") {
            VStack(alignment: .leading, spacing: 10) {
                HStack { TextField("Estimate (minutes)", text: $estimate); TextField("Actual work (minutes, optional)", text: $actual) }
                Button("Suggest a duration range") {
                    busy = true
                    Task { defer { busy = false };do { estimateSuggestion = try await store.decode(TaskEstimate.self,"/v1/planning/estimate",method:"POST",body:["task_id":facts.task_id,"model_assist":true]) } catch { issue = (error as? APIProblem)?.message ?? "Could not estimate. Your saved duration is unchanged." } }
                }.disabled(busy || store.offline)
                if let suggestion = estimateSuggestion {
                    Text("\(suggestion.minimum)–\(suggestion.maximum) minutes • " + suggestion.source).font(.headline)
                    Text(suggestion.reason);if !suggestion.question.isEmpty { Text(suggestion.question).foregroundStyle(.purple) }
                    if let notice = suggestion.model_notice { Text(notice).font(.caption).foregroundStyle(.orange) }
                    Button("Use midpoint in this draft") { estimate = String((suggestion.minimum + suggestion.maximum)/2) }
                    Text(suggestion.notice).font(.caption)
                }
                Toggle("Dean request", isOn: $facts.dean)
                Toggle("Teaching or operations need", isOn: $facts.operational)
                TextField("Room needing confirmed access", text: $facts.room)
                if let hint = plan?.tasks.first(where: { $0.id == selected })?.room_hint { Button("Use room suggested by task title: " + hint) { facts.room = hint } }
                TextField("Possible employee", text: $facts.employee)
                TextField("Confirmed relevant experience / capability", text: $facts.capability)
                Toggle("I confirm this employee can do this independently", isOn: $facts.independent)
                Toggle("Needs my supervision / collaboration", isOn: Binding(get:{facts.supervision ?? false},set:{facts.supervision = $0}))
                TextField("Blocker / dependency (parts, approval, bill, research…)", text: $facts.blocker)
                TextField("Waiting on whom or what?", text: $facts.waiting_on)
                TextField("Next unblocking action", text: $facts.next_action)
                TextField("Next check date, YYYY-MM-DD (optional)", text: $checkDate)
                TextField("Where we stopped and how to resume", text: $facts.resume)
                Button("Apply details to planning draft") { applyFacts(); if dirty { selected = nil } }.disabled(store.offline)
                Button("Remove these planning details") { record?.tasks.removeAll { $0.task_id == facts.task_id }; selected = nil; dirty = true }.disabled(store.offline)
                Text("Missing employee updates are not evidence of poor performance. Reported minutes do not measure intelligence or skill.").font(.caption).foregroundStyle(.secondary)
            }.padding(6)
        }
    }
}
