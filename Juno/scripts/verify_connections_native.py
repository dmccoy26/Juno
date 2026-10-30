"""Actual native Keychain persistence and OAuth URL checks in a unique disposable namespace."""
import subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEST=r'''
let service = CommandLine.arguments[1]
let vault = ProviderVault(service:service)
if CommandLine.arguments.count>2 {
    defer { try? vault.forget(.gmail) }
    let saved = try vault.read(.gmail)!
    precondition(saved.accessToken == "synthetic-access" && saved.refreshToken == "synthetic-rotated-refresh")
    precondition(saved.accountID == "synthetic-account" && saved.resources == ["primary"])
    let other = try vault.read(.slack);precondition(other == nil)
    print("PASS Keychain connection survives a separate native process and remains provider isolated")
} else {
    defer { try? vault.forget(.gmail) }
    var saved = SavedConnection();saved.accessToken = "synthetic-access";saved.refreshToken = "synthetic-initial-refresh";saved.accountID = "synthetic-account";saved.resources = ["primary"]
    try vault.save(saved,provider:.gmail);saved.refreshToken = "synthetic-rotated-refresh";try vault.save(saved,provider:.gmail)
    var q = vault.query(.gmail);q[kSecReturnAttributes as String] = true
    var attrs:CFTypeRef?;precondition(SecItemCopyMatching(q as CFDictionary,&attrs) == errSecSuccess)
    let values = attrs as! [String:Any];if let accessibility = values[kSecAttrAccessible as String] as? String { precondition(accessibility == kSecAttrAccessibleWhenUnlockedThisDeviceOnly as String) }
    precondition((values[kSecAttrSynchronizable as String] as? Bool ?? false) == false)
    let child = Process();child.executableURL = URL(fileURLWithPath:CommandLine.arguments[0]);child.arguments = [service,"read"];try child.run();child.waitUntilExit();precondition(child.terminationStatus == 0)
    let removed = try vault.read(.gmail);precondition(removed == nil)
    let challenge = String(repeating:"A",count:43)
    let base = "https://accounts.google.com/o/oauth2/v2/auth?state=synthetic-flow&client_id=synthetic-client&response_type=code&code_challenge_method=S256&code_challenge=" + challenge + "&redirect_uri=http%3A%2F%2F127.0.0.1%3A18123%2Fv1%2Fproviders%2Foauth%2Fcallback%2Fgoogle"
    _ = try validatedAuthorization(base,provider:.gmail,flow:"synthetic-flow",client:"synthetic-client")
    for bad in [base.replacingOccurrences(of:"accounts.google.com",with:"example.invalid"),base+"&state=other",base.replacingOccurrences(of:"127.0.0.1",with:"example.invalid"),base.replacingOccurrences(of:"S256",with:"plain"),base.replacingOccurrences(of:challenge,with:"short")] {
        do { _ = try validatedAuthorization(bad,provider:.gmail,flow:"synthetic-flow",client:"synthetic-client");fatalError("Invalid authorization accepted") } catch is APIProblem {}
    }
    let ms = base.replacingOccurrences(of:"https://accounts.google.com/o/oauth2/v2/auth",with:"https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize").replacingOccurrences(of:"127.0.0.1",with:"localhost").replacingOccurrences(of:"callback%2Fgoogle",with:"callback%2Fmicrosoft")
    _ = try validatedAuthorization(ms,provider:.outlook_calendar,flow:"synthetic-flow",client:"synthetic-client")
    print("PASS fixed browser destinations, unique state/client, private callback, S256 challenge and atomic token replacement")
}
'''
def main():
    import uuid
    source=(ROOT/'desktop/Connections.swift').read_text().split('struct ConnectionsWorkspace: View',1)[0]
    with tempfile.TemporaryDirectory(prefix='juno-connections-native-') as folder:
        path=Path(folder)
        stub='\nstruct APIProblem:Error { let message:String;let status:Int }\nstruct EvidenceDetails:Decodable {}\nfunc integrationDay(_ offset:Int)->String { "2026-10-29" }\n'
        (path/'main.swift').write_text(source+stub+TEST)
        subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
        subprocess.run([str(path/'check'),'com.dmccoy.juno.synthetic-connection-check.'+str(uuid.uuid4())],check=True,timeout=30)
if __name__=='__main__':main()
