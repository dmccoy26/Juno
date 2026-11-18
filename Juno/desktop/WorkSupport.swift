import SwiftUI

struct WorkSourceRef: Codable, Equatable {
    let task_id: String
    let workspace_id: String
    let snapshot_id: String
}
struct WorkBookmark: Codable, Identifiable {
    let id: String
    let title: String
    let first_action: String
    let finish_point: String
    let where_stopped: String
    let blocker: String
    let status: String
    let source_ref: WorkSourceRef?
    let resume_count: Int
    let created_at: String
    let updated_at: String
    var comparisonText: String {
        "Work: " + title + "\nFirst action: " + first_action + "\nFinish point: " + finish_point + "\nStopped at: " + (where_stopped.isEmpty ? "Not recorded" : where_stopped) + "\nIn the way: " + (blocker.isEmpty ? "Nothing recorded" : blocker)
    }
}
struct WorkSupportState: Decodable {
    let owner_id: String
    let revision: Int
    let current: WorkBookmark?
    let parked: [WorkBookmark]
    let recent_finished: [WorkBookmark]
    let updated_at: String?
    let notice: String
}
struct WorkStepDraft: Codable, Equatable {
    var title = ""
    var first_action = ""
    var finish_point = ""
    var where_stopped = ""
    var blocker = ""
    var source_ref: WorkSourceRef?
    var canStart: Bool { [title, first_action, finish_point].allSatisfy { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty } }
    mutating func useTinyStep() {
        first_action = source_ref == nil ? "Open my notes for this work and write down one thing I can do next." : "Open the issue and write down the first thing to check."
        finish_point = "One next action is written down."
    }
}
enum WorkSupportAccess {
    static func canEdit(connected: Bool, offline: Bool, meeting: Bool, syncing: Bool, queued: Int) -> Bool {
        connected && !offline && !meeting && !syncing && queued == 0
    }
}
private struct WorkEditorRequest: Identifiable {
    let mode: String
    let state: WorkSupportState
    var id: String { mode + ":" + (state.current?.id ?? "new") }
}

