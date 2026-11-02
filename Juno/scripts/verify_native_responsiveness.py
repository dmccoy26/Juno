"""Prove the exact credential bridge permits main-actor progress during a blocked read."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'desktop/Juno.swift').read_text()
bridge='func credentialWork'+source.split('func credentialWork',1)[1].split('@MainActor',1)[0]
check=r'''
@main struct Test {
    @MainActor static func main() async throws {
        let gate=DispatchSemaphore(value:0)
        let operation=Task { try await credentialWork {
            precondition(!Thread.isMainThread,"Credential work blocked the UI thread")
            gate.wait();return 42
        } }
        try await Task.sleep(nanoseconds:80_000_000)
        // This continuation can run while the credential operation is still blocked.
        gate.signal()
        let value=try await operation.value
        precondition(value==42)
        print("PASS native credential wait leaves main actor responsive and preserves its result")
    }
}
'''
with tempfile.TemporaryDirectory(prefix='juno-credential-') as tmp:
    folder=Path(tmp);(folder/'check.swift').write_text('import Foundation\n'+bridge+check)
    subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5',str(folder/'check.swift'),'-o',str(folder/'check')],check=True)
    subprocess.run([str(folder/'check')],check=True,timeout=5)
