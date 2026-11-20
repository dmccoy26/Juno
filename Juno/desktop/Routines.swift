import SwiftUI
import AppKit
import UniformTypeIdentifiers

// Keep footer actions on screen; the form/document body remains scrollable.
func junoSheetHeight(_ preferred: CGFloat, visibleHeight: CGFloat? = nil) -> CGFloat {
    let available = visibleHeight ?? NSApp.keyWindow?.screen?.visibleFrame.height ?? NSScreen.main?.visibleFrame.height ?? 900
    return min(preferred, max(260, available - 100))
}

private func routineDate(_ value: String) -> Date? {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = DeanMeetingSchedule.zone
    formatter.dateFormat = "yyyy-MM-dd"
    formatter.isLenient = false
    return formatter.date(from: value)
}

struct RoutineDefinition: Codable, Equatable {
    var title = ""
    var description = ""
    var frequency = "weekly"
    var interval = 1
    var weekdays = [0]
    var month_day = 1
    var ordinal = 1
    var weekday = 0
    var month_end = "skip"
    var start_date = CheckInReminder.day(Date())
    var end_date: String?
    var creation_time = "09:00"
    var timezone = "America/Chicago"
    var due_offset_days = 0
    var missed_policy = "latest"
    var overlap_policy = "wait"
}

func routineScheduleLabel(_ rule: RoutineDefinition) -> String {
    let days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    let selected = Array(Set(rule.weekdays)).sorted()
    let cadence: String
    switch rule.frequency {
    case "daily": cadence = rule.interval == 1 ? "Daily" : "Every \(rule.interval) days"
    case "weekly":
        let label = selected == [0, 1, 2, 3, 4] ? "Weekdays" : selected.compactMap { days.indices.contains($0) ? days[$0] : nil }.joined(separator: ", ")
        cadence = rule.interval == 1 ? label : "Every \(rule.interval) weeks · " + label
    case "monthly" where rule.interval == 12: cadence = "Annually · " + rule.start_date.dropFirst(5).prefix(2) + String(format: "-%02d", rule.month_day)
    case "monthly": cadence = (rule.interval == 1 ? "Monthly" : "Every \(rule.interval) months") + " · day \(rule.month_day)"
    default:
        let ordinal = rule.ordinal == -1 ? "last" : [1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"][rule.ordinal] ?? "selected"
        let day = days.indices.contains(rule.weekday) ? days[rule.weekday] : "weekday"
        cadence = (rule.interval == 1 ? "Monthly" : "Every \(rule.interval) months") + " · " + ordinal + " " + day
    }
    return cadence + " · " + rule.creation_time + " Central"
}
struct RoutineOccurrence: Decodable, Identifiable {
    let occurrence_date: String
    let creation_at: String
    let due_date: String
    var id: String { occurrence_date }
}
struct RoutineRecord: Decodable, Identifiable {
    let id: String
    let revision: Int
    let status: String
    let definition: RoutineDefinition
    let next_occurrences: [RoutineOccurrence]
    var updated_at:String? = nil
}
struct RoutineState: Decodable {
    let owner_id: String?
    let items: [RoutineRecord]
    let execution_available: Bool
    let notice: String
    let time_policy: String
}
struct RoutinePreview: Decodable { let items: [RoutineOccurrence] }

struct RecurringWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var state: RoutineState?
    @State private var selected: String?
    @State private var showEditor = false
    @State private var editing: RoutineRecord?
    @State private var historyRoutine: RoutineRecord?
    @State private var lifecycleRoutine: RoutineRecord?
    @State private var issue: String?
    @State private var showWriteSetup = false

    private var chosen: RoutineRecord? { state?.items.first { $0.id == selected } }
    private var canEdit: Bool { store.connected && !store.offline && store.sharedProfile == nil }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Recurring tasks").font(.largeTitle.bold()).accessibilityAddTraits(.isHeader)
                    Text("Plan routines for TaskDock’s Juno column.").foregroundStyle(.secondary)
                }
                Spacer()
                Button("New routine…") { editing = nil; showEditor = true }.disabled(!canEdit)
                Button("TaskDock write connection…") { showWriteSetup = true }.disabled(!canEdit)
                Button("Refresh") { Task { await load() } }
            }
            if !store.routineDeliveryNotice.isEmpty { Text(store.routineDeliveryNotice).font(.callout).foregroundStyle(.secondary) }
            if let issue { Text(issue).foregroundStyle(.orange) }
            if let state {
                Label(state.notice, systemImage: "pause.circle").font(.callout).foregroundStyle(.secondary)
                if !canEdit { Text("Edit routine definitions on the connected work Mac. Saved definitions can be read here.").font(.caption) }
                HSplitView {
                    List(state.items, selection: $selected) { item in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.definition.title).font(.headline)
                            Text(item.status.capitalized + " · " + routineScheduleLabel(item.definition)).font(.caption).foregroundStyle(.secondary)
                        }.padding(.vertical, 4).tag(item.id)
                    }.frame(minWidth: 220, idealWidth: 280, maxWidth: 350)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            if let chosen {
                                Text(chosen.definition.title).font(.title2.bold())
                                Text(routineScheduleLabel(chosen.definition)).font(.headline)
                                Text("Starts " + chosen.definition.start_date + (chosen.definition.end_date.map { " · ends " + $0 } ?? " · no end date")).font(.callout).foregroundStyle(.secondary)
                                if !chosen.definition.description.isEmpty { Text(chosen.definition.description).textSelection(.enabled) }
                                Label(chosen.status.capitalized + (chosen.status == "active" ? " · due occurrences are managed on the work Mac" : " · new creation is not running"), systemImage: "doc.badge.clock")
                                if canEdit, state.execution_available, chosen.status != "retired" {
                                    HStack {
                                        Button("Prepare TaskDock approval…") { Task { await managedAction(chosen, action:"approval-preview") } }
                                        if chosen.status == "active" {
                                            Button("Pause routine") { Task { await managedAction(chosen,action:"pause") } }
                                        } else {
                                            Button("Enable approved routine") { Task { await managedAction(chosen,action:"activate") } }
                                        }
                                        Button("Check due routines") { Task { await store.checkManagedRoutines();await load() } }
                                    }
                                    Text("Review the exact recurring rule in TaskDock before enabling it. Pausing stops new local creation; an already in-flight request may still finish. Created tasks and human edits are retained.").font(.caption).foregroundStyle(.secondary)
                                }
                                Text("Next five dates").font(.headline)
                                occurrenceList(chosen.next_occurrences)
                                Text(state.time_policy).font(.caption).foregroundStyle(.secondary)
                                HStack {
                                    Button("Edit routine…") { editing = chosen; showEditor = true }.disabled(!canEdit || chosen.status == "retired")
                                    Button("History…") { historyRoutine = chosen }.disabled(store.offline)
                                    Button(chosen.status == "retired" ? "Restore draft…" : "Retire draft…") { lifecycleRoutine = chosen }.disabled(!canEdit)
                                }
                            } else {
                                Text(state.items.isEmpty ? "No routines yet" : "Choose a routine").font(.title2)
                                Text(state.execution_available ? "Save a schedule, review its upcoming dates and approve its exact rule in TaskDock before enabling it." : "Save a schedule and review its upcoming dates. Connect the separate TaskDock writer before enabling delivery.").foregroundStyle(.secondary)
                            }
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(20)
                    }.frame(minWidth: 320)
                }
            } else { ProgressView("Loading routines…") }
        }.padding(24)
            .task { await load() }
            .onChange(of: store.section) { if $0 == "Recurring" { Task { await load() } } }
            .sheet(isPresented: $showEditor, onDismiss: { Task { await load() } }) {
                RoutineEditor(store: store, original: editing, ownerID: state?.owner_id)
            }
            .sheet(isPresented:$showWriteSetup,onDismiss:{Task { await load() }}) { RoutineWriteSetup(store:store) }
            .onChange(of:store.routineDeliveryRevision) { _ in Task { await load() } }
            .sheet(item: $historyRoutine) { RoutineHistoryView(store: store, routine: $0) }
            .confirmationDialog(lifecycleRoutine?.status == "retired" ? "Restore this routine as a draft?" : "Retire this routine?", isPresented: Binding(get: { lifecycleRoutine != nil }, set: { if !$0 { lifecycleRoutine = nil } })) {
                if let row = lifecycleRoutine {
                    Button(row.status == "retired" ? "Restore draft" : "Retire draft") {
                        Task {
                            do {
                                let _: RoutineRecord = try await store.decode(RoutineRecord.self, "/v1/recurring/" + row.id + "/lifecycle", method: "POST", body: ["expected_revision": row.revision, "action": row.status == "retired" ? "restore" : "retire"])
                                await load()
                            } catch { issue = (error as? APIProblem)?.message ?? "The routine was not changed." }
                            lifecycleRoutine = nil
                        }
                    }
                }
                Button("Cancel", role: .cancel) { lifecycleRoutine = nil }
            } message: { Text("Saved definitions, history and any created tasks are kept. Restoring a draft does not enable TaskDock delivery.") }
    }

    private func managedAction(_ row:RoutineRecord,action:String) async {
        do {
            guard let stamp=row.updated_at else { throw APIProblem(message:"Reload this routine before changing its delivery.",status:0) }
            var body:[String:Any] = ["expected_revision":row.revision,"expected_updated_at":stamp]
            if action != "pause" {
                let origin=UserDefaults.standard.string(forKey:"routineWriteOrigin") ?? ""
                guard let credential=try await credentialWork({try TaskDockKeychain.read(origin+"/managed-write-v2")}) else {
                    throw APIProblem(message:"Connect the separate managed-write credential first.",status:0)
                }
                body["base_url"]=origin;body["token"]=credential
            }
            let data=try await store.request("/v1/recurring/"+row.id+"/"+action,method:"POST",body:body)
            if action == "approval-preview" {
                let result=try JSONSerialization.jsonObject(with:data) as? [String:Any]
                issue=result?["notice"] as? String ?? "Review this exact rule in TaskDock, then enable it here."
            } else { issue=nil }
            await load()
        } catch { issue=(error as? APIProblem)?.message ?? "Routine delivery was not changed; review the saved state before retrying." }
    }
    private func load() async {
        do { state = try await store.decode(RoutineState.self, "/v1/recurring") }
        catch { issue = (error as? APIProblem)?.message ?? "Could not read routines. Reconnect and try again." }
    }
}

