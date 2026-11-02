import SwiftUI
import AppKit
import Security

func providerDate(_ value:String) -> Date? {
    let formatter = ISO8601DateFormatter();formatter.formatOptions = [.withInternetDateTime,.withFractionalSeconds]
    return formatter.date(from:value) ?? ISO8601DateFormatter().date(from:value)
}
enum WorkProvider: String, CaseIterable, Identifiable, Codable {
    case gmail, google_calendar, google_tasks, google_chat, slack, smartsheet, outlook_calendar
    var id:String { rawValue }
    var label:String { ["gmail":"Gmail","google_calendar":"Google Calendar","google_tasks":"Google Tasks","google_chat":"Google Chat","slack":"Slack","smartsheet":"Smartsheet","outlook_calendar":"Outlook Calendar"][rawValue]! }
    var oauth:Bool { self != .slack && self != .smartsheet }
    var google:Bool { [.gmail,.google_calendar,.google_tasks,.google_chat].contains(self) }
    var timed:Bool { [.google_calendar,.google_chat,.slack,.outlook_calendar].contains(self) }
    var help:String {
        switch self {
        case .gmail:return "Read matching email without marking it read, changing labels or sending anything. The default query is your unread inbox. Attachments and remote images are omitted."
        case .google_calendar:return "Read selected calendars in an explicit date window. Recurrences and exceptions come from Google. No event or attendee changes."
        case .google_tasks:return "Read selected lists, including provider-visible completed/hidden/assigned tasks. TaskDock remains your consolidated task hub."
        case .google_chat:return "Read messages created within the chosen window in selected spaces. No messages are sent. Workplace API approval may be required."
        case .slack:return "Use an approved user/bot token with history access for selected conversations. Reading threads in public/private channels may require a user token. Juno never joins channels or sends messages."
        case .smartsheet:return "Use an approved API token and select sheets. Juno reads row/cell excerpts and checks sheet versions. It never changes rows, statuses or checkboxes. A token may have broader provider permissions than Juno uses."
        case .outlook_calendar:return "Use a registered Microsoft public desktop client. Juno requests User.Read, Calendars.Read and offline_access. It reads selected calendarView intervals and never changes events."
        }
    }
}
struct SavedConnection: Codable {
    var clientID = "";var clientSecret = "";var tenant = "organizations"
    var accessToken = "";var refreshToken = "";var expiry:Date?;var scope = ""
    var resources:[String] = [];var resourceLabels:[String:String] = [:]
    var accountID = "";var accountLabel = ""
    var query = "in:inbox is:unread";var start = integrationDay(-30);var end = integrationDay(30);var zone = "America/Chicago"
    var includeThreads = true;var retryAt:Date?
    init() {}
    enum CodingKeys:String,CodingKey { case clientID,clientSecret,tenant,accessToken,refreshToken,expiry,scope,resources,resourceLabels,accountID,accountLabel,query,start,end,zone,includeThreads,retryAt }
    init(from decoder:Decoder) throws {
        self.init();let c = try decoder.container(keyedBy:CodingKeys.self)
        clientID = try c.decodeIfPresent(String.self,forKey:.clientID) ?? clientID;clientSecret = try c.decodeIfPresent(String.self,forKey:.clientSecret) ?? clientSecret;tenant = try c.decodeIfPresent(String.self,forKey:.tenant) ?? tenant
        accessToken = try c.decodeIfPresent(String.self,forKey:.accessToken) ?? accessToken;refreshToken = try c.decodeIfPresent(String.self,forKey:.refreshToken) ?? refreshToken;expiry = try c.decodeIfPresent(Date.self,forKey:.expiry);scope = try c.decodeIfPresent(String.self,forKey:.scope) ?? scope
        resources = try c.decodeIfPresent([String].self,forKey:.resources) ?? resources;resourceLabels = try c.decodeIfPresent([String:String].self,forKey:.resourceLabels) ?? resourceLabels
        accountID = try c.decodeIfPresent(String.self,forKey:.accountID) ?? accountID;accountLabel = try c.decodeIfPresent(String.self,forKey:.accountLabel) ?? accountLabel
        query = try c.decodeIfPresent(String.self,forKey:.query) ?? query;start = try c.decodeIfPresent(String.self,forKey:.start) ?? start;end = try c.decodeIfPresent(String.self,forKey:.end) ?? end;zone = try c.decodeIfPresent(String.self,forKey:.zone) ?? zone
        includeThreads = try c.decodeIfPresent(Bool.self,forKey:.includeThreads) ?? includeThreads;retryAt = try c.decodeIfPresent(Date.self,forKey:.retryAt)
    }
}
struct ProviderVault {
    let service:String
    init(service:String = (Bundle.main.bundleIdentifier ?? "com.dmccoy.juno") + ".providers") { self.service = service }
    func query(_ provider:WorkProvider) -> [String:Any] { [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:provider.rawValue] }
    func read(_ provider:WorkProvider) throws -> SavedConnection? {
        var q = query(provider);q[kSecReturnData as String] = true;q[kSecMatchLimit as String] = kSecMatchLimitOne
        var value:CFTypeRef?;let code = SecItemCopyMatching(q as CFDictionary,&value)
        if code == errSecItemNotFound { return nil }
        guard code == errSecSuccess,let data = value as? Data else { throw APIProblem(message:"The connection could not be read from Keychain.",status:0) }
        do { return try JSONDecoder().decode(SavedConnection.self,from:data) }
        catch { throw APIProblem(message:"The saved connection format could not be read. Its Keychain item was retained.",status:0) }
    }
    func save(_ value:SavedConnection,provider:WorkProvider) throws {
        let data = try JSONEncoder().encode(value);let q = query(provider)
        var code = SecItemUpdate(q as CFDictionary,[kSecValueData as String:data] as CFDictionary)
        if code == errSecItemNotFound {
            var item = q;item[kSecValueData as String] = data;item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly;item[kSecAttrSynchronizable as String] = false
            code = SecItemAdd(item as CFDictionary,nil)
        }
        guard code == errSecSuccess else { throw APIProblem(message:"The connection could not be saved in Keychain. Your previous saved item was retained.",status:0) }
    }
    func forget(_ provider:WorkProvider) throws {
        let code = SecItemDelete(query(provider) as CFDictionary)
        guard code == errSecSuccess || code == errSecItemNotFound else { throw APIProblem(message:"The saved provider credential could not be removed.",status:0) }
    }
}
struct ProviderAccount: Codable { let id:String;let label:String }
struct ProviderResource: Codable, Identifiable { let id:String;let label:String }
struct ProviderDiscovery: Decodable { let provider:String;let account:ProviderAccount;let resources:[ProviderResource];let manual_selection_required:Bool;let notice:String }
struct ConnectionSnapshot: Decodable,Identifiable { let id:String;let kind:String;let count:Int;let fetched_at:String;let error:String?;let details:EvidenceDetails }
struct ConnectionSnapshots: Decodable { let items:[ConnectionSnapshot] }
struct ProviderRefreshReply: Decodable { let review_required:Bool;let account:ProviderAccount? }
struct OAuthStartReply: Decodable { let flow_id:String;let authorization_url:String;let redirect_uri:String;let scopes:[String];let expires_in:Int }
struct OAuthTokens: Decodable { let access_token:String;let refresh_token:String?;let expires_at:String;let scope:String }
struct OAuthPollReply: Decodable { let phase:String;let provider:String;let tokens:OAuthTokens?;let error:String? }
func validatedAuthorization(_ value:String,provider:WorkProvider,flow:String,client:String) throws -> URL {
    guard let parts = URLComponents(string:value),parts.scheme == "https",parts.user == nil,parts.password == nil,parts.fragment == nil,parts.port == nil || parts.port == 443,
          let url = parts.url else { throw APIProblem(message:"The provider sign-in address is invalid.",status:0) }
    let query = parts.queryItems ?? []
    func one(_ key:String) -> String? { let values = query.filter { $0.name == key };return values.count == 1 ? values[0].value : nil }
    guard one("state") == flow,one("client_id") == client,one("response_type") == "code",one("code_challenge_method") == "S256" else { throw APIProblem(message:"The sign-in response does not match this Juno session.",status:0) }
    let google = parts.host == "accounts.google.com" && parts.path == "/o/oauth2/v2/auth"
    let microsoft = parts.host == "login.microsoftonline.com" && parts.path.range(of:"^/[A-Za-z0-9.-]+/oauth2/v2\\.0/authorize$",options:.regularExpression) != nil
    guard provider.google ? google : provider == .outlook_calendar && microsoft else { throw APIProblem(message:"Juno refused an unexpected sign-in destination.",status:0) }
    guard let redirectText = one("redirect_uri"),let redirect = URLComponents(string:redirectText),
          redirect.scheme == "http",redirect.user == nil,redirect.password == nil,redirect.query == nil,redirect.fragment == nil,
          let port = redirect.port,port > 0,port <= 65535,
          redirect.host == (provider.google ? "127.0.0.1" : "localhost"),
          redirect.path == "/v1/providers/oauth/callback/" + (provider.google ? "google" : "microsoft"),
          let challenge = one("code_challenge"),challenge.range(of:"^[A-Za-z0-9_-]{43}$",options:.regularExpression) != nil else { throw APIProblem(message:"The sign-in callback or PKCE challenge is invalid.",status:0) }
    return url
}

