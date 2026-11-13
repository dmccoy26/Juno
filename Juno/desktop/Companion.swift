import SwiftUI
import UserNotifications

struct ConversationRecord: Decodable, Identifiable { let id: String; let title: String }
struct ConversationPage: Decodable { let items: [ConversationRecord]; let has_more: Bool }
struct ChatMessage: Decodable, Identifiable {
    let id: String; let role: String; let text: String; let request_id: String
    let status: String; let order_key: Int64; let model_name: String?; let meeting_mode: Bool
    var saved_memory_id: String? = nil
}
struct MessagePage: Decodable { let items: [ChatMessage]; let has_more: Bool }
struct ModelSettings: Decodable { let base_url: String; let model: String; let configured: Bool }
struct ModelOptions: Decodable { let items: [String] }
struct CheckQuestion: Decodable { let key: String; let text: String }
struct CheckInRecord: Decodable {
    let id: String; let local_date: String; let answers: [String: String]; let diary_text: String
    let status: String; let revision: Int; let questions: [CheckQuestion]; let next_key: String?; let source_notice: String
}

struct MemorySuggestionButton: View {
    @ObservedObject var store: JunoStore
    let source: String
    let text: String
    @State private var reviewing = false
    @State private var saved = false

    var body: some View {
        if !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            Button(saved ? "Memory saved" : "Review memory suggestion…") { reviewing = true }
                .disabled(saved || !store.connected)
                .sheet(isPresented: $reviewing) {
                    Editor(store: store, original: nil, initialText: String(text.prefix(3_000)),
                           initialSource: String(source.prefix(500)), initialConfidence: "observed") { _ in saved = true }
                }
                .onChange(of: text) { _ in saved = false }
                .onChange(of: source) { _ in saved = false }
        }
    }
}

enum CheckInReminder {
    static let enabledKey = "checkInReminderEnabled"
    static let minutesKey = "checkInReminderMinutes"
    static let identifier = "juno.daily-check-in"
    static let testIdentifier = "juno.daily-check-in.test"
    static let defaultMinutes = 16 * 60

    static var calendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "America/Chicago")!
        return calendar
    }

    static func day(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = calendar.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    static func isDue(_ date: Date, minutes: Int) -> Bool {
        let components = calendar.dateComponents([.weekday, .hour, .minute], from: date)
        guard let weekday = components.weekday, (2...6).contains(weekday),
              let hour = components.hour, let minute = components.minute else { return false }
        return hour * 60 + minute >= minutes
    }

    @MainActor static func notifyIfAllowed() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized, !NSApplication.shared.isActive else { return }
        let content = UNMutableNotificationContent()
        content.title = "Daily check-in"
        content.body = "Take a few minutes to review what you did today."
        content.sound = .default
        try? await center.add(UNNotificationRequest(identifier: identifier, content: content, trigger: nil))
    }

    static func sendTest() async throws {
        let content = UNMutableNotificationContent()
        content.title = "Juno reminder test"
        content.body = "Your daily check-in alerts can appear here."
        try await UNUserNotificationCenter.current().add(
            UNNotificationRequest(identifier: testIdentifier, content: content, trigger: nil)
        )
    }
}