private func occurrenceList(_ items: [RoutineOccurrence]) -> some View {
    VStack(alignment: .leading, spacing: 10) {
        if items.isEmpty { Text("No dates in the upcoming preview window. Check the end date or recurrence rule.").foregroundStyle(.secondary) }
        ForEach(items) { item in
            VStack(alignment: .leading, spacing: 3) {
                Text(scheduleDate(item.creation_at))
                Text("Task due " + item.due_date).font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}

// Local recovery is separate from canonical records and scoped to their owner.
enum EditorRecovery {
    static func key(owner: String, kind: String, record: String) -> String {
        let scope = (try? JSONEncoder().encode([owner, kind, record])) ?? Data()
        return "juno.editorRecovery." + scope.base64EncodedString()
    }
    static func save<T: Encodable>(_ value: T, key: String, defaults: UserDefaults = .standard) {
        if let data = try? JSONEncoder().encode(value) { defaults.set(data, forKey: key) }
    }
    static func load<T: Decodable>(_ type: T.Type, key: String, defaults: UserDefaults = .standard) -> T? {
        guard let data = defaults.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
    static func clear(_ key: String, defaults: UserDefaults = .standard) { defaults.removeObject(forKey: key) }
}
struct RoutineEditorDraft: Codable {
    let rule: RoutineDefinition
    let requestID: String
    let revision: Int
}
struct ChairEditorDraft: Codable {
    let subject: String
    let body: String
    let revision: Int
    let selection: ReportEvidenceSelection?
}

private struct RoutineEditor: View {
    @ObservedObject var store: JunoStore
    let original: RoutineRecord?
    let ownerID: String?
    @Environment(\.dismiss) private var dismiss
    @State private var rule = RoutineDefinition()
    @State private var dates: [RoutineOccurrence] = []
    @State private var reviewed: RoutineDefinition?
    @State private var working = false
    @State private var issue: String?
    @State private var requestID = UUID().uuidString
    @State private var discard = false
    @State private var recoveryConflict = false
    @State private var recovering = true
    private let days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    private var changed: Bool { rule != (original?.definition ?? RoutineDefinition()) }
    private var recoveryKey: String? { ownerID.map { EditorRecovery.key(owner: $0, kind: "routine", record: original?.id ?? "new") } }
    private func retainDraft() {
        guard !recovering, let recoveryKey else { return }
        if changed {
            EditorRecovery.save(RoutineEditorDraft(rule: rule, requestID: requestID, revision: original?.revision ?? 0), key: recoveryKey)
        } else { EditorRecovery.clear(recoveryKey) }
    }
    private func discardDraft() {
        recovering = true
        if let recoveryKey { EditorRecovery.clear(recoveryKey) }
        store.unsavedSections.remove("Recurring routine")
    }

    private func dateBinding(_ key: WritableKeyPath<RoutineDefinition, String>) -> Binding<Date> {
        Binding(get: { routineDate(rule[keyPath: key]) ?? Date() }, set: { rule[keyPath: key] = CheckInReminder.day($0) })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(original == nil ? "New recurring routine" : "Edit recurring routine").font(.title2.bold()).padding(20)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Title").font(.headline)
                    TextField("For example, weekly printer checks", text: $rule.title).textFieldStyle(.roundedBorder)
                    Text("Task notes").font(.headline)
                    TextEditor(text: $rule.description).frame(height: 80).accessibilityLabel("Recurring task notes")
                    Picker("Repeat", selection: $rule.frequency) {
                        Text("Daily").tag("daily"); Text("Selected weekdays").tag("weekly")
                        Text("Monthly by date").tag("monthly"); Text("Monthly by weekday").tag("ordinal")
                    }
                    Stepper("Every \(rule.interval) " + (rule.frequency == "daily" ? (rule.interval == 1 ? "day" : "days") : rule.frequency == "weekly" ? (rule.interval == 1 ? "week" : "weeks") : (rule.interval == 1 ? "month" : "months")), value: $rule.interval, in: 1...52)
                    if rule.frequency == "weekly" {
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], alignment: .leading) {
                            ForEach(0..<7) { index in
                                Toggle(days[index], isOn: Binding(get: { rule.weekdays.contains(index) }, set: { enabled in
                                    rule.weekdays.removeAll { $0 == index }; if enabled { rule.weekdays.append(index); rule.weekdays.sort() }
                                }))
                            }
                        }
                    }
                    if rule.frequency == "monthly" {
                        Stepper("Day \(rule.month_day) of the month", value: $rule.month_day, in: 1...31)
                        Picker("If that date does not exist", selection: $rule.month_end) {
                            Text("Skip that month").tag("skip"); Text("Use the last day").tag("last_day")
                        }
                    }
                    if rule.frequency == "ordinal" {
                        Picker("Week", selection: $rule.ordinal) {
                            ForEach(1...5, id: \.self) { Text("\($0)").tag($0) }; Text("Last").tag(-1)
                        }
                        Picker("Weekday", selection: $rule.weekday) { ForEach(0..<7) { Text(days[$0]).tag($0) } }
                    }
                    DatePicker("Start", selection: dateBinding(\.start_date), displayedComponents: .date)
                    Toggle("End on a date", isOn: Binding(get: { rule.end_date != nil }, set: { rule.end_date = $0 ? rule.start_date : nil }))
                    if rule.end_date != nil {
                        DatePicker("End", selection: Binding(get: { routineDate(rule.end_date ?? rule.start_date) ?? Date() }, set: { rule.end_date = CheckInReminder.day($0) }), displayedComponents: .date)
                    }
                    Text("Creation time · Central").font(.headline)
                    DatePicker("Time", selection: Binding(get: {
                        let f = DateFormatter(); f.timeZone = DeanMeetingSchedule.zone; f.dateFormat = "HH:mm"
                        return f.date(from: rule.creation_time) ?? Date()
                    }, set: {
                        let f = DateFormatter(); f.timeZone = DeanMeetingSchedule.zone; f.dateFormat = "HH:mm"
                        rule.creation_time = f.string(from: $0)
                    }), displayedComponents: .hourAndMinute)
                    Stepper("Due \(rule.due_offset_days) days after occurrence", value: $rule.due_offset_days, in: 0...365)
                    Picker("After missed runs", selection: $rule.missed_policy) {
                        Text("Create only the latest missed task").tag("latest")
                        Text("Create each missed task").tag("all"); Text("Skip missed tasks").tag("skip")
                    }
                    Picker("If the previous task is still open", selection: $rule.overlap_policy) {
                        Text("Wait for the previous task").tag("wait"); Text("Allow separate tasks").tag("allow")
                    }
                    Button("Preview next five dates") { Task { await preview() } }.disabled(working || rule.title.trimmingCharacters(in: .whitespaces).isEmpty)
                    if reviewed == rule { occurrenceList(dates) }
                    Text("Draft only. Saving does not create TaskDock tasks, reserve time or assign a worker. Holidays are not excluded. DST uses the first repeated time and shifts nonexistent times forward.")
                        .font(.caption).foregroundStyle(.secondary)
                }.padding(20)
            }.disabled(working)
            if let issue { Text(issue).foregroundStyle(.orange).padding(.horizontal, 20) }
            if recoveryConflict {
                VStack(alignment: .leading, spacing: 8) {
                    Text("This recovered draft was based on an older revision. The saved routine has changed.")
                    Text("Current saved title: " + (original?.definition.title ?? ""))
                    Button("Discard recovered changes and use saved routine") {
                        discardDraft(); rule = original?.definition ?? RoutineDefinition(); recoveryConflict = false; recovering = false
                    }
                }.padding(.horizontal, 20)
            }
            Divider()
            HStack {
                Button("Cancel", role: .cancel) { if changed { discard = true } else { dismiss() } }.keyboardShortcut(.cancelAction)
                Spacer()
                Text(working ? "Working…" : reviewed == rule ? "Preview reviewed · draft only" : "Preview the dates before saving").font(.caption).foregroundStyle(.secondary)
                Button("Save routine draft") { Task { await save() } }.keyboardShortcut("s", modifiers: .command)
                    .buttonStyle(.borderedProminent).disabled(working || reviewed != rule || dates.isEmpty || recoveryConflict)
            }.padding(18).disabled(working)
        }.frame(width: 620, height: junoSheetHeight(700)).interactiveDismissDisabled(true)
            .environment(\.locale, Locale(identifier: "en_US"))
            .environment(\.timeZone, DeanMeetingSchedule.zone)
            .onAppear {
                if let original { rule = original.definition }
                if let recoveryKey, let local = EditorRecovery.load(RoutineEditorDraft.self, key: recoveryKey) {
                    rule = local.rule; requestID = local.requestID
                    recoveryConflict = local.revision != (original?.revision ?? 0)
                    issue = "Recovered an unsaved local draft. Preview its dates again before saving."
                }
                recovering = false
                if changed { store.unsavedSections.insert("Recurring routine") }
            }
            .onChange(of: rule) { _ in
                retainDraft()
                if changed { store.unsavedSections.insert("Recurring routine") } else { store.unsavedSections.remove("Recurring routine") }
            }
            .onDisappear { retainDraft(); store.unsavedSections.remove("Recurring routine") }
            .alert("Discard routine changes?", isPresented: $discard) {
                Button("Keep editing", role: .cancel) {}
                Button("Discard changes", role: .destructive) { discardDraft(); dismiss() }
            } message: { Text("Your saved routine will remain unchanged.") }
    }

    private func payload() throws -> [String: Any] {
        try JSONSerialization.jsonObject(with: JSONEncoder().encode(rule)) as! [String: Any]
    }
    private func preview() async {
        working = true; defer { working = false }; issue = nil
        do { dates = try await store.decode(RoutinePreview.self, "/v1/recurring/preview", method: "POST", body: payload()).items; reviewed = rule }
        catch { issue = (error as? APIProblem)?.message ?? "Could not preview this rule." }
    }
    private func save() async {
        working = true; defer { working = false }; issue = nil
        do {
            var value = try payload()
            if let original { value["expected_revision"] = original.revision }
            else { value["request_id"] = requestID }
            let _: RoutineRecord = try await store.decode(RoutineRecord.self, "/v1/recurring" + (original.map { "/" + $0.id } ?? ""), method: original == nil ? "POST" : "PUT", body: value)
            discardDraft()
            dismiss()
        } catch { issue = (error as? APIProblem)?.message ?? "Could not save. Your draft and retry identity remain here." }
    }
}