struct ConnectionsWorkspace: View {
    @ObservedObject var store:JunoStore
    @State private var route = "taskdock"
    @State private var provider:WorkProvider = .gmail
    var body:some View {
        if store.sharedProfile != nil {
            VStack(alignment:.leading,spacing:16) { Text("Connections live on your work Mac").font(.title2.bold());Text("Use Evidence on this laptop to read saved copies. Configure or authorize programs in Juno on the approved work Mac; credentials are never synchronized to laptops.").foregroundStyle(.secondary) }.padding(30)
        } else {
            VStack(spacing:0) {
                Picker("Connection route",selection:$route) { Text("Through TaskDock").tag("taskdock");Text("Direct programs").tag("direct") }.pickerStyle(.segmented).padding(20)
                if route == "taskdock" { TaskDockBridgeWorkspace(store:store,onDirect:{ selected in provider = selected;route = "direct" }) }
                else { DirectProviderWorkspace(store:store,provider:$provider) }
            }
        }
    }
}

extension ProviderVault {
    func readAsync(_ provider:WorkProvider) async throws -> SavedConnection? { try await credentialWork { try self.read(provider) } }
    func saveAsync(_ value:SavedConnection,provider:WorkProvider) async throws { try await credentialWork { try self.save(value,provider:provider) } }
    func forgetAsync(_ provider:WorkProvider) async throws { try await credentialWork { try self.forget(provider) } }
}

