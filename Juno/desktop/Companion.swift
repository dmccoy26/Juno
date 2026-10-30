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
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Image(systemName: "sparkles").font(.title).foregroundStyle(.purple)
                VStack(alignment: .leading) { Text("Juno").font(.title2.bold()); Text(store.status).font(.caption).foregroundStyle(.secondary) }
                Spacer()
                Toggle("Meeting mode", isOn: $store.meeting).toggleStyle(.switch).help("New replies use a professional tone. Private-mode replies are hidden while this is on.")
            }.padding(18)
            Picker("Workspace", selection: $store.section) {
                Text("Chat").tag("Chat"); Text("Daily check-in").tag("Check-in"); Text("Memories").tag("Memories"); Text("Model connection").tag("Model"); Text("TaskDock").tag("TaskDock"); Text("Evidence").tag("Evidence"); Text("Computers").tag("Computers")
            }.pickerStyle(.segmented).padding(.horizontal, 20).padding(.bottom, 14)
            if store.sharedProfile != nil {
                HStack {
                    Text(store.offline ? "Offline laptop copy" : "Connected to your work Mac")
                    if let date = store.offlineDate { Text("Last full copy: " + date.formatted()).foregroundStyle(.secondary) }
                    Text("\(store.pendingEdits.count) queued edits")
                    Spacer(); Button("Reconnect / sync") { store.reconnectShared() }.disabled(store.syncing)
                }.font(.caption).padding(.horizontal,20).padding(.bottom,10)
                if let issue = store.syncIssue { Text(issue).font(.caption).foregroundStyle(.orange).padding(.horizontal,20) }
            }
            Divider()
            switch store.section {
            case "Memories": MemoryWorkspace(store: store)
            case "Check-in": CheckInWorkspace(store: store)
            case "Model":
                if store.sharedProfile == nil { ModelWorkspace(store: store) } else { VStack(spacing:16) { Text("The work Mac runs Juno’s model").font(.title2.bold()); Text("Configure LM Studio on the work Mac. AI replies need that Mac to be awake and reachable; memories and diary edits work offline.").foregroundStyle(.secondary) }.padding(32) }
            case "TaskDock": TaskDockWorkspace(store: store)
            case "Evidence": IntegrationsWorkspace(store: store)
            case "Computers": ComputersWorkspace(store: store)
            default: ChatWorkspace(store: store)
            }
            if let issue = store.problem { HStack { Text(issue).foregroundStyle(.orange); Spacer(); Button("Dismiss") { store.problem = nil } }.padding(12) }
            Divider()
            HStack { Text(store.sharedProfile == nil ? "Stored on this Mac" : "Work Mac + offline laptop copy"); Spacer(); Text("Juno 0.1.0-preview.7") }.font(.caption).foregroundStyle(.secondary).padding(12)
        }.frame(minWidth: 920, minHeight: 650)
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
                                    if message.status == "failed" { Button("Retry this reply") { store.sendChat(retry: message) }.disabled(store.chatSending) }
                                }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(message.role == "user" ? Color.purple.opacity(0.08) : Color.secondary.opacity(0.04)).clipShape(RoundedRectangle(cornerRadius: 10)).id(message.id)
                            }
                            if store.chatSending { ProgressView("Juno is thinking…") }
                        }.padding(.vertical, 4)
                    }.onChange(of: store.messages.count) { _ in if let last = store.messages.last { reader.scrollTo(last.id, anchor: .bottom) } }
                }
                if let issue = store.chatIssue { Text(issue).foregroundStyle(.orange).textSelection(.enabled) }
                HStack {
                    TextEditor(text: $store.chatDraft).frame(height: 75).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary)).accessibilityLabel("Message to Juno")
                        .onChange(of: store.chatDraft) { value in UserDefaults.standard.set(value, forKey: "chatDraft." + (store.currentConversation ?? "new")) }
                    Button("Send") { store.sendChat() }.keyboardShortcut(.return, modifiers: .command).disabled(!store.connected || store.offline || !store.pendingEdits.isEmpty || !store.modelConfigured || store.chatSending || store.chatDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.chatDraft.count > 6000)
                }
                HStack { Text("⌘ Return to send · \(store.chatDraft.count)/6000").font(.caption).foregroundStyle(.secondary); Spacer(); Button("Refresh chat") { if let id = store.currentConversation { Task { try? await store.loadMessages(id) } } }.disabled(store.chatSending) }
            }.padding(20).frame(minWidth: 480)
        }
    }
}

struct ModelWorkspace: View {
    @ObservedObject var store: JunoStore
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Give Juno a local model").font(.title2.bold())
            Text("Start the local server in LM Studio on this Mac, then find and select a chat model. No cloud fallback is enabled. Your laptop needs its own running model server.").foregroundStyle(.secondary)
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

struct CheckInWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var day = Date()
    var dayKey: String { let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd"; formatter.timeZone = .current; return formatter.string(from: day) }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack { Text("Your daily check-in").font(.title2.bold()); Spacer(); DatePicker("Day", selection: $day, displayedComponents: .date).fixedSize().disabled(store.checkBusy) }
            Text("About 15 minutes · answers save as you continue · no model required").font(.subheadline).foregroundStyle(.secondary)
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
        .onAppear { if store.connected { store.loadCheckIn(day: dayKey) } }
        .onChange(of: store.connected) { value in if value { store.loadCheckIn(day: dayKey) } }
        .onChange(of: day) { _ in store.loadCheckIn(day: dayKey) }
    }
}