func memoryRequestText(_ text: String) -> String? {
    let pattern = #"^\s*(?:(?:hi|hey|hello)\s+juno[,!:.?\s]+)?(?:please\s+)?(?:(?:can|could|will)\s+you\s+)?(?:please\s+)?remember\s+(?:that\b|this\b)[:?,\s]*(.*)$"#
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
    func deleteConversation(_ identity: String) async throws {
        guard !offline else { throw APIProblem(message:"Reconnect to your work Mac before deleting a conversation.",status:0) }
        _ = try await request("/v1/conversations/" + identity,method:"DELETE")
        conversations.removeAll { $0.id == identity }
        for prefix in ["chatDraft.","pendingTurn.","pendingText."] { UserDefaults.standard.removeObject(forKey:prefix + identity) }
        if UserDefaults.standard.string(forKey:"conversationID") == identity { UserDefaults.standard.removeObject(forKey:"conversationID") }
        if currentConversation == identity { chooseConversation(nil) }
        do { try await loadConversations() } catch { chatIssue = "Conversation deleted; the list could not refresh. Try again when connected." }
    }
    func sendChat(retry: ChatMessage? = nil) {
        guard !chatSending else { return }
        let text = retry.flatMap { failed in messages.first { $0.request_id == failed.request_id && $0.role == "user" }?.text } ?? chatDraft
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
        if retry == nil, let draft = memoryRequestText(text) { memoryReviewMessageID = nil;memoryReviewOriginal = text;memoryReviewText = draft;memoryNotice = nil;return }
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

struct JunoBrandLogo: View {
    @Environment(\.colorScheme) private var colorScheme
    private var resource: String { colorScheme == .dark ? "JunoLogoDark" : "JunoLogo" }
    var body: some View {
        Group {
            if let url = Bundle.main.url(forResource: resource, withExtension: "png"), let logo = NSImage(contentsOf: url) {
                Image(nsImage: logo).resizable().interpolation(.high).scaledToFill()
                    .frame(width: 132, height: 42).clipped()
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .background(colorScheme == .dark ? Color(red: 36.0/255, green: 36.0/255, blue: 36.0/255) : Color(red: 0.99, green: 0.97, blue: 0.95))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .accessibilityLabel("Juno")
            } else {
                Text("Juno").font(.title2.bold()).foregroundStyle(.primary)
            }
        }
    }
}

struct RootView: View {
    @ObservedObject var store: JunoStore
    @AppStorage("sidebarVisible") private var showSidebar = true
    @State private var visited = ["Today"]
    @AppStorage("appearance") private var appearance = "system"
    @AppStorage(CheckInReminder.enabledKey) private var remindersEnabled = true
    @AppStorage(CheckInReminder.minutesKey) private var reminderMinutes = CheckInReminder.defaultMinutes
    @AppStorage("checkInReminderLastShown") private var lastReminderDay = ""
    @State private var reminderDay: String?
    private let daily = [("Today","sun.max"),("Chat","bubble.left.and.bubble.right"),("Plan","checklist"),("Schedules","calendar"),("Check-in","square.and.pencil"),("Memories","book.closed"),("Workers","person.2")]
    private let sources = [("TaskDock","tray.full"),("Evidence","doc.text.magnifyingglass")]
    private func title(_ key: String) -> String { ["Check-in":"Daily check-in","Model":"Local model","Workers":"Worker updates" ][key] ?? key }
    @ViewBuilder private func workspace(_ key:String) -> some View {
        switch key {
        case "Today": TodayWorkspace(store:store)
        case "Schedules": SchedulesWorkspace(store:store)
        case "Plan": PlanningWorkspace(store:store)
        case "Reports": ReportsWorkspace(store:store)
        case "Memories": MemoryWorkspace(store:store)
        case "Check-in": CheckInWorkspace(store:store)
        case "Model":
            if store.sharedProfile == nil { ModelWorkspace(store:store) }
            else { VStack(alignment:.leading,spacing:16) { Text("Your work Mac runs Juno’s model").font(.title2.bold());Text("Set up LM Studio on the work Mac. AI replies need that Mac awake and reachable. Memory and diary edits work offline.").foregroundStyle(.secondary) }.padding(32) }
        case "TaskDock": TaskDockWorkspace(store:store)
        case "Connections": ConnectionsWorkspace(store:store)
        case "Evidence": IntegrationsWorkspace(store:store)
        case "Workers": WorkerWorkspace(store:store)
        case "Computers": ComputersWorkspace(store:store)
        default: ChatWorkspace(store:store)
        }
    }
    var body: some View {
        VStack(spacing:0) {
            HStack(spacing:12) {
                Button { showSidebar.toggle() } label: { Image(systemName:"sidebar.left") }.help("Show or hide navigation")
                JunoBrandLogo()
                HStack(alignment:.firstTextBaseline,spacing:6) {
                    Text(Bundle.main.object(forInfoDictionaryKey:"JunoReleaseVersion") as? String ?? "Development")
                        .font(.subheadline).foregroundStyle(.secondary)
                        .accessibilityLabel("Juno version " + (Bundle.main.object(forInfoDictionaryKey:"JunoReleaseVersion") as? String ?? "Development"))
                }
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
            if let reminderDay, remindersEnabled, reminderDay == CheckInReminder.day(Date()), store.section != "Check-in", !store.meeting {
                HStack(spacing: 12) {
                    Label("Time for your daily check-in", systemImage: "bell")
                    Spacer()
                    Button("Open check-in") { store.section = "Check-in" }.buttonStyle(.borderedProminent)
                    Button("Dismiss reminder") { dismissReminder() }
                }.padding(.horizontal, 18).padding(.vertical, 8)
            }
            HStack(spacing:0) {
                if showSidebar {
                    List(selection:$store.section) {
                        Section("My workday") { ForEach(daily,id:\.0) { key,icon in Label(title(key),systemImage:icon).tag(key) } }
                        Section("Reporting") { Label("Reports", systemImage: "doc.text").tag("Reports") }
                        Section("Saved sources") { ForEach(sources,id:\.0) { key,icon in Label(title(key),systemImage:icon).tag(key) } }
                        Section { Button { NotificationCenter.default.post(name:Notification.Name("JunoSettings"),object:nil) } label: { Label("Settings…",systemImage:"gearshape") }.buttonStyle(.plain) }
                    }.listStyle(.sidebar).frame(width:178)
                    Divider()
                }
                ZStack { ForEach(visited,id:\.self) { key in
                    workspace(key).frame(maxWidth:.infinity,maxHeight:.infinity)
                        .opacity(store.section == key ? 1 : 0).disabled(store.section != key)
                        .allowsHitTesting(store.section == key).accessibilityHidden(store.section != key)
                } }
            }
            if let issue = store.problem { HStack { Text(issue).foregroundStyle(.orange);Spacer();Button("Dismiss") { store.problem = nil } }.padding(12) }
            Divider()
            HStack { Text(store.sharedProfile == nil ? "Saved on this Mac" : "Work Mac and offline copy"); Spacer() }
                .font(.caption).foregroundStyle(.secondary).padding(.horizontal,14).padding(.vertical,8)
        }.frame(minWidth:880,minHeight:600).preferredColorScheme(appearance == "light" ? .light : appearance == "dark" ? .dark : nil)
        .onReceive(NotificationCenter.default.publisher(for: Notification.Name("JunoToggleSidebar"))) { _ in showSidebar.toggle() }
        .onChange(of:store.section) { key in
            if !visited.contains(key) { visited.append(key) }
            if key == "Check-in" { dismissReminder() }
        }
        .task(id: "\(remindersEnabled)|\(reminderMinutes)|\(store.connected)|\(store.meeting)|\(store.section)") {
            guard remindersEnabled, store.connected, !store.meeting, store.section != "Check-in" else { return }
            while !Task.isCancelled {
                await checkReminder()
                do { try await Task.sleep(nanoseconds: 30_000_000_000) } catch { return }
            }
        }
        .alert("Keep your existing chat draft?",isPresented:Binding(get:{store.proposedChatDraft != nil},set:{if !$0 {store.proposedChatDraft = nil}})) {
            Button("Keep draft",role:.cancel) { store.proposedChatDraft = nil }
            Button("Add question to draft") { if let proposal = store.proposedChatDraft { store.chatDraft += "\n\n" + proposal };store.proposedChatDraft = nil;store.section = "Chat" }
        } message: { Text("Your unsent message is still here. You can add the planning question below it or keep working on your message.") }
    }
    private func dismissReminder() {
        reminderDay = nil
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [CheckInReminder.identifier])
        UNUserNotificationCenter.current().removeDeliveredNotifications(withIdentifiers: [CheckInReminder.identifier])
    }

    private func checkReminder() async {
        let now = Date()
        let day = CheckInReminder.day(now)
        if let reminderDay, reminderDay != day { self.reminderDay = nil }
        guard day != lastReminderDay, CheckInReminder.isDue(now, minutes: reminderMinutes) else { return }
        do {
            let row = try await store.decode(CheckInRecord.self, "/v1/check-ins/by-date/" + day)
            if row.status == "confirmed" { return }
        } catch let issue as APIProblem where issue.status == 404 {
            // There is no check-in yet for this date.
        } catch { return }
        guard !Task.isCancelled, remindersEnabled, day == CheckInReminder.day(Date()), day != lastReminderDay else { return }
        lastReminderDay = day
        reminderDay = day
        await CheckInReminder.notifyIfAllowed()
    }
}

struct ChatWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var deleteTarget: ConversationRecord?
    @State private var deletingConversation = false
    @State private var deleteIssue: String?
    var body: some View {
        HSplitView {
            VStack(alignment: .leading) {
                Button { store.chooseConversation(nil) } label: { Label("New conversation", systemImage: "plus") }.disabled(store.chatSending)
                List(selection: Binding(get: { store.currentConversation }, set: { store.chooseConversation($0) })) {
                    ForEach(store.conversations) { row in
                        Text(row.title).lineLimit(2).tag(row.id).contextMenu {
                            Button("Delete conversation…",role:.destructive) { deleteTarget = row;deleteIssue = nil }.disabled(store.offline || store.chatSending || deletingConversation)
                        }
                    }
                }.disabled(store.chatSending || deletingConversation)
                if let id = store.currentConversation,let row = store.conversations.first(where: { $0.id == id }) {
                    Button("Delete conversation…",role:.destructive) { deleteTarget = row;deleteIssue = nil }.disabled(store.offline || store.chatSending || deletingConversation)
                }
                if store.offline { Text("Reconnect to delete chats.").font(.caption).foregroundStyle(.secondary) }
                if let deleteIssue { Text(deleteIssue).font(.caption).foregroundStyle(.orange) }
                if store.conversationMore { Button("Older conversations") { Task { do { try await store.loadConversations(more: true) } catch { store.report(error) } } } }
            }.padding(14).frame(minWidth: 210, idealWidth: 250, maxWidth: 300)
            VStack(alignment: .leading, spacing: 14) {
                if !store.modelConfigured {
                    HStack { Text("Connect a local model to talk with Juno. The daily check-in works without one."); Spacer(); Button("Connect model") { store.openSettings("Model") } }.padding(12).background(.purple.opacity(0.1))
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
                                    if message.role == "user" && message.status == "complete" {
                                        if let memoryID = message.saved_memory_id {
                                            HStack {
                                                Label("Saved to memory",systemImage:"checkmark.circle.fill").foregroundStyle(.secondary)
                                                Button("Review memory") { Task { do {
                                                    if !store.items.contains(where:{$0.id == memoryID}) { store.items.insert(try await store.decode(Memory.self,"/v1/memories/"+memoryID),at:0) }
                                                    store.selected = memoryID;store.section = "Memories"
                                                } catch { store.report(error) } } }
                                            }.font(.caption)
                                        } else {
                                            Menu {
                                                Button("Save as memory…") {
                                                    store.memoryReviewOriginal = nil
                                                    store.memoryReviewMessageID = message.id
                                                    store.memoryReviewText = memoryRequestText(message.text) ?? message.text
                                                    store.memoryNotice = nil
                                                }.disabled(!store.connected)
                                            } label: {
                                                Label("Message actions", systemImage: "ellipsis.circle").labelStyle(.iconOnly)
                                            }
                                            .menuStyle(.borderlessButton)
                                            .fixedSize()
                                            .accessibilityLabel("Message actions")
                                            .help("Message actions")
                                        }
                                    }
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
        .alert("Delete this conversation?",isPresented:Binding(get:{deleteTarget != nil},set:{if !$0 {deleteTarget = nil}})) {
            Button("Cancel",role:.cancel) { deleteTarget = nil }
            Button("Delete conversation",role:.destructive) {
                guard let target = deleteTarget else { return };deleteTarget = nil;deletingConversation = true
                Task { defer { deletingConversation = false };do { try await store.deleteConversation(target.id) } catch { deleteIssue = (error as? APIProblem)?.message ?? "Could not delete the conversation. It is still saved." } }
            }
        } message: { Text("“" + (deleteTarget?.title ?? "") + "” and all its messages will be permanently removed from Juno’s active records. Saved memories and diary entries stay intact. Other devices may retain an older copy until they sync; old backups are unchanged.") }
        .sheet(isPresented:Binding(get:{store.memoryReviewText != nil},set:{if !$0 {store.memoryReviewText = nil;store.memoryReviewOriginal = nil;store.memoryReviewMessageID = nil}})) {
            Editor(store:store,original:nil,initialText:store.memoryReviewText ?? "",sourceMessageID:store.memoryReviewMessageID) { saved in
                store.memoryNotice = store.offline ? "Memory saved on this laptop and queued for sync." : "Memory saved. You can review, correct or delete it in Memories."
                if let original = store.memoryReviewOriginal,store.chatDraft == original {
                    store.chatDraft = "";UserDefaults.standard.removeObject(forKey:"chatDraft." + (store.currentConversation ?? "new"))
                }
                store.selected = saved.id;store.memoryReviewOriginal = nil;store.memoryReviewMessageID = nil;store.memoryReviewText = nil
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

struct CarryTaskChoice:Decodable,Identifiable { let task_id:String;let title:String;let reference:String;let context:String;var id:String{task_id} }
struct CarrySource:Decodable {
    let diary_id:String;let diary_revision:Int;let day:String;let text:String;let planning_revision:Int;let workspace_id:String;let snapshot_id:String;let taskdock_saved_at:String;let source_stale:Bool;let tasks:[CarryTaskChoice]
}
struct CarryReviewRow:Decodable,Identifiable {let key:String;let label:String;let before:String;let after:String;var id:String{key}}
struct CarryPreview:Decodable {let rows:[CarryReviewRow];let notice:String}
struct CarryReceipt:Decodable {let operation_id:String;let planning_revision:Int;let saved_at:String}

struct DailyBriefItem: Decodable, Identifiable {
    let task_id: String; let title: String
    var next_action: String?; var blocker: String?
    var id: String { task_id }
}
struct DailyBriefOption: Decodable, Identifiable {
    let task_id: String; let title: String; let estimate_minutes: Int; let reason: String
    let room: String; let employee: String; let resume: String; let slot_start: String; let slot_end: String
    var id: String { task_id }
}
struct OperationalClaim:Decodable,Identifiable {var kind:String;var text:String;var evidence_ids:[String];var id:String{kind+text}}
struct OperationalTask:Decodable,Identifiable {var task_id:String;var title:String;var assignment:String?;var completed:Bool;var impact:String?;var evidence_id:String;var id:String{task_id}}
struct OperationalCard:Decodable,Identifiable {var id:String;var title:String;var asset_id:String?;var issue_id:String?;var issue_state:String;var verification_state:String;var service_impact:String;var decision_authority:String;var relationship:String;var claims:[OperationalClaim];var tasks:[OperationalTask];var conflicts:[String];var next_action:String;var recommendation:String;var missing:[String];var stale:Bool}
struct OperationalEvidence:Decodable,Identifiable {var id:String;var app:String;var record_id:String;var snapshot_id:String;var version:String?;var retrieved_at:String;var updated_at:String?;var observed_at:String?;var source_link:String?;var local_path:String;var stale:Bool}
struct OperationalChoice:Decodable,Identifiable {var id:String;var title:String}
struct OperationalFeedback:Decodable,Identifiable {var operation_id:String;var outcome:String;var task_id:String;var planning_day:String;var rationale:String;var recorded_at:String;var id:String{operation_id}}
struct OperationalBrief:Decodable {var basis_token:String;var revision:Int;var cards:[OperationalCard];var evidence:[OperationalEvidence];var notices:[String];var task_choices:[OperationalChoice];var alert_choices:[OperationalChoice];var feedback:[OperationalFeedback];var notice:String}
struct DailyBrief: Decodable {
    let operations:OperationalBrief?
    let day: String; let workspace_id: String?; let taskdock_saved_at: String?; let source_stale: Bool
    let diary_status: String; let review: [String]; let completed: [DailyBriefItem]; let completed_count: Int
    let blockers: [DailyBriefItem]; let deferred_blocker_count: Int; let upcoming_blocker_count: Int
    let guidance: [String:[String]]; let next_day: String; let has_scheduled_workday: Bool
    let capacity_minutes: Int; let reserve_minutes: Int; let reserve_notice: String
    let question: String?; let recommended_task_id: String?; let alternatives: [DailyBriefOption]
    let continuity: String; let notices: [String]; let notice: String
}
func dailyBriefTime(_ value: String) -> String {
    let parser = ISO8601DateFormatter(); parser.formatOptions = [.withInternetDateTime,.withFractionalSeconds]
    guard let date = parser.date(from:value) ?? ISO8601DateFormatter().date(from:value) else { return "Time unavailable" }
    let formatter = DateFormatter(); formatter.locale = Locale(identifier:"en_US"); formatter.timeZone = TimeZone(identifier:"America/Chicago"); formatter.dateFormat = "h:mm a"
    return formatter.string(from:date)
}

struct CheckInWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var day = Date()
    @State private var brief: DailyBrief?
    @State private var briefIssue: String?
    @State private var briefRefresh = UUID()
    @State private var showCarry = false
    @State private var editingConfirmedDiary = false
    @FocusState private var answerFocused: Bool
    private let workTimeZone = TimeZone(identifier: "America/Chicago")!
    var dayKey: String {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = workTimeZone
        return formatter.string(from: day)
    }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Daily check-in").font(.largeTitle.bold()).accessibilityAddTraits(.isHeader)
                    Text("About 15 minutes · one question at a time").font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Reminder settings…") { store.openSettings("Check-in") }
                DatePicker("Check-in date", selection: $day, displayedComponents: .date)
                    .environment(\.timeZone, workTimeZone).fixedSize().disabled(store.checkBusy)
            }
            if let briefIssue { Text(briefIssue).font(.callout).foregroundStyle(.orange) }

            if let row = store.checkIn, row.local_date == dayKey {
                if row.status != "confirmed", let key = row.next_key, let question = row.questions.first(where: { $0.key == key }) {
                    VStack(alignment: .leading, spacing: 8) {
                        let step = row.questions.firstIndex(where: { $0.key == key }).map { $0 + 1 } ?? 1
                        Label("Question \(step) of \(row.questions.count)", systemImage: "bubble.left")
                            .font(.subheadline).foregroundStyle(.secondary)
                        ProgressView(value: Double(step - 1), total: Double(row.questions.count))
                            .frame(maxWidth: 240).accessibilityHidden(true)
                        Text(question.text).font(.title2.bold()).textSelection(.enabled).accessibilityAddTraits(.isHeader)
                        Text(row.answers.isEmpty ? "Write your answer below." : "\(row.answers.count) of \(row.questions.count) questions reviewed.").font(.callout).foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, alignment: .leading)
                    Text("Your answer").font(.headline)
                    if let hints = brief?.guidance[key], !hints.isEmpty {
                        if key == "completed", brief?.completed_count ?? 0 > 0 {
                            Text("From TaskDock’s saved copy").font(.caption.bold()).foregroundStyle(.secondary)
                        }
                        ForEach(hints,id:\.self) { Text($0).font(.callout).foregroundStyle(.secondary).textSelection(.enabled) }
                    }
                    TextEditor(text: $store.checkAnswer).frame(minHeight: 160).padding(8).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                        .focused($answerFocused).accessibilityLabel("Check-in answer").accessibilityHint(question.text)
                        .onChange(of: store.checkAnswer) { value in UserDefaults.standard.set(value, forKey: "answerDraft." + store.checkDay) }
                    if let issue = store.checkIssue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                    HStack {
                        Button("Skip for now") { store.saveAnswer(skip: true) }
                        Spacer()
                        Button("Save answer and continue") { store.saveAnswer() }
                            .buttonStyle(.borderedProminent)
                            .disabled(store.checkAnswer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.checkAnswer.count > 10000)
                    }.disabled(store.checkBusy)
                    .onChange(of: key) { _ in answerFocused = true }
                } else {
                    diaryReview(row)
                }
            } else if store.checkBusy { ProgressView("Loading check-in…") }
            if let brief {
                DisclosureGroup("Saved work context & freshness") {
                    VStack(alignment:.leading,spacing:8) {
                        Text(brief.source_stale ? "TaskDock context needs a refresh before planning." : "From your dated saved work; please confirm what happened.").foregroundStyle(brief.source_stale ? .orange : .secondary)
                        ForEach(brief.review,id:\.self) { Text($0).font(.callout) }
                        Text("\(brief.deferred_blocker_count) blocker checks are deferred; \(brief.upcoming_blocker_count) fall before the next workday.").font(.caption).foregroundStyle(.secondary)
                        DisclosureGroup("Evidence & freshness") {
                            ForEach(brief.completed) { Text("Completion timestamp: " + $0.title).font(.caption) }
                            ForEach(brief.notices,id:\.self) { Text($0).font(.caption) }
                        }
                    }.frame(maxWidth:.infinity,alignment:.leading)
                }
            }
            if let operations = brief?.operations { OperationalBriefView(store:store,initial:operations) }
            if let brief, let row = store.checkIn, row.local_date == dayKey, row.next_key == nil {
                GroupBox("Next workday · " + brief.next_day) {
                    VStack(alignment:.leading,spacing:10) {
                        Text(row.status == "confirmed" ? "Your diary is confirmed. Review one next step below." : "Confirm your diary when it is ready. These are proposals from saved planning facts.")
                        if !brief.continuity.isEmpty { Text("Your carry-forward note: " + brief.continuity).textSelection(.enabled) }
                        if let question = brief.question { Text(question).font(.headline) }
                        Text("\(brief.capacity_minutes) minutes of possible capacity after a \(brief.reserve_minutes)-minute interruption reserve.").font(.callout)
                        Text(brief.reserve_notice).font(.caption).foregroundStyle(.secondary)
                        ForEach(brief.alternatives) { task in
                            VStack(alignment:.leading,spacing:6) {
                                Text(task.title).font(.headline)
                                Text((task.id == brief.recommended_task_id ? "Suggested first · " : "Alternative · ") + task.reason)
                                Text("\(task.estimate_minutes) minutes · \(dailyBriefTime(task.slot_start))–\(dailyBriefTime(task.slot_end))" + (task.room.isEmpty ? "" : " · " + task.room) + (task.employee.isEmpty ? "" : " · " + task.employee))
                                if !task.resume.isEmpty { Text("Resume: " + task.resume) }
                                RecommendationFeedbackButton(store:store,taskID:task.id,day:brief.next_day)
                                Button("Review this issue in Plan") { openPlan(brief,task.id) }.disabled(store.offline || store.checkBusy || store.unsavedSections.contains("Plan"))
                            }.padding(.vertical,6)
                        }
                        if brief.alternatives.isEmpty { Text("No ready task is established for this workday. Clarify the missing information in Plan.").foregroundStyle(.secondary) }
                        Button("Open Plan for this day") { openPlan(brief,nil) }.disabled(store.offline || store.checkBusy || store.unsavedSections.contains("Plan"))
                        if store.unsavedSections.contains("Plan") { Text("Save or discard your existing Plan draft before opening a different day or issue.").foregroundStyle(.orange) }
                        Text(brief.notice).font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth:.infinity,alignment:.leading)
                }
            }
            if let row = store.checkIn, row.local_date == dayKey { Text(row.source_notice).font(.caption).foregroundStyle(.secondary) }
            if let issue = store.checkIssue, store.checkIn?.local_date != dayKey || store.checkIn?.next_key == nil || store.checkIn?.status == "confirmed" {
                Text(issue).foregroundStyle(.orange).textSelection(.enabled)
            }
            Button("Reload saved check-in") { briefRefresh = UUID();store.loadCheckIn(day: dayKey) }.disabled(!store.connected || store.checkBusy)
            Spacer(minLength: 0)
        }.padding(28) }.disabled(!store.connected)
        .task(id: dayKey + ":" + String(store.connected) + ":" + String(store.offline) + ":" + String(store.checkIn?.revision ?? 0) + ":" + store.section + ":" + briefRefresh.uuidString) {
            brief = nil; briefIssue = nil
            guard store.section == "Check-in" else { return }
            guard store.connected, !store.offline else { briefIssue = "Connect to your work Mac for a fresh daily review and next-workday preview. Diary answers can still save offline."; return }
            do {
                let value = try await store.decode(DailyBrief.self,"/v1/planning/daily-brief?day=" + dayKey)
                guard !Task.isCancelled, value.day == dayKey, !store.offline else { return }
                brief = value
            } catch { if !Task.isCancelled { briefIssue = "Your interview is still available. Saved work context could not refresh; reconnect and reload to preview the next workday." } }
        }
        .sheet(isPresented:$showCarry,onDismiss:{briefRefresh=UUID()}) { CarryForwardEditor(store:store,dayKey:dayKey,planDay:brief?.next_day ?? dayKey) }
        .onAppear { openToday() }
        .onChange(of: store.section) { section in if section == "Check-in" { openToday() } }
        .onChange(of: store.connected) { connected in
            if connected, store.section == "Check-in" { store.loadCheckIn(day: dayKey) }
        }
        .onChange(of: dayKey) { key in
            editingConfirmedDiary = false
            if store.connected, store.section == "Check-in" { store.loadCheckIn(day: key) }
        }
        .onChange(of: store.checkIn?.revision) { _ in
            if let saved = store.checkIn, saved.status == "confirmed", saved.diary_text == store.diaryDraft {
                editingConfirmedDiary = false
            }
        }
    }

    private func diaryReview(_ row: CheckInRecord) -> some View {
        let confirmed = row.status == "confirmed"
        let hasChanges = store.diaryDraft != row.diary_text
        return VStack(alignment: .leading, spacing: 12) {
            Label(confirmed ? "Diary confirmed" : "Review your diary draft",
                  systemImage: confirmed ? "checkmark.circle" : "pencil")
                .font(.title3.bold()).accessibilityAddTraits(.isHeader)
            if !confirmed || editingConfirmedDiary || hasChanges {
                TextEditor(text: $store.diaryDraft).frame(minHeight: 220).padding(8)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                    .accessibilityLabel(confirmed ? "Diary corrections" : "Diary draft")
                    .disabled(store.checkBusy)
                    .onChange(of: store.diaryDraft) { value in
                        UserDefaults.standard.set(value, forKey: "diaryDraft." + store.checkDay)
                    }
                HStack {
                    if confirmed {
                        Button("Cancel edits") {
                            store.diaryDraft = row.diary_text
                            UserDefaults.standard.removeObject(forKey: "diaryDraft." + row.local_date)
                            editingConfirmedDiary = false
                        }.disabled(store.checkBusy)
                    } else {
                        Button("Save draft") { store.saveDiary(confirm: false) }
                            .disabled(!hasChanges || store.checkBusy || !validDiary)
                    }
                    Spacer()
                    Button(confirmed ? "Save corrections" : "Confirm diary") { store.saveDiary(confirm: true) }
                        .buttonStyle(.borderedProminent)
                        .disabled(store.checkBusy || !validDiary || (confirmed && !hasChanges))
                }
            } else {
                Text(row.diary_text).lineSpacing(4).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading).padding(16)
                    .background(.background, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
                HStack {
                    Button("Edit diary…") { editingConfirmedDiary = true }
                    Spacer()
                    Button("Carry a reviewed detail into Plan…") { showCarry = true }
                        .disabled(store.offline || store.checkBusy || store.unsavedSections.contains("Plan"))
                }
                if store.offline || store.unsavedSections.contains("Plan") {
                    Text(store.offline ? "Reconnect to carry a detail into Plan." : "Save or discard the current Plan draft before carrying a detail forward.")
                        .font(.callout).foregroundStyle(.secondary)
                }
            }
        }
    }

    private var validDiary: Bool {
        !store.diaryDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && store.diaryDraft.count <= 60000
    }
    private func openToday() {
        guard store.section == "Check-in" else { return }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = workTimeZone
        let today = Date()
        if !calendar.isDate(day, inSameDayAs: today) {
            day = today
        } else if store.connected {
            store.loadCheckIn(day: dayKey)
        }
    }
    private func openPlan(_ brief: DailyBrief,_ taskID: String?) {
        guard !store.unsavedSections.contains("Plan"), !store.offline else { return }
        store.planningDayKey = brief.next_day
        store.planningWorkspaceID = brief.workspace_id
        store.planningTaskID = taskID
        store.section = "Plan"
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
    [task.text("blocked_reason") ?? "",task.planningText("blockers") ?? "",task.planningText("dependencies") ?? "",task.planningBlockerFlag ?? "",facts?.blocker ?? "",facts?.waiting_on ?? ""].contains { !$0.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty }
}

struct TodayWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var snapshot: TaskDockSnapshot?
    @State private var planning: PlanningRecord?
    @State private var schedules: ScheduleRecord?
    @State private var issues: [String] = []
    @State private var busy = false
    @State private var loadID = UUID()
    @State private var filter = "Due / overdue"
    @State private var search = ""
    @FocusState private var searchFocused: Bool
    @State private var remember = false
    @State private var todayCheckIn: CheckInRecord?
    @State private var recallUnavailable = false
    private var today: String { CheckInReminder.day(Date()) }
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
        guard store.connected else { return }
        let requestID = UUID(); loadID = requestID
        busy = true
        defer { if loadID == requestID { busy = false } }
        var nextSnapshot = snapshot
        var nextPlanning: PlanningRecord?
        var nextSchedules: ScheduleRecord?
        var nextIssues: [String] = []
        var nextCheckIn: CheckInRecord?
        var nextRecallUnavailable = false
        let day = today
        do { let value = try await store.decode(TaskDockState.self,"/v1/taskdock");nextSnapshot = value.snapshot;if let error = value.error { nextIssues.append(error) } }
        catch { nextIssues.append("TaskDock summary could not refresh. Any previous copy stays visible.") }
        guard !Task.isCancelled, loadID == requestID, store.section == "Today" else { return }
        do { nextPlanning = try await store.decode(PlanningRecord.self,"/v1/planning") }
        catch { nextIssues.append("Planning details unavailable; blocker counts may be incomplete.") }
        guard !Task.isCancelled, loadID == requestID, store.section == "Today" else { return }
        do { nextSchedules = try await store.decode(ScheduleRecord.self,"/v1/schedules") }
        catch { nextIssues.append("Planning holds unavailable.") }
        guard !Task.isCancelled, loadID == requestID, store.section == "Today" else { return }
        do { nextCheckIn = try await store.decode(CheckInRecord.self, "/v1/check-ins/by-date/" + day) }
        catch let issue as APIProblem where issue.status == 404 {}
        catch { nextRecallUnavailable = true }
        guard !Task.isCancelled, loadID == requestID, store.section == "Today", store.connected, today == day else { return }
        snapshot = nextSnapshot; planning = nextPlanning; schedules = nextSchedules; issues = nextIssues
        todayCheckIn = nextCheckIn; recallUnavailable = nextRecallUnavailable
    }

    private var recall: some View {
        let completed = (snapshot?.items ?? []).filter { task in
            guard let raw = task.text("completed_at"), let date = providerDate(raw) else { return false }
            return CheckInReminder.day(date) == today
        }
        return GroupBox("Remember what you did today") {
            VStack(alignment: .leading, spacing: 10) {
                if let row = todayCheckIn, row.local_date == today, !row.diary_text.isEmpty {
                    DisclosureGroup(row.status == "confirmed" ? "Read your confirmed diary" : "Read your saved check-in notes") {
                        Text(row.diary_text).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(.vertical, 6)
                    }
                } else if recallUnavailable {
                    Text("Your saved check-in notes are unavailable right now.").foregroundStyle(.secondary)
                }
                if let snapshot {
                    Text(completed.isEmpty ? "No completions are dated today in the saved TaskDock copy." : "TaskDock recorded \(completed.count) \(completed.count == 1 ? "completion" : "completions") today.")
                    if !completed.isEmpty {
                        ForEach(completed.prefix(5)) { task in Label(task.title, systemImage: "checkmark.circle") }
                        if completed.count > 5 {
                            DisclosureGroup("Show \(completed.count - 5) more completions") {
                                ForEach(completed.dropFirst(5)) { task in Label(task.title, systemImage: "checkmark.circle") }
                            }
                        }
                        Text("These records can jog your memory. Review what you did in your check-in.").font(.caption).foregroundStyle(.secondary)
                    }
                    if snapshot.stale { Text("The TaskDock copy is out of date.").font(.caption).foregroundStyle(.secondary) }
                } else {
                    Text("Think back to what you finished, who you helped, and what interrupted your plans.").foregroundStyle(.secondary)
                }
            }.frame(maxWidth: .infinity, alignment: .leading).padding(8)
        }
    }
    private func countCard(_ title: String,_ value: Int,_ icon: String,_ selection: String, scroll: ScrollViewProxy) -> some View {
        Button {
            filter = selection
            scroll.scrollTo("today-issues", anchor: .top)
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Label(title, systemImage: icon).font(.subheadline)
                    Spacer(minLength: 4)
                    if filter == selection { Image(systemName: "checkmark.circle.fill").foregroundStyle(Color.accentColor).accessibilityHidden(true) }
                }
                Text(String(value)).font(.largeTitle.bold())
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Color.accentColor.opacity(filter == selection ? 0.14 : 0.05), in: RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
        .accessibilityLabel("\(title), \(value)")
        .accessibilityAddTraits(filter == selection ? .isSelected : [])
    }
    var body: some View {
        ScrollViewReader { scroll in
        ScrollView {
            VStack(alignment:.leading,spacing:18) {
                HStack {
                    VStack(alignment:.leading,spacing:5) {
                        Text("Today").font(.largeTitle.bold()).accessibilityAddTraits(.isHeader)
                        Text(Date().formatted(Date.FormatStyle(date: .complete, time: .omitted, timeZone: CheckInReminder.calendar.timeZone)))
                            .foregroundStyle(.secondary)
                    }
                    Spacer();Button("Refresh overview") { Task { await load() } }.disabled(busy || !store.connected)
                    if busy { ProgressView().controlSize(.small) }
                }
                HStack {
                    Button("Daily check-in") { store.section = "Check-in" }.buttonStyle(.borderedProminent)
                    Button("Review reports") { store.section = "Reports" }
                    Menu("More actions") {
                        Button("Talk it through") { store.section = "Chat" }
                        Button("Rooms & people") { store.section = "Schedules" }
                        Button("Remember something") { remember = true }.disabled(!store.connected)
                    }.fixedSize()
                }
                if store.offline { Label("Offline overview — dated records; memory and diary edits can queue for sync.",systemImage:"wifi.slash").foregroundStyle(.orange) }
                if store.connected { recall }
                ForEach(issues,id:\.self) { Text($0).font(.caption).foregroundStyle(.orange) }
                if let snapshot {
                    HStack {
                        countCard("Unfinished",tasks.count,"tray.full","All unfinished",scroll:scroll)
                        countCard("Due / overdue",due.count,"calendar.badge.clock","Due / overdue",scroll:scroll)
                        countCard("Recorded blockers",blocked.count,"pause.circle","Recorded blockers",scroll:scroll)
                    }
                    DisclosureGroup(snapshot.stale ? "TaskDock copy is out of date" : "TaskDock source details") {
                        Text("Saved " + scheduleDate(snapshot.fetched_at) + ". Counts include subtasks.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    if let error = snapshot.error { Text(error).font(.caption).foregroundStyle(.orange) }
                    GroupBox("Issues to review") {
                        VStack(alignment:.leading,spacing:12) {
                            HStack {
                                Picker("Show",selection:$filter) { Text("Due / overdue").tag("Due / overdue");Text("Recorded blockers").tag("Recorded blockers");Text("All unfinished").tag("All unfinished") }
                                TextField("Find an issue",text:$search).textFieldStyle(.roundedBorder).focused($searchFocused)
                            }
                            if filtered.isEmpty { Text("No matching issues in the saved copy.").foregroundStyle(.secondary) }
                            ForEach(filtered.prefix(20)) { task in
                                VStack(alignment:.leading,spacing:5) {
                                    HStack {
                                        Text(task.title).font(.headline)
                                        Spacer()
                                        Button("Review") { store.planningTaskID = task.id;store.section = "Plan" }
                                            .accessibilityLabel("Review " + task.title)
                                    }
                                    Text((task.text("status_name") ?? "Status unknown") + " • Due: " + (taskDueDay(task) ?? "Not recorded")).font(.caption).foregroundStyle(.secondary)
                                    if taskHasRecordedBlocker(task,facts(task)) { Text("Blocker: " + ([task.text("blocked_reason"),task.planningText("blockers"),task.planningText("dependencies"),task.planningBlockerFlag,facts(task)?.blocker,facts(task)?.waiting_on].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator:" • "))).font(.caption).foregroundStyle(.orange) }
                                }.padding(.vertical,8)
                                Divider()
                            }
                            if filtered.count > 20 { Text("Showing 20 of \(filtered.count). Search to narrow the list.").font(.caption) }
                            Button("Open all TaskDock records") { store.section = "TaskDock" }
                        }.padding(8).frame(maxWidth:.infinity,alignment:.leading)
                    }.id("today-issues")
                } else if !busy {
                    GroupBox("Your TaskDock context") { VStack(alignment:.leading,spacing:10) {
                        Text(!store.connected ? "Connect to Juno’s service to load your saved TaskDock tasks." : !issues.isEmpty ? "The saved TaskDock summary could not be loaded. Try Refresh overview or check the TaskDock connection." : "No TaskDock snapshot is available yet. Connect TaskDock to see issues and deadlines here.")
                        Button("Open TaskDock") { store.section = "TaskDock" }
                    }.padding(12).frame(maxWidth:.infinity,alignment:.leading) }
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
        }
        .onReceive(NotificationCenter.default.publisher(for: Notification.Name("JunoFind"))) { _ in
            guard store.section == "Today", snapshot != nil else { return }
            scroll.scrollTo("today-issues", anchor: .top)
            searchFocused = true
        }
        }.task(id: String(store.connected) + "|" + store.section) {
            guard store.section == "Today" else { return }
            await load()
        }
        .sheet(isPresented:$remember) { Editor(store:store,original:nil) }
    }
}


struct JunoSettingsView: View {
    @ObservedObject var store:JunoStore
    @AppStorage("appearance") private var appearance = "system"
    @State private var visited = ["Connections"]
    @ViewBuilder private func page(_ key:String) -> some View {
        switch key {
        case "Model": if store.sharedProfile == nil { ModelWorkspace(store:store) } else { Text("Your work Mac runs Juno’s model. Memory and diary edits work offline.").padding(24) }
        case "Computers": ComputersWorkspace(store:store)
        case "Check-in": CheckInSettingsView()
        case "Appearance": VStack(alignment:.leading,spacing:16) { Picker("Appearance",selection:$appearance) { Text("Follow system").tag("system");Text("Light").tag("light");Text("Dark").tag("dark") };Text("Juno uses standard Mac fonts and controls. The system’s accessibility settings remain in effect.").foregroundStyle(.secondary) }.padding(24).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)
        case "Conversation":
            Form {
                Toggle("Meeting mode", isOn: $store.meeting)
                Text(store.meeting
                     ? "Juno uses a professional tone and hides her private chat replies."
                     : "Juno is warm and conversational. She can be lightly flirty when you set a playful tone.")
                    .foregroundStyle(.secondary)
            }.formStyle(.grouped)
        default: ConnectionsWorkspace(store:store)
        }
    }
    var body: some View {
        HSplitView {
            List(selection:$store.settingsSection) {
                Label("Connections",systemImage:"link").tag("Connections")
                Label("Local model",systemImage:"sparkles").tag("Model")
                Label("Computers & sync",systemImage:"desktopcomputer").tag("Computers")
                Label("Daily check-in",systemImage:"bell").tag("Check-in")
                Label("Appearance",systemImage:"circle.lefthalf.filled").tag("Appearance")
                Label("Conversation",systemImage:"bubble.left.and.bubble.right").tag("Conversation")
            }.listStyle(.sidebar).frame(minWidth:170,idealWidth:190,maxWidth:210)
            ZStack { ForEach(visited,id:\.self) { key in
                page(key).opacity(store.settingsSection == key ? 1 : 0).disabled(store.settingsSection != key).allowsHitTesting(store.settingsSection == key).accessibilityHidden(store.settingsSection != key)
            }
            }.frame(minWidth:560,maxWidth:.infinity,maxHeight:.infinity)
        }.frame(minWidth:780,minHeight:560).onAppear { if !visited.contains(store.settingsSection) { visited.append(store.settingsSection) } }.preferredColorScheme(appearance == "light" ? .light : appearance == "dark" ? .dark : nil).onChange(of:store.settingsSection) { key in if !visited.contains(key) { visited.append(key) } }
    }
}

struct CheckInSettingsView: View {
    @AppStorage(CheckInReminder.enabledKey) private var enabled = true
    @AppStorage(CheckInReminder.minutesKey) private var minutes = CheckInReminder.defaultMinutes
    @State private var authorization: UNAuthorizationStatus?
    @State private var notificationStatus: String?
    @State private var requesting = false

    private var time: Binding<Date> {
        Binding(get: {
            let calendar = CheckInReminder.calendar
            return calendar.date(bySettingHour: minutes / 60, minute: minutes % 60, second: 0, of: Date()) ?? Date()
        }, set: { date in
            let parts = CheckInReminder.calendar.dateComponents([.hour, .minute], from: date)
            minutes = (parts.hour ?? 16) * 60 + (parts.minute ?? 0)
        })
    }

    var body: some View {
        Form {
            Section("Daily check-in reminder") {
                Toggle("Remind me on weekdays", isOn: $enabled)
                DatePicker("Reminder time (Central)", selection: time, displayedComponents: .hourAndMinute)
                    .environment(\.timeZone, CheckInReminder.calendar.timeZone).disabled(!enabled)
                Text("Keep Juno open on this Mac. The reminder appears once a day and skips a confirmed check-in.")
                    .font(.callout).foregroundStyle(.secondary)
            }
            Section("macOS notifications") {
                if authorization == .denied {
                    Text("In System Settings → Notifications → Juno, turn on Allow notifications. Return here to send a test.")
                        .font(.callout).foregroundStyle(.secondary)
                } else if authorization == .authorized {
                    Button("Send test notification") {
                        Task {
                            do {
                                try await CheckInReminder.sendTest()
                                notificationStatus = "Test sent. Check Notification Center for “Juno reminder test”."
                            } catch { notificationStatus = "The test notification could not be sent." }
                        }
                    }
                } else if authorization == .notDetermined {
                    Button(requesting ? "Requesting permission…" : "Allow macOS notifications…") {
                        Task { await requestNotificationPermission() }
                    }.disabled(requesting)
                } else {
                    Text("Checking notification permission…").foregroundStyle(.secondary)
                }
                if let notificationStatus { Text(notificationStatus).font(.callout) }
            }
        }.formStyle(.grouped)
        .task { await refreshAuthorization() }
        .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
            Task { await refreshAuthorization() }
        }
    }

    private func refreshAuthorization() async {
        authorization = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
    }

    private func requestNotificationPermission() async {
        requesting = true
        notificationStatus = nil
        defer { requesting = false }
        do {
            _ = try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound])
            await refreshAuthorization()
            if authorization == .notDetermined {
                notificationStatus = "macOS hasn’t granted permission yet. If Juno appears in System Settings → Notifications, enable it there and return here."
            }
        } catch {
            await refreshAuthorization()
            notificationStatus = "Juno couldn’t request notification permission. The in-app reminder is still available."
        }
    }
}
struct JunoHelpView: View {
    var body: some View {
        ScrollView { VStack(alignment:.leading,spacing:20) {
            Text("A little less to keep in your head").font(.title2.bold())
            Text("Start in Today for a saved overview. Plan helps you review one issue at a time. Schedules compares rooms, people and possible work windows.")
            GroupBox("Talk and remember") { Text("Chat drafts stay until you send or clear them. Saving a memory opens a review first. A Saved to memory badge means a memory record exists; a model’s promise does not. Review and correct facts in Memories.").frame(maxWidth:.infinity,alignment:.leading) }
            GroupBox("Plan with confidence") { Text("TaskDock is your task hub. Juno reads shared information and labels unknowns. Estimates and possible work windows need review. Apply changes a draft; Save planning persists it. Juno does not assign or notify staff.").frame(maxWidth:.infinity,alignment:.leading) }
            GroupBox("At the end of the day") { Text("Today shows dated TaskDock completions and your saved diary to help you remember. Daily check-in asks five questions. Set your weekday reminder in Settings → Daily check-in.").frame(maxWidth:.infinity,alignment:.leading) }
            GroupBox("Review a report") { Text("Open Reports from the sidebar or Today. Review Thursday’s Dean talking points or select a recipient for Friday’s email. Save your edits in Juno, then copy the email when you’re ready to send it.").frame(maxWidth:.infinity,alignment:.leading) }
            GroupBox("Away from work") { Text("A paired laptop keeps a dated offline copy and queues memory and diary edits. AI replies need the work Mac awake and reachable. Review sync conflicts in Settings → Computers & sync.").frame(maxWidth:.infinity,alignment:.leading) }
            Text("Command-comma opens Settings. Command-F focuses the current workspace’s search when available. Option-Command-S shows or hides the sidebar. Close Window keeps Juno running. Quit stops this app’s local service.").font(.callout).foregroundStyle(.secondary)
        }.padding(24).textSelection(.enabled) }.frame(minWidth:560,minHeight:440)
    }
}

struct CarryForwardEditor:View {
    @ObservedObject var store:JunoStore
    let dayKey:String
    let planDay:String
    @Environment(\.dismiss) private var dismiss
    @State private var source:CarrySource?
    @State private var query=""
    @State private var taskID=""
    @State private var quote=""
    @State private var selectedFields=Set<String>()
    @State private var resume=""
    @State private var blocker=""
    @State private var waiting=""
    @State private var next=""
    @State private var check=""
    @State private var minutes=""
    @State private var preview:CarryPreview?
    @State private var previewPayload:[String:Any]?
    @State private var pending:[String:Any]?
    @State private var pendingKey:String?
    @State private var receipt:CarryReceipt?
    @State private var busy=false
    @State private var notice=""
    var intentKey:String { ([taskID,quote,resume,blocker,waiting,next,check,minutes]+selectedFields.sorted()).joined(separator:"\u{001f}") }
    private func toggle(_ key:String)->Binding<Bool> { Binding(get:{selectedFields.contains(key)},set:{if $0{selectedFields.insert(key)}else{selectedFields.remove(key)}}) }
    private func load() {
        busy=true;Task { defer{busy=false};do {
            let current=try await store.decode(CarrySource.self,"/v1/planning/carry-forward?day="+dayKey)
            source=current;preview=nil;previewPayload=nil
            pendingKey="carryPending."+current.diary_id
            if let key=pendingKey,let data=UserDefaults.standard.data(forKey:key),let recovered=try JSONSerialization.jsonObject(with:data) as? [String:Any] { pending=recovered;notice="Recovered an unconfirmed save. Retry the same save to recover its receipt." }
            if quote.isEmpty { quote=String(current.text.prefix(3000)) }
            if pending == nil { notice="Read the saved diary, choose the exact task, and select only the fields you want to change." }
        } catch { notice=(error as? APIProblem)?.message ?? "Could not read the confirmed diary and planning context." } }
    }
    private func bodyValues() throws -> [String:Any] {
        guard let source else{throw APIProblem(message:"Reload the saved diary first.",status:0)}
        if selectedFields.contains("minutes") || selectedFields.contains("next_check") {
            if let problem=planningInputIssue(estimate:selectedFields.contains("minutes") ? minutes : "",actual:"",check:selectedFields.contains("next_check") ? check : "") { throw APIProblem(message:problem,status:422) }
        }
        var changes:[String:Any]=[:]
        for (key,value) in [("resume",resume),("blocker",blocker),("waiting_on",waiting),("next_action",next)] where selectedFields.contains(key) { changes[key]=value }
        if selectedFields.contains("minutes"){changes["minutes"]=Int(minutes.trimmingCharacters(in:.whitespacesAndNewlines)).map{$0 as Any} ?? NSNull()}
        if selectedFields.contains("next_check"){changes["next_check"]=check.isEmpty ? NSNull() : check as Any}
        return ["diary_id":source.diary_id,"diary_revision":source.diary_revision,"planning_revision":source.planning_revision,"workspace_id":source.workspace_id,"snapshot_id":source.snapshot_id,"task_id":taskID,"source_quote":quote,"changes":changes]
    }
    private func review() {
        do { let payload=try bodyValues();busy=true
            Task { defer{busy=false};do { preview=try await store.decode(CarryPreview.self,"/v1/planning/carry-forward/preview",method:"POST",body:payload);previewPayload=payload;notice="Review every before-and-after value. An empty selected field explicitly clears that value." } catch { notice=(error as? APIProblem)?.message ?? "Could not prepare this review. Your text remains here." } }
        } catch {notice=(error as? APIProblem)?.message ?? "Check the selected fields."}
    }
    private func save() {
        guard var payload=previewPayload,let key=pendingKey else{return};payload["operation_id"]=UUID().uuidString
        do { let data=try JSONSerialization.data(withJSONObject:payload);UserDefaults.standard.set(data,forKey:key);pending=payload;retry() }
        catch { notice="Could not preserve this save for retry. Your reviewed text remains here; nothing was sent." }
    }
    private func retry() {
        guard let operation=pending,!busy else{return};busy=true
        Task { defer{busy=false};do {
            receipt=try await store.decode(CarryReceipt.self,"/v1/planning/carry-forward/save",method:"POST",body:operation);pending=nil;if let key=pendingKey{UserDefaults.standard.removeObject(forKey:key)};notice="Saved to Juno planning with its diary source and review history. TaskDock has not been edited."
        } catch {
            if let failure=error as? APIProblem,(400..<500).contains(failure.status){pending=nil;if let key=pendingKey{UserDefaults.standard.removeObject(forKey:key)};preview=nil;previewPayload=nil;notice=failure.message+" Reload source and compare before reviewing again."}
            else {notice="No save receipt was received. Keep this window open and retry the same save."}
        } }
    }
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            Text("Carry a reviewed detail into Plan").font(.title2.bold())
            Text("Confirmed diary · "+dayKey).foregroundStyle(.secondary)
            if !notice.isEmpty { Text(notice).foregroundStyle(.orange).textSelection(.enabled) }
            ScrollView { VStack(alignment:.leading,spacing:12) {
                if let source {
                    Text(source.source_stale ? "TaskDock context needs a refresh; the task may have changed." : "Choose the task from your saved TaskDock copy.").foregroundStyle(source.source_stale ? .orange : .secondary)
                    DisclosureGroup("Read the saved diary — revision \(source.diary_revision)") { Text(source.text).textSelection(.enabled) }
                    Text("Diary excerpt supporting this detail").font(.headline)
                    TextEditor(text:$quote).frame(height:100).accessibilityLabel("Carry-forward diary excerpt").overlay(RoundedRectangle(cornerRadius:8).stroke(.quaternary))
                    TextField("Find task by title or reference",text:$query).textFieldStyle(.roundedBorder)
                    Picker("Task to update", selection: $taskID) {
                        Text("Choose a task").tag("")
                        ForEach(source.tasks.filter { task in
                            query.isEmpty || [task.title, task.context, task.reference, task.id]
                                .joined(separator: " ").localizedCaseInsensitiveContains(query)
                        }) { task in
                            Text(task.title + (task.context.isEmpty ? "" : " · " + task.context) + " · " + task.reference).tag(task.id)
                        }
                    }
                    Text("Only checked fields change. Unchecked fields keep their saved values.").font(.callout)
                    Toggle("Where to resume",isOn:toggle("resume"));if selectedFields.contains("resume") {TextField("Reviewed resumption note",text:$resume).textFieldStyle(.roundedBorder);Button("Use diary excerpt as resumption note"){resume=quote}}
                    Toggle("Blocker",isOn:toggle("blocker"));if selectedFields.contains("blocker"){TextField("Reviewed blocker — blank explicitly clears",text:$blocker).textFieldStyle(.roundedBorder)}
                    Toggle("Waiting on",isOn:toggle("waiting_on"));if selectedFields.contains("waiting_on"){TextField("Reviewed dependency",text:$waiting).textFieldStyle(.roundedBorder)}
                    Toggle("Next action",isOn:toggle("next_action"));if selectedFields.contains("next_action"){TextField("Reviewed next action",text:$next).textFieldStyle(.roundedBorder)}
                    Toggle("Next check date",isOn:toggle("next_check"));if selectedFields.contains("next_check"){TextField("YYYY-MM-DD — blank explicitly clears",text:$check).textFieldStyle(.roundedBorder)}
                    Toggle("Estimated minutes",isOn:toggle("minutes"));if selectedFields.contains("minutes"){TextField("Reviewed estimate — blank explicitly clears",text:$minutes).textFieldStyle(.roundedBorder)}
                }
                if let preview {
                    GroupBox("Review selected changes") { VStack(alignment:.leading,spacing:10) {ForEach(preview.rows){row in Text(row.label).bold();Text("Before: "+row.before);Text("After: "+row.after)};Text(preview.notice).font(.caption)}.frame(maxWidth:.infinity,alignment:.leading) }
                }
            }.padding(4).disabled(busy || pending != nil || receipt != nil) }
            HStack {
                Button(receipt == nil ? "Cancel" : "Close") { dismiss() }.disabled(busy || pending != nil).keyboardShortcut(.cancelAction)
                Button("Reload source & compare",action:load).disabled(busy || pending != nil || receipt != nil)
                if pending != nil {Button("Retry same save",action:retry).disabled(busy || store.offline);Button("Keep pending save & close"){dismiss()}.disabled(busy)}
                Spacer()
                Button("Review changes",action:review).disabled(busy || taskID.isEmpty || quote.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty || selectedFields.isEmpty || pending != nil || receipt != nil)
                Button("Save reviewed planning detail",action:save).disabled(busy || previewPayload == nil || pending != nil || receipt != nil || store.offline)
            }
        }.padding(22).frame(width:780,height:720)
        .onAppear(perform:load)
        .onChange(of:intentKey){_ in preview=nil;previewPayload=nil}
        .onChange(of:busy){value in if value || pending != nil {store.unsavedSections.insert("Planning carry-forward")}else{store.unsavedSections.remove("Planning carry-forward")}}
        .onDisappear{store.unsavedSections.remove("Planning carry-forward")}
        .interactiveDismissDisabled(busy || pending != nil)
    }
}