struct DirectProviderWorkspace: View {
    @ObservedObject var store:JunoStore
    @Binding var provider:WorkProvider
    @State private var saved = SavedConnection()
    @State private var tokenField = ""
    @State private var secretField = ""
    @State private var resources:[ProviderResource] = []
    @State private var resourceFilter = ""
    @State private var manualIDs = ""
    @State private var reviewed = false
    @State private var snapshots:[ConnectionSnapshot] = []
    @State private var busy = false
    @State private var notice:String?
    @State private var flowID:String?
    @State private var authTask:Task<Void,Never>?
    @State private var operationTask:Task<Void,Never>?
    @State private var cooldownTask:Task<Void,Never>?
    @State private var forget = false
    private let vault = ProviderVault()
    var current:ConnectionSnapshot? { snapshots.first { $0.kind == provider.rawValue } }
    var waiting:Bool { flowID != nil }
    var cooldown:Bool { (saved.retryAt ?? .distantPast) > Date() }
    func scheduleCooldown() {
        cooldownTask?.cancel()
        guard let retry = saved.retryAt else { return }
        let expectedProvider = provider
        cooldownTask = Task {
            do {
                try await Task.sleep(nanoseconds:UInt64(max(0,retry.timeIntervalSinceNow) * 1_000_000_000))
                try Task.checkCancellation()
                guard provider == expectedProvider,saved.retryAt == retry else { return }
                saved.retryAt = nil;try? await vault.saveAsync(saved,provider:provider)
            } catch {}
        }
    }
    func loadSaved() async {
        let expected = provider
        busy = true;defer { busy = false }
        // Never show or reuse another provider's fields if its Keychain read fails.
        saved = SavedConnection();tokenField = "";secretField = "";resources = [];manualIDs = "";reviewed = false
        do { let loaded = try await vault.readAsync(expected) ?? SavedConnection();guard provider == expected else { return };saved = loaded;tokenField = "";secretField = "";resources = [];manualIDs = "";reviewed = false;notice = nil }
        catch { notice = (error as? APIProblem)?.message ?? "Saved connection unavailable." }
    }
    func loadState() async {
        do { snapshots = try JSONDecoder().decode(ConnectionSnapshots.self,from:await store.localRequest("/v1/providers/state")).items }
        catch { notice = (error as? APIProblem)?.message ?? "Saved connection status is unavailable." }
    }
    func saveForm() async throws {
        if !tokenField.isEmpty { saved.accessToken = tokenField; saved.accountID = "";saved.accountLabel = "";saved.resources = [];reviewed = false }
        if !secretField.isEmpty { saved.clientSecret = secretField }
        if let previous = try await vault.readAsync(provider),provider.oauth,(previous.clientID != saved.clientID || previous.clientSecret != saved.clientSecret || previous.tenant != saved.tenant) {
            saved.accessToken = "";saved.refreshToken = "";saved.expiry = nil;saved.accountID = "";saved.accountLabel = "";saved.resources = [];reviewed = false
        }
        try await vault.saveAsync(saved,provider:provider);tokenField = "";secretField = ""
    }
    func record(_ error:Error) {
        if Task.isCancelled || error is CancellationError { return }
        if let issue = error as? APIProblem {
            notice = issue.message
            if issue.status == 429 { saved.retryAt = Date().addingTimeInterval(Double(issue.retryAfter ?? 60));let value = saved;let target = provider;Task { try? await credentialWork { try vault.save(value,provider:target) } } }
        } else { notice = "The connection could not be completed. The last saved source copy has been retained." }
    }
    func token(force:Bool = false) async throws -> String {
        let expectedProvider = provider
        if provider.oauth && (force || saved.expiry.map { $0 < Date().addingTimeInterval(60) } == true) {
            guard !saved.refreshToken.isEmpty else { throw APIProblem(message:"Sign in again to authorize this program.",status:401) }
            let data = try await store.localRequest("/v1/providers/oauth/renew",method:"POST",body:["provider":provider.rawValue,"client_id":saved.clientID,"client_secret":saved.clientSecret,"tenant":saved.tenant,"refresh_token":saved.refreshToken])
            try Task.checkCancellation();guard provider == expectedProvider else { throw CancellationError() }
            try await applyTokens(JSONDecoder().decode(OAuthTokens.self,from:data))
        }
        guard !saved.accessToken.isEmpty else { throw APIProblem(message:provider.oauth ? "Save your OAuth app setup, then sign in." : "Enter a provider token first.",status:401) }
        return saved.accessToken
    }
    func applyTokens(_ value:OAuthTokens) async throws {
        try Task.checkCancellation()
        guard let expiry = providerDate(value.expires_at) else { throw APIProblem(message:"The provider token expiry could not be read.",status:0) }
        var next = saved;next.accessToken = value.access_token;if let refresh = value.refresh_token { next.refreshToken = refresh };next.expiry = expiry;next.scope = value.scope;next.retryAt = nil
        try await vault.saveAsync(next,provider:provider);saved = next
    }
    func importGoogleClient() {
        let panel = NSOpenPanel();panel.canChooseDirectories = false;panel.allowsMultipleSelection = false;panel.message = "Choose the JSON for your approved Google Desktop app OAuth client. Juno uses fixed Google endpoints and stores this setup in Keychain."
        guard panel.runModal() == .OK,let url = panel.url else { return }
        do {
            let data = try Data(contentsOf:url);guard data.count<32000,let object = try JSONSerialization.jsonObject(with:data) as? [String:Any],let config = object["installed"] as? [String:Any],let client = config["client_id"] as? String,client.hasSuffix(".apps.googleusercontent.com") else { throw APIProblem(message:"Choose a Google Desktop app JSON with an installed section; a web-client configuration is different.",status:0) }
            saved.clientID = client;secretField = config["client_secret"] as? String ?? "";reviewed = false;notice = "Desktop app details loaded. Save setup, then sign in when ready."
        } catch { record(error) }
    }
    func startSignIn() {
        busy = true
        operationTask = Task {
            defer { busy = false }
            do {
                try await saveForm();let expectedProvider = provider
                let response = try JSONDecoder().decode(OAuthStartReply.self,from:await store.localRequest("/v1/providers/oauth/start",method:"POST",body:["provider":provider.rawValue,"client_id":saved.clientID,"client_secret":saved.clientSecret,"tenant":saved.tenant]))
                try Task.checkCancellation();guard provider == expectedProvider else { throw CancellationError() }
                let address = try validatedAuthorization(response.authorization_url,provider:provider,flow:response.flow_id,client:saved.clientID)
                guard NSWorkspace.shared.open(address) else { _ = try? await store.localRequest("/v1/providers/oauth/session/"+response.flow_id,method:"DELETE");throw APIProblem(message:"The system browser could not open provider sign-in.",status:0) }
                flowID = response.flow_id;notice = "Finish read-access consent in your browser, then return here. No program data is read until you discover and choose resources."
                authTask = Task {
                    do {
                        for _ in 0..<300 {
                            try await Task.sleep(nanoseconds:2_000_000_000)
                            try Task.checkCancellation()
                            let value = try JSONDecoder().decode(OAuthPollReply.self,from:await store.localRequest("/v1/providers/oauth/session/"+response.flow_id))
                            try Task.checkCancellation()
                            guard provider == expectedProvider,value.provider == expectedProvider.rawValue else { return }
                            if value.phase == "complete",let tokens = value.tokens {
                                try await applyTokens(tokens)
                                _ = try? await store.localRequest("/v1/providers/oauth/session/"+response.flow_id+"/ack",method:"POST")
                                flowID = nil;reviewed = false;notice = "Signed in. Credentials are saved in this Mac's Keychain. Discover resources, review the account, then refresh."
                                return
                            }
                            if value.phase == "failed" { throw APIProblem(message:value.error ?? "Sign-in was not completed. Start again when ready.",status:401) }
                        }
                        throw APIProblem(message:"Sign-in expired. Start again when ready.",status:401)
                    } catch is CancellationError {} catch { flowID = nil;record(error) }
                }
            } catch { record(error) }
        }
    }
    func cancelSignIn() {
        authTask?.cancel();authTask = nil
        if let id = flowID { Task { _ = try? await store.localRequest("/v1/providers/oauth/session/"+id,method:"DELETE") } }
        flowID = nil
    }
    func discoverResources() {
        busy = true;reviewed = false
        operationTask = Task {
            defer { busy = false }
            do {
                try await saveForm()
                func fetch(_ credential:String) async throws -> Data { try await store.localRequest("/v1/providers/"+provider.rawValue+"/discover",method:"POST",body:["token":credential]) }
                let data:Data
                do { data = try await fetch(token()) }
                catch let issue as APIProblem where issue.status == 401 && provider.oauth { data = try await fetch(token(force:true)) }
                try Task.checkCancellation()
                let found = try JSONDecoder().decode(ProviderDiscovery.self,from:data)
                guard found.provider == provider.rawValue else { throw APIProblem(message:"The discovered provider did not match your selection.",status:0) }
                if saved.accountID != found.account.id { saved.resources = [];saved.resourceLabels = [:] }
                saved.accountID = found.account.id;saved.accountLabel = found.account.label;resources = found.resources
                notice = found.notice + (found.manual_selection_required ? " This token cannot list conversations; enter the exact permitted conversation IDs below." : "")
            } catch { record(error) }
            await loadState()
        }
    }
    func refresh() {
        guard reviewed,!cooldown else { return };busy = true
        operationTask = Task {
            defer { busy = false }
            do {
                if !manualIDs.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
                    let ids = manualIDs.components(separatedBy:CharacterSet(charactersIn:",\n")).map { $0.trimmingCharacters(in:.whitespacesAndNewlines) }.filter { !$0.isEmpty }
                    guard ids.count<=10,Set(ids).count == ids.count else { throw APIProblem(message:"Enter at most ten distinct resource IDs.",status:0) }
                    saved.resources = ids
                }
                guard provider == .gmail || !saved.resources.isEmpty else { throw APIProblem(message:"Choose at least one resource before refreshing.",status:0) }
                try await saveForm()
                let selection:[String:Any] = ["resources":saved.resources,"query":saved.query,"start":saved.start,"end":saved.end,"timezone":saved.zone,"include_threads":saved.includeThreads,"reviewed_account":saved.accountID]
                let expectedID = current?.id
                func fetch(_ credential:String) async throws -> Data {
                    var body:[String:Any] = ["token":credential,"selection":selection]
                    if let expectedID { body["expected_id"] = expectedID }
                    return try await store.localRequest("/v1/providers/"+provider.rawValue+"/refresh",method:"POST",body:body)
                }
                let data:Data
                do { data = try await fetch(token()) }
                catch let issue as APIProblem where issue.status == 401 && provider.oauth { data = try await fetch(token(force:true)) }
                try Task.checkCancellation()
                let result = try JSONDecoder().decode(ProviderRefreshReply.self,from:data)
                if result.review_required { reviewed = false;notice = "The provider account changed. Discover again and review the account before replacing the saved copy." }
                else { saved.retryAt = nil;try await vault.saveAsync(saved,provider:provider);notice = "Read-only refresh complete. Open Evidence to review the dated copy; TaskDock tasks were not changed." }
            } catch { record(error) }
            await loadState()
        }
    }
    @ViewBuilder var setupFields:some View {
        Text(provider.help).foregroundStyle(.secondary)
        if provider.oauth {
            Text(provider.google ? "Use an institution-approved Google Desktop app OAuth client. Sign-in opens your system browser; Juno remains a native app." : "Register a Microsoft public desktop client with http://localhost/v1/providers/oauth/callback/microsoft. Microsoft allows the loopback port to vary; use your approved tenant.").font(.callout)
            TextField("OAuth client ID",text:$saved.clientID).disabled(busy || waiting).onChange(of:saved.clientID) { _ in reviewed = false }
            if provider.google {
                SecureField("Client secret (blank uses saved value)",text:$secretField).disabled(busy || waiting)
                Button("Load Google Desktop client JSON…") { importGoogleClient() }.disabled(busy || waiting)
            } else { TextField("Tenant: organizations, common, or approved tenant ID",text:$saved.tenant).disabled(busy || waiting) }
            HStack {
                Button("Save app setup") { busy = true;Task { defer { busy = false };do { try await saveForm();notice = "Setup saved in this Mac's Keychain. Sign in when ready." } catch { record(error) } } }.disabled(busy || waiting)
                Button("Sign in for read access…") { startSignIn() }.disabled(busy || waiting || saved.clientID.isEmpty)
                if waiting { Button("Cancel sign-in") { cancelSignIn();notice = "Sign-in cancelled in Juno. You can close the provider page." } }
            }
            if !saved.scope.isEmpty { DisclosureGroup("Granted authorization scopes") { Text(saved.scope).font(.caption).textSelection(.enabled) } }
        } else {
            SecureField(provider == .slack ? "Approved Slack token (blank uses Keychain)" : "Approved Smartsheet API token (blank uses Keychain)",text:$tokenField).disabled(busy || waiting).onChange(of:tokenField) { _ in reviewed = false }
            Button("Save credential in Keychain") { busy = true;Task { defer { busy = false };do { try await saveForm();notice = "Credential saved on this Mac. Discover and review the account before reading content." } catch { record(error) } } }.disabled(busy)
        }
        Button("Discover account and resources") { discoverResources() }.disabled(busy || waiting || cooldown)
        if !saved.accountLabel.isEmpty { Text("Account: " + saved.accountLabel).font(.headline).textSelection(.enabled) }
    }
    private func dayBinding(_ path:WritableKeyPath<SavedConnection,String>) -> Binding<Date> {
        let formatter = DateFormatter();formatter.locale = Locale(identifier:"en_US_POSIX");formatter.timeZone = TimeZone(identifier:"America/Chicago");formatter.dateFormat = "yyyy-MM-dd"
        return Binding(get:{formatter.date(from:saved[keyPath:path]) ?? Date()},set:{saved[keyPath:path] = formatter.string(from:$0);reviewed = false})
    }
    @ViewBuilder var selectionFields:some View {
        if provider == .gmail {
            Text("Gmail search query").font(.headline)
            TextField("in:inbox is:unread",text:$saved.query).onChange(of:saved.query) { _ in reviewed = false }
            Text("The query controls coverage; the calendar date fields do not filter Gmail. Narrow large mailboxes. Reading does not mark messages read.").font(.caption).foregroundStyle(.secondary)
        } else {
            Text("Select resources (up to ten)").font(.headline)
            if !resources.isEmpty {
                TextField("Filter discovered resources",text:$resourceFilter)
                ForEach(Array(resources.filter { resourceFilter.isEmpty || $0.label.localizedCaseInsensitiveContains(resourceFilter) || $0.id.localizedCaseInsensitiveContains(resourceFilter) }.prefix(100))) { resource in
                    Toggle(resource.label,isOn:Binding(get:{ saved.resources.contains(resource.id) },set:{ yes in
                        if yes { if !saved.resources.contains(resource.id),saved.resources.count<10 { saved.resources.append(resource.id);saved.resourceLabels[resource.id] = resource.label } }
                        else { saved.resources.removeAll { $0 == resource.id } }
                        reviewed = false
                    })).toggleStyle(.checkbox)
                }
                if resources.count>100 { Text("Filter to find resources beyond the first 100 matches.").font(.caption) }
            }
            if !saved.resources.isEmpty { Text("Selected: " + saved.resources.map { saved.resourceLabels[$0] ?? $0 }.joined(separator:", ")).font(.caption).textSelection(.enabled) }
            DisclosureGroup("Enter exact resource IDs instead") {
                TextField(provider == .google_chat ? "spaces/SPACE_ID, spaces/ANOTHER_ID" : "Comma-separated resource IDs",text:$manualIDs).onChange(of:manualIDs) { _ in reviewed = false }
                Text("Use exact IDs from your approved account. These replace the checkbox selection when you refresh. Juno does not join channels, create spaces or discover credentials.").font(.caption).foregroundStyle(.secondary)
            }
        }
        if provider.timed {
            HStack {
                VStack(alignment:.leading) { Text("From").font(.caption);DatePicker("From",selection:dayBinding(\.start),displayedComponents:.date).labelsHidden() }
                VStack(alignment:.leading) { Text("Until (not included)").font(.caption);DatePicker("Until",selection:dayBinding(\.end),displayedComponents:.date).labelsHidden() }
            }
            TextField("IANA timezone",text:$saved.zone)
            Text("Choose a window of 1–366 days. Missing records do not prove free time, room access, employee availability or capability.").font(.caption).foregroundStyle(.secondary)
        }
        if provider == .slack { Toggle("Include readable replies to parents in this window",isOn:$saved.includeThreads);Text("Replies to older parents may be missing. Bot/user scope and provider retention limits still apply.").font(.caption) }
        Toggle("I reviewed this account, resource selection and coverage.",isOn:$reviewed).toggleStyle(.checkbox).disabled(saved.accountID.isEmpty || busy || waiting)
        Button("Refresh read-only copy") { refresh() }.disabled(busy || waiting || !reviewed || cooldown)
        if let retry = saved.retryAt,retry > Date() { Text("Provider requested a pause. Retry after " + retry.formatted()).font(.caption).foregroundStyle(.orange) }
    }
    var body:some View {
        ScrollView {
            VStack(alignment:.leading,spacing:15) {
                Text("Direct program connections").font(.title2.bold())
                Text("Credentials stay in this Mac's Keychain. Juno's saved evidence is separate from TaskDock's task records. Sign-in and reads start only when you choose them.").foregroundStyle(.secondary)
                Picker("Program",selection:$provider) { ForEach(WorkProvider.allCases) { p in Text(p.label).tag(p) } }.disabled(busy || waiting)
                setupFields
                Divider()
                selectionFields.disabled(busy || waiting)
                if let current {
                    Divider();if current.details.tombstone == true { Text("No saved copy. Discover and review this connection before refreshing.").font(.caption) } else { Text("Last saved copy: \(current.count) records · \(providerDate(current.fetched_at)?.formatted() ?? current.fetched_at)").font(.caption) }
                    if let error = current.error { Text(error).foregroundStyle(.orange) }
                    Text("View/remove historical content in Evidence. Disconnecting does not delete provider data or revoke authorization in the provider's account settings.").font(.caption).foregroundStyle(.secondary)
                }
                if busy || waiting { ProgressView().controlSize(.small) }
                if let notice { Text(notice).foregroundStyle(.secondary).textSelection(.enabled) }
                Button("Disconnect and forget this Mac's credential…",role:.destructive) { forget = true }.disabled(busy || waiting)
            }.padding(28).frame(maxWidth:.infinity,alignment:.leading)
        }.task { await loadSaved();await loadState() }
        .onChange(of:saved.retryAt) { _ in scheduleCooldown() }
        .onChange(of:saved.start) { _ in reviewed = false }
        .onChange(of:saved.end) { _ in reviewed = false }
        .onChange(of:saved.zone) { _ in reviewed = false }
        .onChange(of:saved.includeThreads) { _ in reviewed = false }
        .onChange(of:provider) { _ in cancelSignIn();operationTask?.cancel();Task { await loadSaved() } }
        .onDisappear { cancelSignIn();operationTask?.cancel();cooldownTask?.cancel() }
        .alert("Forget this connection on this Mac?",isPresented:$forget) {
            Button("Cancel",role:.cancel) {}
            Button("Disconnect and forget",role:.destructive) {
                let expectedProvider = provider;let previousID = current?.id;busy = true
                operationTask = Task {
                    defer { busy = false }
                    do {
                        try await vault.forgetAsync(expectedProvider)
                        var body:[String:Any] = [:];if let previousID { body["expected_id"] = previousID }
                        _ = try await store.localRequest("/v1/providers/"+expectedProvider.rawValue+"/disconnect",method:"POST",body:body)
                        guard provider == expectedProvider,!Task.isCancelled else { return }
                        saved = SavedConnection();resources = [];reviewed = false;notice = "Credential removed. The dated copy stays in Evidence and is excluded from new model context until refreshed."
                    } catch { if provider == expectedProvider { notice = "The local credential removal/source update could not finish. Check Evidence and retry before relying on connection status." } }
                    await loadState()
                }
            }
        } message: { Text("The credential is removed from Juno's Keychain storage. A historical source copy is retained; remove it separately in Evidence if desired. No provider data is deleted and no upstream authorization is revoked.") }
    }
}