struct WorkSupportPanel: View {
    @ObservedObject var store: JunoStore
    let snapshot: TaskDockSnapshot?
    let planning: PlanningRecord?
    @State private var value: WorkSupportState?
    @State private var issue: String?
    @State private var busy = false
    @State private var editor: WorkEditorRequest?
    @State private var restarting = false
    private var editable: Bool { WorkSupportAccess.canEdit(connected: store.connected, offline: store.offline, meeting: store.meeting, syncing: store.syncing, queued: store.pendingEdits.count) }
    private var privacyKey: String { "\(store.connected)|\(store.offline)|\(store.meeting)|\(store.sharedProfile?.owner_id ?? "host")" }
    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Label("One small next step", systemImage: "arrow.right.circle").font(.title3.bold())
                    Spacer()
                    if !store.meeting { Button("Reload bookmark") { Task { await load() } }.disabled(busy || !store.connected) }
                }
                if store.meeting {
                    Text("Your personal work bookmark is hidden in Meeting mode.").foregroundStyle(.secondary)
                } else if let value {
                    if store.offline { Text("Saved bookmark from your offline copy. Reconnect to update it; no bookmark edit is queued offline in this version.").font(.callout).foregroundStyle(.secondary) }
                    if let current = value.current {
                        Text(current.title).font(.headline).textSelection(.enabled)
                        Label(current.status == "interrupted" ? "Your place is saved" : "Working on this step", systemImage: current.status == "interrupted" ? "bookmark.fill" : "play.circle")
                            .foregroundStyle(.secondary)
                        Text(current.first_action).font(.title2).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
                        Text("This step is finished when: " + current.finish_point).textSelection(.enabled)
                        if !current.where_stopped.isEmpty { Text("Where you stopped: " + current.where_stopped).textSelection(.enabled) }
                        if !current.blocker.isEmpty { Label("In the way: " + current.blocker, systemImage: "pause.circle").textSelection(.enabled) }
                        Text("Bookmark saved " + scheduleDate(current.updated_at)).font(.caption).foregroundStyle(.secondary)
                        ViewThatFits(in: .horizontal) {
                            HStack { controls(value, current) }
                            VStack(alignment: .leading, spacing: 10) { controls(value, current) }
                        }.disabled(!editable || busy)
                        if restarting {
                            Divider()
                            Text("Choose the easiest way back in.").font(.headline)
                            VStack(alignment: .leading, spacing: 8) {
                                Button("Make the first step smaller…") { editor = WorkEditorRequest(mode: "revise", state: value) }
                                Button("Name what is in the way…") { editor = WorkEditorRequest(mode: "blocker", state: value) }
                                Button("Park this and choose different work…") { editor = WorkEditorRequest(mode: "start", state: value) }
                            }.disabled(!editable || busy)
                        }
                        if let reference = current.source_ref {
                            Button("Open the saved issue context") { store.planningTaskID = reference.task_id; store.section = "Plan" }
                            Text("The bookmark keeps your chosen step. Source status may have changed; review the issue before doing work.").font(.caption).foregroundStyle(.secondary)
                        }
                    } else {
                        Text("Choose a piece of work, then make the first action small enough to begin.").foregroundStyle(.secondary)
                        Button("Help me get started…") { editor = WorkEditorRequest(mode: "start", state: value) }
                            .buttonStyle(.borderedProminent).disabled(!editable || busy)
                        if let last = value.recent_finished.first { Text("Last step finished: " + last.title).font(.callout).foregroundStyle(.secondary) }
                    }
                    if !value.parked.isEmpty {
                        DisclosureGroup("Saved for later · \(value.parked.count)") {
                            ForEach(value.parked) { saved in
                                VStack(alignment: .leading, spacing: 5) {
                                    Text(saved.title).font(.headline)
                                    Text(saved.first_action).textSelection(.enabled)
                                    if !saved.where_stopped.isEmpty { Text("Stopped at: " + saved.where_stopped).font(.caption) }
                                    Button(value.current == nil ? "Resume this step" : "Park current step and resume this") {
                                        Task { await perform("resume", state: value, bookmark: saved, switchCurrent: value.current != nil) }
                                    }.disabled(!editable || busy)
                                }.padding(.vertical, 8)
                            }
                        }
                    }
                    Text(value.notice).font(.caption).foregroundStyle(.secondary)
                } else if store.connected { ProgressView("Loading your work bookmark…") }
                else { Text("Reconnect to Juno to load your saved work bookmark.").foregroundStyle(.secondary) }
                if let issue, !store.meeting { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
            }.frame(maxWidth: .infinity, alignment: .leading).padding(8)
        }
        .task(id: privacyKey) { await load() }
        .onChange(of: store.meeting) { meeting in if meeting { value = nil; editor = nil; restarting = false; issue = nil } }
        .sheet(item: $editor) { request in
            WorkStepEditor(store: store, request: request, snapshot: snapshot, planning: planning) { result in
                value = result; issue = nil; restarting = false
            }
        }
    }
    @ViewBuilder private func controls(_ state: WorkSupportState, _ current: WorkBookmark) -> some View {
        if current.status == "interrupted" {
            Button("Resume this step") { Task { await perform("resume", state: state, bookmark: current) } }.buttonStyle(.borderedProminent)
            Button("Add a stopping note…") { editor = WorkEditorRequest(mode: "revise", state: state) }
        } else {
            Button("I was interrupted") { Task { await perform("interrupt", state: state, bookmark: current) } }
            Button("Step finished") { Task { await perform("finish", state: state, bookmark: current) } }
        }
        Button("Help me restart") { restarting.toggle() }
    }
    private func load() async {
        guard store.connected, !store.meeting else { value = nil; return }
        do {
            let result = try await store.decode(WorkSupportState.self, "/v1/work-support")
            guard !store.meeting else { return }
            value = result; issue = nil
        } catch { if !store.meeting { issue = (error as? APIProblem)?.message ?? "The bookmark could not refresh. Saved notes are retained." } }
    }
    private func perform(_ command: String, state: WorkSupportState, bookmark: WorkBookmark, switchCurrent: Bool = false) async {
        guard editable, !busy else { return }
        busy = true; defer { busy = false }
        do {
            let data = try await store.request("/v1/work-support/actions", method: "POST", body: ["operation_id": UUID().uuidString, "expected_revision": state.revision, "command": command, "bookmark_id": bookmark.id, "switch_current": switchCurrent])
            let result = try JSONDecoder().decode(WorkSupportState.self, from: data)
            guard !store.meeting else { return }; value = result; issue = nil; restarting = command == "interrupt"
        } catch { issue = (error as? APIProblem)?.message ?? "The request could not be confirmed. Reload the saved bookmark before trying again." }
    }
}