struct OperationalBriefView:View {
    @ObservedObject var store:JunoStore
    var initial:OperationalBrief
    @State private var current:OperationalBrief?
    @State private var manage=false
    @State private var refreshing=false
    @State private var selectedEvidence:OperationalEvidence?
    var value:OperationalBrief {current ?? initial}
    var body:some View {
        GroupBox("Equipment & linked work · saved evidence") {
            VStack(alignment:.leading,spacing:12) {
                ForEach(value.notices,id:\.self){Text($0).font(.caption).foregroundStyle(.secondary)}
                ForEach(value.cards){card in
                    DisclosureGroup(card.title+(card.stale ? " · needs refresh" : "")) {
                        VStack(alignment:.leading,spacing:8) {
                            Text("Relationship: "+card.relationship.replacingOccurrences(of:"_",with:" "))
                            ForEach(card.claims){claim in
                                Text(claim.kind.replacingOccurrences(of:"_",with:" ")+": "+claim.text).textSelection(.enabled)
                                HStack {ForEach(claim.evidence_ids,id:\.self){identity in
                                    if let evidence=value.evidence.first(where:{$0.id==identity}) {Button("View "+evidence.app+" evidence"){selectedEvidence=evidence}.font(.caption)}
                                }}
                            }
                            ForEach(card.tasks){task in Text("Assigned person: "+(task.assignment ?? "Not shared / unknown"))}
                            Text("Issue: "+card.issue_state+" · Recovery verification: "+card.verification_state)
                            Text("Next recorded action: "+card.next_action)
                            Text("Juno suggests: "+card.recommendation).font(.callout)
                            ForEach(card.conflicts,id:\.self){Text("Review contradiction: "+$0).foregroundStyle(.orange)}
                            if !card.missing.isEmpty {Text("Missing references: "+card.missing.joined(separator:", ")).font(.caption)}
                        }.padding(.vertical,6)
                    }
                }
                Button("Reload saved operational evidence") {refreshing=true;Task {defer{refreshing=false};do{current=try await store.decode(OperationalBrief.self,"/v1/operations")}catch{current=nil}}}.disabled(store.offline || refreshing)
                Button("Review alert–task links…"){manage=true}.disabled(store.offline || store.sharedProfile != nil)
                if !value.feedback.isEmpty {
                    DisclosureGroup("Recent planning choices") {ForEach(Array(value.feedback.suffix(10).reversed())){item in Text(item.planning_day+" · "+item.outcome+" · Task "+item.task_id+" · "+item.rationale).font(.caption)}}
                }
                OperationalSupportingReferences(store:store)
                Text(value.notice).font(.caption).foregroundStyle(.secondary)
                if store.sharedProfile != nil {Text("Review links on the work Mac. This laptop can read saved operational evidence while connected.").font(.caption)}
            }.frame(maxWidth:.infinity,alignment:.leading)
        }
        .onChange(of:initial.basis_token){_ in current=nil}
        .sheet(isPresented:$manage){OperationalLinkEditor(store:store,value:value){current=$0}}
        .sheet(item:$selectedEvidence){OperationalEvidenceSheet(store:store,evidence:$0)}
    }
}

