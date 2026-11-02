import AppKit
import SwiftUI

struct Memory: Codable, Identifiable, Equatable {
    let id: String
    var text: String
    var source: String
    var confidence: String
    let revision: Int
    let created_at: String
    let updated_at: String
    var source_message_id: String? = nil
    var updatedLabel: String {
        let parser = ISO8601DateFormatter();parser.formatOptions = [.withInternetDateTime,.withFractionalSeconds]
        var date = parser.date(from:updated_at)
        if date == nil { parser.formatOptions = [.withInternetDateTime];date = parser.date(from:updated_at) }
        guard let date else { return "Unknown update time" }
        let f = DateFormatter();f.locale = Locale(identifier:"en_US_POSIX");f.timeZone = TimeZone(identifier:"America/Chicago");f.dateFormat = "MMM d, yyyy 'at' h:mm a";return f.string(from:date)
    }
}
struct MemoryPage: Codable { let items: [Memory]; let has_more: Bool }
struct Handshake: Decodable { let url: String?; let token: String?; let error: String? }
struct APIProblem: Error { let message: String; let status: Int; var retryAfter: Int? = nil }

// Security.framework can wait for macOS authorization; never run it on the UI thread.
func credentialWork<T>(_ operation: @escaping () throws -> T) async throws -> T {
    try await Task.detached(priority:.userInitiated) { try operation() }.value
}

@MainActor
final class JunoStore: ObservableObject {
    @Published var items: [Memory] = []
    @Published var selected: String?
    @Published var query = ""
    @Published var status = "Starting Juno…"
    @Published var problem: String?
    @Published var connected = false
    @Published var busy = false
    @Published var hasMore = false
    @Published var meeting = UserDefaults.standard.bool(forKey: "meetingMode") {
        didSet { UserDefaults.standard.set(meeting, forKey: "meetingMode") }
    }
    @Published var section = "Today"
    @Published var settingsSection = "Connections"
    @Published var unsavedSections:Set<String> = []
    func openSettings(_ section:String) {
        settingsSection = section
        NotificationCenter.default.post(name:Notification.Name("JunoSettings"),object:nil)
    }
    @Published var proposedChatDraft: String?
    func prepareChat(_ text: String) {
        if chatDraft.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty { chatDraft = text;section = "Chat" }
        else { proposedChatDraft = text }
    }
    @Published var planningTaskID: String?
    @Published var memoryReviewText: String?
    @Published var memoryReviewOriginal: String?
    @Published var memoryReviewMessageID: String?
    @Published var memoryNotice: String?
    @Published var conversations: [ConversationRecord] = []
    @Published var conversationMore = false
    @Published var currentConversation: String?
    @Published var messages: [ChatMessage] = []
    @Published var olderMessages = false
    @Published var chatDraft = ""
    @Published var chatSending = false
    @Published var chatIssue: String?
    @Published var modelBase = "http://127.0.0.1:1234/v1"
    @Published var modelName = ""
    @Published var modelOptions: [String] = []
    @Published var modelConfigured = false
    @Published var modelBusy = false
    @Published var modelNotice: String?
    @Published var checkIn: CheckInRecord?
    @Published var checkAnswer = ""
    @Published var diaryDraft = ""
    @Published var checkBusy = false
    @Published var checkIssue: String?
    var checkDay = ""
    @Published var sharedProfile: SharedProfile?
    @Published var offline = false
    @Published var offlineDate: Date?
    @Published var pendingEdits: [OfflineEdit] = []
    @Published var syncing = false
    @Published var syncIssue: String?
    var offlineCopy: OfflineCopy?
    var hostSession: URLSession?
    var localEndpoint: URL?
    var localToken = ""
    var process: Process?
    var endpoint: URL?
    var token = ""
    var connectionTask: Task<Void,Never>?
    var startupTask: Task<Void, Never>?
    var selectedMemory: Memory? { items.first { $0.id == selected } }

