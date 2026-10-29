import SwiftUI
import AppKit
import Security
import CryptoKit

struct SharedProfile: Codable {
    let address: String; let certificate_sha256: String; let owner_id: String; let device_id: String
}
struct HostStatus: Decodable { let enabled: Bool; let address: String; let error: String?; let availability: String }
struct HostInvitation: Codable { let version: Int; let address: String; let certificate_sha256: String; let invitation: String; let expires_at: String }
func pairingFailure(_ error: Error) -> String {
    if let api = error as? APIProblem { return api.message }
    if let url = error as? URLError {
        switch url.code {
        case .cannotFindHost, .dnsLookupFailed: return "The work Mac address could not be resolved. Create a new pairing file on the work Mac using its IP address."
        case .timedOut, .cannotConnectToHost, .networkConnectionLost, .notConnectedToInternet: return "Cannot reach the work Mac on TCP port 8443. Check that Juno is hosting and that wired-to-Wi-Fi traffic is allowed by the network and firewall."
        case .serverCertificateUntrusted, .serverCertificateHasBadDate, .serverCertificateHasUnknownRoot, .secureConnectionFailed, .userCancelledAuthentication, .cancelled: return "The paired HTTPS identity could not be verified. Create and import a fresh pairing file from the work Mac."
        default: return "The work Mac connection failed (network error \(url.errorCode)). Your data and queued edits have been retained."
        }
    }
    return "The pairing file could not be read or used. Export a fresh file from the work Mac and import it within 15 minutes."
}
struct PairResult: Decodable { let token: String; let owner_id: String; let device_id: String }
struct PairedDevice: Decodable, Identifiable { let id: String; let label: String; let current: Bool }
struct PairedDevices: Decodable { let items: [PairedDevice] }

func validatedHost(_ address: String) throws -> URL {
    guard let parts = URLComponents(string: address), parts.scheme == "https", let host = parts.host?.lowercased(), parts.user == nil, parts.password == nil,
          parts.query == nil, parts.fragment == nil, parts.path.isEmpty || parts.path == "/", parts.port == nil || (1...65535).contains(parts.port!) else {
        throw APIProblem(message: "Use an HTTPS Juno address on the local network.", status: 0)
    }
    let octets = host.split(separator: ".").compactMap { Int($0) }
    let privateIPv4 = octets.count == 4 && octets.allSatisfy { (0...255).contains($0) } &&
        (octets[0] == 10 || octets[0] == 127 || (octets[0] == 192 && octets[1] == 168) || (octets[0] == 172 && (16...31).contains(octets[1])) || (octets[0] == 169 && octets[1] == 254))
    guard host == "localhost" || host.hasSuffix(".local") || privateIPv4 else { throw APIProblem(message: "This preview connects only to a local Mac or private IPv4 address.", status: 0) }
    guard let url = parts.url else { throw APIProblem(message: "Invalid host address.", status: 0) }
    return url
}

final class PinnedHostSession: NSObject, URLSessionDelegate, URLSessionTaskDelegate {
    let fingerprint: String
    init(_ fingerprint: String) { self.fingerprint = fingerprint.lowercased() }
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust,
              let certificates = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let certificate = certificates.first else { completionHandler(.cancelAuthenticationChallenge, nil); return }
        let data = SecCertificateCopyData(certificate) as Data
        let actual = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        // A deliberately imported pairing file pins this exact host certificate.
        // No global trust changes, broad trust bypass, or fallback identities.
        guard actual == fingerprint else { completionHandler(.cancelAuthenticationChallenge, nil); return }
        completionHandler(.useCredential, URLCredential(trust: trust))
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) { completionHandler(nil) }
    func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral; config.urlCache = nil
        config.connectionProxyDictionary = [:]
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }
}

