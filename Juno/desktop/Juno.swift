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
    var updatedLabel: String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        guard let date = formatter.date(from: updated_at) else { return updated_at }
        return date.formatted(date: .abbreviated, time: .shortened)
    }
}
struct MemoryPage: Codable { let items: [Memory]; let has_more: Bool }
struct Handshake: Decodable { let url: String?; let token: String?; let error: String? }
struct APIProblem: Error { let message: String; let status: Int }

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
    @Published var section = "Chat"
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
    var process: Process?
    var endpoint: URL?
    var token = ""
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
        let state = packaged ? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Juno").path : root + "/.local"
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
                self.endpoint = url; self.token = token
                self.startupTask = Task {
                    for _ in 0..<40 {
                        do { try await self.load(); await self.loadCompanion(); return }
                        catch { try? await Task.sleep(nanoseconds: 250_000_000) }
                    }
                    self.problem = "The local service did not become ready. Quit and reopen Juno."; self.status = "Connection failed"
                }
            }
        }
    }

    func request(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        guard let endpoint else { throw APIProblem(message: "Juno is still connecting.", status: 0) }
        let url = URL(string: path, relativeTo: endpoint)!.absoluteURL
        var req = URLRequest(url: url); req.httpMethod = method; req.timeoutInterval = path.contains("/messages") && method == "POST" ? 100 : 15
        req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        req.cachePolicy = .reloadIgnoringLocalCacheData
        if let body { req.httpBody = try JSONSerialization.data(withJSONObject: body); req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw APIProblem(message: "Invalid response from Juno’s service.", status: 0) }
        guard (200..<300).contains(http.statusCode) else {
            let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            let message = object?["detail"] as? String ?? "The request could not be completed."
            throw APIProblem(message: message, status: http.statusCode)
        }
        return data
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
        hasMore = page.has_more; connected = true; status = "Connected · Local preview"; problem = nil
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
    func save(original: Memory?, text: String, source: String, confidence: String) async throws {
        var body: [String: Any] = ["text": text, "source": source, "confidence": confidence]
        if let original { body["expected_revision"] = original.revision }
        let data = try await request(original.map { "/v1/memories/" + $0.id } ?? "/v1/memories", method: original == nil ? "POST" : "PUT", body: body)
        let saved = try JSONDecoder().decode(Memory.self, from: data)
        query = ""; items.removeAll { $0.id == saved.id }; items.insert(saved, at: 0); selected = saved.id
        do { try await load() } catch { problem = "Your memory was saved, but the list could not refresh. Try Refresh." }
        messages.removeAll { $0.role == "assistant" }
        if let id = currentConversation { try? await loadMessages(id) }
    }
    func delete(_ row: Memory) async throws {
        _ = try await request("/v1/memories/\(row.id)?expected_revision=\(row.revision)", method: "DELETE")
        selected = nil; items.removeAll { $0.id == row.id }
        do { try await load() } catch { problem = "The memory was deleted, but the list could not refresh. Try Refresh." }
        messages.removeAll { $0.role == "assistant" }
        if let id = currentConversation { try? await loadMessages(id) }
    }
    func stop() { startupTask?.cancel(); process?.terminate() }
}

struct Editor: View {
    @Environment(\.dismiss) var dismiss
    @ObservedObject var store: JunoStore
    let original: Memory?
    @State var text: String
    @State var source: String
    @State var confidence: String
    @State private var saving = false
    @State private var issue: String?
    init(store: JunoStore, original: Memory?) {
        self.store = store; self.original = original
        _text = State(initialValue: original?.text ?? "")
        _source = State(initialValue: original?.source ?? "Manual entry")
        _confidence = State(initialValue: original?.confidence ?? "confirmed")
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(original == nil ? "Add a memory" : "Correct this memory").font(.title2.bold())
            Text("Use fictional information while Juno is in development.").foregroundStyle(.secondary)
            Text("What should Juno remember?").font(.headline)
            TextEditor(text: $text).font(.body).frame(height: 160).padding(6).overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                .accessibilityLabel("Memory text")
            TextField("Source", text: $source).textFieldStyle(.roundedBorder)
            Picker("How do we know?", selection: $confidence) {
                Text("Confirmed by you").tag("confirmed"); Text("Observed in a source").tag("observed"); Text("An assumption to verify").tag("inferred")
            }
            if let issue { Text(issue).foregroundStyle(.red).textSelection(.enabled) }
            HStack {
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction).disabled(saving)
                Spacer()
                Button(saving ? "Saving…" : "Save memory") {
                    saving = true
                    Task {
                        do { try await store.save(original: original, text: text, source: source, confidence: confidence); dismiss() }
                        catch { issue = (error as? APIProblem)?.message ?? "Could not save. Your draft is still here."; saving = false }
                    }
                }.keyboardShortcut(.defaultAction).disabled(saving || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || text.count > 10000 || source.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || source.count > 500)
            }
        }.padding(28).frame(width: 560).interactiveDismissDisabled(saving)
    }
}