    func start() {
        guard process == nil else { return }
        let packaged = Bundle.main.object(forInfoDictionaryKey: "JunoPackaged") as? Bool ?? false
        let resources = Bundle.main.resourceURL!.path
        guard let root = packaged ? resources + "/app" : Bundle.main.object(forInfoDictionaryKey: "JunoProjectRoot") as? String else {
            problem = "The app is missing its service files."; return
        }
        let python = packaged ? resources + "/runtime/python/bin/python3" : root + "/.venv/bin/python"
        let state = !packaged && Bundle.main.object(forInfoDictionaryKey:"JunoTestDataRoot") is String ? Bundle.main.object(forInfoDictionaryKey:"JunoTestDataRoot") as! String : packaged ? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Juno").path : root + "/.local"
        guard FileManager.default.isExecutableFile(atPath: python) else {
            problem = "The local Juno environment is missing. Rebuild the development app after setting up its backend."; return
        }
        let proc = Process(); let pipe = Pipe()
        proc.executableURL = URL(fileURLWithPath: python)
        proc.arguments = [root + "/scripts/desktop_service.py"]
        proc.currentDirectoryURL = URL(fileURLWithPath: root)
        var environment = ProcessInfo.processInfo.environment
        for key in Array(environment.keys) where key.hasPrefix("PYTHON") || key.hasPrefix("JUNO_") || key.hasPrefix("DYLD_") || key.hasPrefix("PG") { environment.removeValue(forKey: key) }
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        environment["JUNO_DATA_ROOT"] = state
        if packaged { environment["JUNO_POSTGRES_BIN"] = resources + "/runtime/postgres/bin" }
        proc.environment = environment
        proc.standardOutput = pipe
        let log = state + "/desktop.log"
        try? FileManager.default.createDirectory(atPath: state, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        if !FileManager.default.fileExists(atPath: log) { FileManager.default.createFile(atPath: log, contents: nil, attributes: [.posixPermissions: 0o600]) }
        proc.standardError = try? FileHandle(forWritingTo: URL(fileURLWithPath: log))
        proc.terminationHandler = { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                self.connected = false; self.status = "Disconnected"
                self.problem = "Juno’s local service stopped. Quit and reopen Juno to reconnect. Your saved memories remain in the database."
            }
        }
        do { try proc.run(); process = proc } catch { problem = "Could not launch Juno’s local service."; return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            var bytes = Data()
            while !bytes.contains(10) {
                let chunk = pipe.fileHandleForReading.availableData
                if chunk.isEmpty { break }
                bytes.append(chunk)
                if bytes.count > 16384 { break }
            }
            let first = bytes.split(separator: 10).first.map(Data.init) ?? Data()
            let hello = try? JSONDecoder().decode(Handshake.self, from: first)
            Task { @MainActor in
                guard let self else { return }
                guard let hello, let address = hello.url, let url = URL(string: address), let token = hello.token else {
                    self.problem = hello?.error ?? "Juno could not connect to her local service."; self.status = "Connection failed"; return
                }
                self.localEndpoint = url; self.localToken = token
                self.endpoint = url; self.token = token
                do { try await self.restoreShared() } catch { self.problem = (error as? APIProblem)?.message ?? "Shared connection could not be restored." }
                self.startupTask = Task {
                    for _ in 0..<40 {
                        do { try await self.load(); await self.loadCompanion(); self.startSharedMonitor(); return }
                        catch {
                            if self.sharedProfile != nil, ((error as? APIProblem)?.status == 401 || self.offlineCopy?.archive.pages.isEmpty == true) {
                                self.status = "Connect work Mac"; self.problem = (error as? APIProblem)?.message ?? "Connect to the work Mac or import a fresh pairing invitation in Computers. Queued edits are retained."; self.startSharedMonitor(); return
                            }
                            try? await Task.sleep(nanoseconds: 250_000_000)
                        }
                    }
                    self.problem = "The local service did not become ready. Quit and reopen Juno."; self.status = "Connection failed"
                }
            }
        }
    }