struct BridgeSource: Decodable,Identifiable {
    let id:String;let mode:String?;let health:String?;let last_success_at:String?;let coverage:String?
}
struct BridgeCatalog: Decodable { let info:TaskDockInfo;let sources:[BridgeSource];let grants:[String];let notice:String }
struct BridgeRefreshReply: Decodable { let review_required:Bool;let catalog:BridgeCatalog? }
struct TaskDockBridgeWorkspace: View {
    @ObservedObject var store:JunoStore
    let onDirect:(WorkProvider)->Void
    @State private var origin = UserDefaults.standard.string(forKey:"taskdockOrigin") ?? "http://127.0.0.1:8100"
    @State private var tokenField = ""
    @State private var catalog:BridgeCatalog?
    @State private var selected:[String] = []
    @State private var reviewed = false
    @State private var snapshots:[ConnectionSnapshot] = []
    @State private var busy = false
    @State private var notice:String?
    var current:ConnectionSnapshot? { snapshots.first { $0.kind == "taskdock_saved" } }
    func credential() async throws -> String {
        let address = origin;let entered = tokenField
        let value = entered.isEmpty ? try await credentialWork { try TaskDockKeychain.read(address) } ?? "" : entered
        guard !value.isEmpty else { throw APIProblem(message:"Pair in Juno's TaskDock tab first, or enter the dedicated Juno token created in TaskDock Settings.",status:0) }
        return value
    }
    func load() async {
        do { snapshots = try JSONDecoder().decode(ConnectionSnapshots.self,from:await store.localRequest("/v1/providers/state")).items }
        catch { notice = (error as? APIProblem)?.message ?? "Saved bridge status unavailable." }
    }
    func discover() {
        busy = true;reviewed = false
        Task {
            defer { busy = false }
            do {
                let requestedOrigin = origin
                let key = try await credential()
                let next = try JSONDecoder().decode(BridgeCatalog.self,from:await store.localRequest("/v1/taskdock/catalog",method:"POST",body:["base_url":origin,"token":key]))
                try await credentialWork { try TaskDockKeychain.save(key,origin:requestedOrigin) };tokenField = "";UserDefaults.standard.set(requestedOrigin,forKey:"taskdockOrigin")
                catalog = next;selected = next.grants;notice = next.notice
            } catch { notice = (error as? APIProblem)?.message ?? "TaskDock could not be discovered. Existing copies were retained." }
            await load()
        }
    }
    func readSaved() {
        guard let catalog,reviewed else { return };busy = true
        Task {
            defer { busy = false }
            do {
                var body:[String:Any] = ["base_url":origin,"token":try await credential(),"kinds":selected,"reviewed_workspace_id":catalog.info.workspace_id,"reviewed_device_id":catalog.info.device_id]
                if let current { body["expected_id"] = current.id }
                let result = try JSONDecoder().decode(BridgeRefreshReply.self,from:await store.localRequest("/v1/taskdock/evidence",method:"POST",body:body))
                if result.review_required { self.catalog = result.catalog;reviewed = false;notice = "The TaskDock identity changed. Review this workspace before replacing its saved evidence." }
                else { notice = "Read the explicitly shared saved evidence. Provider credentials stayed in TaskDock; no source refresh or writeback was triggered." }
            } catch { notice = (error as? APIProblem)?.message ?? "Saved evidence could not be read. The previous copy was retained." }
            await load()
        }
    }
    func label(_ kind:String) -> String { ["events":"Events and schedules","notes":"Notebook notes","time":"Recorded work time","expenses":"Recorded expenses"][kind] ?? kind }
    var body:some View {
        ScrollView {
            VStack(alignment:.leading,spacing:16) {
                Text("Use TaskDock's connections").font(.title2.bold())
                Text("Juno reads stored TaskDock content through its supported bridge. Your provider passwords and tokens remain in TaskDock. Broader inbox, chat and calendar access uses the separate direct connection route.").foregroundStyle(.secondary)
                TextField("Local TaskDock API address",text:$origin).disabled(busy).onChange(of:origin) { _ in catalog = nil;reviewed = false }
                SecureField("Dedicated Juno token (blank uses Juno's saved TaskDock key)",text:$tokenField).disabled(busy).onChange(of:tokenField) { _ in catalog = nil;reviewed = false }
                Button("Discover TaskDock connections") { discover() }.disabled(busy)
                Text("Choose which saved information Juno may read in TaskDock Settings → Juno. Provider credentials stay in TaskDock. Sharing additional information always requires your review.").font(.caption).foregroundStyle(.secondary)
                if let catalog {
                    ForEach(catalog.sources) { source in
                        VStack(alignment:.leading,spacing:6) {
                            HStack { Text(source.id.replacingOccurrences(of:"_",with:" ").capitalized).font(.headline);Text((source.mode ?? "Unknown mode")+" · "+(source.health ?? "Unknown health")).font(.caption) }
                            Text(source.coverage ?? "Saved task content only.").font(.callout)
                            if let date = source.last_success_at { Text("TaskDock last read: " + (providerDate(date)?.formatted() ?? date)).font(.caption) }
                            if let provider = WorkProvider(rawValue:source.id) { Button("Set up direct " + provider.label + " access…") { onDirect(provider) }.disabled(busy) }
                        }.padding(.vertical,6)
                    }
                    Divider();Text("Additional saved evidence").font(.headline)
                    if catalog.grants.isEmpty { Text("No additional sharing grants are enabled. Use TaskDock Settings to review any saved events, note bodies, recorded time or expenses you want Juno to read.").foregroundStyle(.secondary) }
                    ForEach(catalog.grants,id:\.self) { kind in Toggle(label(kind),isOn:Binding(get:{ selected.contains(kind) },set:{ yes in if yes { selected.append(kind) } else { selected.removeAll { $0 == kind } };reviewed = false })).toggleStyle(.checkbox) }
                    Text("Workspace: " + catalog.info.workspace_id + " · Installation: " + catalog.info.device_id).font(.caption).textSelection(.enabled)
                    Toggle("I reviewed this TaskDock workspace and selected saved sections.",isOn:$reviewed).toggleStyle(.checkbox)
                    Button("Read shared saved evidence") { readSaved() }.disabled(busy || !reviewed || selected.isEmpty)
                }
                if let current { if current.details.tombstone == true { Text("No saved bridge copy. Discover and review TaskDock before refreshing.").font(.caption) } else { Text("Last saved bridge copy: \(current.count) records · \(providerDate(current.fetched_at)?.formatted() ?? current.fetched_at)").font(.caption) };if let error = current.error { Text(error).foregroundStyle(.orange) } }
                if let notice { Text(notice).foregroundStyle(.secondary).textSelection(.enabled) }
                if busy { ProgressView() }
            }.padding(28).frame(maxWidth:.infinity,alignment:.leading)
        }.task { await load() }
    }
}
