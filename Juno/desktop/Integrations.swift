import SwiftUI
import AppKit
import Security

struct EvidenceRow: Decodable, Identifiable {
    let id: String
    let title: String?; let item: String?; let location: String?; let problem: String?; let action: String?
    let category: String?; let source: String?; let evidence: String?; let detail: String?; let observed_at: String?
    let start: String?; let end: String?; let kind: String?; let notes: String?; let busy: Bool?; let all_day: Bool?
    let sender: String?; let status: String?; let due_date: String?; let unread: Bool?; let content_truncated: Bool?
    let worker: String?; let minutes: Double?; let amount_cents: Double?; let work_date: String?
    let date: String?; let start_date: String?; let end_date: String?; let start_time: String?; let end_time: String?
    let frequency: String?; let interval: Int?; let anchor_date: String?; let paused: Bool?
    var kindLabel: String { ["classroom_busy":"Classroom occupied", "staff_available":"Employee scheduled availability; capability unknown", "meeting":"Meeting", "calendar_event":"Calendar event", "event":"TaskDock event", "event_session":"TaskDock scheduled session", "event_recurrence":"TaskDock recurrence definition; not expanded", "note":"Notebook note", "time":"Reported work time", "expense":"Recorded expense; currency unknown", "message":"Message", "email":"Email", "task":"Provider task", "external_task":"Provider task", "sheet_row":"Smartsheet row"][kind ?? ""] ?? (kind ?? "Recorded evidence").replacingOccurrences(of:"_",with:" ").capitalized }
    var heading: String { title ?? item ?? "Recorded item" }
}
struct BusyDay: Decodable, Identifiable {
    let date: String; let busy_minutes: Double; let all_day_event: Bool
    var id: String { date }
}
struct EvidenceDetails: Decodable {
    let notice: String?; let start: String?; let end: String?; let timezone: String?; let generated_at: String?; let active: Bool?; let route: String?; let busy_days: [BusyDay]?
}
struct EvidenceSnapshot: Decodable, Identifiable {
    let id: String; let kind: String; let origin: String; let count: Int; let items: [EvidenceRow]
    let fetched_at: String; let stale: Bool; let error: String?; let details: EvidenceDetails
}
struct EvidenceState: Decodable { let items: [EvidenceSnapshot]; let notice: String }

// Separate Keychain namespace, fixed provider path, no token saved in preferences or snapshots.
enum BeaconKeychain {
    static var service: String { (Bundle.main.bundleIdentifier ?? "com.dmccoy.juno") + ".beacon" }
    static func query(_ origin:String) -> [String:Any] {
        [kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:service,kSecAttrAccount as String:origin]
    }
    static func read(_ origin:String) throws -> String? {
        var q = query(origin);q[kSecReturnData as String] = true;q[kSecMatchLimit as String] = kSecMatchLimitOne
        var value:CFTypeRef?;let code = SecItemCopyMatching(q as CFDictionary,&value)
        if code == errSecItemNotFound { return nil }
        guard code == errSecSuccess,let data = value as? Data,let text = String(data:data,encoding:.utf8) else { throw APIProblem(message:"Beacon's key could not be read from Keychain.",status:0) }
        return text
    }
    static func save(_ token:String,origin:String) throws {
        let q = query(origin);let data = Data(token.utf8)
        var code = SecItemUpdate(q as CFDictionary,[kSecValueData as String:data] as CFDictionary)
        if code == errSecItemNotFound {
            var item = q;item[kSecValueData as String] = data;item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly;item[kSecAttrSynchronizable as String] = false
            code = SecItemAdd(item as CFDictionary,nil)
        }
        guard code == errSecSuccess else { throw APIProblem(message:"Beacon was read, but its key could not be saved in Keychain. Enter it again for the next refresh.",status:0) }
    }
    static func forget(_ origin:String) throws {
        let code = SecItemDelete(query(origin) as CFDictionary)
        guard code == errSecSuccess || code == errSecItemNotFound else { throw APIProblem(message:"Beacon's saved key could not be removed.",status:0) }
    }
}

func integrationDay(_ offset:Int) -> String {
    let formatter = DateFormatter();formatter.dateFormat = "yyyy-MM-dd";formatter.timeZone = TimeZone(identifier:"America/Chicago")
    return formatter.string(from:Calendar.current.date(byAdding:.day,value:offset,to:Date())!)
}

