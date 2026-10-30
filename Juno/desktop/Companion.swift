import SwiftUI

struct ConversationRecord: Decodable, Identifiable { let id: String; let title: String }
struct ConversationPage: Decodable { let items: [ConversationRecord]; let has_more: Bool }
struct ChatMessage: Decodable, Identifiable {
    let id: String; let role: String; let text: String; let request_id: String
    let status: String; let order_key: Int64; let model_name: String?; let meeting_mode: Bool
}
struct MessagePage: Decodable { let items: [ChatMessage]; let has_more: Bool }
struct ModelSettings: Decodable { let base_url: String; let model: String; let configured: Bool }
struct ModelOptions: Decodable { let items: [String] }
struct CheckQuestion: Decodable { let key: String; let text: String }
struct CheckInRecord: Decodable {
    let id: String; let local_date: String; let answers: [String: String]; let diary_text: String
    let status: String; let revision: Int; let questions: [CheckQuestion]; let next_key: String?; let source_notice: String
}

func memoryRequestText(_ text: String) -> String? {
    let pattern = #"^\s*(?:please\s+)?(?:(?:can|could|will)\s+you\s+)?(?:please\s+)?remember\s+(?:that\b|this\b)[:?,\s]*(.*)$"#
    guard let regex = try? NSRegularExpression(pattern:pattern,options:[.caseInsensitive,.dotMatchesLineSeparators]),let match = regex.firstMatch(in:text,range:NSRange(text.startIndex...,in:text)),let range = Range(match.range(at:1),in:text) else { return nil }
    return String(text[range]).trimmingCharacters(in:.whitespacesAndNewlines)
}