struct OfflineEdit: Codable, Identifiable {
    let id: String; let kind: String; var recordID: String?; let localID: String?; let body: Data; let createdAt: Date
}
struct OfflineArchive: Codable { var savedAt: Date; var pages: [String: Data]; var pending: [OfflineEdit] = [] }
final class OfflineCopy {
    let file: URL
    var archive: OfflineArchive
    var resolved: [String:String] = [:]
    init(profile: SharedProfile) throws {
        let label = profile.address + "|" + profile.owner_id + "|" + profile.certificate_sha256
        let key = SHA256.hash(data: Data(label.utf8)).map { String(format: "%02x", $0) }.joined()
        let variant = (Bundle.main.bundleIdentifier ?? "com.dmccoy.juno").hasSuffix("development") ? "Juno Development" : "Juno"
        let directory = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/" + variant + "/offline-copies")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        file = directory.appendingPathComponent(key + ".json")
        if FileManager.default.fileExists(atPath: file.path) { archive = try JSONDecoder().decode(OfflineArchive.self, from: Data(contentsOf: file)) }
        else { archive = OfflineArchive(savedAt: .distantPast, pages: [:]) }
    }
    static func key(_ path: String) -> String {
        guard var parts = URLComponents(string: path) else { return path }
        let query = (parts.queryItems ?? []).filter { !(($0.name == "q" && ($0.value ?? "").isEmpty) || ($0.name == "offset" && $0.value == "0")) }.sorted { ($0.name, $0.value ?? "") < ($1.name, $1.value ?? "") }
        parts.queryItems = query.isEmpty ? nil : query
        return parts.string ?? path
    }
    func save() throws {
        let data = try JSONEncoder().encode(archive)
        guard data.count < 90_000_000 else { throw APIProblem(message: "The offline copy is too large; the previous file was retained.", status: 0) }
        try data.write(to: file, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
    }
    func replace(_ data: Data, owner: String) throws {
        guard archive.pending.isEmpty else { throw APIProblem(message:"New edits are queued. The existing laptop copy was retained; synchronize again.",status:409) }
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any], object["version"] as? Int == 1,
              object["owner_id"] as? String == owner, let pages = object["pages"] as? [[String: Any]] else { throw APIProblem(message: "The shared host returned an invalid offline copy.", status: 0) }
        var next: [String: Data] = [:]
        for page in pages {
            guard let path = page["path"] as? String, path.hasPrefix("/v1/"), let body = page["body"] else { throw APIProblem(message: "The offline copy was incomplete.", status: 0) }
            next[Self.key(path)] = try JSONSerialization.data(withJSONObject: body)
        }
        let old = archive
        archive = OfflineArchive(savedAt: .now, pages: next, pending: old.pending)
        do { try save() } catch { archive = old; throw error }
    }
    func read(_ path: String) throws -> Data {
        if let data = archive.pages[Self.key(path)] { return data }
        if let parts = URLComponents(string: path), parts.path == "/v1/memories" {
            let q = parts.queryItems?.first { $0.name == "q" }?.value ?? ""
            let offset = Int(parts.queryItems?.first { $0.name == "offset" }?.value ?? "0") ?? 0
            let rows = archive.pages.filter { $0.key == "/v1/memories" || $0.key.hasPrefix("/v1/memories?offset=") }.flatMap { _, data -> [[String: Any]] in
                ((try? JSONSerialization.jsonObject(with: data)) as? [String: Any])?["items"] as? [[String: Any]] ?? []
            }.filter { q.isEmpty || ($0["text"] as? String ?? "").localizedCaseInsensitiveContains(q) }.sorted { ($0["updated_at"] as? String ?? "", $0["id"] as? String ?? "") > ($1["updated_at"] as? String ?? "", $1["id"] as? String ?? "") }
            return try JSONSerialization.data(withJSONObject: ["items": Array(rows.dropFirst(offset).prefix(50)), "has_more": offset + 50 < rows.count])
        }
        throw APIProblem(message: "This item is not in the offline copy. Reconnect to the work Mac to load it.", status: 0)
    }
    func clear() { archive = OfflineArchive(savedAt: .distantPast, pages: [:], pending: archive.pending); try? FileManager.default.removeItem(at: file) }
}