struct OperationalLinkEditor:View {
    @ObservedObject var store:JunoStore
    var value:OperationalBrief
    var onSaved:(OperationalBrief)->Void
    @Environment(\.dismiss) private var dismiss
    @State private var alert="";@State private var task="";@State private var search="";@State private var rationale="";@State private var issue:String?;@State private var busy=false
    var choices:[OperationalChoice]{value.task_choices.filter{search.isEmpty || ($0.title+" "+$0.id).localizedCaseInsensitiveContains(search)}}
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            Text("Review a source relationship").font(.title2)
            Text("Choose exact records you know describe the same work. This saves references in Juno; it does not change either source.")
            Picker("Beacon observation",selection:$alert){Text("Choose observation").tag("");ForEach(value.alert_choices){Text($0.title+" · "+String($0.id.suffix(8))).tag($0.id)}}
            TextField("Search task titles or references",text:$search).textFieldStyle(.roundedBorder)
            Picker("TaskDock task",selection:$task){Text("Choose task").tag("");ForEach(choices){Text($0.title+" · "+String($0.id.suffix(12))).tag($0.id)}}
            TextField("Why these records belong together (optional)",text:$rationale).textFieldStyle(.roundedBorder)
            Text("Saving replaces the earlier link for this observation. Names and room labels are never used to create a link automatically.").font(.caption)
            if let issue {Text(issue).foregroundStyle(.orange)}
            if !alert.isEmpty {Button("Remove reviewed link") {
                busy=true;Task {defer{busy=false};do {let encoded=alert.addingPercentEncoding(withAllowedCharacters:.urlPathAllowed) ?? "";let result=try await store.decode(OperationalBrief.self,"/v1/operations/links/"+encoded+"?expected_revision="+String(value.revision),method:"DELETE");onSaved(result);dismiss()}catch{issue=(error as? APIProblem)?.message ?? "The link could not be removed. Reload and review."}}
            }}
            HStack {Button("Cancel"){dismiss()}.keyboardShortcut(.cancelAction);Spacer();Button("Save reviewed link"){
                busy=true;Task {defer{busy=false};do {let result=try await store.decode(OperationalBrief.self,"/v1/operations/links",method:"POST",body:["expected_revision":value.revision,"basis_token":value.basis_token,"alert_id":alert,"task_id":task,"rationale":rationale]);onSaved(result);dismiss()}catch{issue=(error as? APIProblem)?.message ?? "The link could not be saved. Reload the briefing before trying again."}}
            }.disabled(alert.isEmpty || task.isEmpty || !choices.contains(where:{$0.id==task}))}
        }.padding(24).frame(width:600).disabled(busy)
    }
}