struct IntegrationsWorkspace: View {
    @ObservedObject var store: JunoStore
    @State private var state: EvidenceState?
    @State private var kind = "calendar"
    @State private var start = integrationDay(0)
    @State private var end = integrationDay(30)
    @State private var zone = "America/Chicago"
    @State private var origin = UserDefaults.standard.string(forKey:"beaconOrigin") ?? "http://127.0.0.1:12108"
    @State private var token = ""
    @State private var search = ""
    @State private var busy = false
    @State private var notice: String?
    @State private var deleting: EvidenceSnapshot?
    func snapshot(_ kind:String) -> EvidenceSnapshot? { state?.items.first { $0.kind == kind } }
    func load() async {
        do { state = try JSONDecoder().decode(EvidenceState.self,from:await store.request("/v1/integrations")) }
        catch { notice = (error as? APIProblem)?.message ?? "The saved integration evidence could not be loaded." }
    }
    func importFile() {
        let panel = NSOpenPanel();panel.canChooseDirectories = false;panel.allowsMultipleSelection = false
        panel.message = kind == "calendar" ? "Choose a calendar .ics export. Juno reads this file without contacting its calendar service." : kind == "schedules" ? "Choose a semester schedule CSV using Juno's template." : "Choose the complete schema-1 Beacon alert-feed JSON."
        guard panel.runModal() == .OK, let url = panel.url else { return }
        busy = true
        Task {
            defer { busy = false }
            do {
                let size = try url.resourceValues(forKeys:[.fileSizeKey]).fileSize ?? 0
                guard size <= 8_000_000 else { throw APIProblem(message:"The selected file exceeds 8 MB. Export a smaller file.",status:0) }
                let content = try String(contentsOf:url,encoding:.utf8)
                var body:[String:Any] = ["kind":kind,"content":content,"label":url.lastPathComponent,"start":start,"end":end,"timezone":zone]
                if let previous = snapshot(kind) { body["expected_id"] = previous.id }
                _ = try await store.request("/v1/integrations/import",method:"POST",body:body)
                notice = "Imported a dated copy. Reimport when the source changes; Juno does not update the original."
            } catch { notice = (error as? APIProblem)?.message ?? "The file could not be read. The previous import has been retained." }
            await load()
        }
    }
    func refreshBeacon() {
        busy = true
        Task {
            defer { busy = false }
            do {
                let key = token.isEmpty ? try BeaconKeychain.read(origin) ?? "" : token
                var body:[String:Any] = ["base_url":origin,"token":key]
                if let previous = snapshot("beacon") { body["expected_id"] = previous.id }
                _ = try await store.request("/v1/integrations/beacon/refresh",method:"POST",body:body)
                try BeaconKeychain.save(key,origin:origin);token = "";UserDefaults.standard.set(origin,forKey:"beaconOrigin")
                notice = "Read Beacon's complete alert feed. No inventory records or tasks were changed."
            } catch { notice = (error as? APIProblem)?.message ?? "Beacon could not be refreshed. The previous snapshot has been retained." }
            await load()
        }
    }
    func template() {
        let panel = NSSavePanel();panel.nameFieldStringValue = "Juno-semester-schedule.csv"
        guard panel.runModal() == .OK,let url = panel.url else { return }
        let content = "kind,name,location,start_date,end_date,days,start_time,end_time,timezone\nclassroom_busy,Fictional animation class,Example Room,2026-11-02,2026-12-18,MO|WE,09:00,10:30,America/Chicago\nstaff_available,Fictional employee,Example Lab,2026-11-02,2026-12-18,TU|TH,10:00,14:00,America/Chicago\nmeeting,Fictional planning meeting,Example Office,2026-11-02,2026-12-18,FR,10:00,11:00,America/Chicago\n"
        do { try Data(content.utf8).write(to:url,options:.atomic);notice = "Template saved. Replace all fictional rows with your actual semester schedule before importing." }
        catch { notice = "The template could not be saved." }
    }
    func timestamp(_ value:String) -> String {
        providerDate(value)?.formatted(date:.abbreviated,time:.shortened) ?? value
    }
    var body: some View {
        ScrollView {
            LazyVStack(alignment:.leading,spacing:16) {
                Text("Work evidence").font(.title2.bold())
                Text("Connected programs, Beacon observations and manually imported schedules help Juno understand your day. Configure direct readers and TaskDock sharing in Connections. TaskDock remains your task hub.").foregroundStyle(.secondary)
                if store.sharedProfile == nil {
                    VStack(alignment:.leading,spacing:8) {
                        Text("Import a dated copy").font(.headline)
                        VStack(alignment:.leading,spacing:12) {
                            Picker("Source",selection:$kind) { Text("Calendar (.ics)").tag("calendar");Text("Semester schedule (.csv)").tag("schedules");Text("Beacon alerts (.json)").tag("beacon") }.pickerStyle(.segmented)
                            if kind != "beacon" {
                                HStack {
                                    VStack(alignment:.leading) { Text("From (YYYY-MM-DD)").font(.caption);TextField("2026-10-29",text:$start) }
                                    VStack(alignment:.leading) { Text("Until, exclusive (YYYY-MM-DD)").font(.caption);TextField("2026-11-29",text:$end) }
                                }
                                TextField("Timezone, e.g. America/Chicago",text:$zone)
                                Text("Import at most 366 days. This timezone interprets floating calendar times and controls day summaries. CSV rows each carry their own timezone; their semester end dates are inclusive.").font(.caption).foregroundStyle(.secondary)
                            }
                            HStack { Button("Choose file and import…") { importFile() };Button("Save schedule CSV template…") { template() } }.disabled(busy)
                            Text("Import replaces the previous copy of that source. A rejected file leaves the last good copy visible with an error. No links in imported content are fetched.").font(.caption).foregroundStyle(.secondary)
                        }.padding(8)
                    }
                    VStack(alignment:.leading,spacing:8) {
                        Text("Beacon on this work Mac").font(.headline)
                        VStack(alignment:.leading,spacing:10) {
                            TextField("Loopback API address",text:$origin)
                            SecureField("Dedicated read-only integration key (blank uses Keychain)",text:$token)
                            HStack {
                                Button("Read Beacon alerts") { refreshBeacon() }.disabled(busy)
                                Button("Forget saved key") { do { try BeaconKeychain.forget(origin);token = "";notice = "Saved Beacon key removed from this Mac. Imported evidence remains until you remove it." } catch { notice = "The saved key could not be removed." } }.disabled(busy)
                            }
                            Text("Use the dedicated Beacon integration key. Juno reads only /api/alerts on loopback and stores the key in this Mac's Keychain. Refresh is manual.").font(.caption).foregroundStyle(.secondary)
                        }.padding(8)
                    }
                } else {
                    Text("This laptop reads the work Mac's saved evidence, including while offline. Import or refresh sources on the work Mac.").foregroundStyle(.secondary)
                }
                if busy { ProgressView() }
                if let notice { Text(notice).foregroundStyle(.orange).textSelection(.enabled) }
                if let state {
                    Text(state.notice).font(.caption).foregroundStyle(.secondary)
                    if state.items.isEmpty { Text("No sources imported yet. Start with a calendar export or your semester schedule.").padding(.vertical) }
                    TextField("Filter saved items",text:$search)
                    ForEach(state.items) { source in
                        VStack(alignment:.leading,spacing:8) {
                            Divider()
                            VStack(alignment:.leading,spacing:10) {
                                HStack {
                                    Text(WorkProvider(rawValue:source.kind)?.label ?? source.kind.replacingOccurrences(of:"_",with:" ").capitalized).font(.headline);Text("\(source.count) records").foregroundStyle(.secondary)
                                    Spacer()
                                    if store.sharedProfile == nil { Button("Remove copy…",role:.destructive) { deleting = source }.disabled(busy) }
                                }
                                Text(source.origin + " · Imported " + timestamp(source.fetched_at)).font(.caption).textSelection(.enabled)
                                if let generated = source.details.generated_at { Text("Provider generated " + timestamp(generated)).font(.caption) }
                                if let start = source.details.start,let end = source.details.end { Text("Coverage: \(start) until \(end) (exclusive) · \(source.details.timezone ?? "")").font(.caption) }
                                if let error = source.error { Text("Last attempt failed: " + error).foregroundStyle(.orange) }
                                if source.details.active == false { Text("Disconnected — retained for review and excluded from new AI context.").font(.caption).foregroundStyle(.orange) }
                                if source.stale { Text("Dated copy — verify current conditions before acting.").font(.caption).foregroundStyle(.orange) }
                                Text(source.details.notice ?? "").font(.caption).foregroundStyle(.secondary)
                                if let days = source.details.busy_days, !days.isEmpty {
                                    DisclosureGroup("Recorded busy time by day (overlaps counted once)") {
                                        Text("This is recorded calendar/meeting time, not a calculation of your free work hours. Staff and room intervals stay separate.").font(.caption)
                                        ForEach(days) { day in HStack { Text(day.date);Text(String(format:"%.1f hours",day.busy_minutes / 60));if day.all_day_event { Text("Includes all-day event").foregroundStyle(.secondary) } }.font(.caption) }
                                    }
                                }
                                let filtered = source.items.filter { search.isEmpty || [$0.heading,$0.location ?? "",$0.problem ?? "",$0.notes ?? "",$0.sender ?? "",$0.worker ?? ""].joined(separator:" ").localizedCaseInsensitiveContains(search) }
                                ForEach(Array(filtered.prefix(100))) { row in
                                    DisclosureGroup(row.heading + (row.location?.isEmpty == false ? " · " + row.location! : "")) {
                                        VStack(alignment:.leading,spacing:6) {
                                            Text(row.kindLabel).font(.caption)
                                            if let sender = row.sender { Text("From: " + sender) }
                                            if row.unread == true { Text("Unread at last refresh; Juno did not mark it read.").font(.caption) }
                                            if let status = row.status { Text("Status: " + status) }
                                            if let due = row.due_date { Text("Due date: " + due + " (not scheduled work time)") }
                                            if let worker = row.worker { Text("Reported worker: " + worker) }
                                            if let minutes = row.minutes { Text(String(format:"Reported time: %.0f minutes",minutes)) }
                                            if let amount = row.amount_cents { Text(String(format:"Recorded amount: %.2f (currency unknown)",amount / 100)) }
                                            if let day = row.work_date ?? row.date ?? row.start_date { Text("Recorded date: " + day + (row.end_date.map { " through " + $0 } ?? "")) }
                                            if let time = row.start_time { Text(time + (row.end_time.map { " – " + $0 } ?? "")) }
                                            if let frequency = row.frequency { Text("Recurrence: " + frequency + " · interval " + String(row.interval ?? 1) + " · anchor " + (row.anchor_date ?? "unknown") + (row.paused == true ? " · paused" : "")) }
                                            if row.content_truncated == true { Text("Excerpt shortened. Consult the original for full context.").foregroundStyle(.orange) }
                                            if let start = row.start,let end = row.end { Text(timestamp(start) + " – " + timestamp(end)) }
                                            if row.all_day == true { Text("All-day event") }
                                            if row.busy == false { Text("Does not block your personal calendar") }
                                            if let category = row.category { Text(category + " · " + (row.evidence ?? "Unknown evidence") + " · " + (row.source ?? "Unknown source")).font(.caption) }
                                            if let problem = row.problem { Text(problem) }
                                            if let action = row.action { Text(action) }
                                            if let observed = row.observed_at,!observed.isEmpty { Text("Observed " + timestamp(observed)).font(.caption) }
                                            if let detail = row.detail,!detail.isEmpty { Text(detail) }
                                            if let notes = row.notes,!notes.isEmpty { Text(notes) }
                                        }.textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading).padding(8)
                                    }
                                }
                                if filtered.count>100 { Text("Showing the first 100 matches. Filter to narrow the list.").font(.caption) }
                            }.padding(8).frame(maxWidth:.infinity,alignment:.leading)
                        }
                    }
                }
            }.padding(26).frame(maxWidth:.infinity,alignment:.leading)
        }.task { await load() }
        .alert("Remove this imported copy?",isPresented:Binding(get:{ deleting != nil },set:{ if !$0 { deleting = nil } })) {
            Button("Cancel",role:.cancel) { deleting = nil }
            Button("Remove copy",role:.destructive) {
                guard let source = deleting else { return };deleting = nil;busy = true
                Task {
                    defer { busy = false }
                    do { _ = try await store.request("/v1/integrations/"+source.kind+"?expected_id="+source.id,method:"DELETE");notice = "Imported copy removed. The provider and TaskDock were not changed." }
                    catch { notice = (error as? APIProblem)?.message ?? "The copy could not be removed." }
                    await load()
                }
            }
        } message: { Text("This removes Juno's saved source text and invalidates replies based on it. The original file/provider stays available for a future import. Paired laptops receive the removal when they reconnect.") }
    }
}