enum SharedKeychain {
    static var service: String { (Bundle.main.bundleIdentifier ?? "com.dmccoy.juno") + ".sharedHost" }
    static func query(_ origin: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: origin]
    }
    static func read(_ origin: String) throws -> String? {
        var q = query(origin); q[kSecReturnData as String] = true; q[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data, let text = String(data: data, encoding: .utf8) else { throw APIProblem(message: "Juno could not read the shared host token from Keychain.", status: 0) }
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
        guard status == errSecSuccess else { throw APIProblem(message: "shared host was reached, but the token could not be saved in Keychain.", status: 0) }
    }
    static func forget(_ origin: String) throws {
        let status = SecItemDelete(query(origin) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw APIProblem(message: "Could not remove the shared host credential from Keychain.", status: 0) }
    }
}


extension OfflineCopy {
    func objects(_ prefix: String) -> [[String: Any]] {
        archive.pages.filter { $0.key == prefix || $0.key.hasPrefix(prefix + "?offset=") }.flatMap { _, data in
            ((try? JSONSerialization.jsonObject(with: data)) as? [String: Any])?["items"] as? [[String: Any]] ?? []
        }
    }
    func memories(_ rows: [[String: Any]]) throws {
        for key in Array(archive.pages.keys) where key == "/v1/memories" || key.hasPrefix("/v1/memories?offset=") { archive.pages.removeValue(forKey: key) }
        let sorted = rows.sorted { ($0["updated_at"] as? String ?? "") > ($1["updated_at"] as? String ?? "") }
        for offset in stride(from: 0, to: max(1, sorted.count), by: 50) {
            archive.pages[Self.key("/v1/memories?offset=\(offset)")] = try JSONSerialization.data(withJSONObject: ["items":Array(sorted.dropFirst(offset).prefix(50)),"has_more":offset+50<sorted.count])
        }
    }
    func invalidateReplies() throws {
        for (key, data) in archive.pages where key.contains("/messages") {
            guard var object = try JSONSerialization.jsonObject(with: data) as? [String: Any], var items = object["items"] as? [[String: Any]] else { continue }
            for i in items.indices where items[i]["role"] as? String == "assistant" {
                items[i]["text"] = "This saved reply was hidden because you edited work context offline. Reconnect for current context."
                items[i]["status"] = "invalidated"
            }
            object["items"] = items; archive.pages[key] = try JSONSerialization.data(withJSONObject: object)
        }
    }
    func perform(_ path: String, method: String, body: [String: Any]) throws -> Data {
        let old = archive
        do {
            let stamp = ISO8601DateFormatter().string(from: .now)
            var kind = ""; var recordID: String?; var localID: String?; var result: [String: Any] = [:]
            let pieces = path.split(separator: "/").map(String.init)
            if path == "/v1/memories", method == "POST" {
                kind = "memory.create"; localID = "offline-" + UUID().uuidString
                result = body; result["id"] = localID!; result["revision"] = 1; result["created_at"] = stamp; result["updated_at"] = stamp
                var rows = objects("/v1/memories"); rows.insert(result, at: 0); try memories(rows)
            } else if pieces.count == 3 && pieces[1] == "memories" && ["PUT","DELETE"].contains(method) {
                recordID = pieces[2]
                var rows = objects("/v1/memories")
                guard let index = rows.firstIndex(where: { $0["id"] as? String == recordID }), let revision = rows[index]["revision"] as? Int,
                      revision == body["expected_revision"] as? Int else { throw APIProblem(message: "The saved memory changed; reload it before editing offline.", status: 409) }
                if method == "DELETE" { kind = "memory.delete"; rows.remove(at: index); result = ["deleted":true] }
                else {
                    kind = "memory.edit"; result = rows[index]
                    for (key,value) in body where key != "expected_revision" { result[key] = value }
                    result["revision"] = revision + 1; result["updated_at"] = stamp; rows[index] = result
                }
                try memories(rows); try invalidateReplies()
            } else if path == "/v1/check-ins", method == "POST", let day = body["local_date"] as? String {
                let key = "/v1/check-ins/by-date/" + day
                if let saved = archive.pages[key] { return saved }
                let template = try JSONSerialization.jsonObject(with: read("/v1/check-in-template")) as? [String: Any]
                guard let questions = template?["questions"] as? [[String: Any]], let first = questions.first?["key"] as? String else { throw APIProblem(message: "Connect once to save the check-in questions for offline use.", status: 0) }
                kind = "checkin.start"; localID = "offline-" + UUID().uuidString
                result = ["id":localID!,"local_date":day,"answers":[String:String](),"diary_text":"","status":"draft","revision":1,"updated_at":stamp,"questions":questions,"next_key":first,"source_notice":"Saved on this laptop; queued to sync with your work Mac."]
                archive.pages[key] = try JSONSerialization.data(withJSONObject: result)
            } else if pieces.count == 4 && pieces[1] == "check-ins" && method == "PUT" {
                recordID = pieces[2]
                guard let entry = archive.pages.first(where: { key,data in
                    key.hasPrefix("/v1/check-ins/by-date/") && ((try? JSONSerialization.jsonObject(with:data)) as? [String:Any])?["id"] as? String == recordID
                }), var row = try JSONSerialization.jsonObject(with: entry.value) as? [String: Any], let revision = row["revision"] as? Int, revision == body["expected_revision"] as? Int else { throw APIProblem(message: "Reload the saved check-in before editing offline.", status: 409) }
                if pieces[3] == "answer" {
                    kind = "checkin.answer"
                    guard let key = body["key"] as? String, let text = body["text"] as? String,
                          let questions = row["questions"] as? [[String:Any]], questions.contains(where: { $0["key"] as? String == key }) else { throw APIProblem(message: "Invalid check-in answer.", status: 422) }
                    var answers = row["answers"] as? [String:String] ?? [:]; answers[key] = text; row["answers"] = answers
                    let labels = ["completed":"Accomplishments","interruptions":"Unexpected work","blockers":"Blockers and next steps","employee_work":"Employee contributions","tomorrow":"Tomorrow"]
                    row["diary_text"] = questions.compactMap { q -> String? in guard let k = q["key"] as? String, let answer = answers[k] else { return nil }; return (labels[k] ?? k) + "\n" + (answer.isEmpty ? "Not provided." : answer) }.joined(separator:"\n\n")
                    row["next_key"] = questions.compactMap { $0["key"] as? String }.first { answers[$0] == nil } ?? NSNull() as Any
                    row["status"] = "draft"
                } else if pieces[3] == "diary" {
                    kind = "checkin.diary"; row["diary_text"] = body["text"]; row["status"] = body["confirm"] as? Bool == true ? "confirmed" : "draft"
                } else { throw APIProblem(message: "This edit cannot be queued offline.", status: 0) }
                row["revision"] = revision + 1; row["updated_at"] = stamp; result = row
                archive.pages[entry.key] = try JSONSerialization.data(withJSONObject: row); try invalidateReplies()
            } else { throw APIProblem(message: "This action needs your work Mac. Memory and diary edits can be saved offline; AI replies cannot.", status: 0) }
            archive.pending.append(OfflineEdit(id:UUID().uuidString,kind:kind,recordID:recordID,localID:localID,body:try JSONSerialization.data(withJSONObject:body),createdAt:.now))
            try save()
            return try JSONSerialization.data(withJSONObject: result)
        } catch { archive = old; throw error }
    }
    func acknowledge(_ edit: OfflineEdit, result: Data) throws {
        let old = archive
        if let local = edit.localID, let object = try JSONSerialization.jsonObject(with:result) as? [String:Any], let real = object["id"] as? String {
            resolved[local] = real
            for index in archive.pending.indices where archive.pending[index].recordID == local { archive.pending[index].recordID = real }
        }
        archive.pending.removeAll { $0.id == edit.id }
        do { try save() } catch { archive = old; throw error }
    }
}