extension JunoStore {
    func decode<T: Decodable>(_ type: T.Type, _ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> T {
        let data = try await request(path, method: method, body: body)
        return try JSONDecoder().decode(type, from: data)
    }
    func loadCompanion() async {
        do {
            let config = try await decode(ModelSettings.self, "/v1/model")
            modelBase = config.base_url; modelName = config.model; modelConfigured = config.configured
            try await loadConversations()
            let remembered = UserDefaults.standard.string(forKey: "conversationID")
            let newDraft = UserDefaults.standard.string(forKey: "chatDraft.new") ?? ""
            let identity = conversations.first { $0.id == remembered }?.id ?? (newDraft.isEmpty ? conversations.first?.id : nil)
            chooseConversation(identity)
        } catch { report(error) }
    }
    func loadConversations(more: Bool = false) async throws {
        let page = try await decode(ConversationPage.self, "/v1/conversations?offset=\(more ? conversations.count : 0)")
        if more { conversations.append(contentsOf: page.items) } else { conversations = page.items }
        conversationMore = page.has_more
    }
    func chooseConversation(_ id: String?) {
        if currentConversation != nil || !chatDraft.isEmpty { UserDefaults.standard.set(chatDraft, forKey: "chatDraft." + (currentConversation ?? "new")) }
        currentConversation = id; messages = []; olderMessages = false
        UserDefaults.standard.set(id, forKey: "conversationID")
        chatDraft = UserDefaults.standard.string(forKey: "chatDraft." + (id ?? "new")) ?? ""
        if let id { Task { do { try await loadMessages(id) } catch { chatIssue = "Could not load this conversation. Try Refresh." } } }
    }
    func loadMessages(_ id: String, older: Bool = false) async throws {
        var path = "/v1/conversations/\(id)/messages"
        if older, let first = messages.first { path += "?before=\(first.order_key)" }
        let page = try await decode(MessagePage.self, path)
        guard id == currentConversation else { return }
        if older { messages.insert(contentsOf: page.items, at: 0) } else { messages = page.items }
        olderMessages = page.has_more
    }
    func sendChat(retry: ChatMessage? = nil) {
        guard !chatSending else { return }
        let text = retry.flatMap { failed in messages.first { $0.request_id == failed.request_id && $0.role == "user" }?.text } ?? chatDraft
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        if retry == nil, let draft = memoryRequestText(text) { memoryReviewOriginal = text;memoryReviewText = draft;memoryNotice = nil;return }
        chatSending = true; chatIssue = nil
        let mode = meeting
        Task {
            defer { chatSending = false }
            do {
                var identity = currentConversation
                if identity == nil {
                    let row = try await decode(ConversationRecord.self, "/v1/conversations", method: "POST", body: ["title": String(text.prefix(70))])
                    identity = row.id; currentConversation = row.id; UserDefaults.standard.set(row.id, forKey: "conversationID")
                    UserDefaults.standard.set(text, forKey: "chatDraft." + row.id)
                }
                let id = identity!
                let pendingID = UserDefaults.standard.string(forKey: "pendingTurn." + id)
                let pendingText = UserDefaults.standard.string(forKey: "pendingText." + id)
                let requestID = retry?.request_id ?? (pendingText == text ? pendingID : nil) ?? UUID().uuidString
                UserDefaults.standard.set(requestID, forKey: "pendingTurn." + id)
                UserDefaults.standard.set(text, forKey: "pendingText." + id)
                _ = try await decode(ChatMessage.self, "/v1/conversations/\(id)/messages", method: "POST", body: ["text": text, "request_id": requestID, "meeting_mode": mode])
                UserDefaults.standard.removeObject(forKey: "pendingTurn." + id)
                UserDefaults.standard.removeObject(forKey: "pendingText." + id)
                if retry == nil { chatDraft = ""; UserDefaults.standard.removeObject(forKey: "chatDraft." + id); UserDefaults.standard.removeObject(forKey: "chatDraft.new") }
                try await loadMessages(id); try await loadConversations()
            } catch {
                chatIssue = (error as? APIProblem)?.message ?? "The reply was interrupted. Refresh before retrying so the same message is not sent twice."
                if let id = currentConversation { try? await loadMessages(id) }
            }
        }
    }
    func probeModel() {
        modelBusy = true; modelNotice = nil
        Task {
            defer { modelBusy = false }
            do {
                var parts = URLComponents(); parts.path = "/v1/model/models"; parts.queryItems = [URLQueryItem(name: "base_url", value: modelBase)]
                modelOptions = try await decode(ModelOptions.self, parts.string!).items
                if modelName.isEmpty || !modelOptions.contains(modelName) { modelName = modelOptions.first ?? "" }
                modelNotice = modelOptions.isEmpty ? "The server has no chat models available. Load one in LM Studio." : "Local server reached. Choose a model, then save the connection."
            } catch { modelNotice = (error as? APIProblem)?.message ?? "Could not reach the local server." }
        }
    }
    func saveModel() {
        modelBusy = true
        Task {
            defer { modelBusy = false }
            do {
                let config = try await decode(ModelSettings.self, "/v1/model", method: "PUT", body: ["base_url": modelBase, "model": modelName])
                modelConfigured = config.configured; modelNotice = "Connection saved. Juno will use this local model for chat."
            } catch { modelNotice = (error as? APIProblem)?.message ?? "The connection could not be saved." }
        }
    }
    func loadCheckIn(day: String) {
        checkBusy = true; checkIssue = nil
        Task {
            defer { checkBusy = false }
            do {
                let row: CheckInRecord
                if sharedProfile != nil {
                    do { row = try await decode(CheckInRecord.self,"/v1/check-ins/by-date/"+day) }
                    catch { row = try await decode(CheckInRecord.self, "/v1/check-ins", method: "POST", body: ["local_date": day]) }
                } else { row = try await decode(CheckInRecord.self, "/v1/check-ins", method: "POST", body: ["local_date": day]) }
                checkIn = row; checkDay = day
                checkAnswer = UserDefaults.standard.string(forKey: "answerDraft." + day) ?? ""
                diaryDraft = UserDefaults.standard.string(forKey: "diaryDraft." + day) ?? row.diary_text
            } catch { checkIssue = (error as? APIProblem)?.message ?? "Could not load the check-in." }
        }
    }
    func saveAnswer(skip: Bool = false) {
        guard let row = checkIn, let key = row.next_key else { return }
        checkBusy = true; checkIssue = nil
        Task {
            defer { checkBusy = false }
            do {
                let updated = try await decode(CheckInRecord.self, "/v1/check-ins/\(row.id)/answer", method: "PUT", body: ["key": key, "text": skip ? "" : checkAnswer, "expected_revision": row.revision])
                checkIn = updated; checkAnswer = ""; diaryDraft = updated.diary_text
                UserDefaults.standard.removeObject(forKey: "answerDraft." + checkDay)
                UserDefaults.standard.removeObject(forKey: "diaryDraft." + checkDay)
            } catch { checkIssue = (error as? APIProblem)?.message ?? "Could not save. Your answer is still here." }
        }
    }
    func saveDiary(confirm: Bool) {
        guard let row = checkIn else { return }
        checkBusy = true; checkIssue = nil
        Task {
            defer { checkBusy = false }
            do {
                checkIn = try await decode(CheckInRecord.self, "/v1/check-ins/\(row.id)/diary", method: "PUT", body: ["text": diaryDraft, "expected_revision": row.revision, "confirm": confirm])
                UserDefaults.standard.removeObject(forKey: "diaryDraft." + checkDay)
                messages.removeAll { $0.role == "assistant" }
                if let id = currentConversation { try? await loadMessages(id) }
            } catch { checkIssue = (error as? APIProblem)?.message ?? "Could not save the diary. Your draft is still here." }
        }
    }
}

struct RootView: View {
    @ObservedObject var store: JunoStore
    @State private var showSidebar = true
    private let daily = [("Today","sun.max"),("Chat","bubble.left.and.bubble.right"),("Plan","checklist"),("Schedules","calendar"),("Check-in","square.and.pencil"),("Memories","book.closed")]
    private let sources = [("TaskDock","tray.full"),("Evidence","doc.text.magnifyingglass")]
    private let setup = [("Connections","link"),("Model","sparkles"),("Computers","desktopcomputer")]
    private func title(_ key: String) -> String { ["Check-in":"Daily check-in","Model":"Local model" ][key] ?? key }
    private func links(_ label: String, _ rows: [(String,String)]) -> some View {
        VStack(alignment:.leading,spacing:4) {
            Text(label.uppercased()).font(.caption.bold()).foregroundStyle(.secondary).padding(.horizontal,10).padding(.top,14)
            ForEach(rows,id:\.0) { key,icon in
                Button { store.section = key } label: {
                    Label(title(key),systemImage:icon).frame(maxWidth:.infinity,alignment:.leading).padding(.horizontal,10).padding(.vertical,8)
                        .background(store.section == key ? Color.accentColor.opacity(0.16) : Color.clear).clipShape(RoundedRectangle(cornerRadius:7))
                }.buttonStyle(.plain).accessibilityLabel(title(key) + (store.section == key ? ", selected" : ""))
            }
        }
    }
    @ViewBuilder private var workspace: some View {
        switch store.section {
        case "Today": TodayWorkspace(store:store)
        case "Schedules": SchedulesWorkspace(store:store)
        case "Plan": PlanningWorkspace(store:store)
        case "Memories": MemoryWorkspace(store:store)
        case "Check-in": CheckInWorkspace(store:store)
        case "Model":
            if store.sharedProfile == nil { ModelWorkspace(store:store) }
            else { VStack(alignment:.leading,spacing:16) { Text("Your work Mac runs Juno’s model").font(.title2.bold());Text("Set up LM Studio on the work Mac. AI replies need that Mac awake and reachable. Memory and diary edits work offline.").foregroundStyle(.secondary) }.padding(32) }
        case "TaskDock": TaskDockWorkspace(store:store)
        case "Connections": ConnectionsWorkspace(store:store)
        case "Evidence": IntegrationsWorkspace(store:store)
        case "Computers": ComputersWorkspace(store:store)
        default: ChatWorkspace(store:store)
        }
    }
    var body: some View {
        VStack(spacing:0) {
            HStack(spacing:12) {
                Button { showSidebar.toggle() } label: { Image(systemName:"sidebar.left") }.help("Show or hide navigation")
                Text("Juno").font(.title2.bold()).foregroundStyle(.purple)
                Divider().frame(height:20)
                Text(title(store.section)).font(.headline)
                Spacer()
                Text(store.status).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                Toggle("Meeting mode",isOn:$store.meeting).toggleStyle(.switch).help("Professional tone; private-mode replies stay hidden.")
            }.padding(.horizontal,18).padding(.vertical,12)
            if store.sharedProfile != nil {
                HStack {
                    Label(store.offline ? "Offline copy" : "Work Mac connected",systemImage:store.offline ? "wifi.slash" : "checkmark.icloud")
                    if let date = store.offlineDate { Text("Last copy: " + scheduleDate(ISO8601DateFormatter().string(from:date))).foregroundStyle(.secondary) }
                    Text("\(store.pendingEdits.count) queued edits")
                    Spacer();Button("Sync") { store.reconnectShared() }.disabled(store.syncing)
                }.font(.caption).padding(.horizontal,18).padding(.bottom,10)
                if let issue = store.syncIssue { Text(issue).font(.caption).foregroundStyle(.orange).padding(.horizontal,18) }
            }
            Divider()
            HStack(spacing:0) {
                if showSidebar {
                    ScrollView { VStack(alignment:.leading,spacing:4) { links("My workday",daily);links("Saved sources",sources);links("Setup",setup);Spacer(minLength:20) }.padding(10) }
                        .frame(width:178).background(Color.secondary.opacity(0.035))
                    Divider()
                }
                workspace.frame(maxWidth:.infinity,maxHeight:.infinity)
            }
            if let issue = store.problem { HStack { Text(issue).foregroundStyle(.orange);Spacer();Button("Dismiss") { store.problem = nil } }.padding(12) }
            Divider()
            HStack { Text(store.sharedProfile == nil ? "Saved on this Mac" : "Work Mac + offline laptop copy");Spacer();Text("Juno 0.1.0-preview.10") }.font(.caption).foregroundStyle(.secondary).padding(.horizontal,14).padding(.vertical,8)
        }.frame(minWidth:1040,minHeight:650)
    }
}

struct ChatWorkspace: View {
    @ObservedObject var store: JunoStore
    var body: some View {
        HSplitView {
            VStack(alignment: .leading) {
                Button { store.chooseConversation(nil) } label: { Label("New conversation", systemImage: "plus") }.disabled(store.chatSending)
                List(selection: Binding(get: { store.currentConversation }, set: { store.chooseConversation($0) })) {
                    ForEach(store.conversations) { row in Text(row.title).lineLimit(2).tag(row.id) }
                }.disabled(store.chatSending)
                if store.conversationMore { Button("Older conversations") { Task { do { try await store.loadConversations(more: true) } catch { store.report(error) } } } }
            }.padding(14).frame(minWidth: 210, idealWidth: 250, maxWidth: 300)
            VStack(alignment: .leading, spacing: 14) {
                if !store.modelConfigured {
                    HStack { Text("Connect a local model to talk with Juno. The daily check-in works without one."); Spacer(); Button("Connect model") { store.section = "Model" } }.padding(12).background(.purple.opacity(0.1))
                }
                ScrollViewReader { reader in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 18) {
                            if store.olderMessages { Button("Load older messages") { if let id = store.currentConversation { Task { do { try await store.loadMessages(id, older: true) } catch { store.report(error) } } } } }
                            if store.messages.isEmpty { Text("What would you like to work through?").font(.title2).padding(.top, 30) }
                            ForEach(store.messages) { message in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(message.role == "user" ? "You" : "Juno").font(.caption.bold()).foregroundStyle(.secondary)
                                    if message.status == "pending" { ProgressView("Preparing a reply…") }
                                    else if message.status == "invalidated" { Text(message.text).italic().foregroundStyle(.secondary) }
                                    else if store.meeting && message.role == "assistant" && !message.meeting_mode { Text("Private-mode reply hidden during Meeting mode.").italic().foregroundStyle(.secondary) }
                                    else { Text(message.text).textSelection(.enabled) }
                                    if message.role == "user" && message.status == "complete" { Button("Save as memory…") { store.memoryReviewOriginal = nil;store.memoryReviewText = memoryRequestText(message.text) ?? message.text;store.memoryNotice = nil }.font(.caption).disabled(!store.connected) }
                                    if message.status == "failed" { Button("Retry this reply") { store.sendChat(retry: message) }.disabled(store.chatSending) }
                                }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(message.role == "user" ? Color.purple.opacity(0.08) : Color.secondary.opacity(0.04)).clipShape(RoundedRectangle(cornerRadius: 10)).id(message.id)
                            }
                            if store.chatSending { ProgressView("Juno is thinking…") }
                        }.padding(.vertical, 4)
                    }.onAppear { if let last = store.messages.last { reader.scrollTo(last.id,anchor:.bottom) } }.onChange(of: store.messages.count) { _ in if let last = store.messages.last { reader.scrollTo(last.id, anchor: .bottom) } }
                }
                if let notice = store.memoryNotice { HStack { Text(notice).font(.caption);Button("Review memory") { store.section = "Memories" };Button("Dismiss") { store.memoryNotice = nil } } }
                if let issue = store.chatIssue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                HStack {
                    TextEditor(text: $store.chatDraft).frame(height: 75).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Message to Juno")
                        .onChange(of: store.chatDraft) { value in UserDefaults.standard.set(value, forKey: "chatDraft." + (store.currentConversation ?? "new")) }
                    Button(memoryRequestText(store.chatDraft) == nil ? "Send" : "Review memory") { store.sendChat() }.keyboardShortcut(.return, modifiers: .command).disabled(!store.connected || (store.offline && memoryRequestText(store.chatDraft) == nil) || (!store.pendingEdits.isEmpty && memoryRequestText(store.chatDraft) == nil) || (!store.modelConfigured && memoryRequestText(store.chatDraft) == nil) || store.chatSending || store.chatDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.chatDraft.count > 6000)
                }
                HStack { Text("⌘ Return to send · \(store.chatDraft.count)/6000").font(.caption).foregroundStyle(.secondary); Spacer(); Button("Refresh chat") { if let id = store.currentConversation { Task { try? await store.loadMessages(id) } } }.disabled(store.chatSending) }
            }.padding(20).frame(minWidth: 480)
        }
        .sheet(isPresented:Binding(get:{store.memoryReviewText != nil},set:{if !$0 {store.memoryReviewText = nil;store.memoryReviewOriginal = nil}})) {
            Editor(store:store,original:nil,initialText:store.memoryReviewText ?? "") { saved in
                store.memoryNotice = store.offline ? "Memory saved on this laptop and queued for sync." : "Memory saved. You can review, correct or delete it in Memories."
                if let original = store.memoryReviewOriginal,store.chatDraft == original {
                    store.chatDraft = "";UserDefaults.standard.removeObject(forKey:"chatDraft." + (store.currentConversation ?? "new"))
                }
                store.selected = saved.id;store.memoryReviewOriginal = nil;store.memoryReviewText = nil
            }
        }
    }
}