    func request(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        guard let endpoint else { throw APIProblem(message: "Juno is still connecting.", status: 0) }
        if sharedProfile == nil {
            return try await wire(path,endpoint:endpoint,token:token,session:URLSession.shared,method:method,body:body)
        }
        guard let copy = offlineCopy, let hostSession else {
            throw APIProblem(message:"The shared laptop copy or encrypted session is unavailable. Open Computers to reconnect; Juno will not use an unpaired connection.",status:0)
        }
        if method != "GET" {
            let components = URLComponents(string:path)!
            let capable = components.path.hasPrefix("/v1/memories") || components.path.hasPrefix("/v1/check-ins")
            if capable {
                var payload = body ?? [:]
                if method == "DELETE", let revision = components.queryItems?.first(where:{$0.name == "expected_revision"})?.value { payload["expected_revision"] = Int(revision) }
                let result = try copy.perform(components.path,method:method,body:payload)
                pendingEdits = copy.archive.pending
                if offline || syncing { syncIssue = "Saved on this laptop; queued for synchronization with the work Mac."; return result }
                syncing = true
                defer { syncing = false }
                do {
                    try await syncOfflineCopy(); syncIssue = nil
                    if let row = try JSONSerialization.jsonObject(with:result) as? [String:Any] {
                        if let day = row["local_date"] as? String { return try copy.read("/v1/check-ins/by-date/"+day) }
                        if let oldID = row["id"] as? String, row["text"] != nil {
                            let identity = copy.resolved[oldID] ?? oldID
                            if let fresh = copy.objects("/v1/memories").first(where:{$0["id"] as? String == identity}) { return try JSONSerialization.data(withJSONObject:fresh) }
                        }
                    }
                } catch {
                    if let issue = error as? APIProblem, issue.status == 401 { sharedRevoked() }
                    offline = (error as? APIProblem)?.status == nil || (error as? APIProblem)?.status == 0 || (error as? APIProblem)?.status == 401; status = sharedLabel
                    syncIssue = (error as? APIProblem)?.message ?? "Saved on this laptop. Changes will sync when the work Mac is reachable."
                }
                return result
            }
            guard !offline && copy.archive.pending.isEmpty else { throw APIProblem(message:"Reconnect and synchronize your saved edits before this action. Your draft is still here.",status:0) }
        }
        if method == "GET" && offline { return try copy.read(path) }
        if method == "GET" && !copy.archive.pending.isEmpty { return try copy.read(path) }
        do {
            let data = try await wire(path,endpoint:endpoint,token:token,session:hostSession,method:method,body:body)
            offline = false; status = sharedLabel
            if method == "GET" { copy.archive.pages[OfflineCopy.key(path)] = data; try copy.save() }
            return data
        } catch let issue as APIProblem {
            if issue.status == 401 { sharedRevoked(); throw APIProblem(message:"This laptop's access was revoked or expired. Its queued edits are retained. Pair again to reconnect.",status:401) }
            throw issue
        } catch {
            offline = true; status = sharedLabel
            if method == "GET" { return try copy.read(path) }
            throw APIProblem(message:"The work Mac is unavailable. Your draft is still here.",status:0)
        }
    }
    func load(more: Bool = false) async throws {
        let requestedQuery = query
        let offset = more ? items.count : 0
        var parts = URLComponents(); parts.path = "/v1/memories"
        parts.queryItems = [URLQueryItem(name: "q", value: requestedQuery), URLQueryItem(name: "offset", value: String(offset))]
        let data = try await request(parts.string!)
        let page = try JSONDecoder().decode(MemoryPage.self, from: data)
        guard query == requestedQuery else { return }
        if more { items.append(contentsOf: page.items.filter { row in !items.contains { $0.id == row.id } }) }
        else { items = page.items }
        hasMore = page.has_more; connected = true; status = sharedLabel; problem = nil
        if let selected, !items.contains(where: { $0.id == selected }) { self.selected = nil }
    }
    func refresh(more: Bool = false) {
        guard !busy else { return }; busy = true
        Task {
            defer { busy = false }
            do { try await load(more: more) } catch { report(error) }
        }
    }
    func report(_ error: Error) {
        if let api = error as? APIProblem { problem = api.message }
        else { problem = "Could not reach Juno’s service. Try refreshing. Unsaved edits have been kept."; connected = false; status = "Disconnected" }
    }
    @discardableResult
    func save(original: Memory?, text: String, source: String, confidence: String, sourceMessageID: String? = nil) async throws -> Memory {
        var body: [String: Any] = ["text": text, "source": source, "confidence": confidence]
        if let original { body["expected_revision"] = original.revision }
        if let sourceMessageID { body["source_message_id"] = sourceMessageID }
        let data = try await request(original.map { "/v1/memories/" + $0.id } ?? "/v1/memories", method: original == nil ? "POST" : "PUT", body: body)
        let saved = try JSONDecoder().decode(Memory.self, from: data)
        query = ""; items.removeAll { $0.id == saved.id }; items.insert(saved, at: 0); selected = saved.id
        do { try await load() } catch { problem = "Your memory was saved, but the list could not refresh. Use Search to refresh the list." }
        messages.removeAll { $0.role == "assistant" }
        if let id = currentConversation { try? await loadMessages(id) }
        return saved
    }
    func delete(_ row: Memory) async throws {
        _ = try await request("/v1/memories/\(row.id)?expected_revision=\(row.revision)", method: "DELETE")
        selected = nil; items.removeAll { $0.id == row.id }
        do { try await load() } catch { problem = "The memory was deleted, but the list could not refresh. Use Search to refresh the list." }
        messages.removeAll { $0.role == "assistant" }
        if let id = currentConversation { try? await loadMessages(id) }
    }
    func stop() { connectionTask?.cancel(); startupTask?.cancel(); process?.terminate() }
}