struct PurchaseItem: Decodable, Identifiable {
    let id: String
    let merchant: String
    let amount: String
    let currency: String
    let date: String
    let status: String
    var statusLabel: String {
        ["missing_receipt":"No receipt matched", "review":"Match needs review",
         "already_attached":"Helper reports receipt attached", "ambiguous":"Multiple possible matches",
         "not_checked":"Receipt not checked"][status] ?? "Unknown"
    }
}
struct PurchaseAssetChoice: Decodable, Identifiable { let id: String; let title: String; let location: String }
struct PurchaseAssetLink: Decodable { let expense_id: String; let asset_id: String; let active: Bool; let asset_title: String?; let recorded_at: String }
struct PurchaseTaskChoice: Decodable, Identifiable { let id: String; let title: String }
struct PurchaseTaskLink: Decodable {
    let expense_id: String; let active: Bool; let task_id: String; let workspace_id: String
    let task_title: String?; let recorded_at: String
}
private struct ConcurReportOrg: Decodable {
    let org: String
    let amount: String
}

private struct ConcurReportEvidence: Decodable, Identifiable {
    let id: String
    let title: String
    let source_status: String
    let observed_at: String
    let start: String
    let end: String
    let currency: String
    let total: String
    let allocation_state: String
    let org_totals: [ConcurReportOrg]

    private func display(_ value: String) -> String {
        Decimal(string: value, locale: Locale(identifier: "en_US_POSIX"))?
            .formatted(.currency(code: currency)) ?? currency + " " + value
    }

    func updateText(for audience: String) -> String {
        if audience == "Dean" { return meetingText }
        guard audience == "VISU", allocation_state == "verified",
              let amount = org_totals.first(where: { $0.org == "30405" }) else {
            return "No verified allocation for this audience in the reviewed report."
        }
        return "\(title) (\(start) to \(end))\nConcur status as of \(sourceReadDate(observed_at)): \(source_status)\nVISU (30405): \(display(amount.amount))"
    }

    var meetingText: String {
        let knownOrgNames = ["30400": "AHMX (30400)", "30405": "VISU (30405)"]
        var lines = ["\(title) (\(start) to \(end))",
                     "Concur status as of \(sourceReadDate(observed_at)): \(source_status)",
                     "Report total: \(display(total))"]
        if allocation_state == "verified" {
            lines += org_totals.map { "\(knownOrgNames[$0.org] ?? "Org " + $0.org): \(display($0.amount))" }
        } else {
            lines.append("Org totals unavailable in the reviewed Concur observation.")
        }
        return lines.joined(separator: "\n")
    }
}

struct HelperPeriod: Decodable { let state:String; let start:String?; let end:String? }
struct HelperReport: Decodable, Identifiable {
    let id:String;let source_status:String;let observed_at:String;let reporting_period:HelperPeriod;let submission_time_state:String
}
struct HelperRun: Decodable, Identifiable {
    let id:String;let operation:String;let started_at:String;let ended_at:String;let outcome:String;let coverage:[String:String];let sign_in_state:String
}
struct HelperExport: Decodable {
    let schema_version:Int;let helper_instance_id:String;let export_id:String;let created_at:String
    let observation_window:HelperPeriod;let completeness:[String:String];let reports:[HelperReport];let runs:[HelperRun]
}
struct HelperExportSummary: View {
    let helper:HelperExport
    var body:some View {
        DisclosureGroup("Helper reports and coverage") {
            VStack(alignment:.leading,spacing:10) {
                Text("Exported " + scheduleDate(helper.created_at)).font(.caption)
                Text("Requested window: " + (helper.observation_window.start ?? "Unknown") + " through " + (helper.observation_window.end ?? "Unknown") + ". This is not the report’s accounting period.").font(.caption)
                ForEach(helper.completeness.keys.sorted(),id: \.self) { key in
                    Text(key.capitalized + ": " + (helper.completeness[key] ?? "unknown").replacingOccurrences(of:"_",with:" "))
                }
                ForEach(helper.reports) { report in
                    VStack(alignment:.leading,spacing:4) {
                        Text("Report " + String(report.id.prefix(12))).font(.headline)
                        Text("Source status: " + report.source_status)
                        Text("Observed " + scheduleDate(report.observed_at)).font(.caption)
                        Text("Report period: " + (report.reporting_period.start ?? "Unknown") + " through " + (report.reporting_period.end ?? "Unknown") + "; submission time: " + report.submission_time_state.replacingOccurrences(of:"_",with:" ")).font(.caption)
                    }
                }
                Text("Orders were not searched by this helper version. No order count or delivery status is inferred.").font(.caption)
                Text("Latest " + String(min(20,helper.runs.count)) + " of " + String(helper.runs.count) + " run observations").font(.headline)
                ForEach(Array(helper.runs.suffix(20).reversed())) { run in
                    VStack(alignment:.leading,spacing:3) {
                        Text(run.operation.replacingOccurrences(of:"_",with:" ") + " · " + run.outcome + " · " + scheduleDate(run.ended_at))
                        Text("Sign-in: " + run.sign_in_state.replacingOccurrences(of:"_",with:" ")).font(.caption)
                        ForEach(run.coverage.keys.sorted(),id: \.self) { source in
                            Text(source + ": " + (run.coverage[source] ?? "unknown").replacingOccurrences(of:"_",with:" ")).font(.caption)
                        }
                    }
                }
                Text("Read-only reviewed evidence. Submission, approval, payment and receipt uploads remain in Concur Helper/Concur; nothing is sent by this import.").font(.caption).foregroundStyle(.secondary)
            }.frame(maxWidth:.infinity,alignment:.leading).textSelection(.enabled)
        }
    }
}
struct PurchasingState: Decodable {
    let items: [PurchaseItem]
    let id: String?
    let observed_at: String?
    let imported_at: String?
    let notice: String
    fileprivate var reports: [ConcurReportEvidence]? = nil
    var helper_export: HelperExport? = nil
    var links_revision: Int? = nil
    var links: [PurchaseTaskLink]? = nil
    var workspace_id: String? = nil
    var task_choices: [PurchaseTaskChoice]? = nil
    var link_notice: String? = nil
    var asset_choices: [PurchaseAssetChoice]? = nil
    var asset_links: [PurchaseAssetLink]? = nil
    var beacon_snapshot_id: String? = nil
    var beacon_instance: String? = nil
    var asset_notice: String? = nil
}
private struct PurchasingPreview: Decodable {
    let items: [PurchaseItem]
    let reports: [ConcurReportEvidence]?
    let helper_export:HelperExport?
    let preserves_expenses:Bool?
}

enum ConcurReconciliationPeriod: String {
    case week, month

    static func command(_ text: String) -> Self? {
        switch text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case "/concur week": return .week
        case "/concur month": return .month
        default: return nil
        }
    }

    func requestURL(on date: Date = Date()) -> URL? {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = DeanMeetingSchedule.zone
        calendar.firstWeekday = 2
        guard let interval = calendar.dateInterval(of: self == .week ? .weekOfYear : .month, for: date),
              let inclusiveEnd = calendar.date(byAdding: .day, value: -1, to: interval.end) else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        var parts = URLComponents()
        parts.scheme = "concur-helper"
        parts.host = "reconcile"
        parts.queryItems = [
            URLQueryItem(name: "id", value: UUID().uuidString),
            URLQueryItem(name: "period", value: rawValue),
            URLQueryItem(name: "start", value: formatter.string(from: interval.start)),
            URLQueryItem(name: "end", value: formatter.string(from: inclusiveEnd))
        ]
        return parts.url
    }

    @MainActor
    func open() async throws {
        let workspace = NSWorkspace.shared
        guard let app = workspace.urlForApplication(withBundleIdentifier: "local.concur-helper.mac"),
              let url = requestURL() else {
            throw APIProblem(message: "Open the current Concur Helper app on this Mac once, then try again.", status: 0)
        }
        let configuration = NSWorkspace.OpenConfiguration()
        configuration.activates = true
        _ = try await workspace.open([url], withApplicationAt: app, configuration: configuration)
    }
}

