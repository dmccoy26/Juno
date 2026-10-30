import SwiftUI
import Security

indirect enum TaskJSON: Decodable {
    case object([String: TaskJSON]), array([TaskJSON]), string(String), number(Double), bool(Bool), null
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode([String: TaskJSON].self) { self = .object(v) }
        else { self = .array(try c.decode([TaskJSON].self)) }
    }
    var value: Any {
        switch self {
        case .object(let v): return v.mapValues { $0.value }
        case .array(let v): return v.map { $0.value }
        case .string(let v): return v
        case .number(let v): return v
        case .bool(let v): return v
        case .null: return NSNull()
        }
    }
    var pretty: String {
        guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys, .fragmentsAllowed]) else { return "" }
        return String(data: data, encoding: .utf8) ?? ""
    }
}
struct TaskDockInfo: Decodable {
    let workspace_id: String; let device_id: String; let definitions: TaskJSON; let capabilities: [String: Bool]
    var sharing_version: Int?;var sharing: TaskJSON?;var retention_notice: String?;var sharing_restricted: Bool?
}
struct TaskDockTask: Decodable, Identifiable {
    let id: String; let fields: TaskJSON
    var title: String { text("title") ?? "Untitled task" }
    func text(_ key: String) -> String? { if case .object(let fields) = fields, case .string(let text) = fields[key] { return text }; return nil }
    func planningText(_ key: String) -> String? {
        guard case .object(let fields) = fields,case .object(let details) = fields["planning_details"],case .object(let fact) = details[key],case .string("provided") = fact["state"],case .string(let value) = fact["value"] else { return nil };return value
    }
    var planningBlockerFlag: String? {
        guard case .object(let fields) = fields,case .object(let details) = fields["planning_details"],case .object(let fact) = details["blockers"],case .string(let value) = fact["taskdock_flag"] else { return nil };return value
    }
    init(from decoder: Decoder) throws {
        fields = try TaskJSON(from: decoder)
        guard case .object(let object) = fields, case .string(let ident) = object["id"] else { throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "Missing task identity")) }
        id = ident
    }
}
struct TaskDockSnapshot: Decodable, Identifiable {
    let id: String; let origin: String; let fetched_at: String; let count: Int; let stale: Bool
    let error: String?; let info: TaskDockInfo; let sources: TaskJSON; let items: [TaskDockTask]
}
struct TaskDockHistory: Decodable { let items: [TaskJSON]; let read_at: String; let notice: String }
struct TaskDockState: Decodable { let snapshot: TaskDockSnapshot?; let error: String? }
struct TaskDockRefresh: Decodable { let review_required: Bool; let info: TaskDockInfo?; let snapshot: TaskDockSnapshot? }