struct MemoryWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var editing = false
    @State private var draft: Memory?
    @State private var deleting = false
    @State private var deleteTarget: Memory?
    @State private var removing = false
    var body: some View {
        VStack(spacing: 0) {
            HSplitView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("MEMORY").font(.caption.bold()).foregroundStyle(.secondary)
                    TextField("Search memories", text: $store.query).textFieldStyle(.roundedBorder).onSubmit { store.refresh() }.disabled(!store.connected)
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
                    Button { draft = nil; editing = true } label: { Label("Add memory", systemImage: "plus") }.disabled(!store.connected || store.busy)
                }.padding(16).frame(minWidth: 250, idealWidth: 300, maxWidth: 370)
                VStack(alignment: .leading, spacing: 20) {
                    if let row = store.selectedMemory {
                        Label(row.confidence == "confirmed" ? "Confirmed by you" : row.confidence == "observed" ? "Observed in a source" : "Assumption · needs verification", systemImage: row.confidence == "inferred" ? "questionmark.circle" : "checkmark.circle").font(.subheadline).foregroundStyle(.secondary)
                        ScrollView { Text(row.text).font(.title3).frame(maxWidth: .infinity, alignment: .leading).textSelection(.enabled) }
                        Divider()
                        Text("Source: \(row.source)").textSelection(.enabled)
                        Text("Updated \(row.updatedLabel) · Revision \(row.revision)").font(.caption).foregroundStyle(.secondary)
                        HStack {
                            Button("Correct memory") { draft = row; editing = true }
                            Button("Delete…", role: .destructive) { deleteTarget = row; deleting = true }
                        }.disabled(removing || !store.connected)
                    } else {
                        Spacer()
                        Image(systemName: "book.closed").font(.system(size: 42)).foregroundStyle(.purple)
                        Text(!store.query.isEmpty && store.items.isEmpty ? "No matching memories" : store.meeting ? "Your work memory" : "A little less to keep in your head.").font(.title2.bold())
                        Text(!store.query.isEmpty && store.items.isEmpty ? "Try another search, or clear the search to see all your memories." : store.items.isEmpty ? "Add a fictional memory to try Juno’s first working feature. You can review, correct, or delete it anytime." : "Choose a memory to see what Juno knows and where it came from.").foregroundStyle(.secondary).frame(maxWidth: 440, alignment: .leading)
                        Spacer()
                    }
                }.padding(32).frame(minWidth: 400, maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }.frame(minWidth: 850, minHeight: 570)
        .toolbar { Button { store.refresh() } label: { Label("Refresh", systemImage: "arrow.clockwise") }.disabled(store.busy || store.endpoint == nil) }
        .sheet(isPresented: $editing) { Editor(store: store, original: draft) }
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
final class AppDelegate: NSObject, NSApplicationDelegate {
    let store = JunoStore()
    var window: NSWindow?
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        let menu = NSMenu(); let appItem = NSMenuItem(); menu.addItem(appItem)
        let appMenu = NSMenu(); appItem.submenu = appMenu
        appMenu.addItem(withTitle: "About Juno", action: #selector(about), keyEquivalent: "").target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Juno", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit Juno", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let editItem = NSMenuItem(); menu.addItem(editItem); let edit = NSMenu(title: "Edit"); editItem.submenu = edit
        for (name, action, key) in [("Undo", "undo:", "z"), ("Cut", "cut:", "x"), ("Copy", "copy:", "c"), ("Paste", "paste:", "v"), ("Select All", "selectAll:", "a")] { edit.addItem(withTitle: name, action: Selector(action), keyEquivalent: key) }
        let windowItem = NSMenuItem(); menu.addItem(windowItem); let windows = NSMenu(title: "Window"); windowItem.submenu = windows; NSApp.windowsMenu = windows
        windows.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windows.addItem(withTitle: "Close Window", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        NSApp.mainMenu = menu
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1080, height: 720), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Juno"; window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: RootView(store: store)); self.window = window
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        store.start()
    }
    @objc func about() { NSApp.orderFrontStandardAboutPanel(options: [.applicationName: "Juno", .applicationVersion: "0.1.0-preview.2", .credits: NSAttributedString(string: "Native Mac work companion\nChat, check-ins and memory · synthetic data only\nLocal storage; cross-device synchronization is not connected")]) }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { window?.makeKeyAndOrderFront(nil); return true }
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
