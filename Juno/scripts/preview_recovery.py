"""Build a disposable native UI using fictional conflict data; never opens real Juno state."""
from pathlib import Path
import plistlib, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
folder=Path(tempfile.mkdtemp(prefix='juno-recovery-ui-'))
app=folder/'Juno Recovery QA.app'; (app/'Contents/MacOS').mkdir(parents=True)
(app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.dmccoy.juno.recovery.qa','CFBundleName':'Juno Recovery QA','CFBundleExecutable':'Juno','CFBundlePackageType':'APPL','LSMinimumSystemVersion':'13.5'}))
(folder/'Juno.swift').write_text((ROOT/'desktop/Juno.swift').read_text().split('@main\nstruct JunoApplication',1)[0])
(folder/'QA.swift').write_text(r'''
import SwiftUI
@main struct RecoveryQA: App {
    @StateObject var store = JunoStore()
    var body: some Scene {
        WindowGroup("Juno Recovery QA · Fictional data") {
            ComputersWorkspace(store:store).frame(width:950,height:800).task {
                do {
                    let profile = SharedProfile(address:"https://fictional.local:8443",certificate_sha256:String(repeating:"b",count:64),owner_id:"qa-owner",device_id:"qa-device")
                    let copy = try OfflineCopy(profile:profile)
                    copy.archive = OfflineArchive(savedAt:.now,pages:[:]);try copy.save()
                    _ = try copy.perform("/v1/memories",method:"POST",body:["text":"Fictional projector repair is waiting for a replacement cable.","source":"synthetic","confidence":"confirmed"])
                    try copy.block(copy.archive.pending[0],status:409,message:"The work Mac record changed. Review both versions before continuing.")
                    store.sharedProfile = profile;store.offlineCopy = copy;store.pendingEdits = copy.archive.pending;store.offlineDate = .now
                } catch { fatalError("QA fixture failed: \(error)") }
            }
        }
    }
}
''')
subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-target','arm64-apple-macosx13.5',str(folder/'Juno.swift'),*[str(ROOT/'desktop'/n) for n in ['Companion.swift','TaskDock.swift','Shared.swift','Integrations.swift','Connections.swift','Planning.swift']],str(folder/'QA.swift'),'-o',str(app/'Contents/MacOS/Juno')],check=True)
print(app)