extension JunoStore {
    var sharedLabel: String { sharedProfile == nil ? "Connected · This Mac" : offline ? "Offline · Laptop copy" : "Connected · Work Mac" }
    func activateShared(_ profile: SharedProfile) throws {
        let credential = try SharedKeychain.read(profile.address) ?? ""
        let address = try validatedHost(profile.address)
        guard profile.certificate_sha256.count == 64 else { throw APIProblem(message:"Invalid host certificate identity.",status:0) }
        sharedProfile = profile; endpoint = address; token = credential; offline = true
        hostSession = PinnedHostSession(profile.certificate_sha256).session()
        offlineCopy = try OfflineCopy(profile:profile)
        pendingEdits = offlineCopy?.archive.pending ?? []
        offlineDate = offlineCopy?.archive.savedAt
    }
    func restoreShared() throws {
        if let data = UserDefaults.standard.data(forKey:"sharedProfile") { let profile = try JSONDecoder().decode(SharedProfile.self,from:data); sharedProfile = profile; try activateShared(profile) }
    }
    func localRequest(_ path:String,method:String = "GET",body:[String:Any]? = nil) async throws -> Data {
        guard let localEndpoint else { throw APIProblem(message:"The local app is starting.",status:0) }
        return try await wire(path,endpoint:localEndpoint,token:localToken,session:URLSession.shared,method:method,body:body)
    }
    func wire(_ path:String,endpoint:URL,token:String,session:URLSession,method:String,body:[String:Any]?) async throws -> Data {
        guard let url = URL(string:path,relativeTo:endpoint)?.absoluteURL else { throw APIProblem(message:"Invalid request.",status:0) }
        var request = URLRequest(url:url); request.httpMethod = method; request.timeoutInterval = path.contains("/messages") && method == "POST" ? 100 : (path.hasPrefix("/v1/taskdock/") ? 300 : 30)
        request.setValue("Bearer " + token,forHTTPHeaderField:"Authorization"); request.cachePolicy = .reloadIgnoringLocalCacheData
        if let body { request.httpBody = try JSONSerialization.data(withJSONObject:body);request.setValue("application/json",forHTTPHeaderField:"Content-Type") }
        let (data,response) = try await session.data(for:request)
        guard let response = response as? HTTPURLResponse else { throw APIProblem(message:"Invalid service response.",status:0) }
        guard (200..<300).contains(response.statusCode) else {
            let object = (try? JSONSerialization.jsonObject(with:data)) as? [String:Any]
            throw APIProblem(message:object?["detail"] as? String ?? "The service could not complete this request.",status:response.statusCode)
        }
        return data
    }
    func syncOfflineCopy() async throws {
        guard let profile = sharedProfile, let endpoint, let hostSession, let copy = offlineCopy else { return }
        while let edit = copy.archive.pending.first {
            var body:[String:Any] = ["operation_id":edit.id,"kind":edit.kind,"body":try JSONSerialization.jsonObject(with:edit.body)]
            if let record = edit.recordID { body["record_id"] = record }
            do {
                let result = try await wire("/v1/offline-operations",endpoint:endpoint,token:token,session:hostSession,method:"POST",body:body)
                try copy.acknowledge(edit,result:result);pendingEdits = copy.archive.pending
            } catch {
                pendingEdits = copy.archive.pending
                if (error as? APIProblem)?.status == 401 { sharedRevoked() }
                throw APIProblem(message:(error as? APIProblem)?.message ?? "The work Mac is unavailable. Your offline edits are still saved on this laptop.",status:(error as? APIProblem)?.status ?? 0)
            }
        }
        let data: Data
        do { data = try await wire("/v1/cache",endpoint:endpoint,token:token,session:hostSession,method:"GET",body:nil) }
        catch { if (error as? APIProblem)?.status == 401 { sharedRevoked() }; throw error }
        try copy.replace(data,owner:profile.owner_id)
        offlineDate = copy.archive.savedAt; offline = false; status = sharedLabel
    }
    func sharedRevoked() {
        offlineCopy?.clear(); items = []; messages = []; checkIn = nil; connected = false; offline = true; modelConfigured = false
        if let profile = sharedProfile { try? SharedKeychain.forget(profile.address) }
        token = ""
    }
    func reconnectShared() {
        guard !syncing else { return }; syncing = true; syncIssue = nil
        Task {
            defer { syncing = false }
            do { try await syncOfflineCopy(); try await load(); await loadCompanion(); syncIssue = "Offline copy refreshed. All queued changes are synchronized." }
            catch { syncIssue = (error as? APIProblem)?.message ?? "Could not reconnect. Your saved copy and queued edits remain on this laptop." }
        }
    }
}