struct ModelWorkspace: View {
    @ObservedObject var store: JunoStore
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Give Juno a local model").font(.title2.bold())
            Text("Start the local server in LM Studio on this Mac, then find and select a chat model. No cloud fallback is enabled. Paired laptops use this work Mac’s model while connected.").foregroundStyle(.secondary)
            TextField("Local server", text: $store.modelBase).textFieldStyle(.roundedBorder).accessibilityLabel("Local model server address")
            Button("Find models") { store.probeModel() }.disabled(!store.connected || store.modelBusy)
            if !store.modelOptions.isEmpty {
                Picker("Chat model", selection: $store.modelName) { ForEach(store.modelOptions, id: \.self) { Text($0).tag($0) } }
            } else { TextField("Model identifier", text: $store.modelName).textFieldStyle(.roundedBorder) }
            Button("Save connection") { store.saveModel() }.disabled(!store.connected || store.modelBusy || store.modelName.isEmpty)
            if store.modelBusy { ProgressView() }
            if let notice = store.modelNotice { Text(notice).textSelection(.enabled) }
            Text("Juno stores your history and memory herself. The model generates replies using relevant records. Model weights are not included in the installer.").font(.callout).foregroundStyle(.secondary)
            Spacer()
        }.padding(32).frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct CheckInStarter: Decodable { let text: String; let notices: [String] }