private struct WorkEditorRecovery: Codable {
    let draft: WorkStepDraft
    let revision: Int
    let operation: String
}
private struct WorkStepEditor: View {
    @ObservedObject var store: JunoStore
    let request: WorkEditorRequest
    let snapshot: TaskDockSnapshot?
    let planning: PlanningRecord?
    let saved: (WorkSupportState) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var draft = WorkStepDraft()
    @State private var revision = 0
    @State private var operation = UUID().uuidString
    @State private var submission = ""
    @State private var latest: WorkSupportState?
    @State private var conflict = false
    @State private var issue: String?
    @State private var busy = false
    @State private var accepted = false
    @State private var discard = false
    @State private var recovered = false
    @State private var initial = WorkStepDraft()
    private var key: String { EditorRecovery.key(owner: request.state.owner_id, kind: "work-step", record: request.mode + ":" + (request.mode == "start" ? "new" : request.state.current?.id ?? "missing")) }
    private var currentState: WorkSupportState { latest ?? request.state }
    private var canSave: Bool { !busy && !conflict && WorkSupportAccess.canEdit(connected: store.connected, offline: store.offline, meeting: store.meeting, syncing: store.syncing, queued: store.pendingEdits.count) && (store.sharedProfile == nil || store.sharedProfile?.owner_id == request.state.owner_id) && (request.mode == "blocker" ? !draft.blocker.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty : draft.canStart) }
    private var heading: String { request.mode == "start" ? "Make a small start" : request.mode == "blocker" ? "What is in the way?" : "Make this step easier to resume" }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(heading).font(.title2.bold())
            if store.meeting {
                Text("Your work notes are hidden in Meeting mode. Your local draft is retained.")
                Button("Close") { dismiss() }
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 14) {
                        if recovered { Text("Recovered your local draft. Review it before saving.").foregroundStyle(.secondary) }
                        if request.mode == "start", let snapshot {
                            Menu("Use a saved issue…") {
                                ForEach(snapshot.items.filter(taskIsUnfinished)) { task in
                                    Button(task.title) { select(task, from: snapshot) }
                                }
                            }
                            Text("Issue copy saved " + scheduleDate(snapshot.fetched_at) + (snapshot.stale ? "; refresh source details before relying on its status." : "."))
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        if request.mode != "blocker" {
                            field("What are you working on?", text: $draft.title)
                            field("First action", text: $draft.first_action)
                            field("A clear finish point for this small step", text: $draft.finish_point)
                            Button("Use a tiny starting step") { draft.useTinyStep() }
                            Text("For example: open the device list and check five addresses. Finish point: those five results are written down.").font(.caption).foregroundStyle(.secondary)
                        }
                        if request.mode != "start" || !draft.where_stopped.isEmpty {
                            field("Where did you stop?", text: $draft.where_stopped)
                        }
                        if request.mode == "revise" {
                            field("In the way (optional; clear when resolved)", text: $draft.blocker)
                        }
                        if request.mode == "blocker" {
                            Text(request.state.current?.title ?? "Your saved step").font(.headline)
                            field("What needs to happen before you can continue?", text: $draft.blocker)
                            Text("This saves a blocker in your personal bookmark. TaskDock and issue status are unchanged.").font(.caption).foregroundStyle(.secondary)
                        }
                        if let current = currentState.current, request.mode == "start" {
                            Text("Starting this will park “\(current.title)” with its notes saved for later.").font(.callout)
                        }
                        if store.offline || store.syncing || !store.pendingEdits.isEmpty {
                            Text("Reconnect and synchronize before saving. Your typed draft stays on this Mac.").font(.callout).foregroundStyle(.secondary)
                        }
                        if let issue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                        if conflict {
                            Button("Reload latest and compare") { Task { await compare() } }
                            if let latest {
                                Text("Saved now on the work Mac\n" + (latest.current?.comparisonText ?? "No current step")).textSelection(.enabled)
                                if request.mode == "start" || latest.current?.id == request.state.current?.id {
                                    Button("Keep my draft and use this latest revision") { revision = latest.revision; conflict = false; operation = UUID().uuidString; submission = "" }
                                } else { Text("The current step changed. Your draft stays on this Mac; close this sheet and review the saved bookmark before continuing.").font(.caption) }
                            }
                        }
                    }.padding(4)
                }
                Divider()
                HStack {
                    Button("Cancel") { if draft != initial { discard = true } else { dismiss() } }.keyboardShortcut(.cancelAction)
                    Spacer()
                    Button(request.mode == "start" ? (currentState.current == nil ? "Start this" : "Park current and start this") : request.mode == "blocker" ? "Save blocker and bookmark" : "Save my next step") { Task { await save() } }
                        .buttonStyle(.borderedProminent).disabled(!canSave).keyboardShortcut("s", modifiers: .command)
                }
            }
        }.padding(22).frame(width: 620, height: junoSheetHeight(620)).interactiveDismissDisabled(true)
        .onAppear { setup() }
        .onChange(of: draft) { _ in recover() }
        .onDisappear { recover() }
        .confirmationDialog("Keep this draft for later?", isPresented: $discard, titleVisibility: .visible) {
            Button("Keep local draft and close") { recover(); dismiss() }
            Button("Discard local draft", role: .destructive) { accepted = true; EditorRecovery.clear(key); dismiss() }
            Button("Keep editing", role: .cancel) {}
        }
    }
    private func field(_ title: String, text: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.headline)
            TextField(title, text: text, axis: .vertical).lineLimit(2...4).textFieldStyle(.roundedBorder)
        }
    }
    private func setup() {
        revision = request.state.revision
        if request.mode != "start", let row = request.state.current {
            draft = WorkStepDraft(title: row.title, first_action: row.first_action, finish_point: row.finish_point, where_stopped: row.where_stopped, blocker: row.blocker, source_ref: row.source_ref)
        }
        initial = draft
        if let recovery = EditorRecovery.load(WorkEditorRecovery.self, key: key) {
            draft = recovery.draft; revision = recovery.revision; operation = recovery.operation; recovered = true
            if revision != request.state.revision { conflict = true; latest = request.state; issue = "The saved bookmark changed after this draft. Compare before saving." }
        }
    }
    private func recover() {
        guard !accepted, draft != initial else { return }
        EditorRecovery.save(WorkEditorRecovery(draft: draft, revision: revision, operation: operation), key: key)
    }
    private func select(_ task: TaskDockTask, from snapshot: TaskDockSnapshot) {
        draft.title = task.title
        draft.source_ref = WorkSourceRef(task_id: task.id, workspace_id: snapshot.info.workspace_id, snapshot_id: snapshot.id)
        if planning?.workspace_id == snapshot.info.workspace_id, let facts = planning?.tasks.first(where: { $0.task_id == task.id }) {
            if draft.first_action.isEmpty { draft.first_action = facts.next_action }
            if draft.where_stopped.isEmpty { draft.where_stopped = facts.resume }
        }
    }
    private func compare() async {
        do { latest = try await store.decode(WorkSupportState.self, "/v1/work-support") }
        catch { issue = (error as? APIProblem)?.message ?? "The latest bookmark is unavailable. Your local draft is retained." }
    }
    private func save() async {
        guard canSave else { return }; busy = true; defer { busy = false }
        var body: [String: Any] = ["expected_revision": revision, "command": request.mode == "start" ? "start" : request.mode == "blocker" ? "interrupt" : "revise"]
        if request.mode == "start" {
            body["title"] = draft.title; body["first_action"] = draft.first_action; body["finish_point"] = draft.finish_point
            body["switch_current"] = currentState.current != nil
            if let ref = draft.source_ref { body["source_ref"] = ["task_id": ref.task_id, "workspace_id": ref.workspace_id, "snapshot_id": ref.snapshot_id] }
        } else {
            body["bookmark_id"] = request.state.current?.id
            body["where_stopped"] = draft.where_stopped
            if request.mode == "blocker" { body["blocker"] = draft.blocker }
            else { body["title"] = draft.title; body["first_action"] = draft.first_action; body["finish_point"] = draft.finish_point; body["blocker"] = draft.blocker }
        }
        do {
            let signature = String(data: try JSONSerialization.data(withJSONObject: body, options: .sortedKeys), encoding: .utf8)!
            if !submission.isEmpty && submission != signature { operation = UUID().uuidString }
            submission = signature; body["operation_id"] = operation; recover()
            let data = try await store.request("/v1/work-support/actions", method: "POST", body: body)
            let result = try JSONDecoder().decode(WorkSupportState.self, from: data)
            accepted = true; EditorRecovery.clear(key); saved(result); dismiss()
        } catch {
            issue = (error as? APIProblem)?.message ?? "Could not confirm the save. Your local draft is retained; retrying the same request is safe."
            if (error as? APIProblem)?.status == 409 { conflict = true }
        }
    }
}