struct OperationalEvidenceSheet:View {
    @ObservedObject var store:JunoStore;var evidence:OperationalEvidence
    @Environment(\.dismiss) private var dismiss
    @State private var original="Loading the saved source record…"
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            Text(evidence.app+" evidence").font(.title2)
            Text("Record: "+evidence.record_id+"\nSnapshot: "+evidence.snapshot_id+"\nRetrieved: "+evidence.retrieved_at+"\nObserved: "+(evidence.observed_at ?? "Unknown")+"\nVersion: "+(evidence.version ?? "Not supplied")).font(.caption).textSelection(.enabled)
            ScrollView {Text(original).font(.system(.body,design:.monospaced)).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)}
            Text("Saved source evidence, not proof of current equipment condition.").font(.caption)
            Button("Close"){dismiss()}.keyboardShortcut(.cancelAction)
        }.padding(24).frame(width:660,height:540)
        .task {
            do {let data=try await store.request(evidence.local_path);let object=try JSONSerialization.jsonObject(with:data)
                var selected:Any?
                if let root=object as? [String:Any] {
                    if evidence.app=="TaskDock",let items=root["items"] as? [[String:Any]] {selected=items.first{String(describing:$0["id"] ?? "")==evidence.record_id}}
                    if evidence.app=="Beacon",let sources=root["items"] as? [[String:Any]],let source=sources.first(where:{($0["id"] as? String)==evidence.snapshot_id}),let items=source["items"] as? [[String:Any]] {selected=items.first{($0["id"] as? String)==evidence.record_id}}
                }
                if let selected {original=String(data:try JSONSerialization.data(withJSONObject:selected,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8) ?? "Record unavailable."} else {original="The record is no longer available in this authorized snapshot. Reload the briefing; no older content is substituted."}
            }catch{original="The saved evidence could not be loaded. Reconnect or refresh the source; its contents remain unknown."}
        }
    }
}

