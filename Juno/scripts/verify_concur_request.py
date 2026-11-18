"""Verify native helper request periods without opening Concur or starting a job."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'desktop/Routines.swift').read_text()
command = source[source.index('enum ConcurReconciliationPeriod:'):source.index('    @MainActor\n    func open()')] + '}\n'
planning = (ROOT / 'desktop/Planning.swift').read_text()
schedule = planning[planning.index('struct DeanMeetingSchedule {'):planning.index('struct ChairPreparationSchedule {')]
checks = '''
func date(_ s:String)->Date { ISO8601DateFormatter().date(from:s)! }
func parts(_ p:ConcurReconciliationPeriod,_ d:String)->[String:String] {
    Dictionary(uniqueKeysWithValues:URLComponents(url:p.requestURL(on:date(d))!,resolvingAgainstBaseURL:false)!.queryItems!.map{($0.name,$0.value!)})
}
let week = parts(.week,"2026-11-18T16:00:00Z")
precondition(week["start"] == "2026-11-16" && week["end"] == "2026-11-22")
let leap = parts(.month,"2028-02-18T16:00:00Z")
precondition(leap["start"] == "2028-02-01" && leap["end"] == "2028-02-29")
precondition(ConcurReconciliationPeriod.command(" /CONCUR WEEK ") == .week)
precondition(ConcurReconciliationPeriod.command("/concur pay") == nil)
let url = ConcurReconciliationPeriod.month.requestURL()!
precondition(url.scheme == "concur-helper" && url.host == "reconcile")
precondition(Set(parts(.month,"2026-12-31T18:00:00Z").keys) == ["id", "period", "start", "end"])
print("PASS helper request URL period boundaries and recognized commands; no live job started")
'''
with tempfile.TemporaryDirectory(prefix='juno-helper-request-') as temp:
    folder = Path(temp)
    (folder / 'main.swift').write_text('import Foundation\n' + schedule + command + checks)
    subprocess.run(['xcrun', 'swiftc', str(folder / 'main.swift'), '-o', str(folder / 'check')], check=True)
    subprocess.run([str(folder / 'check')], check=True)