struct PurchasingWorkspace: View {
    @State private var linking: PurchaseItem?
    @State private var equipmentLinking: PurchaseItem?
    @State private var selectedExpense: String?
    @ObservedObject var store: JunoStore
    @State private var state: PurchasingState?
    @State private var search = ""
    @State private var issue: String?
    @State private var working = false
    @State private var pending: String?
    @State private var preview: [PurchaseItem] = []
    @State private var previewHelper:HelperExport?
    @State private var preservesExpenses = false
    @State private var previewReports: [ConcurReportEvidence] = []
    @State private var reviewingMeetingNotes = false
    @State private var reviewing = false
    @State private var observed = Date()
    @State private var jobNotice: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Purchasing").font(.largeTitle.bold()).accessibilityAddTraits(.isHeader)
                    Text("Review a dated Receipt Helper export.").foregroundStyle(.secondary)
                }
            }
            HStack {
                if store.sharedProfile == nil {
                    Menu("Request Concur Job") {
                        Button("Reconcile This Week") { requestJob(.week) }
                        Button("Reconcile This Month") { requestJob(.month) }
                    }
                    Button("Import helper export…") { chooseFile() }.disabled(working || store.offline || state == nil)
                }
                Button("Reload saved copy") { Task { await load() } }.disabled(working)
                if !store.meeting, let reports = state?.reports, !reports.isEmpty {
                    Button("Concur meeting update…") { reviewingMeetingNotes = true }
                }
            }
            if let jobNotice { Text(jobNotice).font(.callout).foregroundStyle(.secondary) }
            if let issue { Text(issue).foregroundStyle(.orange) }
            if let state {
                Text(state.notice).font(.callout).foregroundStyle(.secondary)
                if let helper = state.helper_export { ScrollView { HelperExportSummary(helper:helper) }.frame(maxHeight:260) }
                if let date = state.observed_at { Text("Helper observation: " + scheduleDate(date)).font(.caption) }
                if let date = state.imported_at { Text("Imported into Juno: " + scheduleDate(date)).font(.caption).foregroundStyle(.secondary) }
                TextField("Search merchant or expense ID", text: $search).textFieldStyle(.roundedBorder)
                if state.items.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Label("No expense rows imported", systemImage: "cart").font(.title2)
                        Text("Choose expenses.json or plan.json from Receipt Helper. Juno imports expense IDs, merchants, dates, exact amounts, currencies and receipt-match states. Local attachment paths and report links stay with the helper.")
                    }.padding(24)
                }
                List(state.items.filter { search.isEmpty || $0.merchant.localizedCaseInsensitiveContains(search) || $0.id.localizedCaseInsensitiveContains(search) }, selection: $selectedExpense) { item in
                    HStack(alignment: .top) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.merchant).font(.headline)
                            Text(item.date + " · " + item.id).font(.caption).foregroundStyle(.secondary)
                            Text(item.statusLabel).font(.callout)
                            if let link = state.asset_links?.first(where: { $0.expense_id == item.id }) {
                                Text(link.active ? "Equipment: " + (link.asset_title ?? link.asset_id) : "Equipment link needs review; source or expense changed").font(.caption).foregroundStyle(link.active ? Color.secondary : Color.orange)
                            }
                            if let link = state.links?.first(where: { $0.expense_id == item.id }) {
                                Text(link.active ? "Linked: " + (link.task_title ?? "Task") : "Previous link needs review; expense or task evidence changed").font(.caption).foregroundStyle(link.active ? Color.secondary : Color.orange)
                            }
                        }
                        Spacer()
                        Text(item.currency + " " + item.amount).monospacedDigit()
                    }.padding(.vertical, 6).tag(item.id)
                }
                HStack {
                    if let item = state.items.first(where: { $0.id == selectedExpense }),
                       search.isEmpty || item.merchant.localizedCaseInsensitiveContains(search) || item.id.localizedCaseInsensitiveContains(search) {
                        Text(item.merchant + " · " + item.currency + " " + item.amount).font(.callout).lineLimit(2)
                        Spacer()
                        Button("Review equipment link…") { equipmentLinking = item }.disabled(working || store.offline || state.links_revision == nil)
                        Button("Review task link…") { linking = item }
                            .disabled(working || store.offline || state.links_revision == nil)
                    } else { Text("Select an expense to review its task link.").font(.callout).foregroundStyle(.secondary) }
                }
                if state.links_revision == nil { Text("Task link review needs Juno 0.2.9 or later on the work Mac.").font(.caption).foregroundStyle(.secondary) }
            } else { ProgressView("Reading saved purchasing evidence…") }
        }.padding(24).task { await load() }
            .onChange(of: store.section) { if $0 == "Purchasing" { Task { await load() } } }
            .sheet(item: $equipmentLinking) { item in
                if let state { PurchaseAssetReview(store: store, item: item, state: state) { self.state = $0 } }
            }
            .sheet(item: $linking) { item in
                if let state { PurchaseLinkReview(store: store, item: item, state: state) { self.state = $0 } }
            }
            .sheet(isPresented: $reviewingMeetingNotes) {
                if let reports = state?.reports {
                    ConcurMeetingUpdate(reports: reports)
                }
            }
            .sheet(isPresented: $reviewing, onDismiss: { pending = nil; preview = []; previewReports = [] }) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Review purchasing import").font(.title2.bold())
                    Text(preservesExpenses ? "Run diagnostics only. Existing expense rows and their observation time will be retained." : "\(preview.count) expense records. This replaces only Juno’s saved purchasing copy.")
                    if let helper = previewHelper { ScrollView { HelperExportSummary(helper:helper) }.frame(maxHeight:190) }
                    DatePicker("When the helper observed these records", selection: $observed, in: ...Date(), displayedComponents: [.date, .hourAndMinute]).disabled(previewHelper != nil)
                    List {
                        ForEach(previewReports) { report in
                            Text(report.meetingText).textSelection(.enabled)
                        }
                        ForEach(preview) { item in
                            VStack(alignment: .leading) {
                                Text(item.merchant + " · " + item.currency + " " + item.amount)
                                Text(item.statusLabel).font(.caption)
                            }
                        }
                    }
                    if let issue { Text(issue).foregroundStyle(.orange) }
                    HStack {
                        Button("Cancel", role: .cancel) { reviewing = false }.keyboardShortcut(.cancelAction)
                        Spacer()
                        Button("Import reviewed copy") { Task { await importCopy() } }.buttonStyle(.borderedProminent)
                    }.disabled(working)
                }.padding(24).frame(width: 640, height: junoSheetHeight(540)).interactiveDismissDisabled(working)
                    .environment(\.locale, Locale(identifier: "en_US"))
                    .environment(\.timeZone, DeanMeetingSchedule.zone)
            }
    }

    private func load() async {
        do { state = try await store.decode(PurchasingState.self, "/v1/purchasing"); issue = nil }
        catch { issue = (error as? APIProblem)?.message ?? "Could not load purchasing evidence." }
    }
    private func requestJob(_ period: ConcurReconciliationPeriod) {
        jobNotice = nil
        issue = nil
        Task {
            do {
                try await period.open()
                jobNotice = "Opened Concur Helper. Review the request there."
            } catch {
                issue = (error as? APIProblem)?.message ?? "Could not open Concur Helper."
            }
        }
    }

    private func chooseFile() {
        let panel = NSOpenPanel(); panel.allowedContentTypes = [.json]; panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let handle = try FileHandle(forReadingFrom: url); defer { try? handle.close() }
            let data = try handle.read(upToCount: 4_000_001) ?? Data()
            guard data.count <= 4_000_000, let text = String(data: data, encoding: .utf8) else {
                throw APIProblem(message: "Choose a UTF-8 JSON export no larger than 4 MB.", status: 0)
            }
            working = true; observed = Date(); issue = nil
            Task {
                defer { working = false }
                do {
                    let result = try await store.decode(PurchasingPreview.self, "/v1/purchasing/preview", method: "POST",
                                                        body: ["content": text, "observed_at": ISO8601DateFormatter().string(from: observed)])
                    preview = result.items;previewHelper = result.helper_export;preservesExpenses = result.preserves_expenses ?? false
                    previewReports = result.reports ?? []
                    pending = text; reviewing = true
                } catch { issue = (error as? APIProblem)?.message ?? "The helper export could not be read." }
            }
        } catch { issue = (error as? APIProblem)?.message ?? "Could not read that export." }
    }
    private func importCopy() async {
        guard let pending else { return }; working = true; defer { working = false }
        do {
            var value: [String: Any] = ["content": pending, "observed_at": ISO8601DateFormatter().string(from: observed)]
            if let id = state?.id { value["expected_id"] = id }
            state = try await store.decode(PurchasingState.self, "/v1/purchasing/import", method: "POST", body: value)
            reviewing = false; issue = nil
        } catch { issue = (error as? APIProblem)?.message ?? "Import did not complete. Your earlier copy is retained." }
    }
}

private struct ConcurMeetingUpdate: View {
    let reports: [ConcurReportEvidence]
    @Environment(\.dismiss) private var dismiss
    @State private var selected: Set<String> = []
    @State private var copied = false
    @State private var audience = "Dean"

    private var text: String {
        reports.filter { selected.contains($0.id) }.map { $0.updateText(for: audience) }.joined(separator: "\n\n")
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Concur meeting update").font(.title2.bold())
            Text("Select reviewed reports and the audience for this update.")
            Picker("Audience", selection: $audience) {
                Text("Dean · all verified allocations").tag("Dean")
                Text("Alex · VISU allocation only").tag("VISU")
            }.onChange(of: audience) { _ in copied = false }
            Text("Other chair allocations are not inferred. Copying prepares text for your review; it does not update or send a report.").font(.caption).foregroundStyle(.secondary)
            List(reports) { report in
                Toggle(isOn: Binding(get: { selected.contains(report.id) }, set: {
                    if $0 { selected.insert(report.id) } else { selected.remove(report.id) }
                    copied = false
                })) {
                    Text(report.updateText(for: audience))
                }
            }
            HStack {
                Button("Close") { dismiss() }
                Spacer()
                if copied { Text("Copied").foregroundStyle(.secondary) }
                Button("Copy selected update") {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                    copied = true
                }.buttonStyle(.borderedProminent).disabled(text.isEmpty)
            }
        }.padding(24).frame(width: 640, height: junoSheetHeight(500))
    }
}

// The copy timestamp changes only after a successful import/read, never on a failed refresh.
func sourceReadDate(_ text: String) -> String {
    guard let date = providerDate(text) else { return "Date unavailable" }
    let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX")
    f.timeZone = TimeZone(identifier: "America/Chicago"); f.dateFormat = "EEE, MMM d, yyyy 'at' h:mm a 'Central'"
    return f.string(from: date)
}