struct ComputersWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var host: HostStatus?
    @State private var devices: [PairedDevice] = []
    @State private var busy = false
    @State private var notice: String?
    @State private var discard = false
    func loadHost() async {
        do {
            host = try JSONDecoder().decode(HostStatus.self,from:await store.localRequest("/v1/host"))
            devices = try JSONDecoder().decode(PairedDevices.self,from:await store.localRequest("/v1/host/devices")).items
        } catch { notice = (error as? APIProblem)?.message ?? "Could not load local host settings." }
    }
    func toggleHost(_ enabled:Bool) {
        busy = true
        Task {
            defer { busy = false }
            do {
                host = try JSONDecoder().decode(HostStatus.self,from:await store.localRequest("/v1/host",method:"PUT",body:["enabled":enabled]))
                notice = enabled ? "This Mac is hosting Juno on your local network." : "Shared hosting is off. Paired laptops retain their offline copies."
            } catch { notice = (error as? APIProblem)?.message ?? "Hosting could not change." }
        }
    }
    func exportInvitation() {
        busy = true
        Task {
            defer { busy = false }
            do {
                let data = try await store.localRequest("/v1/host/invitations",method:"POST")
                let panel = NSSavePanel(); panel.nameFieldStringValue = "Juno-work-Mac.junopair"; panel.message = "Transfer this one-use invitation directly to your laptop. It expires in 15 minutes. Treat it like a temporary password."
                if panel.runModal() == .OK, let file = panel.url {
                    guard FileManager.default.createFile(atPath:file.path,contents:data,attributes:[.posixPermissions:0o600]) else { throw APIProblem(message:"The invitation file could not be written.",status:0) }
                    notice = "One-use pairing file saved. Transfer it directly to the laptop and import it within 15 minutes."
                }
            } catch { notice = (error as? APIProblem)?.message ?? "Could not export an invitation." }
        }
    }
    func importInvitation() {
        let panel = NSOpenPanel(); panel.canChooseDirectories = false; panel.allowsMultipleSelection = false
        panel.message = "Choose the pairing file you transferred directly from your work Mac. It establishes that Mac's encrypted identity."
        guard panel.runModal() == .OK, let file = panel.url else { return }
        busy = true
        Task {
            defer { busy = false }
            do {
                if host?.enabled == true { throw APIProblem(message:"Stop hosting on this Mac before joining another host.",status:0) }
                let raw = try Data(contentsOf:file)
                guard raw.count < 16000 else { throw APIProblem(message:"Invalid pairing file.",status:0) }
                let invitation = try JSONDecoder().decode(HostInvitation.self,from:raw)
                guard invitation.version == 1, invitation.certificate_sha256.count == 64,
                      invitation.certificate_sha256.allSatisfy({$0.isHexDigit}), (40...256).contains(invitation.invitation.count) else { throw APIProblem(message:"Invalid pairing file.",status:0) }
                if let old = store.sharedProfile, !store.pendingEdits.isEmpty,
                   old.address != invitation.address || old.certificate_sha256 != invitation.certificate_sha256 {
                    throw APIProblem(message:"Export or synchronize your existing queued edits before switching to a different host identity.",status:409)
                }
                let address = try validatedHost(invitation.address)
                let session = PinnedHostSession(invitation.certificate_sha256).session()
                defer { session.finishTasksAndInvalidate() }
                let data = try await store.wire("/v1/pair",endpoint:address,token:"",session:session,method:"POST",body:["invitation":invitation.invitation,"label":Host.current().localizedName ?? "Juno laptop"])
                let paired = try JSONDecoder().decode(PairResult.self,from:data)
                if let old = store.sharedProfile, old.owner_id != paired.owner_id, !store.pendingEdits.isEmpty { throw APIProblem(message:"This invitation belongs to a different work history. Your existing queued edits have been retained; export them before switching.",status:409) }
                try SharedKeychain.save(paired.token,origin:invitation.address)
                let profile = SharedProfile(address:invitation.address,certificate_sha256:invitation.certificate_sha256,owner_id:paired.owner_id,device_id:paired.device_id)
                try store.activateShared(profile)
                UserDefaults.standard.set(try JSONEncoder().encode(profile),forKey:"sharedProfile")
                store.items = []; store.messages = []; store.checkIn = nil; store.currentConversation = nil
                try await store.syncOfflineCopy(); try await store.load(); await store.loadCompanion()
                notice = "Paired. The work Mac's history and an offline copy are ready. Existing standalone laptop data was not merged."
            } catch { notice = pairingFailure(error) }
        }
    }
    var body: some View {
        ScrollView {
            VStack(alignment:.leading,spacing:18) {
                Text("Your Juno computers").font(.title2.bold())
                if let profile = store.sharedProfile {
                    Text("This Mac uses the work Mac at \(profile.address). Its credential is stored in Keychain.")
                    Text("Memory and diary edits save on this laptop when offline. AI replies need the work Mac. Conflicts keep your queued version until you resolve them.").foregroundStyle(.secondary)
                    Button("Import a new pairing file…") { importInvitation() }.disabled(busy || store.syncing)
                    Button(store.syncing ? "Synchronizing…" : "Reconnect and synchronize") { store.reconnectShared() }.disabled(store.syncing)
                    if let date = store.offlineDate { Text("Last complete offline copy: " + date.formatted()).font(.caption) }
                    if !store.pendingEdits.isEmpty {
                        Text("Queued edits (\(store.pendingEdits.count))").font(.headline)
                        ForEach(store.pendingEdits) { edit in
                            DisclosureGroup(edit.kind + " · " + edit.createdAt.formatted()) {
                                Text(String(data:edit.body,encoding:.utf8) ?? "Saved edit").font(.caption.monospaced()).textSelection(.enabled)
                            }
                        }
                        Button("Export queued edits…") {
                            let panel = NSSavePanel(); panel.nameFieldStringValue = "Juno-unsynchronized-edits.json"
                            if panel.runModal() == .OK, let url = panel.url, let data = try? JSONEncoder().encode(store.pendingEdits) { _ = FileManager.default.createFile(atPath:url.path,contents:data,attributes:[.posixPermissions:0o600]) }
                        }
                        Button("Discard queued edits and use the work Mac's versions…",role:.destructive) { discard = true }
                    }
                    Button("Use standalone Juno on this Mac") {
                        UserDefaults.standard.removeObject(forKey:"sharedProfile")
                        store.hostSession?.invalidateAndCancel(); store.hostSession = nil; store.sharedProfile = nil; store.offlineCopy = nil; store.pendingEdits = []
                        store.endpoint = store.localEndpoint; store.token = store.localToken; store.offline = false
                        store.items = []; store.messages = []; store.checkIn = nil; store.currentConversation = nil
                        Task { try? await store.load(); await store.loadCompanion() }
                        notice = "Using this Mac's standalone data. Any queued shared edits remain saved separately for reconnection."
                    }.disabled(store.syncing)
                } else {
                    Text("Use this Mac as the shared home for your conversations, memories, diaries, TaskDock snapshots and local model. Paired laptops can save offline edits and synchronize when they return.").foregroundStyle(.secondary)
                    if let host {
                        Text(host.enabled ? "Hosting at \(host.address)" : "Hosting is off").font(.headline).textSelection(.enabled)
                        Text(host.availability).font(.callout).foregroundStyle(.secondary)
                        if let error = host.error { Text(error).foregroundStyle(.orange) }
                        HStack {
                            Button(host.enabled ? "Stop hosting" : "Host Juno on this Mac") { toggleHost(!host.enabled) }.disabled(busy)
                            Button("Create laptop pairing file…") { exportInvitation() }.disabled(busy || !host.enabled)
                        }
                    }
                    Text("On your laptop").font(.headline)
                    Button("Import work Mac pairing file…") { importInvitation() }.disabled(busy || host?.enabled == true)
                    Text("Pairing uses a 15-minute, one-use invitation and pins the work Mac's certificate. Each laptop has a separate revocable credential. No router forwarding or cloud service is configured.").font(.callout).foregroundStyle(.secondary)
                    if !devices.isEmpty {
                        Text("Devices with access").font(.headline)
                        ForEach(devices) { device in
                            HStack { Text(device.label); Spacer(); if device.current { Text("This app").foregroundStyle(.secondary) } else { Button("Revoke access") {
                                Task { do { _ = try await store.localRequest("/v1/host/devices/"+device.id,method:"DELETE"); await loadHost() } catch { notice = "Could not revoke this device." } }
                            } } }
                        }
                    }
                }
                if let notice { Text(notice).foregroundStyle(.secondary).textSelection(.enabled) }
                if busy { ProgressView() }
            }.padding(30).frame(maxWidth:.infinity,alignment:.leading)
        }.task { await loadHost() }
        .alert("Discard all queued edits?",isPresented:$discard) {
            Button("Keep edits",role:.cancel) {}
            Button("Discard queued edits",role:.destructive) {
                guard let copy = store.offlineCopy else { return }
                copy.archive.pending = []
                do { try copy.save(); store.pendingEdits = []; store.reconnectShared() }
                catch { notice = "The queue could not be changed." }
            }
        } message: { Text("This removes unsynchronized laptop changes. Export them first if you want a separate copy. Juno will then reload the work Mac's records.") }
    }
}


