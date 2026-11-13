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
    var operational_reasons:[String]?
    var dean: Bool?
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
    var employee: String; var reported_assignment_minutes: Int; var unknown_estimates: Int; var blocked_tasks: Int; var available_minutes: Int?; var weekly_limit_minutes: Int?; var notice: String
    var id: String { employee }
}
struct ProposedAllocationBlock:Decodable,Identifiable {var task_id:String;var title:String;var employee:String;var room:String;var start:String;var end:String;var minutes:Int;var id:String{task_id}}
struct AllocationProposal:Decodable {var blocks:[ProposedAllocationBlock];var notice:String}
struct PlanningResult: Decodable {
    var allocation_proposal:AllocationProposal?
    var staff_loads: [StaffPlanningLoad]
    var capacity_minutes: Int; var free_minutes: Int; var reserve_minutes: Int
    var question: String?; var recommended_task_id: String?; var tasks: [PlanningTask]; var notices: [String]; var notice: String
}
struct OperationalSourceBasis: Codable, Equatable {
    var taskdock_snapshot:String?;var workspace_id:String?;var beacon_snapshot:String?;var beacon_error:String?
    var taskdock_stale:Bool;var beacon_stale:Bool;var operations_revision:Int;var planning_revision:Int
    enum CodingKeys:String,CodingKey {case taskdock_snapshot,workspace_id,beacon_snapshot,beacon_error,taskdock_stale,beacon_stale,operations_revision,planning_revision}
    func encode(to encoder:Encoder)throws {var c=encoder.container(keyedBy:CodingKeys.self);try c.encode(taskdock_snapshot,forKey:.taskdock_snapshot);try c.encode(workspace_id,forKey:.workspace_id);try c.encode(beacon_snapshot,forKey:.beacon_snapshot);try c.encode(beacon_error,forKey:.beacon_error);try c.encode(taskdock_stale,forKey:.taskdock_stale);try c.encode(beacon_stale,forKey:.beacon_stale);try c.encode(operations_revision,forKey:.operations_revision);try c.encode(planning_revision,forKey:.planning_revision)}
}
struct WeeklyDiaryBasis: Codable, Equatable { var id:String; var revision:Int; var day:String }
struct DeanMeetingWindow: Codable, Equatable {
    let previous:String;let meeting:String;let prepared:String;let previous_confirmed:Bool
}
struct CompletionArchiveBasis: Codable, Equatable {
    let snapshot_id: String
    let available: Bool
    let uncertain: Bool
}
struct WeeklyBasis: Codable, Equatable {
    var operations_basis:OperationalSourceBasis?
    var meeting_window:DeanMeetingWindow?
    var completion_archive: CompletionArchiveBasis?
    var diaries:[WeeklyDiaryBasis]; var snapshot_id:String?; var workspace_id:String?; var taskdock_saved_at:String?; var planning_revision:Int;var taskdock_uncertain:Bool
    enum CodingKeys:String,CodingKey { case meeting_window,completion_archive,operations_basis,diaries,snapshot_id,workspace_id,taskdock_saved_at,planning_revision,taskdock_uncertain }
    func encode(to encoder:Encoder) throws { var c=encoder.container(keyedBy:CodingKeys.self);try c.encodeIfPresent(meeting_window,forKey:.meeting_window);try c.encodeIfPresent(completion_archive,forKey:.completion_archive);try c.encode(operations_basis,forKey:.operations_basis);try c.encode(diaries,forKey:.diaries);try c.encode(snapshot_id,forKey:.snapshot_id);try c.encode(workspace_id,forKey:.workspace_id);try c.encode(taskdock_saved_at,forKey:.taskdock_saved_at);try c.encode(planning_revision,forKey:.planning_revision);try c.encode(taskdock_uncertain,forKey:.taskdock_uncertain) }
}
struct WeeklyPlanningDraft: Decodable { var text:String; var notices:[String]; var basis:WeeklyBasis; var missing_diary_dates:[String] }
struct SavedDeanDraft: Decodable {
    var owner_id:String;var week_start:String;var exists:Bool;var id:String?;var text:String;var revision:Int;var basis:WeeklyBasis;var sources_changed:Bool;var updated_at:String?;var notice:String
}
struct DeanSaveReceipt: Decodable { var id:String;var revision:Int;var saved_at:String }


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

struct PlanningSourceChange:Decodable,Identifiable {let key:String;let label:String;let before:String;let after:String;var id:String{key}}
struct PlanningDiarySource:Decodable,Identifiable {let operation_id:String;let diary_day:String;let diary_revision:Int;let source_quote:String;let source_changed:Bool;let rows:[PlanningSourceChange];var id:String{operation_id}}
struct PlanningDiarySources:Decodable {let items:[PlanningDiarySource]}