struct SourceFreshnessPanel: View {
    @ObservedObject var store: JunoStore
    @State private var taskdock: TaskDockState?
    @State private var evidence: EvidenceState?
    @State private var taskError = false
    @State private var evidenceError = false
    @State private var busy = false
    private var sources: [EvidenceSnapshot] {
        (evidence?.items ?? []).filter { ["beacon", "smartsheet"].contains($0.kind) }
    }
    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Last successful source updates").font(.headline)
                    Spacer()
                    Button("Reload status") { Task { await load() } }.disabled(busy)
                    Button("Sources") { store.section = "Evidence" }
                }
                if let copy = taskdock?.snapshot {
                    Text("TaskDock · " + sourceReadDate(copy.fetched_at)).textSelection(.enabled)
                    if taskError { Text("Status unavailable; showing the previously loaded copy time.").foregroundStyle(.orange) }
                    else if taskdock?.error != nil || copy.error != nil { Text("Latest TaskDock refresh failed. Last successful copy retained.").foregroundStyle(.orange) }
                    else if copy.stale { Text("TaskDock copy needs a freshness review.").foregroundStyle(.orange) }
                } else { Text(taskError ? "TaskDock · status unavailable" : "TaskDock · no successful copy saved") }
                ForEach(sources) { copy in
                    VStack(alignment: .leading, spacing: 3) {
                        Text((copy.kind == "smartsheet" ? "Smartsheet archive" : "Beacon") + " · " + sourceReadDate(copy.fetched_at)).textSelection(.enabled)
                        if copy.error != nil { Text("Latest refresh failed; last successful copy retained.").foregroundStyle(.orange) }
                        else if copy.stale { Text("Dated copy; review freshness before acting.").foregroundStyle(.secondary) }
                    }
                }
                if evidenceError { Text("Other source status unavailable; any times shown are from the earlier status read.").foregroundStyle(.orange) }
                else if evidence != nil {
                    ForEach(["beacon", "smartsheet"].filter { kind in !sources.contains { $0.kind == kind } }, id: \.self) { kind in
                        Text((kind == "beacon" ? "Beacon" : "Smartsheet archive") + " · no successful copy saved").foregroundStyle(.secondary)
                    }
                }
                Text("These are Juno’s successful read/import times. Providers may have older updates. Reload status checks saved copies; open Sources to refresh a connection.")
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
            }.font(.callout).frame(maxWidth: .infinity, alignment: .leading).padding(4)
        }.task(id: "\(store.connected)|\(store.section)|\(store.offline)") { await load() }
    }
    private func load() async {
        busy = true; defer { busy = false }
        do { taskdock = try await store.decode(TaskDockState.self, "/v1/taskdock"); taskError = false }
        catch { taskError = true }
        do { evidence = try await store.decode(EvidenceState.self, "/v1/integrations"); evidenceError = false }
        catch { evidenceError = true }
    }
}

struct SourceHealthButton: View {
    @ObservedObject var store: JunoStore
    @State private var showing = false
    @State private var taskdock: TaskDockSnapshot?
    @State private var evidence: EvidenceState?
    @State private var issue: String?
    private var warning: Bool { taskdock?.stale == true || evidence?.items.contains(where: { $0.stale || $0.error != nil }) == true || issue != nil }

    var body: some View {
        Button { showing.toggle() } label: {
            Label(store.offline ? "Offline copy" : warning ? "Review source freshness" : "Source status",
                  systemImage: store.offline ? "wifi.slash" : warning ? "exclamationmark.triangle" : "externaldrive")
                .font(.callout)
        }.popover(isPresented: $showing) {
            VStack(alignment: .leading, spacing: 14) {
                Text("Saved source copies").font(.headline)
                Text("Juno’s read time and each provider’s update time are separate. Opening this panel does not refresh the providers.")
                    .font(.caption).foregroundStyle(.secondary)
                if let issue { Text(issue).foregroundStyle(.orange) }
                if let taskdock {
                    Text("TaskDock · " + (taskdock.stale ? "stale" : "saved copy"))
                    Text("Last successful update " + sourceReadDate(taskdock.fetched_at)).font(.caption)
                    Button("Open TaskDock connection") { showing = false; store.section = "TaskDock" }
                } else { Text("No TaskDock copy loaded").foregroundStyle(.secondary) }
                ForEach(evidence?.items ?? []) { source in
                    Divider()
                    Text(source.kind.capitalized + (source.error != nil ? " · refresh failed" : source.stale ? " · dated copy; review freshness" : " · saved copy"))
                    Text("Last successful update " + sourceReadDate(source.fetched_at)).font(.caption)
                    if let error = source.error { Text(error).font(.caption).foregroundStyle(.orange) }
                }
                HStack {
                    Button("Reload status") { Task { await load() } }
                    Spacer(); Button("Open sources") { showing = false; store.section = "Evidence" }
                }
            }.padding(20).frame(width: 390)
        }
        .task(id: "\(showing)|\(store.connected)|\(store.section)|\(store.offline)") { await load() }
    }
    private func load() async {
        do {
            taskdock = try await store.decode(TaskDockState.self, "/v1/taskdock").snapshot
            evidence = try await store.decode(EvidenceState.self, "/v1/integrations")
            issue = nil
        } catch { issue = "Could not refresh saved-source status. Review the last successful copy before relying on it." }
    }
}

struct ReportReviewRecord: Decodable, Identifiable {
    let audience: String
    let reviewed: Bool
    let reviewed_at: String?
    var id: String { audience }
}
struct ReportReviewState: Decodable { let items: [ReportReviewRecord] }

struct ReportReviewButton: View {
    @ObservedObject var store: JunoStore
    let kind: String
    let week: String
    let audience: String
    let revision: Int
    var onMarked: () -> Void = {}
    @State private var reviewed = false
    @State private var working = false
    @State private var issue: String?
    private var path: String { "/v1/reports/" + kind + "/" + week + "/review" }
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Button { Task { await update(mark: true) } } label: {
                Label(reviewed ? "Reviewed" : "Mark reviewed", systemImage: reviewed ? "checkmark.circle.fill" : "checkmark.circle")
            }.disabled(working || store.offline || revision < 1 || reviewed)
            if let issue { Text(issue).font(.caption).foregroundStyle(.orange) }
        }
        .task(id: path + "|" + audience + "|\(revision)") { await update(mark: false) }
    }
    private func update(mark: Bool) async {
        working = true; defer { working = false }
        do {
            let result = try await store.decode(ReportReviewState.self, path, method: mark ? "POST" : "GET",
                body: mark ? ["expected_revision": revision, "audience": audience] : nil)
            reviewed = result.items.first { $0.audience == audience }?.reviewed == true; issue = nil
            if mark { onMarked() }
        } catch { reviewed = false; issue = (error as? APIProblem)?.message ?? "Review status unavailable." }
    }
}

// Search only the authorized saved copy. No model request or write happens here.
struct JunoCommandPalette: View {
    @ObservedObject var store: JunoStore
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var tasks: [TaskDockTask] = []
    @State private var memories: [Memory] = []
    @State private var notice = ""
    @State private var busy = false
    @FocusState private var focused: Bool
    private let destinations = [
        ("Today", "Today", "sun.max"), ("Chat", "Chat", "bubble.left"),
        ("Issues", "Plan", "checklist"), ("Schedule", "Schedules", "calendar"),
        ("Recurring tasks", "Recurring", "repeat"), ("Purchasing", "Purchasing", "cart"),
        ("Team", "Workers", "person.2"), ("Reports", "Reports", "doc.text"),
        ("Memories", "Memories", "book.closed"), ("Daily check-in", "Check-in", "square.and.pencil"),
        ("TaskDock connection", "TaskDock", "link"), ("Sources", "Evidence", "tray"),
        ("Computers & sync", "Computers", "laptopcomputer")]
    private var key: String { query.trimmingCharacters(in: .whitespacesAndNewlines) }
    private var visibleTasks: [TaskDockTask] {
        guard !key.isEmpty else { return [] }
        return tasks.filter { task in
            // Field values are already limited by TaskDock's reviewed sharing grant.
            String(describing: task.fields.value).localizedCaseInsensitiveContains(key)
        }
    }
    private func go(_ section: String) { store.section = section; dismiss() }
    private func search() async {
        memories = []; notice = ""
        let requested = key
        guard !requested.isEmpty, !store.meeting else { return }
        busy = true; defer { busy = false }
        do {
            try await Task.sleep(nanoseconds: 250_000_000)
            try Task.checkCancellation()
            var parts = URLComponents(); parts.path = "/v1/memories"
            parts.queryItems = [URLQueryItem(name: "q", value: requested), URLQueryItem(name: "offset", value: "0")]
            let page = try await store.decode(MemoryPage.self, parts.string!)
            guard !Task.isCancelled, !store.meeting, requested == key else { return }
            memories = page.items
            if page.has_more { notice = "More memories match. Open Memories to continue searching." }
        } catch {
            if !Task.isCancelled, requested == key { notice = "Memory search is unavailable. You can still open a workspace or search the saved task copy." }
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                TextField("Search saved tasks, memories, or go to a workspace", text: $query)
                    .textFieldStyle(.roundedBorder).focused($focused).accessibilityLabel("Search Juno")
                Button("Close") { dismiss() }.keyboardShortcut(.cancelAction)
            }
            Text(store.meeting ? "Meeting mode: private memory search and private workspaces are hidden." : "Searches saved records. Asking Juno opens a chat draft for your review.")
                .font(.caption).foregroundStyle(.secondary)
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(destinations.filter { destination in
                        (!store.meeting || !["Memories", "Check-in", "Workers", "Purchasing", "Evidence"].contains(destination.1)) && (key.isEmpty || destination.0.localizedCaseInsensitiveContains(key))
                    }, id: \.1) { destination in
                        Button { go(destination.1) } label: { Label(destination.0, systemImage: destination.2).frame(maxWidth: .infinity, alignment: .leading).padding(5) }
                            .buttonStyle(.plain)
                    }
                    if !visibleTasks.isEmpty {
                        Divider(); Text("Saved TaskDock issues").font(.caption.bold())
                        ForEach(Array(visibleTasks.prefix(12))) { task in
                            Button {
                                store.planningTaskID = task.id
                                go("Plan")
                            } label: {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(task.title).lineLimit(2)
                                    Text("Open issue details · saved copy").font(.caption).foregroundStyle(.secondary)
                                }.frame(maxWidth: .infinity, alignment: .leading).padding(5)
                            }.buttonStyle(.plain)
                        }
                        if visibleTasks.count > 12 { Text("\(visibleTasks.count) matches. Narrow the search to see a specific issue.").font(.caption) }
                    }
                    if !store.meeting, !memories.isEmpty {
                        Divider(); Text("Memories").font(.caption.bold())
                        ForEach(memories.prefix(8)) { memory in
                            Button {
                                guard !store.meeting else { return }
                                store.query = key; store.items = memories; store.selected = memory.id
                                go("Memories")
                            } label: { Text(memory.text).lineLimit(2).frame(maxWidth: .infinity, alignment: .leading).padding(5) }.buttonStyle(.plain)
                        }
                    }
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            if busy { ProgressView("Searching saved memories…").controlSize(.small) }
            if !notice.isEmpty { Text(notice).font(.caption).foregroundStyle(.secondary) }
            HStack {
                Button("Settings…") { dismiss(); store.openSettings("Connections") }
                Spacer()
                Button("Ask Juno…") { store.prepareChat(key); dismiss() }
                    .disabled(key.isEmpty).buttonStyle(.borderedProminent)
            }
        }.padding(20).frame(width: 620, height: 480)
            .task { focused = true; do { tasks = try await store.decode(TaskDockState.self, "/v1/taskdock").snapshot?.items ?? [] } catch { notice = "Saved TaskDock copy is unavailable." } }
            .task(id: key + "|" + String(store.meeting)) { await search() }
            .onChange(of: store.meeting) { _ in memories = []; query = "" }
    }
}

