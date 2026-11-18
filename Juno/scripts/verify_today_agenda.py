"""Verify actual native agenda day boundaries, including Central DST and midnight."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[1]
s=(root/'desktop/Routines.swift').read_text()
code=s[s.index('func agendaOverlaps('):s.index('struct TodayCalendarAgenda:')]
checks=r'''
func date(_ s:String)->Date { ISO8601DateFormatter().date(from:s)! }
let day = date("2026-11-18T18:00:00Z")
precondition(agendaOverlaps(start:date("2026-11-18T15:00:00Z"),end:date("2026-11-18T16:00:00Z"),day:day))
precondition(agendaOverlaps(start:date("2026-11-17T23:00:00Z"),end:date("2026-11-18T07:00:00Z"),day:day))
precondition(!agendaOverlaps(start:date("2026-11-17T23:00:00Z"),end:date("2026-11-18T06:00:00Z"),day:day))
precondition(!agendaOverlaps(start:date("2026-11-19T06:00:00Z"),end:date("2026-11-19T07:00:00Z"),day:day))
precondition(!agendaOverlaps(start:day,end:day,day:day))
// 25-hour fall-back day and 23-hour spring-forward day.
precondition(agendaOverlaps(start:date("2026-11-02T05:30:00Z"),end:date("2026-11-02T05:59:00Z"),day:date("2026-11-01T18:00:00Z")))
precondition(!agendaOverlaps(start:date("2026-03-09T05:00:00Z"),end:date("2026-03-09T06:00:00Z"),day:date("2026-03-08T18:00:00Z")))
precondition(agendaClock(date("2026-11-18T21:05:00Z")) == "3:05 PM")
precondition(agendaClock(date("2026-11-18T06:00:00Z")) == "12:00 AM")
print("PASS Central agenda midnight/exclusive end, overnight, DST and AM/PM")
'''
with tempfile.TemporaryDirectory(prefix='juno-agenda-') as t:
 p=Path(t);(p/'main.swift').write_text('import Foundation\n'+code+checks)
 subprocess.run(['xcrun','swiftc',str(p/'main.swift'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