struct RecommendationFeedbackButton:View {
    @ObservedObject var store:JunoStore;var taskID:String;var day:String
    @State private var show=false
    var body:some View {Button("Record planning choice…"){show=true}.disabled(store.offline || store.sharedProfile != nil).sheet(isPresented:$show){RecommendationFeedbackEditor(store:store,taskID:taskID,day:day)}}
}
struct RecommendationFeedbackEditor:View {
    @ObservedObject var store:JunoStore;var taskID:String;var day:String
    @Environment(\.dismiss) private var dismiss
    @State private var value:OperationalBrief?;@State private var outcome="accepted";@State private var rationale="";@State private var reschedule="";@State private var busy=false;@State private var issue:String?;@State private var pending:[String:Any]?;@State private var saved=false
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            Text("Record your planning choice").font(.title2)
            Text("This records feedback in Juno. It does not assign work, reserve time or change a TaskDock deadline.")
            Picker("Choice",selection:$outcome){Text("Accepted proposal").tag("accepted");Text("Dismissed").tag("dismissed");Text("Reschedule proposal").tag("rescheduled")}.disabled(pending != nil || saved)
            TextField("Reason (optional)",text:$rationale).textFieldStyle(.roundedBorder).disabled(pending != nil || saved)
            if outcome=="rescheduled" {TextField("Proposed date · YYYY-MM-DD",text:$reschedule).textFieldStyle(.roundedBorder).disabled(pending != nil || saved)}
            if let issue {Text(issue).foregroundStyle(.orange)}
            if saved {Text("Choice saved in Juno. TaskDock and calendar records were not changed.")}
            HStack {Button(saved ? "Close" : "Cancel"){dismiss()}.keyboardShortcut(.cancelAction);Spacer();if !saved {Button(pending == nil ? "Save choice" : "Retry same choice"){
                guard let value else{return};busy=true
                if pending == nil {var body:[String:Any]=["operation_id":UUID().uuidString,"expected_revision":value.revision,"basis_token":value.basis_token,"task_id":taskID,"planning_day":day,"outcome":outcome,"rationale":rationale];if outcome=="rescheduled"{body["reschedule_day"]=reschedule};pending=body}
                Task {defer{busy=false};do {_ = try await store.request("/v1/operations/feedback",method:"POST",body:pending);saved=true;pending=nil;issue=nil}catch{let error=error as? APIProblem;issue=error?.message ?? "Save result uncertain. Retry the same choice to recover its receipt.";if let status=error?.status,status>=400 && status<500{pending=nil}}}
            }.disabled(value == nil)}}
        }.padding(24).frame(width:560).disabled(busy)
        .task {do{value=try await store.decode(OperationalBrief.self,"/v1/operations");reschedule=day}catch{issue="Planning context could not load. Reconnect and try again."}}
    }
}