struct ReportEvidenceItem: Decodable, Identifiable {
    let id: String; let text: String; let source: String; let state: String
}
struct ReportEvidencePacket: Decodable {
    let items: [ReportEvidenceItem]; let coverage: [String]; let token: String; let revision: Int
}
struct ReportEvidenceSelection: Codable, Equatable {
    let token: String; let selected_ids: [String]
}
struct ReportEvidencePreview: Decodable {
    let subject: String; let body: String; let coverage: [String]; let composition: String
    let token: String; let selected_ids: [String]; let expected_revision: Int
}
struct ChairEvidenceReview: View {
    @ObservedObject var store: JunoStore
    let week: String; let recipient: String; let revision: Int; let original: String
    let useDraft: (ReportEvidencePreview) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var packet: ReportEvidencePacket?
    @State private var selected = Set<String>()
    @State private var preview: ReportEvidencePreview?
    @State private var busy = false
    @State private var issue: String?
    private var path: String { "/v1/reports/chairs/" + week }
    private func load() async {
        busy = true; defer { busy = false }
        do {
            let fresh = try await store.decode(ReportEvidencePacket.self, path + "/evidence?recipient=" + recipient)
            guard fresh.revision == revision else { issue = "The saved draft changed. Close and reopen it before choosing evidence."; return }
            packet = fresh; selected = Set(fresh.items.map(\.id))
        } catch {
            issue = (error as? APIProblem)?.status == 404 ? "Reopen the saved draft, and make sure the work Mac runs Juno 0.2.8 or later to choose report evidence." : (error as? APIProblem)?.message ?? "Could not load this recipient’s saved evidence."
        }
    }
    private func generate() async {
        guard let packet else { return }; busy = true; issue = nil; defer { busy = false }
        do {
            preview = try await store.decode(ReportEvidencePreview.self, path + "/preview", method: "POST", body: [
                "recipient": recipient, "expected_revision": revision, "token": packet.token, "selected_ids": selected.sorted()])
        } catch { issue = (error as? APIProblem)?.message ?? "Could not prepare a comparison. The saved email is unchanged." }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(preview == nil ? "Choose this email’s evidence" : "Review new wording").font(.title2.bold())
            Text("Current saved records for this recipient. Preparing a preview never replaces the saved email or sends it.")
                .font(.callout).foregroundStyle(.secondary)
            if let preview {
                Text(preview.composition == "lm_studio" ? "Written with LM Studio · review every claim" : preview.composition == "fallback" ? "Model wording was unusable; factual fallback shown" : "Written from the checked saved records")
                    .font(.caption).foregroundStyle(.secondary)
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Text(preview.subject).font(.headline)
                        Text(preview.body).lineSpacing(4)
                        DisclosureGroup("Compare original saved email") { Text(original).font(.callout) }
                        DisclosureGroup("Source coverage and review notes") { ForEach(preview.coverage, id: \.self) { Text($0).font(.caption) } }
                    }.textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(12)
                }
            } else if let packet {
                HStack {
                    Text("\(selected.count) of \(packet.items.count) included").font(.headline)
                    Spacer()
                    Button("Select all") { selected = Set(packet.items.map(\.id)) }
                    Button("Clear selection") { selected = [] }
                }
                List(packet.items) { item in
                    Toggle(isOn: Binding(get: { selected.contains(item.id) }, set: { if $0 { selected.insert(item.id) } else { selected.remove(item.id) } })) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(item.text)
                            Text(item.source + " · " + (item.state == "last_update" ? "Last update; closure date unknown" : item.state.capitalized))
                                .font(.caption).foregroundStyle(.secondary)
                        }.padding(.vertical, 4)
                    }.toggleStyle(.checkbox)
                }
                if packet.items.isEmpty { Text("No reportable items are available for this recipient in the saved sources.").foregroundStyle(.secondary) }
                DisclosureGroup("Coverage and missing sources") { ForEach(packet.coverage, id: \.self) { Text($0).font(.caption) } }
            } else { Spacer() }
            if let issue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
            if busy { ProgressView(preview == nil && packet != nil ? "Preparing reviewed evidence…" : "Loading…").controlSize(.small) }
            HStack {
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction).disabled(busy)
                Spacer()
                if let preview {
                    Button("Change selection") { self.preview = nil }.disabled(busy)
                    Button("Use this draft") { useDraft(preview); dismiss() }.buttonStyle(.borderedProminent).disabled(busy)
                } else {
                    Button("Preview email") { Task { await generate() } }.buttonStyle(.borderedProminent)
                        .disabled(busy || selected.isEmpty || packet == nil || store.offline)
                }
            }
        }.padding(22).frame(width: 700, height: junoSheetHeight(650)).interactiveDismissDisabled(busy)
            .task { await load() }
    }
}

struct PurchaseLinkReview: View {
    @ObservedObject var store: JunoStore
    let item: PurchaseItem; let state: PurchasingState
    let saved: (PurchasingState) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var search = ""
    @State private var selected: String?
    @State private var busy = false
    @State private var issue: String?
    @State private var confirmUnlink = false
    private var existing: PurchaseTaskLink? { state.links?.first { $0.expense_id == item.id } }
    private var choices: [PurchaseTaskChoice] {
        (state.task_choices ?? []).filter { search.isEmpty || $0.title.localizedCaseInsensitiveContains(search) || $0.id.localizedCaseInsensitiveContains(search) }
    }
    private func save(remove: Bool = false) async {
        guard let snapshot = state.id,
              let task = remove ? existing?.task_id : selected,
              let workspace = remove ? existing?.workspace_id : state.workspace_id else { return }
        busy = true; defer { busy = false }
        do {
            let result = try await store.decode(PurchasingState.self, remove ? "/v1/purchasing/unlink" : "/v1/purchasing/link", method: "POST", body: [
                "expense_id": item.id, "snapshot_id": snapshot, "task_id": task,
                "workspace_id": workspace, "expected_revision": state.links_revision ?? 0])
            saved(result); dismiss()
        } catch { issue = (error as? APIProblem)?.message ?? "The link was not saved. Your selection is still here." }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Review purchase-to-task link").font(.title2.bold())
            Text(item.merchant + " · " + item.currency + " " + item.amount).font(.headline)
            Text(item.date + " · Expense " + item.id).font(.caption).foregroundStyle(.secondary)
            Text(state.link_notice ?? "Use a current work-Mac version to review task links.").font(.callout).foregroundStyle(.secondary)
            TextField("Search task title or exact ID", text: $search).textFieldStyle(.roundedBorder)
            List(choices, selection: $selected) { task in
                VStack(alignment: .leading, spacing: 3) {
                    Text(task.title)
                    Text(task.id).font(.caption).foregroundStyle(.secondary)
                }.padding(4).tag(task.id)
            }
            if let selected, let task = state.task_choices?.first(where: { $0.id == selected }) {
                Text("Link to: " + task.title).font(.headline)
                Text("Workspace: " + (state.workspace_id ?? "Unavailable")).font(.caption).foregroundStyle(.secondary)
            }
            if let issue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
            if busy { ProgressView("Saving reviewed reference…").controlSize(.small) }
            HStack {
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction)
                if existing != nil { Button("Remove link…", role: .destructive) { confirmUnlink = true } }
                Spacer()
                Button("Save reviewed link") { Task { await save() } }.buttonStyle(.borderedProminent)
                    .disabled(selected == nil || state.workspace_id == nil || store.offline)
            }.disabled(busy)
        }.padding(22).frame(width: 620, height: junoSheetHeight(580)).interactiveDismissDisabled(busy)
            .onAppear { if existing?.active == true { selected = existing?.task_id } }
            .confirmationDialog("Remove this Juno reference?", isPresented: $confirmUnlink) {
                Button("Remove link", role: .destructive) { Task { await save(remove: true) } }
                Button("Keep link", role: .cancel) {}
            } message: { Text("The expense and TaskDock task are kept. The previous reference remains in Juno’s link history.") }
    }
}