extension JunoStore {
    func startSharedMonitor() {
        connectionTask?.cancel()
        connectionTask = Task { [weak self] in
            var initial = true
            while !Task.isCancelled {
                if !initial { do { try await Task.sleep(nanoseconds:30_000_000_000) } catch { return } }
                initial = false
                guard let self, self.sharedProfile != nil, !self.token.isEmpty, !self.syncing, !self.chatSending, !self.checkBusy else { continue }
                self.syncing = true
                do {
                    if !self.offline && self.pendingEdits.isEmpty && Date().timeIntervalSince(self.offlineDate ?? .distantPast) < 300,
                       let endpoint = self.endpoint, let session = self.hostSession {
                        do { _ = try await self.wire("/v1/ping",endpoint:endpoint,token:self.token,session:session,method:"GET",body:nil) }
                        catch { if (error as? APIProblem)?.status == 401 { self.sharedRevoked() }; throw error }
                        self.syncing = false
                        continue
                    }
                    try await self.syncOfflineCopy()
                    self.syncIssue = nil
                    try await self.load()
                    if self.conversations.isEmpty || !self.modelConfigured { await self.loadCompanion() }
                    if let id = self.currentConversation { try? await self.loadMessages(id) }
                    if let check = self.checkIn, let data = try? self.offlineCopy?.read("/v1/check-ins/by-date/"+check.local_date), let fresh = try? JSONDecoder().decode(CheckInRecord.self,from:data) { self.checkIn = fresh }
                } catch {
                    if let issue = error as? APIProblem, issue.status != 0 { self.syncIssue = issue.message }
                    self.offline = true; self.status = self.sharedLabel
                }
                self.syncing = false
            }
        }
    }
}