enum TaskDockKeychain {
    static var service: String { (Bundle.main.bundleIdentifier ?? "com.dmccoy.juno") + ".taskdock" }
    static func query(_ origin: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: origin]
    }
    static func read(_ origin: String) throws -> String? {
        var q = query(origin); q[kSecReturnData as String] = true; q[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data, let text = String(data: data, encoding: .utf8) else { throw APIProblem(message: "Juno could not read the TaskDock token from Keychain.", status: 0) }
        return text
    }
    static func save(_ token: String, origin: String) throws {
        let q = query(origin)
        let data = Data(token.utf8)
        var status = SecItemUpdate(q as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var item = q; item[kSecValueData as String] = data
            item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            item[kSecAttrSynchronizable as String] = false
            status = SecItemAdd(item as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw APIProblem(message: "TaskDock was reached, but the token could not be saved in Keychain.", status: 0) }
    }
    static func forget(_ origin: String) throws {
        let status = SecItemDelete(query(origin) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw APIProblem(message: "Could not remove the TaskDock credential from Keychain.", status: 0) }
    }
}

struct TaskDockWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var origin = UserDefaults.standard.string(forKey: "taskdockOrigin") ?? "http://127.0.0.1:8100"
    @State private var token = ""
    @State private var state: TaskDockState?
    @State private var reviewing: TaskDockInfo?
    @State private var reviewOrigin: String?
    @State private var notice: String?
    @State private var busy = false
    @State private var selected: String?
    @State private var search = ""
    @State private var definitions = false
    @State private var settingsExpanded = false
    @State private var history: TaskDockHistory?
    @State private var historyTask: String?
    @State private var historyKind = ""
    func loadSavedHistory() async {
        history = nil
        guard let snapshot = state?.snapshot, let selected else { return }
        var parts = URLComponents(); parts.path = "/v1/taskdock/history"
        parts.queryItems = [URLQueryItem(name: "snapshot_id", value: snapshot.id), URLQueryItem(name: "task_id", value: selected), URLQueryItem(name: "kind", value: "updates")]
        if let saved = try? await store.decode(TaskDockHistory.self, parts.string!), self.selected == selected {
            history = saved; historyTask = selected; historyKind = "updates"
        }
    }
    func readHistory(task: TaskDockTask, kind: String) {
        guard let snapshot = state?.snapshot, !busy else { return }
        busy = true; notice = nil
        Task {
            defer { busy = false }
            do {
                guard let credential = try TaskDockKeychain.read(snapshot.origin) else { throw APIProblem(message: "Pair with TaskDock before reading history.", status: 0) }
                var parts = URLComponents(); parts.path = "/v1/taskdock/history"
                parts.queryItems = [URLQueryItem(name: "task_id", value: task.id), URLQueryItem(name: "kind", value: kind)]
                let result = try await store.decode(TaskDockHistory.self, parts.string!, method: "POST", body: ["base_url": snapshot.origin, "token": credential, "expected_snapshot_id": snapshot.id])
                history = result; historyTask = task.id; historyKind = kind
            } catch { notice = (error as? APIProblem)?.message ?? "History could not be read. The previous history view has been kept." }
        }
    }
    var tasks: [TaskDockTask] { (state?.snapshot?.items ?? []).filter { search.isEmpty || $0.title.localizedCaseInsensitiveContains(search) } }
    func load() async {
        do {
            let loaded = try await store.decode(TaskDockState.self, "/v1/taskdock")
            if state?.snapshot?.id != loaded.snapshot?.id { history = nil; historyTask = nil }
            state = loaded
            if let id = store.currentConversation { try? await store.loadMessages(id) }
        }
        catch { notice = (error as? APIProblem)?.message ?? "Could not load the TaskDock snapshot." }
    }
    func refresh(accept: Bool = false) {
        guard !busy else { return }
        busy = true; notice = nil
        let address = origin.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        Task {
            defer { busy = false }
            do {
                guard store.sharedProfile == nil else { throw APIProblem(message: "Manage TaskDock on the work Mac.", status: 0) }
                let credential = token.isEmpty ? try TaskDockKeychain.read(address) ?? "" : token
                guard !credential.isEmpty else { throw APIProblem(message: "Paste the dedicated Juno token from TaskDock Settings → Connections.", status: 0) }
                var body: [String: Any] = ["base_url": address, "token": credential]
                if let snapshot = state?.snapshot { body["expected_snapshot_id"] = snapshot.id }
                if accept, let review = reviewing, reviewOrigin == address {
                    body["reviewed_workspace_id"] = review.workspace_id; body["reviewed_device_id"] = review.device_id
                }
                let response = try await store.decode(TaskDockRefresh.self, "/v1/taskdock/refresh", method: "POST", body: body)
                try TaskDockKeychain.save(credential, origin: address)
                token = ""; UserDefaults.standard.set(address, forKey: "taskdockOrigin")
                if response.review_required {
                    reviewing = response.info; reviewOrigin = address
                    notice = "Review this TaskDock installation before importing. Previous snapshots stay separate."
                } else {
                    reviewing = nil; reviewOrigin = nil
                    notice = "Complete snapshot saved. TaskDock remains the task system of record."
                }
                await load()
            } catch {
                notice = (error as? APIProblem)?.message ?? "TaskDock could not be refreshed. The previous snapshot has been kept."
                await load()
            }
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("TaskDock · read-only").font(.title2.bold())
            Text("Review TaskDock’s saved tasks here. Connection settings are below when you need them.").foregroundStyle(.secondary)
            if store.sharedProfile == nil {
            HStack { Button("Refresh from TaskDock") { reviewing = nil;refresh() }.disabled(busy || !store.connected); if busy { ProgressView().controlSize(.small) } }
            DisclosureGroup("TaskDock connection settings",isExpanded:$settingsExpanded) {
            Text("Enable Juno access in TaskDock Settings → Connections. Use the dedicated token; it stays in this Mac’s Keychain.").font(.caption).foregroundStyle(.secondary)
            HStack {
                TextField("Local TaskDock API address", text: $origin).textFieldStyle(.roundedBorder)
                SecureField("Dedicated Juno token (leave blank to use Keychain)", text: $token).textFieldStyle(.roundedBorder)
            }.disabled(busy)
            HStack {
                Button("Connect / refresh snapshot") { reviewing = nil; refresh() }.disabled(busy || !store.connected)
                Button("Forget saved token") {
                    do { try TaskDockKeychain.forget(origin.trimmingCharacters(in: CharacterSet(charactersIn: "/"))); token = ""; reviewing = nil; notice = "Token removed from this Mac’s Keychain. Saved snapshots remain. Revoke access in TaskDock to invalidate the token." }
                    catch { notice = (error as? APIProblem)?.message }
                }.disabled(busy)
                if busy { ProgressView().controlSize(.small) }
            }
            if let review = reviewing {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Review connection").font(.headline)
                    Text("Workspace: \(review.workspace_id)\nInstallation: \(review.device_id)").font(.caption).textSelection(.enabled)
                    Button("Use this workspace and installation") { refresh(accept: true) }.disabled(busy || origin.trimmingCharacters(in: CharacterSet(charactersIn: "/")) != reviewOrigin)
                }.padding(12).background(.orange.opacity(0.1))
            }
            }
            } else { Text("This laptop reads the work Mac’s dated TaskDock snapshot. Manage pairing and refresh TaskDock on the work Mac.").foregroundStyle(.secondary) }
            if let notice { Text(notice).foregroundStyle(.secondary).textSelection(.enabled) }
            if let snapshot = state?.snapshot {
                if let version = snapshot.info.sharing_version {
                    Text("Controlled sharing • version \(version). Change shared fields in TaskDock Settings → Juno.").font(.caption).foregroundStyle(.secondary)
                    DisclosureGroup("Shared information groups") { Text(snapshot.info.sharing?.pretty ?? "Unknown selection").font(.caption).textSelection(.enabled) }
                } else { Text("Legacy task scope. Optional planning facts are not shared. Choose them in TaskDock Settings → Juno.").font(.caption).foregroundStyle(.secondary) }
                if let notice = snapshot.info.retention_notice { Text(notice).foregroundStyle(.orange) }
                TimelineView(.periodic(from: .now, by: 60)) { tick in
                    let parser = ISO8601DateFormatter()
                    let _ = parser.formatOptions.insert(.withFractionalSeconds)
                    let date = parser.date(from: snapshot.fetched_at) ?? ISO8601DateFormatter().date(from: snapshot.fetched_at) ?? .distantPast
                    let stale = snapshot.stale || tick.date.timeIntervalSince(date) > 900
                    Text("\(snapshot.count) tasks · Juno saved: \(scheduleDate(snapshot.fetched_at))\(stale ? " · STALE — refresh before relying on this" : " · saved snapshot; provider freshness shown separately")").font(.caption).foregroundStyle(stale ? .orange : .secondary)
                }
                if let error = state?.error { Text(error).foregroundStyle(.orange) }
                DisclosureGroup("TaskDock source freshness (separate from Juno’s read time)") { Text(snapshot.sources.pretty).font(.caption.monospaced()).textSelection(.enabled).frame(maxHeight: 110) }
                HSplitView {
                    VStack {
                        TextField("Filter saved tasks", text: $search).textFieldStyle(.roundedBorder)
                        List(selection: $selected) {
                            ForEach(tasks) { task in
                                VStack(alignment: .leading) { Text(task.title); Text(task.text("status_name") ?? task.text("behavior") ?? "Status unknown").font(.caption).foregroundStyle(.secondary) }.tag(task.id)
                            }
                        }
                    }.frame(minWidth: 240, idealWidth: 300)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 12) {
                            if let task = snapshot.items.first(where: { $0.id == selected }) {
                                Text(task.title).font(.headline)
                                Text("Recorded TaskDock fields · unknown values stay unknown · source content is displayed as plain text").font(.caption).foregroundStyle(.secondary)
                                Button("Plan this task in Juno") { store.planningTaskID = task.id; store.section = "Plan" }.disabled(["completed","archived","done"].contains(task.text("behavior") ?? ""))
                                TaskDockDetails(task: task, info: snapshot.info)
                                HStack {
                                    if snapshot.info.capabilities["read_updates"] == true { Button("Read updates") { readHistory(task: task, kind: "updates") }.disabled(busy) }
                                    if snapshot.info.capabilities["read_activity"] == true { Button("Read activity") { readHistory(task: task, kind: "activity") }.disabled(busy) }
                                }
                                if let history, historyTask == task.id {
                                    Text("\(historyKind.capitalized) · read \(history.read_at)").font(.caption.bold())
                                    Text(history.notice).font(.caption).foregroundStyle(.secondary)
                                    if history.items.isEmpty { Text("No recorded history.") }
                                    ForEach(Array(history.items.enumerated()), id: \.offset) { _, item in Text(item.pretty).font(.caption.monospaced()).textSelection(.enabled) }
                                }
                                DisclosureGroup("Original recorded fields") { Text(task.fields.pretty).font(.caption.monospaced()).textSelection(.enabled) }
                            } else { Text("Select a task to review its recorded fields, blockers and parent link.").foregroundStyle(.secondary) }
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(12)
                    }.frame(minWidth: 350)
                }
                DisclosureGroup("Field definitions", isExpanded: $definitions) { ScrollView { Text(snapshot.info.definitions.pretty).font(.caption.monospaced()).textSelection(.enabled) }.frame(maxHeight: 100) }
            } else {
                if let error = state?.error { Text(error).foregroundStyle(.orange) }
                Spacer(); Text("No complete TaskDock snapshot saved yet.").foregroundStyle(.secondary); Spacer()
            }
            Text("TaskDock stays read-only. Provider refresh and task changes happen in TaskDock. Chat can use selected dated task excerpts; suggested hours are estimates.").font(.caption).foregroundStyle(.secondary)
        }.padding(22).task { await load();if state?.snapshot == nil { settingsExpanded = true } }.onChange(of:reviewing?.workspace_id) { id in if id != nil { settingsExpanded = true } }.onChange(of: selected) { _ in Task { await loadSavedHistory() } }
    }
}