struct SourcesWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var visited = ["Overview"]
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Sources").font(.title2.bold())
                Spacer()
                Button("Connection settings…") { store.openSettings("Connections") }
            }.padding(.horizontal, 24).padding(.top, 18)
            Picker("Sources view", selection: $store.sourcesTab) {
                Text("Status").tag("Overview")
                Text("TaskDock").tag("TaskDock")
                Text("Saved records").tag("Records")
            }.pickerStyle(.segmented).frame(maxWidth: 500).padding(.horizontal, 24).padding(.vertical, 14)
            Divider()
            ZStack {
                ForEach(visited, id: \.self) { tab in
                    Group {
                        if tab == "TaskDock" { TaskDockWorkspace(store: store, embedded: true) }
                        else if tab == "Records" { IntegrationsWorkspace(store: store) }
                        else { SourceOverview(store: store) }
                    }.opacity(store.sourcesTab == tab ? 1 : 0).disabled(store.sourcesTab != tab)
                        .allowsHitTesting(store.sourcesTab == tab).accessibilityHidden(store.sourcesTab != tab)
                }
            }.frame(maxWidth: .infinity, maxHeight: .infinity)
        }.onAppear { if !visited.contains(store.sourcesTab) { visited.append(store.sourcesTab) } }
            .onChange(of: store.sourcesTab) { if !visited.contains($0) { visited.append($0) } }
    }
}

struct SourceOverview: View {
    @ObservedObject var store: JunoStore
    @State private var taskdock: TaskDockState?
    @State private var records: EvidenceState?
    @State private var busy = false
    @State private var issue: String?
    private func load() async {
        busy = true; issue = nil; defer { busy = false }
        do { taskdock = try await store.decode(TaskDockState.self, "/v1/taskdock") }
        catch { taskdock = nil; issue = "TaskDock’s saved status could not be read." }
        do { records = try await store.decode(EvidenceState.self, "/v1/integrations") }
        catch { records = nil; issue = (issue.map { $0 + " " } ?? "") + "Other saved-source statuses could not be read." }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack {
                    Text("What Juno can draw from").font(.title2.bold())
                    Spacer()
                    Button("Reload saved status") { Task { await load() } }.disabled(busy)
                }
                Text("These are dated copies, not continuous observation. Reloading status does not contact the original providers. Use the source’s connection controls to refresh it.")
                    .foregroundStyle(.secondary)
                if let issue { Text(issue).foregroundStyle(.orange) }
                if let snapshot = taskdock?.snapshot {
                    GroupBox {
                        VStack(alignment: .leading, spacing: 8) {
                            Label("TaskDock", systemImage: "checklist").font(.headline)
                            Text("\(snapshot.items.count) tasks · last successful update " + sourceReadDate(snapshot.fetched_at))
                            if snapshot.stale { Label("Saved copy needs a freshness review", systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
                            if let error = taskdock?.error { Text(error).foregroundStyle(.orange) }
                            Button("Open TaskDock source") { store.sourcesTab = "TaskDock" }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                } else {
                    GroupBox("TaskDock") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("No saved TaskDock copy is available.")
                            Button("Set up TaskDock") { store.sourcesTab = "TaskDock" }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                ForEach(records?.items ?? []) { source in
                    GroupBox {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(source.kind.replacingOccurrences(of: "_", with: " ").capitalized).font(.headline)
                            Text("\(source.count) records · last successful update " + sourceReadDate(source.fetched_at))
                            if let error = source.error { Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(.orange) }
                            else if source.stale { Label("Dated copy; review freshness before acting", systemImage: "clock").foregroundStyle(.orange) }
                            Button("Browse saved records") { store.sourcesTab = "Records" }
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                if records?.items.isEmpty == true { Text("No additional source copies are saved yet.").foregroundStyle(.secondary) }
                Text("Receipt Helper expenses have their own reviewed import in Purchasing. Credentials stay in Keychain or the owning helper; source setup and sharing are explicit.").font(.callout).foregroundStyle(.secondary)
                Button("Open Purchasing") { store.section = "Purchasing" }
                if busy { ProgressView("Reading saved status…").controlSize(.small) }
            }.frame(maxWidth: 900, alignment: .leading).padding(24)
        }.task(id: String(store.connected) + "|" + store.section + "|" + store.sourcesTab) {
            if store.connected && store.section == "Evidence" && store.sourcesTab == "Overview" { await load() }
        }
    }
}

struct RoutineHistoryVersion: Decodable, Identifiable {
    let revision: Int; let definition: RoutineDefinition; let status: String; let action: String; let recorded_at: String
    var id: Int { revision }
}
struct RoutineHistoryOccurrence: Decodable, Identifiable {
    let id: String; let period_key: String; let local_date: String; let status: String; let reason: String; let task_id: String?; let updated_at: String
}
struct RoutineHistoryPage: Decodable {
    let versions: [RoutineHistoryVersion]; let occurrences: [RoutineHistoryOccurrence]; let has_more: Bool; let notice: String
}
struct RoutineHistoryView: View {
    @ObservedObject var store: JunoStore
    let routine: RoutineRecord
    @Environment(\.dismiss) private var dismiss
    @State private var versions: [RoutineHistoryVersion] = []
    @State private var occurrences: [RoutineHistoryOccurrence] = []
    @State private var hasMore = false
    @State private var offset = 0
    @State private var busy = false
    @State private var issue: String?
    @State private var notice = ""
    private func load() async {
        busy = true; defer { busy = false }
        do {
            let page = try await store.decode(RoutineHistoryPage.self, "/v1/recurring/" + routine.id + "/history?offset=\(offset)")
            versions += page.versions; occurrences += page.occurrences; offset += 20
            hasMore = page.has_more; notice = page.notice; issue = nil
        } catch { issue = store.offline ? "Reconnect to read routine history." : (error as? APIProblem)?.message ?? "Could not read this routine’s history." }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Routine history").font(.title2.bold())
            Text(routine.definition.title).font(.headline)
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Saved rules").font(.headline)
                    ForEach(versions) { version in
                        DisclosureGroup("Revision \(version.revision) · " + version.action.replacingOccurrences(of: "_", with: " ") + " · " + scheduleDate(version.recorded_at)) {
                            Text(version.definition.title).font(.headline)
                            Text(version.definition.description)
                            Text(version.status.capitalized + " · " + version.definition.frequency.capitalized + " · every \(version.definition.interval)")
                            Text("Starts " + version.definition.start_date + " · ends " + (version.definition.end_date ?? "when retired"))
                            Text("Missed runs: " + version.definition.missed_policy + " · previous open task: " + version.definition.overlap_policy)
                        }
                    }
                    Divider(); Text("Occurrences").font(.headline)
                    if occurrences.isEmpty { Text("No delivery occurrences are recorded. Saving a draft does not start a scheduler.").foregroundStyle(.secondary) }
                    ForEach(occurrences) { row in
                        VStack(alignment: .leading, spacing: 5) {
                            Text(row.local_date + " · " + row.status.replacingOccurrences(of: "_", with: " ").capitalized).font(.headline)
                            Text(row.reason)
                            if let task = row.task_id { Text("TaskDock task ID: " + task).font(.caption) }
                        }
                    }
                    if hasMore { Button("Load more history") { Task { await load() } }.disabled(busy) }
                }.textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
            }
            if let issue { Text(issue).foregroundStyle(.orange) }
            Text(notice).font(.caption).foregroundStyle(.secondary)
            HStack { if busy { ProgressView().controlSize(.small) }; Spacer(); Button("Close") { dismiss() }.keyboardShortcut(.cancelAction) }
        }.padding(22).frame(width: 700, height: junoSheetHeight(620)).task { await load() }
    }
}


struct TodayAgendaEvent: Identifiable {
    let id: String; let title: String; let start: Date; let end: Date; let allDay: Bool; let busy: Bool; let source: String
}
func agendaOverlaps(start: Date, end: Date, day: Date) -> Bool {
    var calendar = Calendar(identifier: .gregorian); calendar.timeZone = TimeZone(identifier: "America/Chicago")!
    let left = calendar.startOfDay(for: day)
    guard let right = calendar.date(byAdding: .day, value: 1, to: left) else { return false }
    return start < end && start < right && end > left
}
func agendaSpansDays(start: Date, end: Date) -> Bool {
    var calendar = Calendar(identifier: .gregorian); calendar.timeZone = TimeZone(identifier: "America/Chicago")!
    return !calendar.isDate(start, inSameDayAs: end)
}
func agendaClock(_ date: Date) -> String {
    let f = DateFormatter(); f.locale = Locale(identifier: "en_US_POSIX"); f.timeZone = TimeZone(identifier: "America/Chicago"); f.dateFormat = "h:mm a"; return f.string(from: date)
}
struct TodayCalendarAgenda: View {
    @ObservedObject var store: JunoStore
    @State private var snapshots: [EvidenceSnapshot] = []
    @State private var error: String?
    @State private var busy = false
    private var events: [TodayAgendaEvent] {
        snapshots.flatMap { source in
            source.items.compactMap { row -> TodayAgendaEvent? in
                guard row.status?.lowercased() != "cancelled", row.status?.lowercased() != "canceled",
                      let startText = row.start, let endText = row.end, let start = providerDate(startText), let end = providerDate(endText),
                      agendaOverlaps(start: start, end: end, day: Date()) else { return nil }
                return TodayAgendaEvent(id: source.id + ":" + row.id, title: row.heading, start: start, end: end,
                    allDay: row.all_day == true, busy: row.busy == true, source: source.kind.replacingOccurrences(of: "_", with: " ").capitalized)
            }
        }.sorted { a, b in a.start == b.start ? a.id < b.id : a.start < b.start }
    }
    var body: some View {
        GroupBox("Today’s calendar commitments") {
            VStack(alignment: .leading, spacing: 12) {
                Text(store.sharedProfile != nil ? "Calendar refresh is managed on your work Mac. Check this copy’s date and coverage." : store.calendarRefreshStatus).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                HStack { Text("Central time").font(.caption).foregroundStyle(.secondary); Spacer(); Button("Reload agenda") { Task { await load() } }.disabled(busy) }
                if let error { Text(error).foregroundStyle(.orange) }
                if snapshots.isEmpty { Text("No saved personal calendar is available. Connect a calendar in Sources; this does not mean the day is free.").foregroundStyle(.secondary) }
                else if events.isEmpty { Text("No events for today in these copies. Missing calendars or limited date ranges can leave commitments out.").foregroundStyle(.secondary) }
                ForEach(events) { event in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(event.allDay ? "All day" : agendaClock(event.start) + "–" + agendaClock(event.end)).font(.headline)
                        Text(store.meeting ? (event.busy ? "Busy calendar commitment" : "Calendar item · not marked busy") : event.title)
                        Text(event.source + (event.busy ? " · busy" : " · not marked busy")).font(.caption).foregroundStyle(.secondary)
                        if !event.allDay && agendaSpansDays(start: event.start, end: event.end) { Text("Spans more than one day; shown because it overlaps today.").font(.caption).foregroundStyle(.secondary) }
                    }
                    Divider()
                }
                DisclosureGroup("Calendar coverage") {
                    ForEach(snapshots) { source in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(source.kind.replacingOccurrences(of: "_", with: " ").capitalized).font(.headline)
                            Text("Last successful update: " + sourceReadDate(source.fetched_at)).font(.caption)
                            if let start = source.details.start, let end = source.details.end { Text("Saved range: " + start + " through " + end + " (end may be exclusive)").font(.caption) }
                            else { Text("Date-range coverage not supplied.").font(.caption) }
                            if source.error != nil { Text("Refresh failed; showing the earlier copy.").foregroundStyle(.orange) }
                            else if source.stale { Text("Dated copy; refresh before relying on it.").foregroundStyle(.orange) }
                        }
                    }
                }
                Text("These are source events, not Juno holds. Duplicate events across calendars remain separate; missing events do not establish free time.").font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                Button("Open calendar sources") { store.section = "Evidence"; store.sourcesTab = "Records" }
            }.frame(maxWidth: .infinity, alignment: .leading).padding(8)
        }.task(id: "\(store.connected)|\(store.section)|\(store.offline)|\(store.calendarCopyRevision)") { await load() }
    }
    private func load() async {
        guard store.connected else { return }
        busy = true; defer { busy = false }
        do {
            let result = try await store.decode(EvidenceState.self, "/v1/integrations")
            snapshots = result.items.filter { ["calendar", "google_calendar", "outlook_calendar"].contains($0.kind) && $0.details.active != false && $0.details.tombstone != true }
            error = nil
        } catch { self.error = "Calendar status unavailable. Any displayed commitments are from the previously loaded copy." }
    }
}