struct Editor: View {
    @Environment(\.dismiss) var dismiss
    @ObservedObject var store: JunoStore
    let original: Memory?
    var onSaved: ((Memory) -> Void)?
    let sourceMessageID: String?
    @State var text: String
    @State var source: String
    @State var confidence: String
    @State private var saving = false
    @State private var issue: String?
    @State private var base:Memory?
    @State private var conflict = false
    @State private var comparison:Memory?
    init(store: JunoStore, original: Memory?, initialText: String = "", sourceMessageID: String? = nil, onSaved: ((Memory) -> Void)? = nil) {
        self.store = store; self.original = original;self.onSaved = onSaved;self.sourceMessageID = sourceMessageID
        _base = State(initialValue:original)
        _text = State(initialValue: original?.text ?? initialText)
        _source = State(initialValue: original?.source ?? "Manual entry")
        _confidence = State(initialValue: original?.confidence ?? "confirmed")
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(original == nil ? "Add a memory" : "Correct this memory").font(.title2.bold())
            Text("Save work context you want Juno to remember. You can correct or delete it later.").foregroundStyle(.secondary)
            Text("What should Juno remember?").font(.headline)
            TextEditor(text: $text).font(.body).frame(height: 160).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                .accessibilityLabel("Memory text")
            TextField("Source", text: $source).textFieldStyle(.roundedBorder)
            Picker("How do we know?", selection: $confidence) {
                Text("Confirmed by you").tag("confirmed"); Text("Observed in a source").tag("observed"); Text("An assumption to verify").tag("inferred")
            }
            if let issue { Text(issue).foregroundStyle(.red).textSelection(.enabled) }
            if conflict {
                Button("Load latest saved version") {
                    guard let base else { return };saving = true
                    Task { defer { saving = false };do { comparison = try await store.decode(Memory.self,"/v1/memories/"+base.id) } catch { issue = (error as? APIProblem)?.message ?? "The saved version could not be loaded. Your draft remains here." } }
                }.disabled(saving)
            }
            if let latest = comparison {
                GroupBox("Latest saved version · revision \(latest.revision)") {
                    VStack(alignment:.leading,spacing:6) {
                        ScrollView { Text(latest.text).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading) }.frame(height:65)
                        Text("Source: " + latest.source + " • " + latest.confidence).font(.caption).lineLimit(1).help(latest.source)
                        HStack {
                            Button("Use latest values") { text = latest.text;source = latest.source;confidence = latest.confidence;base = latest;comparison = nil;conflict = false;issue = nil }
                            Button("Keep my draft for review") { base = latest;comparison = nil;conflict = false;issue = "Review your draft, then Save memory. Nothing has been overwritten." }
                        }.font(.caption)
                    }
                }
            }
            HStack {
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction).disabled(saving)
                Spacer()
                Button(saving ? "Saving…" : "Save memory") {
                    saving = true
                    Task {
                        do { let saved = try await store.save(original: base, text: text, source: source, confidence: confidence,sourceMessageID:sourceMessageID);onSaved?(saved); dismiss() }
                        catch { issue = (error as? APIProblem)?.message ?? "Could not save. Your draft is still here."; saving = false;conflict = (error as? APIProblem)?.status == 409 && base != nil && !store.offline }
                    }
                }.keyboardShortcut(.defaultAction).disabled(saving || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || text.count > 10000 || source.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || source.count > 500)
            }
        }.padding(28).frame(width: 600).interactiveDismissDisabled(saving)
        .onAppear { store.unsavedSections.insert("memory review") }
        .onDisappear { store.unsavedSections.remove("memory review") }
    }
}

