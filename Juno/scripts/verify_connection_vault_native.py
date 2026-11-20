"""Exercise the actual connection-vault code using only disposable Keychain items."""
from pathlib import Path
import subprocess,tempfile,uuid
ROOT=Path(__file__).resolve().parents[1]
TEST=r'''
struct APIProblem: Error { let message: String; let status: Int }
let prefix = CommandLine.arguments[1]
let task = prefix + ".taskdock", beacon = prefix + ".beacon"
let data = Data("synthetic-only".utf8)
if CommandLine.arguments.count > 2 {
    precondition(try ConnectionSecrets.read(service: task, account: "read", legacy: { fatalError("Legacy unexpectedly used") }) == data)
    print("PASS vault survives a separate process")
} else {
    defer { SecItemDelete(ConnectionSecrets.query(task) as CFDictionary) }
    var reads = 0
    for _ in 0..<10 {
        let value = try ConnectionSecrets.read(service: task, account: "read") { reads += 1; return data }
        precondition(value == data)
    }
    precondition(reads == 1)
    let group = DispatchGroup()
    for index in 0..<20 {
        group.enter()
        DispatchQueue.global().async {
            defer { group.leave() }
            try! ConnectionSecrets.save(Data("value-\(index)".utf8), service: task, account: "parallel-\(index)")
        }
    }
    group.wait()
    for index in 0..<20 {
        precondition(tryRead(service: task, account: "parallel-\(index)", legacy: { nil }) == Data("value-\(index)".utf8))
    }
    try ConnectionSecrets.save(Data("separate-write".utf8), service: task, account: "managed-write")
    try ConnectionSecrets.save(Data("separate-beacon".utf8), service: beacon, account: "read")
    precondition(try ConnectionSecrets.read(service: task, account: "read", legacy: { nil }) == data)
    precondition(try ConnectionSecrets.read(service: beacon, account: "read", legacy: { nil }) != data)
    let child=Process();child.executableURL=URL(fileURLWithPath:CommandLine.arguments[0]);child.arguments=[prefix,"read"];try child.run();child.waitUntilExit();precondition(child.terminationStatus == 0)
    var q=ConnectionSecrets.query(task);q[kSecReturnAttributes as String]=true
    var attributes:CFTypeRef?;precondition(SecItemCopyMatching(q as CFDictionary,&attributes)==errSecSuccess)
    let attrs=attributes as! [String:Any]
    if let accessibility = attrs[kSecAttrAccessible as String] as? String { precondition(accessibility == kSecAttrAccessibleWhenUnlockedThisDeviceOnly as String) }
    precondition(!(attrs[kSecAttrSynchronizable as String] as? Bool ?? false))
    try ConnectionSecrets.save(nil, service: task, account: "read")
    ConnectionSecrets.clearCache()
    precondition(try ConnectionSecrets.read(service: task, account: "read", legacy: { fatalError("Forgotten legacy credential resurrected") }) == nil)
    do { _ = try ConnectionSecrets.read(service: task, account: "denied", legacy: { throw APIProblem(message:"denied",status:0) }); fatalError("Denial swallowed") } catch is APIProblem {}
    precondition(try ConnectionSecrets.read(service: task, account: "denied", legacy: { data }) == data)
    let other=prefix+".other"
    defer { SecItemDelete(ConnectionSecrets.query(other) as CFDictionary) }
    var corrupt=ConnectionSecrets.query(other);corrupt[kSecValueData as String]=Data("invalid vault".utf8)
    precondition(SecItemAdd(corrupt as CFDictionary,nil)==errSecSuccess)
    do { _=try ConnectionSecrets.read(service:other,account:"read",legacy:{fatalError("Corrupt vault fell back")});fatalError("Corruption accepted") } catch is APIProblem {}
    print("PASS one-vault migration, cache reuse, separate scopes, persistence, lock-cache reset, forget tombstones, denial retry and corruption protection")
}
'''
def main():
    source=(ROOT/'desktop/Connections.swift').read_text()
    source='import Foundation\nimport AppKit\nimport Security\n'+source[source.index('enum ConnectionSecrets {'):source.index('struct ProviderVault {')]
    # Swift's precondition is nonthrowing; evaluate the throwing expression first.
    test=TEST.replace('precondition(try ConnectionSecrets.read(', 'precondition(tryRead(')
    helper='\nfunc tryRead(service:String,account:String,legacy:() throws -> Data?) -> Data? { try! ConnectionSecrets.read(service:service,account:account,legacy:legacy) }\n'
    with tempfile.TemporaryDirectory(prefix='juno-vault-native-') as folder:
        path=Path(folder);(path/'main.swift').write_text(source+helper+test)
        subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
        subprocess.run([str(path/'check'),'com.dmccoy.juno.synthetic-vault.'+str(uuid.uuid4())],check=True,timeout=35)
if __name__=='__main__':main()