struct PurchaseAssetReview: View {
    @ObservedObject var store: JunoStore
    let item: PurchaseItem; let state: PurchasingState; let saved: (PurchasingState) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var selected: String?
    @State private var search = ""
    @State private var busy = false
    @State private var issue: String?
    @State private var removing = false
    private var existing: PurchaseAssetLink? { state.asset_links?.first { $0.expense_id == item.id } }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Review purchase-to-equipment link").font(.title2.bold())
            Text(item.merchant + " · " + item.currency + " " + item.amount).font(.headline)
            Text(state.asset_notice ?? "Update the work Mac to review equipment links.").foregroundStyle(.secondary)
            if let existing { Text(existing.active ? "Current link: " + (existing.asset_title ?? existing.asset_id) : "Previous link unavailable in the current feed; review before reuse.") }
            TextField("Search equipment name, room or exact ID", text: $search).textFieldStyle(.roundedBorder)
            List((state.asset_choices ?? []).filter { search.isEmpty || [$0.title,$0.location,$0.id].contains { $0.localizedCaseInsensitiveContains(search) } }, selection: $selected) { asset in
                VStack(alignment: .leading) { Text(asset.title).font(.headline); Text(asset.location + " · " + asset.id).font(.caption).foregroundStyle(.secondary) }.tag(asset.id)
            }
            if let selected { Text("Selected exact equipment ID: " + selected).font(.callout).textSelection(.enabled) }
            if let issue { Text(issue).foregroundStyle(.orange) }
            HStack {
                Button("Cancel", role: .cancel) { dismiss() }.keyboardShortcut(.cancelAction)
                if existing != nil { Button("Remove link…", role: .destructive) { removing = true } }
                Spacer(); Button("Save reviewed equipment link") { Task { await save(remove: false) } }.disabled(selected == nil || busy || store.offline)
            }.disabled(busy)
        }.padding(24).frame(width: 620, height: junoSheetHeight(600)).interactiveDismissDisabled(busy)
        .confirmationDialog("Remove this Juno equipment reference?", isPresented: $removing) { Button("Remove link", role: .destructive) { Task { await save(remove: true) } }; Button("Cancel", role: .cancel) {} }
        .onAppear { if existing?.active == true { selected = existing?.asset_id } }
    }
    private func save(remove: Bool) async {
        guard let snapshot = state.id, let asset = remove ? existing?.asset_id : selected else { return }
        busy = true; defer { busy = false }
        var body: [String: Any] = ["expense_id":item.id,"snapshot_id":snapshot,"asset_id":asset,"expected_revision":state.links_revision ?? 0]
        if !remove { body["beacon_snapshot_id"] = state.beacon_snapshot_id; body["beacon_instance"] = state.beacon_instance }
        do { let result = try await store.decode(PurchasingState.self, remove ? "/v1/purchasing/asset-unlink" : "/v1/purchasing/asset-link", method: "POST", body: body); saved(result); dismiss() }
        catch { issue = (error as? APIProblem)?.message ?? "Link not saved. Your selection remains here; reload sources before retrying." }
    }
}

struct ManagedWriteInfo:Decodable {
    let instance_id:String;let workspace_id:String;let column_id:String;let column_name:String;let grant_id:String;let owner_id:String
    var scope:[String:Any] { ["instance_id":instance_id,"workspace_id":workspace_id,"column_id":column_id,"grant_id":grant_id,"owner_id":owner_id] }
}
struct ManagedWriteConnectionState:Decodable { let connection:ManagedWriteInfo?;let revision:Int }
struct RoutineWriteSetup:View {
    @ObservedObject var store:JunoStore
    @Environment(\.dismiss) private var dismiss
    @State private var origin=UserDefaults.standard.string(forKey:"routineWriteOrigin") ?? "http://127.0.0.1:8100"
    @State private var token=""
    @State private var info:ManagedWriteInfo?
    @State private var revision=0
    @State private var busy=false
    @State private var issue:String?
    private func credential() async throws -> String {
        if !token.isEmpty { return token }
        guard let saved=try await credentialWork({try TaskDockKeychain.read(origin+"/managed-write-v2")}) else { throw APIProblem(message:"Paste the separate TaskDock write credential here. Keep the read-only key unchanged.",status:0) }
        return saved
    }
    var body:some View {
        VStack(alignment:.leading,spacing:16) {
            Text("TaskDock managed task connection").font(.title2.bold())
            Text("In TaskDock Settings → Juno access, choose or create the exact Juno column and approve a separate managed-write credential. This does not grant Juno access to edit existing tasks, submit expenses or send email.")
            TextField("Local TaskDock API address",text:$origin).onChange(of:origin) { _ in info=nil }
            SecureField("Separate TaskDock managed-write credential",text:$token).onChange(of:token) { _ in info=nil }
            Button("Review destination") {
                Task { busy=true;defer { busy=false };do {
                    info=try await store.decode(ManagedWriteInfo.self,"/v1/recurring/probe",method:"POST",body:["base_url":origin,"token":try await credential()]);issue=nil
                } catch { issue=(error as? APIProblem)?.message ?? "The managed-write connection could not be reviewed." } }
            }
            if let info {
                Text("Destination: " + info.column_name).font(.headline)
                Text("Workspace: " + info.workspace_id + "\nInstallation: " + info.instance_id + "\nColumn: " + info.column_id).font(.caption).textSelection(.enabled)
                Text("Only explicitly approved routine versions can create matching due tasks. TaskDock enforces the destination and durable occurrence identity.").font(.callout)
            }
            if let issue { Text(issue).foregroundStyle(.orange) }
            Spacer()
            HStack {
                Button("Close") { dismiss() }.keyboardShortcut(.cancelAction)
                Spacer()
                Button("Use this reviewed destination") {
                    guard let info else { return }
                    Task { busy=true;defer { busy=false };do {
                        let credential=try await credential()
                        let result=try await store.decode(ManagedWriteConnectionState.self,"/v1/recurring/connection",method:"POST",body:["base_url":origin,"token":credential,"expected_revision":revision,"expected_scope":info.scope,"approved":true])
                        try await credentialWork { try TaskDockKeychain.save(credential,origin:origin+"/managed-write-v2") }
                        revision=result.revision;UserDefaults.standard.set(origin,forKey:"routineWriteOrigin");token="";dismiss()
                    } catch { issue=(error as? APIProblem)?.message ?? "Connection was not saved. Review it again." } }
                }.buttonStyle(.borderedProminent).disabled(info==nil)
            }
        }.padding(24).frame(width:640,height:junoSheetHeight(540)).disabled(busy).task {
            do { revision=try await store.decode(ManagedWriteConnectionState.self,"/v1/recurring/connection").revision }
            catch { issue="Could not read connection revision. Reopen this setup before saving." }
        }
    }
}

extension JunoStore {
    func checkManagedRoutines() async {
        guard connected,sharedProfile==nil,!offline,!routineDeliveryBusy,
              let origin=UserDefaults.standard.string(forKey:"routineWriteOrigin"),!origin.isEmpty else { return }
        routineDeliveryBusy=true;defer { routineDeliveryBusy=false }
        do {
            guard let token=try await credentialWork({try TaskDockKeychain.read(origin+"/managed-write-v2")}) else { return }
            _ = try await localRequest("/v1/recurring/tick",method:"POST",body:["base_url":origin,"token":token])
            routineDeliveryNotice="Managed routines checked " + sourceReadDate(ISO8601DateFormatter().string(from:Date())) + ". Review each routine’s history for task receipts and follow-up states."
            routineDeliveryRevision += 1
        } catch {
            routineDeliveryNotice=(error as? APIProblem)?.message ?? "Managed routine check could not finish. Prior receipts are retained; do not recreate unknown outcomes manually."
            routineDeliveryRevision += 1
        }
    }
}