struct TaskDockDetails: View {
    let task: TaskDockTask
    let info: TaskDockInfo
    var values: [String: TaskJSON] { if case .object(let fields) = task.fields { return fields }; return [:] }
    func display(_ key: String) -> String {
        guard let v = values[key] else { return "Unknown" }
        switch v {
        case .null: return "Unknown"
        case .string(let s): return s.isEmpty ? "None recorded" : s
        default: return v.pretty
        }
    }
    func definition(_ collection: String, id: TaskJSON?) -> String? {
        guard case .object(let definitions) = info.definitions, case .array(let rows) = definitions[collection], let id else { return nil }
        for row in rows {
            if case .object(let fields) = row, (fields["id"] ?? fields["value"])?.pretty == id.pretty, case .string(let name) = fields["name"] { return name }
        }
        return nil
    }
    var custom: [(String, String)] {
        guard case .object(let fields) = values["custom_values"] else { return [] }
        return fields.sorted { $0.key < $1.key }.map { (definition("custom_fields", id: .string($0.key)) ?? "Unrecognized field (\($0.key))", $0.value.pretty) }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Status: \(display("status_name")) · source status: \(display("source_status"))")
            Text("Source completion flag: \(display("source_completed")) · native task: \(display("native"))").font(.caption).foregroundStyle(.secondary)
            Text("Owner: \(display("owner"))")
            Text("Priority: \(definition("priorities", id: values["priority"]) ?? display("priority"))")
            Text("Starts: \(display("start_date")) · Due: \(display("due_date"))")
            Text("Completion time: \(display("completed_at"))")
            Text("Blocker: \(display("blocked_reason"))")
            Text("Blocked since: \(display("blocked_since"))")
            Text("Parent: \(task.text("parent_title") ?? task.text("parent_id") ?? "None recorded")")
            Text("Category: \(display("category_name"))")
            TaskDockRequestFacts(task:task)
            Text("Description").font(.caption.bold()); Text(display("description"))
            Text("Latest update").font(.caption.bold()); Text(display("latest_update"))
            ForEach(Array(custom.enumerated()), id: \.offset) { _, field in Text("\(field.0): \(field.1)") }
        }.textSelection(.enabled)
    }
}