struct CheckInWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var day = Date()
    @State private var starter: CheckInStarter?
    var dayKey: String { let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd"; formatter.timeZone = TimeZone(identifier:"America/Chicago"); return formatter.string(from: day) }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack { Text("Your daily check-in").font(.title2.bold()); Spacer(); DatePicker("Day", selection: $day, displayedComponents: .date).fixedSize().disabled(store.checkBusy) }
            Text("About 15 minutes · answers save as you continue · no model required").font(.subheadline).foregroundStyle(.secondary)
            if let starter { DisclosureGroup("From your saved work context — review before answering") { ScrollView { Text(starter.text).textSelection(.enabled); ForEach(starter.notices, id: \.self) { Text($0).font(.caption).foregroundStyle(.secondary) } }.frame(maxHeight: 140) } }
            if let row = store.checkIn, row.local_date == dayKey {
                Text(row.source_notice).font(.callout).foregroundStyle(.secondary)
                if let key = row.next_key, let question = row.questions.first(where: { $0.key == key }) {
                    Text("Question \(row.answers.count + 1) of \(row.questions.count)").font(.caption).foregroundStyle(.secondary)
                    Text(question.text).font(.title3)
                    TextEditor(text: $store.checkAnswer).frame(minHeight: 160).padding(8).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Check-in answer")
                        .onChange(of: store.checkAnswer) { value in UserDefaults.standard.set(value, forKey: "answerDraft." + store.checkDay) }
                    HStack { Button("Skip for now") { store.saveAnswer(skip: true) }; Spacer(); Button("Save and continue") { store.saveAnswer() }.disabled(store.checkAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.checkAnswer.count > 10000) }.disabled(store.checkBusy)
                } else {
                    Label(row.status == "confirmed" ? "Diary confirmed" : "Review your diary draft", systemImage: row.status == "confirmed" ? "checkmark.circle" : "pencil").font(.headline)
                    TextEditor(text: $store.diaryDraft).frame(minHeight: 220).padding(8).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Diary draft")
                        .onChange(of: store.diaryDraft) { value in UserDefaults.standard.set(value, forKey: "diaryDraft." + store.checkDay) }
                    HStack { Button("Save draft") { store.saveDiary(confirm: false) }; Spacer(); Button(row.status == "confirmed" ? "Save confirmed changes" : "Confirm diary") { store.saveDiary(confirm: true) } }.disabled(store.checkBusy || store.diaryDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.diaryDraft.count > 60000)
                }
            } else if store.checkBusy { ProgressView("Loading check-in…") }
            if let issue = store.checkIssue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
            Button("Reload saved check-in") { store.loadCheckIn(day: dayKey) }.disabled(!store.connected || store.checkBusy)
            Spacer(minLength: 0)
        }.padding(28).disabled(!store.connected)
        .task(id: dayKey) {
            starter = nil
            if store.connected && !store.offline { starter = try? await store.decode(CheckInStarter.self, "/v1/planning/check-in?day=" + dayKey) }
        }
        .onAppear { if store.connected { store.loadCheckIn(day: dayKey) } }
        .onChange(of: store.connected) { value in if value { store.loadCheckIn(day: dayKey) } }
        .onChange(of: day) { _ in store.loadCheckIn(day: dayKey) }
    }
}