struct ProcedureChoice:Decodable,Identifiable {var kind:String;var snapshot_id:String;var record_id:String;var title:String;var id:String{kind+":"+record_id}}
struct ProcedureReference:Decodable,Identifiable {var kind:String;var record_id:String;var label:String;var text:String?;var changed:Bool;var stale:Bool;var available:Bool;var notice:String;var retrieved_at:String?;var source_updated_at:String?;var current_snapshot_id:String?;var id:String{kind+":"+record_id}}
struct ProcedureReferences:Decodable {var revision:Int;var items:[ProcedureReference];var choices:[ProcedureChoice];var limited:Bool;var notice:String}
struct LifecycleEvidence:Decodable,Identifiable {var id:String;var work_date:String;var summary:String}
struct LifecycleCandidate:Decodable,Identifiable {var room:String;var equipment:String;var reports:Int;var verified_repairs:Int;var evidence:[LifecycleEvidence];var recommendation:String;var missing:[String];var replacement_supported:Bool;var id:String{room+equipment}}
struct LifecycleReview:Decodable {var candidates:[LifecycleCandidate];var limited:Bool;var notice:String}
struct OperationalSupportingReferences:View {
    @ObservedObject var store:JunoStore
    @State private var procedures:ProcedureReferences?;@State private var lifecycle:LifecycleReview?;@State private var issue:String?;@State private var choose=false;@State private var selected="";@State private var label="";@State private var busy=false
    var body:some View {
        DisclosureGroup("Procedures & longer-term repair review") {
            VStack(alignment:.leading,spacing:10) {
                Button("Load authorized references") {load()}.disabled(store.offline || busy)
                if let issue {Text(issue).foregroundStyle(.orange)}
                if let procedures {
                    Text(procedures.notice).font(.caption)
                    ForEach(procedures.items){reference in
                        DisclosureGroup(reference.label+((reference.changed || reference.stale) ? " · review source" : "")) {
                            Text("Source: "+reference.kind+" · Record: "+reference.record_id+" · Snapshot: "+(reference.current_snapshot_id ?? "Unavailable")).font(.caption).textSelection(.enabled)
                            Text("Retrieved: "+(reference.retrieved_at ?? "Unknown")+" · Source update: "+(reference.source_updated_at ?? "Unknown")).font(.caption)
                            Text(reference.text ?? "Instructions are unavailable in the current authorized source.").textSelection(.enabled)
                            Text(reference.notice).font(.caption).foregroundStyle(.secondary)
                            Button("Remove reference") {
                                busy=true;Task{defer{busy=false};do{self.procedures=try await store.decode(ProcedureReferences.self,"/v1/operations/procedures/remove",method:"POST",body:["expected_revision":procedures.revision,"kind":reference.kind,"record_id":reference.record_id]);issue=nil}catch{issue=(error as? APIProblem)?.message ?? "The reference could not be removed. Reload and review."}}
                            }.disabled(store.sharedProfile != nil || busy)

                        }
                    }
                    Button("Designate a saved reference…"){choose=true}.disabled(store.sharedProfile != nil || procedures.choices.isEmpty || busy)
                    if procedures.limited {Text("Only the first 500 eligible saved records are listed.").font(.caption)}
                }
                if let lifecycle {
                    Text(lifecycle.notice).font(.caption)
                    ForEach(lifecycle.candidates){candidate in
                        Text(candidate.equipment+" · "+candidate.room).font(.headline)
                        Text(candidate.recommendation)
                        Text("Missing lifecycle inputs: "+candidate.missing.joined(separator:", ")).font(.caption)
                        ForEach(candidate.evidence){record in Text(record.work_date+": "+record.summary+" · Report "+record.id).font(.caption).textSelection(.enabled)}
                    }
                    if lifecycle.candidates.isEmpty {Text("No recurring-repair candidate is established in the reviewed history.").font(.caption)}
                    if lifecycle.limited {Text("Analysis covers the latest 2,000 included repair reports; older records remain retained.").font(.caption)}
                }
            }.padding(.vertical,6)
        }
        .sheet(isPresented:$choose) {
            VStack(alignment:.leading,spacing:12) {
                Text("Designate an authorized reference").font(.title2)
                Text("Select a record already shared with Juno. This does not mark its instructions as officially approved or permit execution.")
                Picker("Saved record",selection:$selected){Text("Choose record").tag("");ForEach(procedures?.choices ?? []){Text($0.kind+" · "+$0.title+" · "+String($0.record_id.suffix(10))).tag($0.id)}}
                TextField("Reference label",text:$label).textFieldStyle(.roundedBorder)
                if let issue {Text(issue).foregroundStyle(.orange)}
                HStack {Button("Cancel"){choose=false}.keyboardShortcut(.cancelAction);Spacer();Button("Save reference"){
                    guard let procedures,let choice=procedures.choices.first(where:{$0.id==selected}) else{return};busy=true
                    Task {defer{busy=false};do{self.procedures=try await store.decode(ProcedureReferences.self,"/v1/operations/procedures",method:"POST",body:["expected_revision":procedures.revision,"kind":choice.kind,"snapshot_id":choice.snapshot_id,"record_id":choice.record_id,"label":label]);choose=false;issue=nil}catch{issue=(error as? APIProblem)?.message ?? "The reference could not be saved. Reload the current source before retrying."}}
                }.disabled(selected.isEmpty || label.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty)}
            }.padding(24).frame(width:590).disabled(busy)
        }
    }
    func load(){busy=true;Task {defer{busy=false};do{procedures=try await store.decode(ProcedureReferences.self,"/v1/operations/procedures");lifecycle=try await store.decode(LifecycleReview.self,"/v1/operations/lifecycle");issue=nil}catch{issue="Saved references could not load. Reconnect to the work Mac and retry."}}}
}