struct TaskDockRequestFacts: View {
    let task: TaskDockTask
    private let labels = ["issue_description":"Issue description","requested_outcome":"Requested outcome","building":"Building","room":"Room","equipment":"Affected equipment","requester":"Requester","contact":"Access / contact person","impact":"Operational impact","reported_priority":"Reported priority","troubleshooting":"Troubleshooting attempted","blockers":"Blockers","dependencies":"Dependencies"]
    private func text(_ fields:[String:TaskJSON],_ key:String) -> String? { if case .string(let value) = fields[key] { return value };return nil }
    var body: some View {
        if case .object(let fields) = task.fields {
            if case .object(let details) = fields["planning_details"], !details.isEmpty {
                GroupBox("Shared request facts") {
                    VStack(alignment:.leading,spacing:10) {
                        ForEach(details.keys.sorted(),id:\.self) { key in
                            if case .object(let fact) = details[key] {
                                VStack(alignment:.leading,spacing:3) {
                                    Text(labels[key] ?? key).font(.subheadline.bold())
                                    Text(text(fact,"state") == "none" ? "Explicitly none" : text(fact,"state") == "provided" ? text(fact,"value") ?? "Not supplied" : "Not supplied / unknown")
                                    if let origin = text(fact,"origin") { Text("Source: " + origin).font(.caption).foregroundStyle(.secondary) }
                                    if let observed = text(fact,"updated_at") { Text("Recorded: " + scheduleDate(observed)).font(.caption).foregroundStyle(.secondary) }
                                    if let stamp = text(fact,"source_updated_at") { Text("Source updated: " + scheduleDate(stamp)).font(.caption).foregroundStyle(.secondary) }
                                    if case .bool(true) = fact["review_conflict"] { Text("Conflicts with TaskDock’s blocked flag — review before planning.").font(.caption).foregroundStyle(.orange) }
                                    if let flag = text(fact,"taskdock_flag") { Text("TaskDock flag: " + flag).font(.caption).foregroundStyle(.orange) }
                                }
                            }
                        }
                        if case .object(let readiness) = fields["planning_readiness"],let state = text(readiness,"state") {
                            Text(state == "limited_sharing" ? "Request completeness is limited by sharing." : state == "needs_information" ? "Request information is missing." : "Shared request details are complete; staffing still needs review.").font(.caption).foregroundStyle(.secondary)
                        }
                        Text("Only selected shared facts are shown. Estimates, skills, supervision, preparation and staffing still need your review.").font(.caption).foregroundStyle(.secondary)
                    }.padding(6).frame(maxWidth:.infinity,alignment:.leading)
                }
            }
            if case .object(let sample) = fields["source_updates"],case .array(let comments) = sample["items"] {
                DisclosureGroup("Saved source comment sample (\(comments.count))") {
                    Text("This is a dated sample, not a complete or live conversation.").font(.caption).foregroundStyle(.secondary)
                    if let read = text(sample,"read_at") { Text("Read: " + scheduleDate(read)).font(.caption) }
                    if let scope = text(sample,"scope") { Text(scope).font(.caption) }
                    if case .bool(let complete) = sample["complete"] { Text(complete ? "Sample reports complete within its stated scope." : "Partial sample — additional comments may be missing.").font(.caption) }
                    ForEach(Array(comments.enumerated()),id:\.offset) { _,item in
                        if case .object(let comment) = item { VStack(alignment:.leading) { if let author = text(comment,"author") { Text(author).font(.caption.bold()) };Text(text(comment,"body") ?? "");if let date = text(comment,"created_at") { Text(scheduleDate(date)).font(.caption).foregroundStyle(.secondary) } }.padding(.vertical,6) }
                    }
                }
            }
        }
    }
}