struct MemoryEditRequest: Identifiable { let id = UUID(); let original:Memory? }

struct MemoryWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var editRequest:MemoryEditRequest?
    @FocusState private var searchFocused:Bool
    @State private var deleting = false
    @State private var deleteTarget: Memory?
    @State private var removing = false
    var body: some View {
        VStack(spacing: 0) {
            HSplitView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("MEMORY").font(.caption.bold()).foregroundStyle(.secondary)
                    TextField("Search memories", text: $store.query).focused($searchFocused).onReceive(NotificationCenter.default.publisher(for:Notification.Name("JunoFind"))) { _ in if store.section == "Memories" { searchFocused = true } }.textFieldStyle(.roundedBorder).onSubmit { store.refresh() }.disabled(!store.connected)
                    HStack { Button("Search") { store.refresh() }; Button("Clear") { store.query = ""; store.refresh() } }.disabled(!store.connected || store.busy)
                    List(selection: $store.selected) {
                        ForEach(store.items) { row in
                            VStack(alignment: .leading, spacing: 5) {
                                Text(row.text).lineLimit(2)
                                Text(row.source).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                            }.padding(.vertical, 6).tag(row.id)
                        }
                    }.listStyle(.sidebar)
                    if store.hasMore { Button("Load more") { store.refresh(more: true) }.disabled(store.busy) }
                    Button { editRequest = MemoryEditRequest(original:nil) } label: { Label("Add memory", systemImage: "plus") }.disabled(!store.connected || store.busy)
                }.padding(16).frame(minWidth: 250, idealWidth: 300, maxWidth: 370)
                VStack(alignment: .leading, spacing: 20) {
                    if let row = store.selectedMemory {
                        Label(row.confidence == "confirmed" ? "Confirmed by you" : row.confidence == "observed" ? "Observed in a source" : "Assumption · needs verification", systemImage: row.confidence == "inferred" ? "questionmark.circle" : "checkmark.circle").font(.subheadline).foregroundStyle(.secondary)
                        ScrollView { Text(row.text).font(.title3).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled) }
                        Divider()
                        Text("Source: \(row.source)").textSelection(.enabled)
                        Text("Updated \(row.updatedLabel) · Revision \(row.revision)").font(.caption).foregroundStyle(.secondary)
                        HStack {
                            Button("Correct memory") { editRequest = MemoryEditRequest(original:row) }
                            Button("Delete…", role: .destructive) { deleteTarget = row; deleting = true }
                        }.disabled(removing || !store.connected)
                    } else {
                        Spacer()
                        Image(systemName: "book.closed").font(.system(size: 42)).foregroundStyle(.purple)
                        Text(!store.query.isEmpty && store.items.isEmpty ? "No matching memories" : store.meeting ? "Your work memory" : "A little less to keep in your head.").font(.title2.bold())
                        Text(!store.query.isEmpty && store.items.isEmpty ? "Try another search, or clear the search to see all your memories." : store.items.isEmpty ? "Save something you want Juno to remember. You can review, correct or delete it anytime." : "Choose a memory to see what Juno knows and where it came from.").foregroundStyle(.secondary).frame(maxWidth: 440, alignment: .leading)
                        Spacer()
                    }
                }.padding(32).frame(minWidth: 400, maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }.frame(minWidth: 850, minHeight: 570)
        .sheet(item:$editRequest) { request in Editor(store:store,original:request.original).id(request.id) }
        .alert("Delete this memory?", isPresented: $deleting) {
            Button("Cancel", role: .cancel) { deleteTarget = nil }
            Button("Delete memory", role: .destructive) {
                guard let target = deleteTarget else { return }; removing = true
                Task { defer { removing = false; deleteTarget = nil }; do { try await store.delete(target) } catch { store.report(error) } }
            }
        } message: { Text("Juno will remove this memory and block identical source content from silently recreating it. This does not delete information in other applications or old backups.") }
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuItemValidation {
    let store = JunoStore()
    var window: NSWindow?
    var settingsWindow: NSWindow?
    var helpWindow: NSWindow?
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        let menu = NSMenu(); let appItem = NSMenuItem(); menu.addItem(appItem)
        let appMenu = NSMenu(); appItem.submenu = appMenu
        appMenu.addItem(withTitle: "About Juno", action: #selector(about), keyEquivalent: "").target = self
        appMenu.addItem(withTitle:"Settings…",action:#selector(showSettings),keyEquivalent:",").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Juno", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Juno", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(); menu.addItem(editItem); let edit = NSMenu(title: "Edit"); editItem.submenu = edit
        for (name, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] { edit.addItem(withTitle: name, action: Selector(action), keyEquivalent: key) }
        let find = edit.addItem(withTitle:"Find…",action:#selector(findInWorkspace),keyEquivalent:"f");find.target = self
        let redo = edit.addItem(withTitle:"Redo",action:Selector(("redo:")),keyEquivalent:"z");redo.keyEquivalentModifierMask = [.command,.shift]
        let viewItem = NSMenuItem();menu.addItem(viewItem);let view = NSMenu(title:"View");viewItem.submenu = view
        for (index,title) in ["Today","Chat","Plan","Schedules","Check-in","Memories","TaskDock","Evidence"].enumerated() {
            let item = view.addItem(withTitle:title == "Check-in" ? "Daily check-in" : title,action:#selector(navigate(_:)),keyEquivalent:String(index+1));item.representedObject = title;item.target = self
        }
        let windowItem = NSMenuItem(); menu.addItem(windowItem); let windows = NSMenu(title: "Window"); windowItem.submenu = windows; NSApp.windowsMenu = windows
        windows.addItem(withTitle: "Minimize", action: #selector(minimizeCurrent(_:)), keyEquivalent: "m").target = self
        windows.addItem(withTitle: "Close Window", action: #selector(closeCurrent(_:)), keyEquivalent: "w").target = self
        windows.addItem(withTitle:"Bring All to Front",action:#selector(NSApplication.arrangeInFront(_:)),keyEquivalent:"").target = NSApp
        let helpItem = NSMenuItem();menu.addItem(helpItem);let help = NSMenu(title:"Help");helpItem.submenu = help;NSApp.helpMenu = help
        help.addItem(withTitle:"Juno Help",action:#selector(showHelp),keyEquivalent:"?").target = self
        NotificationCenter.default.addObserver(self,selector:#selector(showSettings),name:Notification.Name("JunoSettings"),object:nil)
        NSApp.mainMenu = menu
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1080, height: 720), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = Bundle.main.object(forInfoDictionaryKey:"JunoTestDataRoot") == nil ? "Juno" : "Juno — Interaction Lab"; window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: RootView(store: store)); self.window = window
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        store.start()
    }
    private var activeWindow:NSWindow? { NSApp.keyWindow ?? NSApp.mainWindow ?? window }
    func validateMenuItem(_ item:NSMenuItem) -> Bool {
        if item.action == #selector(findInWorkspace) { return ["Plan","Memories","TaskDock"].contains(store.section) && (NSApp.keyWindow == nil || NSApp.keyWindow === window) }
        if item.action == #selector(minimizeCurrent(_:)) { return activeWindow?.isVisible == true && activeWindow?.isMiniaturized == false }
        if item.action == #selector(closeCurrent(_:)) { return activeWindow?.isVisible == true }
        return true
    }
    @objc func minimizeCurrent(_ sender:Any?) { activeWindow?.miniaturize(sender) }
    @objc func closeCurrent(_ sender:Any?) { activeWindow?.performClose(sender) }
    @objc func navigate(_ item:NSMenuItem) { NSApp.unhide(nil);NSApp.activate(ignoringOtherApps:true); if let key = item.representedObject as? String { store.section = key };window?.deminiaturize(nil);window?.makeKeyAndOrderFront(nil) }
    @objc func showSettings() {
        if settingsWindow == nil {
            let panel = NSWindow(contentRect:NSRect(x:0,y:0,width:860,height:650),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
            panel.title = "Juno Settings";panel.isReleasedWhenClosed = false
            panel.contentView = NSHostingView(rootView:JunoSettingsView(store:store));panel.center();settingsWindow = panel
        }
        settingsWindow?.makeKeyAndOrderFront(nil)
    }
    @objc func showHelp() {
        if helpWindow == nil {
            let panel = NSWindow(contentRect:NSRect(x:0,y:0,width:640,height:540),styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false)
            panel.title = "Juno Help";panel.isReleasedWhenClosed = false;panel.contentView = NSHostingView(rootView:JunoHelpView());panel.center();helpWindow = panel
        }
        helpWindow?.makeKeyAndOrderFront(nil)
    }
    @objc func findInWorkspace() { window?.makeKeyAndOrderFront(nil);NotificationCenter.default.post(name:Notification.Name("JunoFind"),object:nil) }
    @objc func about() { NSApp.orderFrontStandardAboutPanel(options: [.applicationName: "Juno", .applicationVersion: Bundle.main.object(forInfoDictionaryKey: "JunoReleaseVersion") as? String ?? "Development", .credits: NSAttributedString(string: "Native Mac work companion\nChat, check-ins and memory · local shared host\nEncrypted work-Mac connection with offline memory and diary edits")]) }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { window?.makeKeyAndOrderFront(nil); return true }
    func applicationShouldTerminate(_ sender:NSApplication) -> NSApplication.TerminateReply {
        guard !store.unsavedSections.isEmpty else { return .terminateNow }
        let alert = NSAlert();alert.messageText = "You have unsaved changes"
        alert.informativeText = "Return to " + store.unsavedSections.sorted().joined(separator:" and ") + " to save your draft, or quit and discard those draft changes. Your saved records are kept."
        alert.addButton(withTitle:"Return to Juno");alert.addButton(withTitle:"Quit without saving")
        return alert.runModal() == .alertFirstButtonReturn ? .terminateCancel : .terminateNow
    }
    func applicationWillTerminate(_ notification: Notification) { store.stop() }
}

@main
struct JunoApplication {
    @MainActor static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        withExtendedLifetime(delegate) { app.run() }
    }
}
