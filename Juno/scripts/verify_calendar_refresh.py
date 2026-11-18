"""Exercise the production native refresh scheduler with private isolated preferences and fake transport/vault."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'desktop/Connections.swift').read_text()
models=s[s.index('struct SavedConnection:'):s.index('struct ProviderVault {')]
method=s[s.index('    func refreshWorkCalendarAutomatically('):s.index('    func refreshCompletionArchive(')]
# The real scheduler uses standard preferences; this executable substitutes an isolated suite.
method=method.replace('let prefs = UserDefaults.standard','let prefs = testPreferences')
header=r'''
import Foundation
let testPreferences = UserDefaults(suiteName: "juno.test.calendar.\(UUID().uuidString)")!
func integrationDay(_ n:Int)->String { "2026-11-18" }
func providerDate(_ s:String)->Date? { ISO8601DateFormatter().date(from:s) }
func sourceReadDate(_ s:String)->String { s }
enum WorkProvider { case google_calendar }
struct APIProblem: Error { var message:String; var status:Int; var retryAfter:Int? = nil }
struct Detail:Decodable { var active:Bool?; var tombstone:Bool? }
struct Snapshot:Decodable { var id:String; var kind:String; var details:Detail }
struct ConnectionSnapshots:Decodable { var items:[Snapshot] }
struct OAuthTokens:Decodable { var access_token:String; var refresh_token:String?; var expires_at:String; var scope:String }
struct ProviderRefreshReply:Decodable { var review_required:Bool }
@MainActor enum FakeVault { static var value:SavedConnection?; static var saves = 0 }
struct ProviderVault {
    @MainActor func readAsync(_ provider:WorkProvider) async throws -> SavedConnection? { FakeVault.value }
    @MainActor func saveAsync(_ v:SavedConnection,provider:WorkProvider) async throws { FakeVault.value=v;FakeVault.saves += 1 }
}
@MainActor final class JunoStore {
    var connected=true;var sharedProfile:String?;var offline=false;var calendarRefreshInProgress=false;var calendarSettingsOpen=false
    var calendarRefreshStatus="";var calendarCopyRevision=0
    var calls:[String]=[];var bodies:[[String:Any]]=[];var mode="success";var renewed=false
    func localRequest(_ path:String,method:String="GET",body:[String:Any]=[:]) async throws -> Data {
        calls.append(path);bodies.append(body)
        if path.hasSuffix("/state") { return Data(#"{"items":[{"id":"retained-copy","kind":"google_calendar","details":{"active":true}}]}"#.utf8) }
        if path.hasSuffix("/renew") {
            renewed=true
            if mode=="disconnect-renew" { FakeVault.value=nil }
            return Data(#"{"access_token":"new-synthetic-token","refresh_token":"rotated-synthetic-token","expires_at":"2030-01-01T00:00:00Z","scope":"read"}"#.utf8)
        }
        if mode=="401-once" && !renewed { throw APIProblem(message:"Synthetic expired token",status:401) }
        if mode=="failure" { throw APIProblem(message:"Private diagnostic must not appear",status:502) }
        if mode=="rate" { throw APIProblem(message:"Synthetic throttle",status:429,retryAfter:3600) }
        if mode=="denied" { throw APIProblem(message:"Synthetic denied",status:403) }
        return Data((mode=="account-change" ? #"{"review_required":true}"# : #"{"review_required":false}"#).utf8)
    }
'''
checks=r'''
}
@main struct Verify {
    @MainActor static func main() async throws {
        let instant=providerDate("2026-11-18T20:00:00Z")!
        func reset(_ mode:String="success")->JunoStore {
            for k in [CalendarRefreshPolicy.enabledKey,CalendarRefreshPolicy.approvalKey,CalendarRefreshPolicy.attemptKey,CalendarRefreshPolicy.retryKey,CalendarRefreshPolicy.statusKey] { testPreferences.removeObject(forKey:k) }
            var c=SavedConnection();c.accountID="fictional-account";c.clientID="fictional-client";c.resources=["primary"];c.accessToken="synthetic-token";c.refreshToken="synthetic-refresh";c.expiry=instant.addingTimeInterval(3600)
            FakeVault.value=c;FakeVault.saves=0
            testPreferences.set(true,forKey:CalendarRefreshPolicy.enabledKey);testPreferences.set(CalendarRefreshPolicy.selection(c),forKey:CalendarRefreshPolicy.approvalKey)
            let store=JunoStore();store.mode=mode;return store
        }
        let range=CalendarRefreshPolicy.window(now:instant);precondition(range.0=="2026-11-11" && range.1=="2027-02-17")
        let spring=CalendarRefreshPolicy.window(now:providerDate("2026-03-09T04:30:00Z")!);precondition(spring.0=="2026-03-01" && spring.1=="2026-06-07")
        precondition(!CalendarRefreshPolicy.due(now:instant,attempt:instant.addingTimeInterval(-899),retry:nil))
        precondition(CalendarRefreshPolicy.due(now:instant,attempt:instant.addingTimeInterval(-900),retry:nil))
        var store=reset();await store.refreshWorkCalendarAutomatically(now:instant)
        precondition(store.calls.count==2 && store.calendarCopyRevision==1)
        let body=store.bodies.last!;precondition(body["expected_id"] as? String=="retained-copy")
        let selection=body["selection"] as! [String:Any];precondition(selection["resources"] as? [String]==["primary"] && selection["busy_only"] as? Bool==true && selection["end"] as? String==range.1)
        await store.refreshWorkCalendarAutomatically(now:instant.addingTimeInterval(100));precondition(store.calls.count==2)
        let restarted=JunoStore();await restarted.refreshWorkCalendarAutomatically(now:instant.addingTimeInterval(100));precondition(restarted.calls.isEmpty)
        await restarted.refreshWorkCalendarAutomatically(now:instant.addingTimeInterval(900));precondition(restarted.calls.count==2)
        for mode in ["failure","rate","denied","account-change"] {
            store=reset(mode);await store.refreshWorkCalendarAutomatically(now:instant)
            precondition(!store.calendarRefreshStatus.contains("Private diagnostic"))
            if mode=="denied" || mode=="account-change" { precondition(!testPreferences.bool(forKey:CalendarRefreshPolicy.enabledKey)) }
            else { precondition(testPreferences.object(forKey:CalendarRefreshPolicy.retryKey) is Date);let count=store.calls.count;await store.refreshWorkCalendarAutomatically(now:instant.addingTimeInterval(10));precondition(store.calls.count==count) }
        }
        store=reset("401-once");await store.refreshWorkCalendarAutomatically(now:instant);precondition(store.renewed && FakeVault.saves==1 && store.calendarCopyRevision==1)
        store=reset("disconnect-renew");FakeVault.value!.expiry=instant.addingTimeInterval(-1);await store.refreshWorkCalendarAutomatically(now:instant);precondition(FakeVault.value==nil && FakeVault.saves==0 && store.calendarCopyRevision==0)
        store=reset();FakeVault.value!.resources=["different"];await store.refreshWorkCalendarAutomatically(now:instant);precondition(store.calls.isEmpty && !testPreferences.bool(forKey:CalendarRefreshPolicy.enabledKey))
        for mode in ["remote","offline","settings","overlap","disabled"] {
            store=reset();if mode=="remote" { store.sharedProfile="air" };if mode=="offline" { store.offline=true };if mode=="settings" { store.calendarSettingsOpen=true };if mode=="overlap" { store.calendarRefreshInProgress=true };if mode=="disabled" { testPreferences.set(false,forKey:CalendarRefreshPolicy.enabledKey) }
            await store.refreshWorkCalendarAutomatically(now:instant);precondition(store.calls.isEmpty)
        }
        print("PASS actual native scheduler: rolling Central/DST dates, restart cadence, scope, privacy, renewal, disconnect fencing, retry/backoff, account-change and remote/offline/overlap gates")
    }
}
'''
with tempfile.TemporaryDirectory(prefix='juno-calendar-refresh-') as t:
 p=Path(t);(p/'main.swift').write_text(header+models+method+checks)
 # Models and policy must be outside the fake store declaration.
 text=(p/'main.swift').read_text();text=text.replace('@MainActor final class JunoStore {',models+'\n@MainActor final class JunoStore {',1);text=text.replace(models+method,method,1);(p/'main.swift').write_text(text)
 subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5',str(p/'main.swift'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