func taskIsUnfinished(_ task: TaskDockTask) -> Bool {
    if case .object(let fields) = task.fields, case .bool(true) = fields["source_completed"] { return false }
    return (task.text("completed_at") ?? "").isEmpty && !["done","completed","archived"].contains((task.text("behavior") ?? "").lowercased())
}
func taskDueDay(_ task: TaskDockTask) -> String? {
    guard let raw = task.text("due_date"), raw.count >= 10 else { return nil }
    let value = String(raw.prefix(10));let f = DateFormatter();f.locale = Locale(identifier:"en_US_POSIX");f.timeZone = TimeZone(identifier:"America/Chicago");f.dateFormat = "yyyy-MM-dd";f.isLenient = false
    guard let date = f.date(from:value),f.string(from:date) == value else { return nil };return value
}
func taskHasRecordedBlocker(_ task: TaskDockTask, _ facts: PlanningFacts?) -> Bool {
    [task.text("blocked_reason") ?? "",facts?.blocker ?? "",facts?.waiting_on ?? ""].contains { !$0.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty }
}

struct TodayWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var snapshot: TaskDockSnapshot?
    @State private var planning: PlanningRecord?
    @State private var schedules: ScheduleRecord?
    @State private var issues: [String] = []
    @State private var busy = false
    @State private var filter = "Due / overdue"
    @State private var search = ""
    @State private var remember = false
    private var today: String { integrationDay(0) }
    private var tasks: [TaskDockTask] { (snapshot?.items ?? []).filter(taskIsUnfinished) }
    private func facts(_ task: TaskDockTask) -> PlanningFacts? {
        guard planning?.workspace_id == snapshot?.info.workspace_id else { return nil }
        return planning?.tasks.first { $0.task_id == task.id }
    }
    private var due: [TaskDockTask] { tasks.filter { taskDueDay($0).map { $0 <= today } ?? false } }
    private var blocked: [TaskDockTask] { tasks.filter { taskHasRecordedBlocker($0,facts($0)) } }
    private var filtered: [TaskDockTask] {
        let rows = filter == "All unfinished" ? tasks : filter == "Recorded blockers" ? blocked : due
        return rows.filter { search.isEmpty || $0.title.localizedCaseInsensitiveContains(search) }.sorted { a,b in
            let left = taskDueDay(a) ?? "9999-12-31",right = taskDueDay(b) ?? "9999-12-31"
            return left == right ? a.title.localizedStandardCompare(b.title) == .orderedAscending : left < right
        }
    }
    private func load() async {
        guard store.connected else { return };busy = true;issues = [];defer { busy = false }
        do { let value = try await store.decode(TaskDockState.self,"/v1/taskdock");snapshot = value.snapshot;if let error = value.error { issues.append(error) } }
        catch { issues.append("TaskDock summary could not refresh. Any previous copy stays visible.") }
        do { planning = try await store.decode(PlanningRecord.self,"/v1/planning") }
        catch { planning = nil;issues.append("Planning details unavailable; blocker counts may be incomplete.") }
        do { schedules = try await store.decode(ScheduleRecord.self,"/v1/schedules") }
        catch { schedules = nil;issues.append("Planning holds unavailable.") }
    }
    private func countCard(_ title: String,_ value: Int,_ icon: String,_ selection: String) -> some View {
        Button { filter = selection } label: {
            VStack(alignment:.leading,spacing:8) { Label(title,systemImage:icon).font(.subheadline);Text(String(value)).font(.largeTitle.bold()) }
                .frame(maxWidth:.infinity,alignment:.leading).padding(16).background(Color.accentColor.opacity(filter == selection ? 0.14 : 0.05)).clipShape(RoundedRectangle(cornerRadius:10))
        }.buttonStyle(.plain)
    }
    var body: some View {
        ScrollView {
            VStack(alignment:.leading,spacing:18) {
                HStack {
                    VStack(alignment:.leading,spacing:5) { Text("Your workday, together").font(.title.bold());Text(today + " • a snapshot of what Juno has saved").foregroundStyle(.secondary) }
                    Spacer();Button("Refresh overview") { Task { await load() } }.disabled(busy || !store.connected)
                    if busy { ProgressView().controlSize(.small) }
                }
                HStack { Button("Talk it through") { store.section = "Chat" };Button("Rooms & people") { store.section = "Schedules" };Button("Daily check-in") { store.section = "Check-in" };Button("Remember something") { remember = true }.disabled(!store.connected) }
                if store.offline { Label("Offline overview — dated records; memory and diary edits can queue for sync.",systemImage:"wifi.slash").foregroundStyle(.orange) }
                ForEach(issues,id:\.self) { Text($0).font(.caption).foregroundStyle(.orange) }
                if let snapshot {
                    HStack {
                        countCard("Unfinished",tasks.count,"tray.full","All unfinished")
                        countCard("Due / overdue",due.count,"calendar.badge.clock","Due / overdue")
                        countCard("Recorded blockers",blocked.count,"pause.circle","Recorded blockers")
                    }
                    Text("Includes subtasks. TaskDock saved " + scheduleDate(snapshot.fetched_at) + (snapshot.stale ? " • stale copy" : "") + ". Source refresh times can be older.").font(.caption).foregroundStyle(.secondary)
                    if let error = snapshot.error { Text(error).font(.caption).foregroundStyle(.orange) }
                    GroupBox("Issues to review") {
                        VStack(alignment:.leading,spacing:12) {
                            HStack { Picker("Show",selection:$filter) { Text("Due / overdue").tag("Due / overdue");Text("Recorded blockers").tag("Recorded blockers");Text("All unfinished").tag("All unfinished") };TextField("Find an issue",text:$search).textFieldStyle(.roundedBorder) }
                            if filtered.isEmpty { Text("No matching issues in the saved copy.").foregroundStyle(.secondary) }
                            ForEach(filtered.prefix(20)) { task in
                                VStack(alignment:.leading,spacing:5) {
                                    HStack { Text(task.title).font(.headline);Spacer();Button("Review") { store.planningTaskID = task.id;store.section = "Plan" } }
                                    Text((task.text("status_name") ?? "Status unknown") + " • Due: " + (taskDueDay(task) ?? "Not recorded")).font(.caption).foregroundStyle(.secondary)
                                    if taskHasRecordedBlocker(task,facts(task)) { Text("Blocker: " + ([task.text("blocked_reason"),facts(task)?.blocker,facts(task)?.waiting_on].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator:" • "))).font(.caption).foregroundStyle(.orange) }
                                }.padding(.vertical,8)
                                Divider()
                            }
                            if filtered.count > 20 { Text("Showing 20 of \(filtered.count). Search to narrow the list.").font(.caption) }
                            Button("Open all TaskDock records") { store.section = "TaskDock" }
                        }.padding(8).frame(maxWidth:.infinity,alignment:.leading)
                    }
                } else if !busy {
                    GroupBox("Start with your work context") { VStack(alignment:.leading,spacing:10) { Text("No TaskDock snapshot is available yet. Connect TaskDock to see issues and deadlines here.");Button("Open TaskDock") { store.section = "TaskDock" } }.padding(12).frame(maxWidth:.infinity,alignment:.leading) }
                }
                if let schedules {
                    let holds = schedules.reservations.filter { hold in
                        guard let start = providerDate(hold.start) else { return false }
                        let f = DateFormatter();f.timeZone = TimeZone(identifier:"America/Chicago");f.dateFormat = "yyyy-MM-dd";return f.string(from:start) == today
                    }
                    GroupBox("Today’s local planning holds") {
                        VStack(alignment:.leading,spacing:10) {
                            if holds.isEmpty { Text("No holds recorded for today.").foregroundStyle(.secondary) }
                            ForEach(holds) { hold in Text(hold.room + " • " + (hold.employee.isEmpty ? "My work" : hold.employee) + " • " + scheduleDate(hold.start) + " → " + scheduleDate(hold.end)) }
                            if let notice = schedules.reservation_notice,!notice.isEmpty { Text(notice).foregroundStyle(.orange) }
                            Button("Review schedules") { store.section = "Schedules" }
                        }.padding(8).frame(maxWidth:.infinity,alignment:.leading)
                    }
                }
                Text("This overview does not choose a priority or assign work. Missing records and unreported blockers stay unknown.").font(.caption).foregroundStyle(.secondary)
            }.padding(26).frame(maxWidth:1100,alignment:.leading)
        }.task(id:store.connected) { await load() }
        .sheet(isPresented:$remember) { Editor(store:store,original:nil) }
    }
}
