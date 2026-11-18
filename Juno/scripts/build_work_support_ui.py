"""Build the real work-bookmark views around a disposable fixture-only store."""
from pathlib import Path
import plistlib,subprocess
root=Path(__file__).resolve().parents[1]
folder=root/'.local/mission17-ui';folder.mkdir(exist_ok=True)
app=folder/'Work Bookmark Check.app';contents=app/'Contents';(contents/'MacOS').mkdir(parents=True,exist_ok=True)
(folder/'Juno.swift').write_text((root/'desktop/Juno.swift').read_text().split('@main\nstruct JunoApplication',1)[0])
fixture='''
import SwiftUI
import AppKit
@MainActor final class WorkFixtureDelegate:NSObject,NSApplicationDelegate {
 var window:NSWindow!
 let store=JunoStore()
 func applicationDidFinishLaunching(_ notification:Notification) {
  let bytes=try! Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[0]).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("fixture.json"))
  let setup=try! JSONSerialization.jsonObject(with:bytes) as! [String:String]
  store.endpoint=URL(string:setup["url"]!)!;store.token=setup["token"]!;store.connected=true;store.meeting=false
  window=NSWindow(contentRect:NSRect(x:100,y:100,width:780,height:640),styleMask:[.titled,.closable,.resizable,.miniaturizable],backing:.buffered,defer:false)
  window.title="Synthetic Work Bookmark Check"
  window.contentView=NSHostingView(rootView:WorkFixtureView(store:store))
  window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
 }
 func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool { true }
}
struct WorkFixtureView:View {
 @ObservedObject var store:JunoStore
 var body:some View {
  VStack(alignment:.leading) {
   Text("Synthetic Mission 17 workspace · no live tasks or pairing").font(.caption)
   HStack { Toggle("Meeting mode",isOn:$store.meeting);Toggle("Simulated offline view",isOn:$store.offline) }
   ScrollView { WorkSupportPanel(store:store,snapshot:nil,planning:nil).padding() }
  }.padding()
 }
}
@main struct WorkFixtureApplication {
 @MainActor static func main() {
  let app=NSApplication.shared;app.setActivationPolicy(.regular)
  let delegate=WorkFixtureDelegate();app.delegate=delegate
  withExtendedLifetime(delegate) { app.run() }
 }
}
'''
(folder/'Fixture.swift').write_text(fixture)
files=[folder/'Juno.swift']+[root/'desktop'/name for name in ['Companion.swift','TaskDock.swift','Shared.swift','Integrations.swift','Connections.swift','Planning.swift','Schedules.swift','Workers.swift','Routines.swift','WorkSupport.swift']]+[folder/'Fixture.swift']
subprocess.run(['xcrun','swiftc','-parse-as-library','-swift-version','5','-target','arm64-apple-macosx13.5',*map(str,files),'-o',str(contents/'MacOS/WorkFixture')],check=True)
(contents/'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'WorkFixture','CFBundleIdentifier':'local.juno.synthetic.work-bookmark','CFBundleName':'Work Bookmark Check','CFBundlePackageType':'APPL','LSMinimumSystemVersion':'13.5','NSAppTransportSecurity':{'NSAllowsLocalNetworking':True}}))
subprocess.run(['codesign','--force','--sign','-',str(app)],check=True)
print('Built fixture-only native work-bookmark app.')
