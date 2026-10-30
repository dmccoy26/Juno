"""Exercise the native weekly projection with synthetic schedules; no work data access."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'desktop/Schedules.swift').read_text()
models = source.split('struct SchedulesWorkspace:', 1)[0]
projection = source.split('struct ScheduleWeekItem:', 1)[1]
projection = 'struct ScheduleWeekItem:' + projection.split('    var body: some View {', 1)[0] + '}\n'
projection = projection.replace('struct ScheduleWeekView: View', 'struct ScheduleWeekView').replace('@State ', '').replace('private ', '')
# The production parser is ISO8601 based; fixtures use the same explicit offsets.
parser = '''
func providerDate(_ text:String) -> Date? { ISO8601DateFormatter().date(from:text) }
func integrationDay(_ offset:Int) -> String { "2026-11-02" }
'''
checks = r'''
func rule(_ id:String,_ kind:String,_ name:String,_ location:String="",_ start:String="09:00",_ end:String="12:00") -> RecurringSchedule {
    RecurringSchedule(id:id,kind:kind,name:name,location:location,start_date:"2026-08-24",end_date:"2026-12-10",days:[0,2],start_time:start,end_time:end,timezone:"America/Chicago")
}
var record = ScheduleRecord(revision:1,rules:[rule("owner","work",""),rule("staff","staff_available","Alex"),rule("access","room","ROOM 1","","07:00","21:00"),rule("class","classroom_busy","Course","ROOM 1","10:00","11:00"),rule("other","room","ROOM 2")],people:[StaffSchedule(name:"Alex",status:"active"),StaffSchedule(name:"Candidate",status:"candidate")],exceptions:[],reservations:[PlanningReservation(id:"hold",task_id:"task",workspace_id:"work",room:"ROOM 1",employee:"Alex",start:"2026-11-02T11:00:00-06:00",end:"2026-11-02T12:00:00-06:00",uses_owner:true)])
let anchor = providerDate("2026-11-04T12:00:00-06:00")!
var room = ScheduleWeekView(record:record,byRoom:true,selected:"ROOM 1",anchor:anchor)
precondition(room.format(room.week[0],"yyyy-MM-dd") == "2026-11-02")
precondition(room.choices == ["ROOM 1","ROOM 2"])
precondition(Set(room.items(room.week[0]).map(\.id)) == ["access","class","hold"])
precondition(room.items(room.week[1]).isEmpty)
let staff = ScheduleWeekView(record:record,byRoom:false,selected:"Alex",anchor:anchor)
precondition(Set(staff.items(staff.week[0]).map(\.id)) == ["staff","hold"])
let owner = ScheduleWeekView(record:record,byRoom:false,selected:"My work",anchor:anchor)
precondition(Set(owner.items(owner.week[0]).map(\.id)) == ["owner","hold"])
let candidate = ScheduleWeekView(record:record,byRoom:false,selected:"Candidate",anchor:anchor)
precondition(candidate.items(candidate.week[0]).isEmpty)
record.exceptions = [DailyScheduleException(id:"closure",kind:"room",name:"ROOM 1",day:"2026-11-02",closed:true,start_time:nil,end_time:nil,note:"Closure"),DailyScheduleException(id:"cancel",kind:"classroom_busy",name:"ROOM 1",day:"2026-11-02",closed:true,start_time:nil,end_time:nil,note:"No classes")]
room = ScheduleWeekView(record:record,byRoom:true,selected:"ROOM 1",anchor:anchor)
precondition(Set(room.items(room.week[0]).map(\.id)) == ["closure","cancel","hold"])
let after = ScheduleWeekView(record:record,byRoom:true,selected:"ROOM 1",anchor:providerDate("2026-12-14T12:00:00-06:00")!)
precondition(after.items(after.week[0]).isEmpty)
let dst = ScheduleWeekView(record:record,byRoom:true,selected:"ROOM 1",anchor:providerDate("2026-10-30T12:00:00-05:00")!)
precondition(dst.format(dst.week[6],"yyyy-MM-dd HH:mm") == "2026-11-01 00:00")
print("PASS native weekly views: person/room isolation, supervised holds, candidate without shifts, exceptions, semester bounds, Monday week and DST")
'''
with tempfile.TemporaryDirectory(prefix='juno-schedule-views-') as tmp:
    path = Path(tmp)
    (path/'main.swift').write_text(models + parser + projection + checks)
    subprocess.run(['xcrun','swiftc','-swift-version','5',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
