"""Exercise native staffing compatibility and Central-time chair availability."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'desktop/Planning.swift').read_text()
facts = source[source.index('enum PlanningStaffing:'):source.index('struct PlanningRecord:')]
schedule = source[source.index('struct DeanMeetingSchedule {'):source.index('private struct DeanPrepareResult:')]
timeline_source = (ROOT / 'desktop/Schedules.swift').read_text()
timeline = timeline_source[timeline_source.index('func scheduleTimelineMinute('):timeline_source.index('struct ScheduleTimeline:')]
checks = r'''
var facts = PlanningFacts(task_id: "fixture")
let clean = facts
precondition(facts.changedFields(from: clean, estimate: "", actual: "", check: "") == 0)
facts.room = "Fictional room"
precondition(facts.changedFields(from: clean, estimate: "45", actual: "", check: "") == 2)
facts.room = ""
precondition(facts.staffing == .me && facts.staffingIssue == nil)
facts.employee = "Fictional worker"
precondition(facts.staffing == .unreviewed)
facts.setStaffing(.independent)
precondition(facts.independent && facts.supervision == false && facts.staffingIssue == nil)
facts.setStaffing(.supervised)
precondition(!facts.independent && facts.supervision == true && facts.staffingIssue == nil)
facts.independent = true
let ambiguous = try JSONEncoder().encode(facts)
var restored = try JSONDecoder().decode(PlanningFacts.self, from: ambiguous)
precondition(restored.staffing == .conflicting && restored.staffingIssue != nil)
precondition(restored.independent && restored.supervision == true)
restored.setStaffing(.supervised)
precondition(!restored.independent && restored.supervision == true)
restored.setStaffing(.unreviewed)
precondition(!restored.independent && restored.supervision == false && restored.employee == "Fictional worker")
restored.setStaffing(.me)
precondition(restored.employee.isEmpty && restored.staffing == .me)
restored.setStaffing(.independent)
precondition(restored.staffingIssue != nil)
restored.setStaffing(.supervised)
precondition(restored.staffingIssue != nil)
restored.employee = "  "
precondition(restored.staffingIssue != nil)
let encoded = try JSONSerialization.jsonObject(with: JSONEncoder().encode(restored)) as! [String: Any]
precondition(encoded["staffing"] == nil && encoded["staffingIssue"] == nil)
precondition(encoded["independent"] as? Bool == false && encoded["supervision"] as? Bool == true)

func date(_ text: String) -> Date { ISO8601DateFormatter().date(from: text)! }
let tuesday = date("2026-11-17T16:00:00Z")
let winter = ChairPreparationSchedule(day: tuesday)
precondition(winter.friday == date("2026-11-20T06:00:00Z"))
precondition(winter.automaticAt == date("2026-11-20T15:00:00Z"))
precondition(!winter.canPrepare(at: tuesday))
precondition(winter.emptySummary(at: tuesday).contains("Fri, Nov 20 at 9:00 AM Central"))
precondition(!winter.emptySummary(at: tuesday).contains("ready"))
precondition(winter.emptySummary(at: tuesday, automatic: false).contains("automatic preparation is off"))
precondition(!winter.canPrepare(at: date("2026-11-20T05:59:59Z")))
precondition(winter.canPrepare(at: winter.friday))
precondition(winter.emptySummary(at: date("2026-11-20T14:59:59Z")).hasPrefix("Scheduled"))
precondition(winter.emptySummary(at: winter.automaticAt).hasPrefix("No email draft saved"))
let summer = ChairPreparationSchedule(day: date("2026-06-09T15:00:00Z"))
precondition(summer.automaticAt == date("2026-06-12T14:00:00Z"))
let nextWeek = ChairPreparationSchedule(day: date("2026-11-23T06:00:00Z"))
precondition(nextWeek.week != winter.week && nextWeek.automaticAt == date("2026-11-27T15:00:00Z"))
print("PASS staffing exclusivity, legacy conflict preservation, wire compatibility and chair schedule boundaries in Central time")
precondition(scheduleTimelineMinute("00:00") == 0)
precondition(scheduleTimelineMinute("09:30") == 570)
precondition(scheduleTimelineMinute("24:00") == 1440)
precondition(scheduleTimelineMinute("24:01") == nil && scheduleTimelineMinute("09:60") == nil)
print("PASS aligned timeline boundaries, midnight and invalid times")
'''

with tempfile.TemporaryDirectory(prefix='juno-workspace-states-') as temporary:
    folder = Path(temporary)
    program = folder / 'main.swift'
    program.write_text('import Foundation\n' + facts + schedule + timeline + checks)
    subprocess.run(['xcrun', 'swiftc', '-swift-version', '5', str(program), '-o', str(folder / 'verify')], check=True)
    subprocess.run([str(folder / 'verify')], check=True)