struct PlanningWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var loadIdentity = UUID()
    @State private var planningSources:PlanningDiarySources?
    @State private var sourceIssue:String?
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
    @State private var showDeanDraft = false
    @State private var estimateSuggestion: TaskEstimate?
    @State private var taskSearch = ""
    @FocusState private var searchFocused:Bool
    @State private var editorIssue: String?
    @State private var estimateTask: Task<Void,Never>?
    @State private var estimating = false
    private enum Page: String, CaseIterable, Identifiable {
        case week = "Week", issues = "Issues", scheduling = "Scheduling", briefing = "Dean briefing"
        var id: Self { self }
    }
    private enum IssueFilter: String, CaseIterable, Identifiable {
        case all = "All issues", details = "Needs details", blocked = "Blocked", ready = "Ready to review"
        var id: Self { self }
        var icon: String {
            switch self {
            case .all: return "list.bullet"
            case .details: return "questionmark.circle"
            case .blocked: return "hand.raised"
            case .ready: return "checkmark.circle"
            }
        }
    }
    @State private var page: Page = .week
    @State private var taskFilter: IssueFilter = .all
    @State private var inspected: String?
    @State private var guided = false
    @State private var guideStep = 0
    private func dateString(_ date: Date) -> String {
        let f = DateFormatter(); f.timeZone = TimeZone(identifier: "America/Chicago"); f.dateFormat = "yyyy-MM-dd"; return f.string(from: date)
    }
    private func object<T: Encodable>(_ value: T) throws -> [String: Any] {
        try JSONSerialization.jsonObject(with: JSONEncoder().encode(value)) as! [String: Any]
    }
    private func load(discard: Bool = false) async {
        guard (!dirty || discard), selected == nil else { return }
        if let key = store.planningDayKey {
            let formatter = DateFormatter(); formatter.locale = Locale(identifier:"en_US_POSIX"); formatter.timeZone = TimeZone(identifier:"America/Chicago"); formatter.dateFormat = "yyyy-MM-dd"; formatter.isLenient = false
            if let requested = formatter.date(from:key), formatter.string(from:requested) == key { day = requested }
            store.planningDayKey = nil
        }
        let identity = UUID(); loadIdentity = identity
        let requestedDay = dateString(day)
        plan = nil
        busy = true
        defer { if loadIdentity == identity { busy = false } }
        do {
            let fresh = try await store.decode(PlanningRecord.self, "/v1/planning")
            let result = store.offline ? nil : try await store.decode(PlanningResult.self, "/v1/planning/next?day=" + requestedDay)
            guard loadIdentity == identity else { return }
            record = fresh; plan = result; dirty = false
            issue = store.offline ? "Saved planning facts are available offline. Reconnect to calculate recommendations or save planning changes." : nil
            if let workspace = store.planningWorkspaceID, workspace != fresh.workspace_id {
                issue = "TaskDock workspace changed since your check-in preview. Review the current workspace before choosing an issue."
                store.planningTaskID = nil; store.planningWorkspaceID = nil; return
            }
            store.planningWorkspaceID = nil
            if let wanted = store.planningTaskID {
                if let task = plan?.tasks.first(where:{$0.id == wanted}) { inspect(task); choose(task) }
                else { issue = "This issue is completed or outside the current planning candidate set. Review the source details in TaskDock." }
                store.planningTaskID = nil
            }
        } catch { if loadIdentity == identity { issue = (error as? APIProblem)?.message ?? "Could not load planning. Your changes remain here." } }
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
    private func duration(_ minutes: Int) -> String {
        let hours = minutes / 60
        let remainder = minutes % 60
        if hours == 0 { return "\(remainder)m" }
        return remainder == 0 ? "\(hours)h" : "\(hours)h \(remainder)m"
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Plan your week").font(.title2.bold())
                Spacer()
                if busy { ProgressView().controlSize(.small).accessibilityLabel("Loading plan") }
                Menu {
                    Button("Reload saved planning") { Task { await load() } }.disabled(busy || dirty)
                    if dirty { Button("Discard changes and reload") { Task { await load(discard: true) } }.disabled(busy) }
                } label: {
                    Label("Plan actions", systemImage: "ellipsis.circle")
                }.menuStyle(.borderlessButton).fixedSize()
                if dirty {
                    Button("Save planning") { Task { await save() } }
                        .buttonStyle(.borderedProminent)
                        .disabled(busy || store.offline)
                }
            }
            HStack {
                Picker("Plan view", selection: $page) {
                    ForEach(Page.allCases) { page in Text(page.rawValue).tag(page) }
                }.pickerStyle(.segmented).labelsHidden().frame(maxWidth: 430)
                Spacer()
                if page != .briefing {
                    DatePicker("Starting", selection: $day, displayedComponents: .date)
                        .fixedSize().disabled(dirty || busy)
                }
            }
            if dirty {
                Label("Unsaved planning changes", systemImage: "pencil.circle")
                    .font(.caption).foregroundStyle(.orange)
            }
            if let issue { Text(issue).font(.callout).foregroundStyle(.secondary).textSelection(.enabled) }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .frame(maxWidth: 1100)
    }

    private func metric(_ minutes: Int, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(duration(minutes)).font(.title2.weight(.semibold)).monospacedDigit()
            Text(label).font(.caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.quaternary.opacity(0.35), in: RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
    }

    private var currentPlan: PlanningResult? { dirty || busy ? nil : plan }

    @ViewBuilder
    private var week: some View {
        if let plan = currentPlan {
            Text("Time available").font(.headline).accessibilityAddTraits(.isHeader)
            HStack(spacing: 10) {
                metric(plan.capacity_minutes, "To plan")
                metric(plan.free_minutes, "After recorded meetings")
                metric(plan.reserve_minutes, "Reserved for interruptions")
            }
            if let question = plan.question,
               plan.tasks.contains(where: { $0.dean == true }),
               plan.tasks.contains(where: { $0.reason == "Teaching/operations need" }) {
                GroupBox("Choose a priority") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(question)
                        ForEach(plan.tasks.filter { $0.dean == true || $0.reason == "Teaching/operations need" }.prefix(4)) { task in
                            Button("Prioritize " + task.title) {
                                record?.priority_choice = task.id
                                record?.priority_choice_date = dateString(day)
                                dirty = true
                            }
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
            } else if let next = plan.tasks.first(where: { $0.id == plan.recommended_task_id }) {
                GroupBox("Suggested next") {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(next.title).font(.headline)
                        Text(duration(next.estimate_minutes) + " · " + next.reason).foregroundStyle(.secondary)
                        Button("Review issue") { inspect(next) }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            if let allocation = plan.allocation_proposal, !allocation.blocks.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Suggested work times").font(.headline).accessibilityAddTraits(.isHeader)
                    ForEach(allocation.blocks) { block in
                        GroupBox {
                            VStack(alignment: .leading, spacing: 5) {
                                Text(block.title).font(.headline)
                                Text(scheduleDate(block.start) + "–" + dailyBriefTime(block.end))
                                Text([duration(block.minutes), block.employee.isEmpty ? "Me" : block.employee, block.room]
                                    .filter { !$0.isEmpty }.joined(separator: " · "))
                                    .font(.callout).foregroundStyle(.secondary)
                                HStack {
                                    if let task = plan.tasks.first(where: { $0.id == block.id }) {
                                        Button("Review issue") { inspect(task) }
                                    }
                                    RecommendationFeedbackButton(store: store, taskID: block.id, day: dateString(day))
                                }
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    DisclosureGroup("About these suggestions") {
                        Text(allocation.notice).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            Button("Browse issues (\(plan.tasks.count))") { page = .issues }
            DisclosureGroup("Sources and availability limits") {
                VStack(alignment: .leading, spacing: 5) {
                    ForEach(plan.notices, id: \.self) { Text($0) }
                    Text(plan.notice)
                }.font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
            }
        } else {
            planUnavailable
        }
        Button("Open daily check-in") { store.section = "Check-in" }
    }

    private var planUnavailable: some View {
        Text(busy ? "Loading the plan…" : dirty ? "Save planning to see updated recommendations." :
             store.offline ? "Reconnect to see planning recommendations." : "No plan available for these dates.")
            .foregroundStyle(.secondary)
    }

    private func inspect(_ task: PlanningTask) {
        inspected = task.id
        page = .issues
        taskSearch = ""
        taskFilter = .all
    }

    private func issueList(width: CGFloat) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("TaskDock issues").font(.headline).accessibilityAddTraits(.isHeader)
                Spacer()
                Button("Open TaskDock") { store.section = "TaskDock" }
            }
            HStack {
                TextField("Search issues by title or room", text: $taskSearch)
                    .focused($searchFocused)
                    .textFieldStyle(.roundedBorder)
                Picker("Status", selection: $taskFilter) {
                    ForEach(IssueFilter.allCases) { filter in Text(filter.rawValue).tag(filter) }
                }.fixedSize()
            }
            if let plan = currentPlan {
                let search = taskSearch.trimmingCharacters(in: .whitespacesAndNewlines)
                let tasks = plan.tasks.filter {
                    (search.isEmpty || [$0.title, $0.roomSummary].contains { $0.localizedCaseInsensitiveContains(search) })
                        && (taskFilter == .all || taskStatus($0) == taskFilter)
                }
                Text("\(tasks.count) of \(plan.tasks.count) issues").font(.caption).foregroundStyle(.secondary)
                if tasks.isEmpty {
                    Text(plan.tasks.isEmpty ? "No issues in this plan." : "No issues match your search and status.")
                        .foregroundStyle(.secondary)
                }
                if !tasks.isEmpty {
                    if width >= 760 {
                        HStack(alignment: .top, spacing: 16) {
                            issueResults(tasks).frame(width: min(330, width * 0.37))
                            Divider()
                            issueInspector(tasks, recommended: plan.recommended_task_id)
                        }
                    } else {
                        VStack(alignment: .leading, spacing: 16) {
                            issueResults(tasks)
                            issueInspector(tasks, recommended: plan.recommended_task_id)
                        }
                    }
                }
            } else { planUnavailable }
        }
    }

    private func taskStatus(_ task: PlanningTask) -> IssueFilter {
        if !task.blocker.isEmpty { return .blocked }
        return task.actionable && (task.request_questions ?? []).isEmpty ? .ready : .details
    }

    private func issueResults(_ tasks: [PlanningTask]) -> some View {
        ScrollViewReader { reader in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 4) {
                    ForEach(tasks) { task in issueRow(task).id(task.id) }
                }.padding(6)
            }.frame(height: 250)
                .background(.background, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
                .accessibilityLabel("Issue results")
                .onAppear { if let inspected { reader.scrollTo(inspected) } }
                .onChange(of: inspected) { id in if let id { reader.scrollTo(id) } }
        }
    }

    @ViewBuilder
    private func issueInspector(_ tasks: [PlanningTask], recommended: String?) -> some View {
        if let task = tasks.first(where: { $0.id == inspected }) {
            VStack(alignment: .leading, spacing: 12) {
                Text(task.title).font(.title3.bold()).accessibilityAddTraits(.isHeader)
                issueDetails(task, recommended: recommended == task.id)
            }.id(task.id).frame(maxWidth: .infinity, alignment: .leading)
        } else {
            Label("Select an issue to review its details.", systemImage: "sidebar.right")
                .foregroundStyle(.secondary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, 12)
        }
    }

    private func issueRow(_ task: PlanningTask) -> some View {
        let selected = inspected == task.id
        let status = taskStatus(task)
        let location = task.roomSummary
        let metadata = [location == "Unknown" || location == "Not supplied / unknown" ? nil : location,
                        task.priority_label.flatMap { $0 == "Unknown" ? nil : $0 + " priority" },
                        task.due_date.map { "Due " + scheduleDate($0) }].compactMap { $0 }

        return Button { inspected = task.id } label: {
            VStack(alignment: .leading, spacing: 4) {
                Text(task.title).font(.headline)
                if !metadata.isEmpty {
                    Text(metadata.joined(separator: " · ")).font(.caption).foregroundStyle(.secondary)
                }
                Label(status.rawValue, systemImage: status.icon).font(.caption).foregroundStyle(.secondary)
            }.padding(8).frame(maxWidth: .infinity, alignment: .leading)
                .background(selected ? Color.accentColor.opacity(0.15) : .clear,
                            in: RoundedRectangle(cornerRadius: 6))
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Inspect " + task.title)
        .accessibilityValue(status.rawValue)
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private func issueDetails(_ task: PlanningTask, recommended: Bool) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Divider()
            if recommended { Label("Suggested next", systemImage: "sparkle").font(.subheadline.weight(.semibold)) }
            HStack {
                Button("Planning details") { choose(task) }
                Button("Clarify with Juno") { choose(task, guidedMode: true) }
                Menu("More actions") {
                    Button("Discuss estimate") {
                        store.prepareChat("Help me estimate this task from the saved evidence: “" + task.title + "”. Give a range and explain the uncertainty. Ask one scope question if needed. Do not change my confirmed estimate; I will review and enter it in Plan.")
                    }
                    Button("Request worker update…") {
                        store.workerTaskID = task.id
                        store.section = "Workers"
                    }.disabled(store.sharedProfile != nil)
                }.fixedSize()
            }
            PlanningRequestOverview(task: task) { question in
                store.prepareChat("Help me clarify “" + task.title + "”. Start with this question: “" + question.question + "” Ask me one question at a time.")
            }
            Text(duration(task.estimate_minutes) + " · " + task.reason)
            ForEach(task.operational_reasons ?? [], id: \.self) { Text($0).font(.caption) }
            Text(task.estimate_reason).font(.caption).foregroundStyle(.secondary)
            if !task.missing.isEmpty {
                DisclosureGroup("\(task.missing.count) details to confirm") {
                    ForEach(task.missing, id: \.self) { Text($0).font(.caption) }
                }
            }
            if !task.next_action.isEmpty { Text("Unblock: " + task.next_action) }
            if let check = task.next_check { Text("Next blocker check: " + check).font(.caption) }
            if !task.resume.isEmpty { Text("Resume: " + task.resume) }
            DisclosureGroup("Reviewed check-in sources") {
                if let sourceIssue { Text(sourceIssue).font(.caption) }
                else if let planningSources {
                    if planningSources.items.isEmpty { Text("No diary carry-forward history recorded for this task.").font(.caption) }
                    ForEach(planningSources.items) { source in
                        Text("Diary \(source.diary_day) · revision \(source.diary_revision)").font(.headline)
                        Text(source.source_quote).textSelection(.enabled)
                        if source.source_changed { Text("The diary has changed since this review. Compare the current source before reusing this evidence.").foregroundStyle(.orange) }
                        ForEach(source.rows) { change in Text(change.label+": "+change.before+" → "+change.after).font(.caption) }
                    }
                    Text("Historical reviewed changes; later planning edits can supersede these values.").font(.caption).foregroundStyle(.secondary)
                } else { Text("Loading source history…").font(.caption) }
            }
        }
    }

    @ViewBuilder
    private var scheduling: some View {
        RepairWindowsView(store: store, day: dateString(day), tasks: currentPlan?.tasks ?? [], workspace: record?.workspace_id)
        if let loads = currentPlan?.staff_loads, !loads.isEmpty {
            DisclosureGroup("Staff workload") {
                VStack(alignment: .leading, spacing: 12) {
                    ForEach(loads) { load in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(load.employee).font(.headline)
                            Text(duration(load.reported_assignment_minutes) + " estimated · \(load.unknown_estimates) without estimates · \(load.blocked_tasks) blocked")
                            Text(load.available_minutes.map { duration($0) + " scheduled before weekly limits" } ?? "Availability unknown")
                            if let limit = load.weekly_limit_minutes { Text("Weekly limit " + duration(limit)) }
                            Text(load.notice).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }.padding(.vertical, 8)
            }
        }
        if let record {
            DisclosureGroup("Planning settings and dated availability") {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Times are shown in Central time. Add individual work, room access or staff windows.").font(.caption)
                    HStack {
                        Text("Interruption reserve, minutes per seven days")
                        Stepper("\(record.reserve_minutes)", value: Binding(get: { self.record?.reserve_minutes ?? 240 }, set: { self.record?.reserve_minutes = $0; dirty = true }), in: 0...2400, step: 30)
                    }
                    ForEach(Array(record.windows.enumerated()), id: \.offset) { index, w in
                        HStack {
                            Text("\(w.name.isEmpty ? w.kind.capitalized : w.name) · \(scheduleDate(w.start)) – \(scheduleDate(w.end))").font(.caption).textSelection(.enabled)
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
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            Divider()
            GeometryReader { geometry in
              ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    switch page {
                    case .week: week
                    case .issues: issueList(width: geometry.size.width)
                    case .scheduling: scheduling
                    case .briefing:
                        DeanMeetingControls(store: store, open: { showDeanDraft = true },
                                            refreshPlan: { Task { await load() } })
                        ChairsReportControls(store: store)
                    }
                }
                .padding(24)
                .frame(maxWidth: 1100, alignment: .leading)
                .frame(maxWidth: .infinity)
              }.id(page)
            }
        }
        .environment(\.locale, Locale(identifier: "en_US"))
        .environment(\.timeZone, DeanMeetingSchedule.zone)
        .onReceive(NotificationCenter.default.publisher(for: Notification.Name("JunoFind"))) { _ in
            guard store.section == "Plan" else { return }
            page = .issues
            Task { @MainActor in
                await Task.yield()
                searchFocused = true
            }
        }
        .task(id:(inspected ?? "")+":"+(record?.workspace_id ?? "")+":"+String(record?.revision ?? 0)) {
            planningSources=nil;sourceIssue=nil
            guard let id=inspected,let workspace=record?.workspace_id else{return}
            if store.offline {sourceIssue="Reconnect to read reviewed diary sources.";return}
            let task=id.addingPercentEncoding(withAllowedCharacters:.alphanumerics) ?? ""
            let scope=workspace.addingPercentEncoding(withAllowedCharacters:.alphanumerics) ?? ""
            do { let result=try await store.decode(PlanningDiarySources.self,"/v1/planning/carry-forward/history?task_id="+task+"&workspace_id="+scope);if !Task.isCancelled {planningSources=result} }
            catch {if !Task.isCancelled {sourceIssue="Source history unavailable; reconnect to read it."}}
        }
        .task { await load() }
        .sheet(isPresented:$showDeanDraft) { WeeklyDeanEditor(store:store,initialDay:DeanMeetingSchedule(now:Date()).week) }
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
        .onChange(of:dirty) { value in if value { store.unsavedSections.insert("Plan") } else { store.unsavedSections.remove("Plan") } }
        .onChange(of:store.section) { key in if key == "Plan",!dirty,selected == nil { Task { await load() } } }
        .onChange(of:store.planningTaskID) { wanted in
            if store.section == "Plan", !dirty, selected == nil, !busy, store.planningDayKey == nil, store.planningWorkspaceID == nil, let task = plan?.tasks.first(where:{$0.id == wanted}) { inspect(task);choose(task);store.planningTaskID = nil }
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
            if let description = task.requestField("issue_description"),description.state == "provided",let text = description.value {
                Text(text).lineLimit(4).frame(maxWidth:.infinity,alignment:.leading)
            }
            if let outcome = task.requestField("requested_outcome"),outcome.state == "provided",let text = outcome.value { Text("Goal: " + text).font(.callout).lineLimit(3) }
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

private struct DeanDocumentLine {
    enum Style { case title, date, heading, paragraph, list }
    let style: Style
    let text: String
    var marker = ""
    var startsParagraph = false

    static func read(_ document: String) -> [Self] {
        let lines = document.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespaces) }
        var result: [Self] = []
        var inHeader = false

        for (index, line) in lines.enumerated() {
            guard !line.isEmpty else { continue }
            let startsParagraph = index > 0 && lines[index - 1].isEmpty
            let followedByBlank = index + 1 < lines.count && lines[index + 1].isEmpty
            let markdownHeading = line.range(of: #"^#{1,6}[ \t]+"#, options: .regularExpression)
            let marker = line.range(of: #"^(?:[•*-]|[0-9]{1,3}[.)])[ \t]+"#, options: .regularExpression)
            let looksLikeHeading = line.count <= 80 && line.first?.isUppercase == true
                && !line.hasSuffix(".") && !line.hasSuffix("?") && !line.hasSuffix("!")
            let date = line.range(of: #"^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}(?:$| through )|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[ .]+[0-9]{1,2}(?:\b|–))"#,
                                  options: .regularExpression) != nil
            let nextIsBullet = index + 1 < lines.count && lines[index + 1].hasPrefix("•")
            let text = markdownHeading.map { String(line[$0.upperBound...]) } ?? line

            if result.isEmpty && marker == nil && !date && (looksLikeHeading || markdownHeading != nil) {
                result.append(.init(style: .title, text: text))
                inHeader = true
            } else if inHeader && !startsParagraph && (date || line.hasPrefix("From ")) {
                result.append(.init(style: .date, text: text))
            } else if let marker {
                let symbol = line[marker].trimmingCharacters(in: .whitespaces)
                result.append(.init(style: .list, text: String(line[marker.upperBound...]),
                                    marker: symbol == "-" || symbol == "*" ? "•" : symbol,
                                    startsParagraph: startsParagraph))
                inHeader = false
            } else {
                let isSection = markdownHeading != nil || (startsParagraph && looksLikeHeading
                    && (followedByBlank || nextIsBullet || line.hasPrefix("TaskDock:") || line.hasPrefix("Beacon:")
                        || ["Confirmed daily records", "Confirmed check-ins (day-level records)",
                            "Decisions to raise", "Source coverage", "Decisions and meeting agenda",
                            "Unresolved operational issues and source evidence", "Milestones and next-week priorities",
                            "Priorities and blockers from the current saved task copy"].contains(line)))
                result.append(.init(style: isSection ? .heading : .paragraph,
                                    text: text, startsParagraph: startsParagraph))
                inHeader = false
            }
        }
        return result
    }
}

private struct DeanDocumentPage: View {
    let document: String

    var body: some View {
        let lines = DeanDocumentLine.read(document)
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(lines.enumerated()), id: \.offset) { index, line in
                row(line)
                    .padding(.top, spacing(for: line, after: index > 0 ? lines[index - 1].style : nil))
            }
        }
        .lineSpacing(5)
        .textSelection(.enabled)
        .padding(.horizontal, 44)
        .padding(.vertical, 38)
        .frame(maxWidth: 660, alignment: .leading)
        .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
    }

    private func spacing(for line: DeanDocumentLine, after previous: DeanDocumentLine.Style?) -> CGFloat {
        guard let previous else { return 0 }
        switch line.style {
        case .title: return 0
        case .date: return previous == .title ? 9 : 5
        case .heading: return 24
        case .paragraph: return line.startsParagraph || previous == .date ? 16 : 7
        case .list: return line.startsParagraph ? 13 : 9
        }
    }

    @ViewBuilder
    private func row(_ line: DeanDocumentLine) -> some View {
        switch line.style {
        case .title:
            Text(verbatim: line.text)
                .font(.system(size: 33, weight: .semibold, design: .serif))
                .accessibilityAddTraits(.isHeader)
        case .date:
            Text(verbatim: line.text).font(.system(size: 14)).foregroundStyle(.secondary)
        case .heading:
            Text(verbatim: line.text)
                .font(.system(size: 18, weight: .semibold))
                .accessibilityAddTraits(.isHeader)
        case .paragraph:
            Text(verbatim: line.text).font(.system(size: 15))
        case .list:
            HStack(alignment: .firstTextBaseline, spacing: 9) {
                Text(verbatim: line.marker)
                    .foregroundStyle(.secondary)
                    .frame(minWidth: 13, alignment: .leading)
                Text(verbatim: line.text)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .font(.system(size: 15))
            .accessibilityElement(children: .combine)
        }
    }
}

struct WeeklyDeanEditor: View {
    @ObservedObject var store:JunoStore
    @Environment(\.dismiss) private var dismiss
    @State private var day:Date
    init(store:JunoStore,initialDay:Date) {
        self.store=store
        _day=State(initialValue:initialDay)
    }
    @State private var saved:SavedDeanDraft?
    @State private var basis:WeeklyBasis?
    @State private var text=""
    @State private var dirty=false
    @State private var busy=false
    @State private var notice=""
    @State private var prepared:WeeklyPlanningDraft?
    @State private var comparison:SavedDeanDraft?
    @State private var pending:[String:Any]?
    @State private var baseRevision=0
    @State private var confirmClose=false
    @State private var editing = false
    @State private var showDetails = false
    @State private var showFresh = false
    var dayKey:String { let f=DateFormatter();f.locale=Locale(identifier:"en_US_POSIX");f.timeZone=TimeZone(identifier:"America/Chicago");f.dateFormat="yyyy-MM-dd";return f.string(from:day) }
    var recoveryKey:String? { saved.map { "deanDraft."+$0.owner_id+":"+dayKey } }
    private func object<T:Encodable>(_ value:T) throws -> [String:Any] { try JSONSerialization.jsonObject(with:JSONEncoder().encode(value)) as! [String:Any] }
    private func recoverable() {
        guard let key=recoveryKey, let basis else { return }
        if !dirty && pending == nil { UserDefaults.standard.removeObject(forKey:key);return }
        var value:[String:Any] = ["text":text,"revision":baseRevision,"basis":(try? object(basis)) ?? [:]]
        if let pending { value["pending"]=pending }
        if let data=try? JSONSerialization.data(withJSONObject:value) { UserDefaults.standard.set(data,forKey:key) }
    }
    private func load() async {
        guard !busy else { return }
        busy = true
        defer { busy = false }
        if saved?.week_start != dayKey {
            saved = nil
            basis = nil
            text = ""
            prepared = nil
            comparison = nil
            showFresh = false
            showDetails = false
            notice = ""
        }
        do {
            let result=try await store.decode(SavedDeanDraft.self,"/v1/planning/weekly-draft/"+dayKey)
            saved=result;basis=result.basis;baseRevision=result.revision;text=result.text;dirty=false;prepared=nil;comparison=nil;notice=""
            editing = false; showFresh = false; showDetails = false
            if let key=recoveryKey,let data=UserDefaults.standard.data(forKey:key),let local=try JSONSerialization.jsonObject(with:data) as? [String:Any],let recovered=local["text"] as? String,let revision=local["revision"] as? Int,let raw=local["basis"] {
                text=recovered;baseRevision=revision;basis=try JSONDecoder().decode(WeeklyBasis.self,from:JSONSerialization.data(withJSONObject:raw));pending=local["pending"] as? [String:Any];dirty=true
                notice="Recovered local writing. Compare it with the saved draft before replacing either version."
            }
        } catch { notice=(error as? APIProblem)?.message ?? "Could not open the saved draft. Reconnect to your work Mac." }
    }
    private func prepare() {
        guard !busy, pending == nil else { return };busy=true
        Task { defer{busy=false};do {
            let value=try await store.decode(WeeklyPlanningDraft.self,"/v1/planning/weekly?day="+dayKey)
            prepared=value
            if saved?.exists == false && !dirty { text=value.text;basis=value.basis;dirty=true;recoverable();notice="Prepared for your review. Save draft keeps your edited writing on the work Mac." }
            else { showFresh = true; comparison = nil; notice = "" }
        } catch { notice=(error as? APIProblem)?.message ?? "Could not prepare the draft. Your writing is still here." } }
    }
    private func save() {
        guard let basis,!busy,pending == nil else{return}
        do { pending=["operation_id":UUID().uuidString,"expected_revision":baseRevision,"text":text,"basis":try object(basis)];recoverable();retry() }
        catch { notice="Could not prepare this save. Your writing is still here." }
    }
    private func retry() {
        guard let operation=pending,!busy else{return};busy=true
        Task { defer{busy=false};do {
            let receipt=try await store.decode(DeanSaveReceipt.self,"/v1/planning/weekly-draft/"+dayKey,method:"PUT",body:operation)
            pending=nil;dirty=false;baseRevision=receipt.revision;recoverable();notice="Saved on your work Mac."; editing = false
            do { saved=try await store.decode(SavedDeanDraft.self,"/v1/planning/weekly-draft/"+dayKey) } catch { notice="Saved on your work Mac, but the view could not refresh. Your text remains here." }
        } catch {
            if let problem=error as? APIProblem,(400..<500).contains(problem.status){pending=nil;notice=problem.message+" Use Compare saved copy; your writing remains here."}
            else { notice="Save receipt unavailable. Your writing and save identity are retained; retry this same save." }
            recoverable()
        } }
    }
    private func compare() {
        busy=true;Task { defer{busy=false};do { comparison=try await store.decode(SavedDeanDraft.self,"/v1/planning/weekly-draft/"+dayKey); showFresh = false } catch { notice=(error as? APIProblem)?.message ?? "Could not read the saved copy." } }
    }
    private var comparisonOpen: Bool { comparison != nil || showFresh }
    private var hasWriting: Bool { !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    private var statusLabel: String {
        if dirty { return "Unsaved changes" }
        if saved?.exists == true { return "Saved · Revision \(baseRevision)" }
        return "No draft saved"
    }

    private var header: some View {
        HStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Dean briefing").font(.headline)
                if saved != nil { Text(statusLabel).font(.caption).foregroundStyle(.secondary) }
            }
            Spacer()
            DatePicker("Week of", selection: $day, displayedComponents: .date)
                .fixedSize()
                .disabled(dirty || busy || pending != nil || editing)
            if let saved {
                Menu("Draft actions", systemImage: "ellipsis.circle") {
                    Button(saved.basis.meeting_window != nil ? "Prepare seven-day comparison" :
                            saved.exists || dirty ? "Prepare fresh comparison" : "Prepare draft", action: prepare)
                        .disabled(busy || store.offline || pending != nil)
                    Button("Compare saved copy", action: compare)
                        .disabled(busy || store.offline || pending != nil)
                    if prepared != nil && !showFresh {
                        Button("Show prepared comparison") { comparison = nil; showFresh = true }
                    }
                    Divider()
                    Button(showDetails ? "Hide source details" : "Show source details") { showDetails.toggle() }
                }
                .menuStyle(.borderlessButton)
                .fixedSize()
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 14)
    }

    @ViewBuilder
    private var sourceDetails: some View {
        if let basis, showDetails || saved?.sources_changed == true {
            DisclosureGroup(isExpanded: $showDetails) {
                VStack(alignment: .leading, spacing: 5) {
                    if saved?.sources_changed == true { Text("Source data changed after this draft was prepared.") }
                    if basis.taskdock_uncertain { Text("Check the freshness of the TaskDock copy used for this draft.") }
                    Text("\(basis.diaries.count) confirmed check-ins in " +
                         (basis.meeting_window == nil ? "the seven-day period." : "the meeting window."))
                }
                .foregroundStyle(.secondary)
                .padding(.vertical, 7)
            } label: {
                Label(saved?.sources_changed == true ? "Sources updated" : "Source details",
                      systemImage: saved?.sources_changed == true ? "clock.arrow.circlepath" : "info.circle")
            }
            .font(.caption)
            .padding(.horizontal, 24)
            .padding(.bottom, 10)
        }
    }

    private func documentPage(_ content: String) -> some View {
        ScrollView {
            DeanDocumentPage(document: content)
                .frame(maxWidth: .infinity)
                .padding(.horizontal, 24)
                .padding(.vertical, 20)
        }
    }

    @ViewBuilder
    private var documentArea: some View {
        if let comparison {
            VStack(alignment: .leading, spacing: 0) {
                Text("Saved copy · Revision \(comparison.revision)")
                    .font(.subheadline.weight(.medium)).padding(.horizontal, 24).padding(.top, 12)
                if comparison.text.isEmpty {
                    Text("No saved writing for this week.")
                        .foregroundStyle(.secondary).frame(maxWidth: .infinity, maxHeight: .infinity)
                } else { documentPage(comparison.text).id("savedComparison") }
            }
        } else if showFresh, let prepared {
            VStack(alignment: .leading, spacing: 0) {
                Text("Prepared comparison").font(.subheadline.weight(.medium))
                    .padding(.horizontal, 24).padding(.top, 12)
                documentPage(prepared.text).id("preparedComparison")
            }
        } else if editing {
            TextEditor(text: Binding(get: { text }, set: { text = $0; dirty = true; recoverable() }))
                .font(.system(size: 15))
                .lineSpacing(5)
                .padding(20)
                .accessibilityLabel("Dean briefing text")
                .disabled(busy || pending != nil)
                .frame(maxWidth: 660, maxHeight: .infinity)
                .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
                .padding(20)
        } else if hasWriting {
            documentPage(text).id(dayKey)
        } else {
            VStack(spacing: 12) {
                if busy {
                    ProgressView("Opening briefing…")
                } else {
                    Text(saved == nil ? "Briefing unavailable" : "No briefing for this week")
                        .font(.title3.weight(.semibold))
                    if saved != nil {
                        Button("Prepare draft", action: prepare).disabled(store.offline)
                    } else {
                        Button("Try again") { Task { await load() } }
                    }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func adoptSavedCopy(_ comparison: SavedDeanDraft, keepWriting: Bool) {
        saved = comparison
        baseRevision = comparison.revision
        basis = comparison.basis
        self.comparison = nil
        dirty = keepWriting
        if !keepWriting { text = comparison.text; editing = false }
        recoverable()
        notice = keepWriting ? "Review your writing and save it against the current revision." : ""
    }

    private var footer: some View {
        HStack {
            Button(comparisonOpen ? "Back to briefing" : "Close") {
                if comparisonOpen { comparison = nil; showFresh = false }
                else if dirty || pending != nil { confirmClose = true }
                else { dismiss() }
            }.keyboardShortcut(.cancelAction)
            Spacer()
            if let comparison {
                Button("Keep my writing") { adoptSavedCopy(comparison, keepWriting: true) }.disabled(pending != nil)
                Button("Use saved text") { adoptSavedCopy(comparison, keepWriting: false) }.disabled(pending != nil)
            } else if !comparisonOpen {
                Button("Copy briefing") {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                }.disabled(!hasWriting || busy)
                if pending != nil {
                    Button("Retry save", action: retry).disabled(busy || store.offline)
                } else if editing {
                    Button("Preview") { editing = false }.disabled(busy)
                } else if saved != nil {
                    Button("Edit briefing") { editing = true }.disabled(busy)
                }
                if dirty && pending == nil {
                    Button("Save draft", action: save)
                        .buttonStyle(.borderedProminent)
                        .disabled(busy || store.offline || !hasWriting || text.count > 60000)
                }
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 13)
    }

    var body: some View {
        VStack(spacing: 0) {
            header
            sourceDetails
            if !notice.isEmpty {
                Text(notice)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 24)
                    .padding(.bottom, 10)
            }
            Divider()
            documentArea
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(nsColor: .windowBackgroundColor))
            Divider()
            footer
        }
        .frame(width: 780, height: 760)
        .environment(\.locale, Locale(identifier: "en_US"))
        .environment(\.timeZone,DeanMeetingSchedule.zone)
        .task { await load() }
        .onChange(of:day) { _ in if !dirty && !busy { Task { await load() } } }
        .onChange(of:dirty) { value in if value { store.unsavedSections.insert("Dean draft") } else { store.unsavedSections.remove("Dean draft") } }
        .onDisappear { recoverable();store.unsavedSections.remove("Dean draft") }
        .interactiveDismissDisabled(dirty || pending != nil)
        .alert("Keep this unsaved writing for later?",isPresented:$confirmClose) { Button("Keep local recovery and close") { recoverable();dismiss() };Button("Return to draft",role:.cancel){} } message:{Text("Your work-Mac draft changes only after Save succeeds. A local recovery copy keeps this writing for the next time you open this period.")}
    }
}

struct DeanMeetingSchedule {
    static let zone = TimeZone(identifier:"America/Chicago")!
    static var calendar:Calendar {
        var calendar=Calendar(identifier:.iso8601);calendar.timeZone=zone;return calendar
    }
    let week:Date
    let meeting:Date
    let automaticAt:Date
    let previous:Date
    init(now:Date) {
        let cal=Self.calendar
        week=cal.dateInterval(of:.weekOfYear,for:now)!.start
        let thursday=cal.date(byAdding:.day,value:3,to:week)!
        meeting=cal.date(bySettingHour:10,minute:0,second:0,of:thursday)!
        automaticAt=cal.date(bySettingHour:9,minute:0,second:0,of:thursday)!
        previous=cal.date(byAdding:.day,value:-7,to:meeting)!
    }
    var key:String {
        let formatter=DateFormatter()
        formatter.locale=Locale(identifier:"en_US_POSIX");formatter.timeZone=Self.zone;formatter.dateFormat="yyyy-MM-dd"
        return formatter.string(from:week)
    }
    func due(at now:Date) -> Bool { automaticAt<=now && now<meeting }
}

private struct DeanPrepareResult: Decodable { let created:Bool }

private struct ChairEmail: Decodable {
    let subject: String
    let body: String
    let coverage: [String]
    var composition: String? = nil

    var compositionLabel: String? {
        switch composition {
        case "lm_studio": return "Written with LM Studio"
        case "built_in": return "Written from saved records"
        case "fallback": return "Written from saved records after LM Studio could not complete the email"
        default: return nil
        }
    }
}

struct ReportsWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var showDeanDraft = false
    @State private var deanStatus = "Checking saved briefing…"
    @State private var chairStatus = "Checking saved emails…"
    @State private var chairDraft: ChairsDraft?
    @State private var chairEditor: ChairDraftSelection?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Reports").font(.largeTitle.bold()).accessibilityAddTraits(.isHeader)
                DeanMeetingControls(store: store, open: { showDeanDraft = true }, refreshPlan: {}, summary: deanStatus)
                ChairsReportControls(store: store, summary: chairStatus,
                                     showsRecipientList: chairDraft?.emails?.isEmpty == false,
                                     hasSavedDraft: chairDraft?.exists == true,
                                     onReviewDismiss: { Task { await refreshStatus() } })
                if let emails = chairDraft?.emails, !emails.isEmpty {
                    GroupBox("Review by department") {
                        VStack(alignment: .leading, spacing: 0) {
                            ForEach(ChairDraftSelection.recipients) { recipient in
                                if let email = emails[recipient.id] {
                                    Button {
                                        chairEditor = recipient
                                    } label: {
                                        HStack {
                                            VStack(alignment: .leading, spacing: 4) {
                                                Text(recipient.name).font(.headline)
                                                Text(email.subject).font(.callout).foregroundStyle(.secondary).lineLimit(2)
                                                if let label = email.compositionLabel {
                                                    Text(label).font(.caption).foregroundStyle(.secondary)
                                                }
                                            }
                                            Spacer()
                                            Image(systemName: "chevron.right").foregroundStyle(.secondary)
                                        }.frame(maxWidth: .infinity, alignment: .leading).padding(10).contentShape(Rectangle())
                                    }.buttonStyle(.plain)
                                        .accessibilityLabel("Review " + recipient.name + " email")
                                        .accessibilityHint([email.subject, email.compositionLabel].compactMap { $0 }.joined(separator: ". "))
                                    Divider()
                                }
                            }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .padding(24)
            .frame(maxWidth: 880, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .task(id: store.section + "|" + String(store.connected) + "|" + String(store.chairsPreparing) + "|" + String(store.deanPreparing)) {
            guard store.section == "Reports" else { return }
            await refreshStatus()
        }
        .sheet(isPresented: $showDeanDraft) {
            WeeklyDeanEditor(store: store, initialDay: DeanMeetingSchedule(now: Date()).week)
        }
        .sheet(item: $chairEditor, onDismiss: { Task { await refreshStatus() } }) { recipient in
            ChairsReportEditor(store: store, initialRecipient: recipient.id)
        }
    }

    private func refreshStatus() async {
        let key = DeanMeetingSchedule(now: Date()).key
        do {
            let draft = try await store.decode(SavedDeanDraft.self, "/v1/planning/weekly-draft/" + key)
            deanStatus = draft.exists ? "Talking points saved for this week" : "No talking points saved this week"
        } catch { deanStatus = "Saved briefing status unavailable" }
        do {
            let draft = try await store.decode(ChairsDraft.self, "/v1/planning/chairs-draft/" + key)
            guard !Task.isCancelled else { return }
            chairDraft = draft
            let count = draft.emails?.count ?? 0
            chairStatus = count > 0 ? "\(count) drafts ready to review" : draft.exists ? "Weekly draft ready to review" : "No email draft saved this week"
        } catch {
            guard !Task.isCancelled else { return }
            chairDraft = nil
            chairStatus = "Saved email status unavailable"
        }
    }
}

private struct ChairDraftSelection: Identifiable {
    let id: String
    let name: String
    static let recipients = [
        Self(id: "lwr", name: "Languages, Literatures and Cultures"),
        Self(id: "visu", name: "Visual Studies"),
        Self(id: "performing", name: "Performing Arts")
    ]
}

private struct ChairsDraft: Decodable {
    let emails: [String: ChairEmail]?
    let exists: Bool
    let subject: String
    let body: String
    let coverage: [String]
    let revision: Int
}

extension JunoStore {
    private func refreshReportingTasks() async throws -> (TaskDockSnapshot, String) {
        guard let task=try await decode(TaskDockState.self,"/v1/taskdock").snapshot else {
            throw APIProblem(message:"Connect TaskDock on this Mac first.",status:0)
        }
        guard let taskToken=try await credentialWork({try TaskDockKeychain.read(task.origin)}),!taskToken.isEmpty else {
            throw APIProblem(message:"The TaskDock token is missing. Reconnect TaskDock in Connections.",status:0)
        }
        let result=try await decode(TaskDockRefresh.self,"/v1/taskdock/refresh",method:"POST",
            body:["base_url":task.origin,"token":taskToken,"expected_snapshot_id":task.id])
        guard !result.review_required,let refreshed=result.snapshot else {
            throw APIProblem(message:"Review the TaskDock workspace in Connections before continuing.",status:0)
        }
        return (refreshed, taskToken)
    }

    private func refreshReportingBeacon() async throws -> EvidenceSnapshot {
        let savedBeacon=try await decode(EvidenceState.self,"/v1/integrations").items.first{$0.kind=="beacon"}
        let origin=UserDefaults.standard.string(forKey:"beaconOrigin") ?? savedBeacon?.origin ?? "http://127.0.0.1:12108"
        let (beaconToken,retainedToken)=try await credentialWork { (try BeaconKeychain.read(origin),try BeaconKeychain.read(origin+"/retained-issues")) }
        guard let beaconToken,!beaconToken.isEmpty else {
            throw APIProblem(message:"The Beacon key is missing. Connect Beacon in Work Evidence.",status:0)
        }
        var body:[String:Any]=["base_url":origin,"token":beaconToken,"include_issue_snapshot":UserDefaults.standard.bool(forKey:"beaconIncludeIssueSnapshot")]
        if let savedBeacon { body["expected_id"]=savedBeacon.id }
        if let retainedToken { body["retained_issue_token"]=retainedToken }
        return try await decode(EvidenceSnapshot.self,"/v1/integrations/beacon/refresh",method:"POST",body:body)
    }

    func startDeanMonitor() {
        guard deanMonitor == nil else{return}
        deanMonitor=Task { [weak self] in
            while !Task.isCancelled {
                await self?.prepareDeanMeeting(automatic:true)
                await self?.prepareChairsDraft(automatic: true)
                do { try await Task.sleep(nanoseconds:30_000_000_000) } catch { return }
            }
        }
    }

    func prepareChairsDraft(automatic: Bool) async {
        guard !chairsPreparing, !deanPreparing, connected, sharedProfile == nil, !offline else { return }
        let current = Date()
        let schedule = DeanMeetingSchedule(now: current)
        let calendar = DeanMeetingSchedule.calendar
        let friday = calendar.date(byAdding: .day, value: 4, to: schedule.week)!
        let scheduledTime = calendar.date(bySettingHour: 9, minute: 0, second: 0, of: friday)!
        guard current >= friday else { return }
        if automatic {
            guard chairsAutomatic, current >= scheduledTime, chairsHandledWeek != schedule.key,
                  chairsLastAttempt.map({ current.timeIntervalSince($0) >= 300 }) ?? true else { return }
            chairsLastAttempt = current
        }
        chairsPreparing = true
        chairsNotice = "Checking this week’s email draft…"
        defer { chairsPreparing = false }
        let path = "/v1/planning/chairs-draft/" + schedule.key
        do {
            let existing = try await decode(ChairsDraft.self, path)
            if existing.exists {
                chairsHandledWeek = schedule.key
                chairsNotice = "This week’s draft is ready to review."
                return
            }
            var unavailable: [String] = []
            chairsNotice = "Refreshing TaskDock…"
            do { _ = try await refreshReportingTasks() }
            catch { unavailable.append("TaskDock") }
            chairsNotice = "Refreshing Beacon…"
            do { _ = try await refreshReportingBeacon() }
            catch { unavailable.append("Beacon") }
            chairsNotice = "Checking the Smartsheet archive…"
            do { try await refreshCompletionArchive() }
            catch { unavailable.append("Smartsheet") }
            guard sharedProfile == nil, !automatic || chairsAutomatic else {
                chairsNotice = "Draft preparation stopped."
                return
            }
            chairsNotice = "Writing the department emails…"
            _ = try await decode(ChairsDraft.self, path + "/prepare", method: "POST",
                                 body: ["unavailable": unavailable])
            chairsHandledWeek = schedule.key
            chairsNotice = "This week’s draft is ready to review."
        } catch {
            chairsNotice = (error as? APIProblem)?.message ?? "Could not prepare the draft. Try again from Reports."
        }
    }

    func prepareDeanMeeting(automatic:Bool) async {
        guard !deanPreparing, !chairsPreparing, connected, sharedProfile == nil, !offline else {return}
        let current=Date(), schedule=DeanMeetingSchedule(now:current)
        guard current<schedule.meeting else {
            if !automatic { deanNotice="This week’s meeting has passed. Open its saved draft or prepare next week’s draft on Monday." }
            return
        }
        if automatic {
            guard deanAutomatic, schedule.due(at:current), deanHandledWeek != schedule.key,
                  deanLastAttempt.map({current.timeIntervalSince($0)>=300}) ?? true else {return}
            deanLastAttempt=current
        }
        deanPreparing=true;deanNotice="Checking this week’s draft…"
        defer { deanPreparing=false }
        var source="Juno"
        do {
            let draft=try await decode(SavedDeanDraft.self,"/v1/planning/weekly-draft/"+schedule.key)
            if draft.exists {
                deanHandledWeek=schedule.key;deanNotice="This week’s Dean draft is already saved. Open it to review."
                return
            }
            guard UserDefaults.standard.data(forKey:"deanDraft."+draft.owner_id+":"+schedule.key)==nil else {
                deanNotice="Unsaved Dean draft writing is on this Mac. Open this week’s draft to review it."
                return
            }
            source="TaskDock";deanNotice="Refreshing TaskDock…"
            let (refreshed, taskToken) = try await refreshReportingTasks()
            if refreshed.info.capabilities["read_updates"] == true {
                deanNotice="Reading shared TaskDock progress notes…"
                let candidates=refreshed.items.filter{!($0.text("latest_update") ?? "").isEmpty}.sorted {
                    ($0.text("last_changed_at") ?? "") > ($1.text("last_changed_at") ?? "")
                }
                for task in candidates.prefix(40) {
                    guard Date()<schedule.meeting, sharedProfile == nil, !automatic || deanAutomatic else {return}
                    var path=URLComponents();path.path="/v1/taskdock/history"
                    path.queryItems=[URLQueryItem(name:"task_id",value:task.id),URLQueryItem(name:"kind",value:"updates")]
                    guard let target=path.string else {continue}
                    // A single unavailable timeline need not hide the remaining evidence. The draft reports coverage.
                    _ = try? await request(target,method:"POST",body:["base_url":refreshed.origin,"token":taskToken,
                        "expected_snapshot_id":refreshed.id])
                }
            }
            source="Beacon";deanNotice="Refreshing Beacon…"
            let beacon = try await refreshReportingBeacon()
            var archiveRefreshFailed = false
            deanNotice = "Checking the completed-task archive…"
            do { try await refreshCompletionArchive() }
            catch { archiveRefreshFailed = true }
            guard sharedProfile == nil, !automatic || deanAutomatic,
                  UserDefaults.standard.data(forKey:"deanDraft."+draft.owner_id+":"+schedule.key)==nil else {
                deanNotice="Preparation stopped before saving. Any saved or unsaved writing has been kept."
                return
            }
            source="Juno"
            let override = deanOverrideWeek == schedule.key ? deanOverride : nil
            let formatter=ISO8601DateFormatter()
            let prepared=try await decode(DeanPrepareResult.self,"/v1/planning/dean-meeting/prepare",method:"POST",body:[
                "previous":formatter.string(from:override ?? schedule.previous),"previous_confirmed":override != nil,
                "meeting":formatter.string(from:schedule.meeting),"taskdock_id":refreshed.id,"beacon_id":beacon.id,
                "archive_refresh_failed":archiveRefreshFailed])
            deanHandledWeek=schedule.key
            deanNotice=prepared.created ? "This week’s Dean draft is ready to review." : "This week’s saved draft was kept."
            if prepared.created && archiveRefreshFailed { deanNotice += " Check Smartsheet archive coverage." }
        } catch {
            deanNotice=source+": "+((error as? APIProblem)?.message ?? "The draft could not be prepared. Try again from Plan.")
        }
    }
}

private struct DeanMeetingControls: View {
    @ObservedObject var store:JunoStore
    let open:()->Void
    let refreshPlan: () -> Void
    var summary: String? = nil
    @State private var correcting=false
    @State private var actual=Date()
    @State private var followUp = false
    var body: some View {
        let current=Date(), schedule=DeanMeetingSchedule(now:current)
        let overridden=store.deanOverrideWeek == schedule.key ? store.deanOverride : nil
        GroupBox("Thursday Dean meeting") {
            VStack(alignment:.leading,spacing:8) {
                if let summary { Text(summary).font(.headline) }
                if store.sharedProfile == nil {
                    Toggle("Prepare automatically at 9:00 AM Central on Thursdays",isOn:$store.deanAutomatic)
                    Text("Juno refreshes TaskDock and Beacon and combines their shared updates with your confirmed check-ins. Keep Juno open and this Mac awake. Saved drafts stay available for review.")
                        .font(.caption).foregroundStyle(.secondary)
                    HStack {
                        Text((overridden == nil ? "Previous scheduled meeting: " : "Last meeting: ") + (overridden ?? schedule.previous).formatted(.dateTime.month(.abbreviated).day().year().hour().minute().timeZone(.specificName(.short))))
                        Button("Correct last meeting…") { actual=overridden ?? schedule.previous;correcting=true }.disabled(store.deanPreparing)
                    }
                }
                HStack {
                    Button("Open this week’s draft…") { open() }
                    Button("Meeting follow-up…") { followUp = true }
                    if store.sharedProfile == nil {
                        Button("Refresh sources and prepare now") { Task { await store.prepareDeanMeeting(automatic:false) } }
                            .disabled(store.deanPreparing || !store.connected || current>=schedule.meeting)
                    }
                }
                if !store.deanNotice.isEmpty { Text(store.deanNotice).font(.callout).textSelection(.enabled) }
            }.frame(maxWidth:.infinity,alignment:.leading)
        }.environment(\.timeZone,DeanMeetingSchedule.zone)
        .sheet(isPresented: $followUp) { DeanFollowUpEditor(store: store, onSave: refreshPlan) }
        .sheet(isPresented:$correcting) {
            VStack(alignment:.leading,spacing:14) {
                Text("When did the last meeting happen?").font(.headline)
                Text("Choose the earlier meeting if a Thursday was skipped or rescheduled. This applies to this week’s draft. Times are Central.").foregroundStyle(.secondary)
                DatePicker("Last meeting",selection:$actual,in:...Date(),displayedComponents:[.date,.hourAndMinute])
                HStack {
                    Button("Cancel",role:.cancel) { correcting=false }.keyboardShortcut(.cancelAction)
                    if overridden != nil { Button("Use usual Thursday") { store.deanOverride=nil;store.deanOverrideWeek="";correcting=false } }
                    Spacer()
                    Button("Use this meeting") { store.deanOverride=actual;store.deanOverrideWeek=schedule.key;correcting=false }
                        .keyboardShortcut(.defaultAction)
                }
            }.padding(20).frame(width:440).environment(\.timeZone,DeanMeetingSchedule.zone)
        }
    }
}

private struct DeanFollowUpCandidate: Decodable {
    let title: String
    let owner: String
    let timing: String
    let waiting_on: String
    let quote: String
}

private struct DeanFollowUpItem: Codable, Identifiable, Equatable {
    var id = UUID()
    var title = ""
    var owner = ""
    var timing = ""
    var waiting_on = ""
    var quote = ""
    var task_id: String?
    var workspace_id: String?
    var closed = false
}

private struct DeanFollowUpRecord: Decodable {
    let notes: String
    let items: [DeanFollowUpItem]
    let revision: Int
}

private struct DeanFollowUpExtraction: Decodable {
    let items: [DeanFollowUpCandidate]
}

private struct DeanFollowUpEditor: View {
    @ObservedObject var store: JunoStore
    let onSave: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var day = Date()
    @State private var saved: DeanFollowUpRecord?
    @State private var snapshot: TaskDockSnapshot?
    @State private var notes = ""
    @State private var items: [DeanFollowUpItem] = []
    @State private var working = false
    @State private var confirmClose = false
    @State private var notice = ""

    private var path: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = DeanMeetingSchedule.zone
        formatter.dateFormat = "yyyy-MM-dd"
        return "/v1/planning/dean-follow-up/" + formatter.string(from: day)
    }
    private var changed: Bool { notes != (saved?.notes ?? "") || items != (saved?.items ?? []) }
    private var hasNotes: Bool { !notes.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
    private var canSave: Bool {
        saved != nil && changed && hasNotes && items.allSatisfy {
            !$0.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty &&
            !$0.quote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Dean meeting follow-up").font(.title2.weight(.semibold))
                Spacer()
                DatePicker("Meeting date", selection: $day, displayedComponents: .date)
                    .fixedSize().disabled(changed || working)
            }.padding(20)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Meeting notes").font(.headline)
                    Text("Paste your notes or a list headed “From the Dean”. Review each request before saving it for the next briefing.")
                        .foregroundStyle(.secondary)
                    TextEditor(text: $notes)
                        .font(.body).frame(minHeight: 120)
                        .accessibilityLabel("Dean meeting notes")
                        .overlay(RoundedRectangle(cornerRadius: 5).strokeBorder(.quaternary))
                    HStack {
                        Button("Find Dean requests") { Task { await extract() } }
                            .disabled(!hasNotes || !items.isEmpty || store.offline)
                        Button("Add request") { items.append(DeanFollowUpItem()) }.disabled(items.count >= 24)
                    }
                    if !changed, let saved, !saved.items.isEmpty {
                        MemorySuggestionButton(store: store, source: "Dean meeting · " + CheckInReminder.day(day) + " · revision \(saved.revision)",
                            text: saved.items.map { item in
                                ["Dean meeting follow-up: " + item.title, item.timing.isEmpty ? "" : "Timing: " + item.timing, item.quote.isEmpty ? "" : "Meeting note: " + item.quote]
                                    .filter { !$0.isEmpty }.joined(separator: "\n")
                            }.joined(separator: "\n\n"))
                    }
                    ForEach($items) { $item in
                        DeanFollowUpRow(item: $item, snapshot: snapshot) {
                            let id = item.id
                            items.removeAll { $0.id == id }
                        }
                    }
                }.padding(20).disabled(working || saved == nil || store.offline)
            }
            Divider()
            HStack {
                Button("Close") { if changed { confirmClose = true } else { dismiss() } }
                    .keyboardShortcut(.cancelAction).disabled(working)
                if working { ProgressView().controlSize(.small) }
                Text(notice).font(.callout).foregroundStyle(.secondary)
                Spacer()
                Button("Save follow-up") { Task { await save() } }
                    .keyboardShortcut(.defaultAction).disabled(!canSave || working || store.offline)
            }.padding(20)
        }
        .frame(minWidth: 690, idealWidth: 760, minHeight: 510, idealHeight: 680)
        .environment(\.timeZone, DeanMeetingSchedule.zone)
        .interactiveDismissDisabled(changed || working)
        .task(id: path) { await load() }
        .confirmationDialog("Discard unsaved follow-up changes?", isPresented: $confirmClose) {
            Button("Discard changes", role: .destructive) { dismiss() }
            Button("Keep editing", role: .cancel) {}
        }
    }

    private func apply(_ value: DeanFollowUpRecord) {
        saved = value
        notes = value.notes
        items = value.items
    }

    private func load() async {
        working = true
        defer { working = false }
        saved = nil
        notes = ""
        items = []
        notice = ""
        do {
            apply(try await store.decode(DeanFollowUpRecord.self, path))
            snapshot = (try? await store.decode(TaskDockState.self, "/v1/taskdock"))?.snapshot
            if store.offline { notice = "Offline copy. Reconnect to save or find requests." }
        } catch {
            notice = (error as? APIProblem)?.message ?? "Could not open follow-up for this date."
        }
    }

    private func extract() async {
        working = true
        defer { working = false }
        do {
            let result = try await store.decode(DeanFollowUpExtraction.self, path + "/extract",
                                                method: "POST", body: ["notes": notes])
            items = result.items.map {
                DeanFollowUpItem(title: $0.title, owner: $0.owner, timing: $0.timing,
                                 waiting_on: $0.waiting_on, quote: $0.quote)
            }
            notice = items.isEmpty ? "No requests found. You can add one manually." : "Review the requests before saving."
        } catch {
            notice = (error as? APIProblem)?.message ?? "Could not find requests. You can add one manually."
        }
    }

    private func save() async {
        guard let saved else { return }
        working = true
        defer { working = false }
        do {
            let encoded = try JSONEncoder().encode(items)
            let payload = try JSONSerialization.jsonObject(with: encoded)
            apply(try await store.decode(DeanFollowUpRecord.self, path, method: "PUT",
                body: ["notes": notes, "expected_revision": saved.revision, "items": payload]))
            notice = "Saved for future Dean briefings."
            onSave()
        } catch {
            notice = (error as? APIProblem)?.message ?? "Could not save. Your edits are still here."
        }
    }
}

private struct DeanFollowUpRow: View {
    @Binding var item: DeanFollowUpItem
    let snapshot: TaskDockSnapshot?
    let remove: () -> Void
    @State private var search = ""

    private var linkedTask: TaskDockTask? {
        guard item.workspace_id == snapshot?.info.workspace_id else { return nil }
        return snapshot?.items.first { $0.id == item.task_id }
    }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                TextField("Request", text: $item.title)
                HStack {
                    TextField("Owner", text: $item.owner)
                    TextField("Deadline or timing", text: $item.timing)
                }
                TextField("Waiting on", text: $item.waiting_on)
                TextField("Exact quote from your notes", text: $item.quote, axis: .vertical)
                    .lineLimit(1...3)
                if let id = item.task_id {
                    HStack {
                        Label(linkedTask?.title ?? "TaskDock reference unavailable · \(id.suffix(8))",
                              systemImage: "link")
                        Spacer()
                        Button("Unlink") { item.task_id = nil; item.workspace_id = nil }
                    }
                } else if let snapshot, snapshot.info.sharing_restricted != true {
                    let query = search.trimmingCharacters(in: .whitespacesAndNewlines)
                    let matches = query.isEmpty ? [] : Array(snapshot.items.filter {
                        $0.title.localizedCaseInsensitiveContains(query)
                    }.prefix(15))
                    HStack {
                        TextField("Search existing TaskDock cards", text: $search)
                        Menu(matches.isEmpty ? "Link card" : "Choose card") {
                            ForEach(matches) { task in
                                Button(task.title + " · " + task.id.suffix(8)) {
                                    item.task_id = task.id
                                    item.workspace_id = snapshot.info.workspace_id
                                    search = ""
                                }
                            }
                        }.disabled(matches.isEmpty)
                    }
                }
                HStack {
                    Toggle("Closed for briefing", isOn: $item.closed)
                    Spacer()
                    Button("Remove request", role: .destructive, action: remove)
                }
            }.textFieldStyle(.roundedBorder).padding(4)
        }
    }
}

private struct ChairsReportControls: View {
    @ObservedObject var store: JunoStore
    var summary: String? = nil
    var showsRecipientList = false
    var hasSavedDraft = false
    var onReviewDismiss: () -> Void = {}
    @State private var showDraft = false
    private var weekClosed: Bool {
        let now = Date()
        let week = DeanMeetingSchedule(now: now).week
        return now >= DeanMeetingSchedule.calendar.date(byAdding: .day, value: 4, to: week)!
    }

    var body: some View {
        GroupBox("Department chairs email") {
            VStack(alignment: .leading, spacing: 10) {
                if let summary { Text(summary).font(.headline) }
                if store.sharedProfile == nil {
                    Toggle("Prepare Fridays at 9:00 AM Central", isOn: $store.chairsAutomatic)
                    Text("Covers Friday through Thursday. Keep Juno open on the work Mac. It can catch up through Sunday.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                HStack {
                    Button(showsRecipientList ? "Browse draft weeks…" : "Review email draft…") { showDraft = true }
                    if store.sharedProfile == nil && !hasSavedDraft {
                        Button("Prepare this week’s draft") { Task { await store.prepareChairsDraft(automatic: false) } }
                            .disabled(store.chairsPreparing || store.deanPreparing || !store.connected || store.offline || !weekClosed)
                    }
                }
                if store.chairsPreparing {
                    ProgressView(store.chairsNotice).controlSize(.small)
                } else if !hasSavedDraft && !store.chairsNotice.isEmpty {
                    Text(store.chairsNotice).font(.callout)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }.sheet(isPresented: $showDraft, onDismiss: onReviewDismiss) { ChairsReportEditor(store: store) }
    }
}

private struct ChairsReportEditor: View {
    @ObservedObject var store: JunoStore
    @Environment(\.dismiss) private var dismiss
    @State private var day = Date()
    @State private var recipient: String
    @State private var saved: ChairsDraft?
    @State private var subject = ""
    @State private var draftBody = ""
    @State private var busy = false
    @State private var notice = ""
    @State private var confirmClose = false
    @State private var editing = false

    init(store: JunoStore, initialRecipient: String = "lwr") {
        self.store = store
        _recipient = State(initialValue: initialRecipient)
    }

    private var path: String { "/v1/planning/chairs-draft/" + DeanMeetingSchedule(now: day).key }
    private var selected: ChairEmail? {
        guard let saved, saved.exists else { return nil }
        if let emails = saved.emails, !emails.isEmpty { return emails[recipient] }
        return ChairEmail(subject: saved.subject, body: saved.body, coverage: saved.coverage)
    }
    private var changed: Bool { subject != (selected?.subject ?? "") || draftBody != (selected?.body ?? "") }
    private var ready: Bool {
        saved?.exists == true && !subject.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !draftBody.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Department chairs email").font(.title2.bold())
                Spacer()
                DatePicker("Reporting week", selection: $day, in: ...Date(), displayedComponents: .date)
                    .disabled(changed || busy)
            }
            if let emails = saved?.emails, !emails.isEmpty {
                Picker("Recipient", selection: $recipient) {
                    ForEach(ChairDraftSelection.recipients) { recipient in
                        if emails[recipient.id] != nil { Text(recipient.name).tag(recipient.id) }
                    }
                }.disabled(changed || busy)
                .onChange(of: recipient) { _ in populateEditor() }
            }
            if let selected {
                if let label = selected.compositionLabel {
                    Text(label).font(.callout).foregroundStyle(.secondary)
                }
                if !selected.coverage.isEmpty {
                    DisclosureGroup("Source coverage and review notes") {
                        ForEach(Array(selected.coverage.enumerated()), id: \.offset) { _, line in
                            Text(line).frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                if editing {
                    TextField("Subject", text: $subject).textFieldStyle(.roundedBorder).disabled(store.offline || busy)
                    TextEditor(text: $draftBody).font(.body).accessibilityLabel("Department chairs email body")
                        .disabled(store.offline || busy)
                        .overlay(RoundedRectangle(cornerRadius: 5).strokeBorder(.quaternary))
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            Text(subject).font(.title2.bold()).accessibilityAddTraits(.isHeader)
                            Text(draftBody).font(.body).lineSpacing(4)
                        }.textSelection(.enabled).frame(maxWidth: 620, alignment: .leading).padding(20)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.background, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
                }
            } else {
                Text(busy ? "Loading draft…" : "No saved draft for this week.").foregroundStyle(.secondary)
                Spacer()
            }
            if !notice.isEmpty { Text(notice).font(.callout).foregroundStyle(.secondary) }
            HStack {
                Button("Close") { if changed { confirmClose = true } else { dismiss() } }
                    .keyboardShortcut(.cancelAction).disabled(busy)
                Spacer()
                Button("Copy email") {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString("Subject: " + subject + "\n\n" + draftBody, forType: .string)
                    notice = "Subject and email body copied."
                }.disabled(!ready || busy)
                if editing {
                    Button("Save edits") { Task { await save() } }
                        .keyboardShortcut(.defaultAction).disabled(!ready || !changed || busy || store.offline)
                    Button("Cancel edits") { populateEditor() }.disabled(busy)
                } else {
                    if let selected, ready {
                        MemorySuggestionButton(store: store, source: "Department chair draft · " + DeanMeetingSchedule(now: day).key + " · " + recipient,
                            text: "Saved department chair draft: " + selected.subject + "\n\n" + selected.body)
                    }
                    Button("Edit email") { editing = true }.disabled(!ready || busy || store.offline)
                }
            }
        }
        .padding(22).frame(minWidth: 700, idealWidth: 800, minHeight: 540, idealHeight: 680)
        .environment(\.timeZone, DeanMeetingSchedule.zone)
        .interactiveDismissDisabled(changed || busy)
        .confirmationDialog("Discard unsaved email edits?", isPresented: $confirmClose) {
            Button("Discard edits", role: .destructive) { dismiss() }
            Button("Keep editing", role: .cancel) {}
        }
        .task(id: path) { await load() }
    }

    private func apply(_ draft: ChairsDraft) {
        saved = draft
        if let emails = draft.emails, !emails.isEmpty, emails[recipient] == nil,
           let available = ChairDraftSelection.recipients.first(where: { emails[$0.id] != nil }) {
            recipient = available.id
        }
        populateEditor()
    }

    private func populateEditor() {
        editing = false
        subject = selected?.subject ?? ""
        draftBody = selected?.body ?? ""
        notice = ""
    }

    private func load() async {
        let requestedPath = path
        busy = true
        defer { if requestedPath == path { busy = false } }
        saved = nil
        subject = ""
        draftBody = ""
        notice = ""
        do {
            let draft = try await store.decode(ChairsDraft.self, requestedPath)
            guard !Task.isCancelled, requestedPath == path else { return }
            apply(draft)
        } catch {
            guard !Task.isCancelled, requestedPath == path else { return }
            notice = (error as? APIProblem)?.message ?? "Could not open this draft."
        }
    }

    private func save() async {
        guard let saved else { return }
        busy = true
        defer { busy = false }
        do {
            var payload: [String: Any] = ["expected_revision": saved.revision, "subject": subject, "body": draftBody]
            if saved.emails?[recipient] != nil { payload["recipient"] = recipient }
            apply(try await store.decode(ChairsDraft.self, path, method: "PUT", body: payload))
            notice = "Edits saved."
        } catch {
            notice = (error as? APIProblem)?.message ?? "Could not save your edits."
        }
    }
}
