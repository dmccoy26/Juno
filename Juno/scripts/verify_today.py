"""Exercise exact native Today task/date helpers using fictional records."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
companion=(root/'desktop/Companion.swift').read_text()
functions='func taskIsUnfinished'+companion.split('func taskIsUnfinished',1)[1].split('struct TodayWorkspace',1)[0]
models=(root/'desktop/TaskDock.swift').read_text().split('enum TaskDockKeychain',1)[0]
models+=(root/'desktop/Planning.swift').read_text().split('struct PlanningWorkspace',1)[0]
checks=r'''
func task(_ extra:[String:Any]) throws -> TaskDockTask {
    var row:[String:Any] = ["id":"synthetic","title":"Fictional issue"]
    for (key,value) in extra { row[key] = value }
    return try JSONDecoder().decode(TaskDockTask.self,from:JSONSerialization.data(withJSONObject:row))
}
precondition(taskIsUnfinished(try task([:])))
precondition(!taskIsUnfinished(try task(["source_completed":true])))
precondition(!taskIsUnfinished(try task(["completed_at":"2026-10-30T12:00:00Z"])))
precondition(!taskIsUnfinished(try task(["behavior":"ARCHIVED"])))
precondition(taskIsUnfinished(try task(["completed_at":NSNull(),"behavior":"in_progress"])))
precondition(try taskDueDay(task(["due_date":"2026-10-30"])) == "2026-10-30")
precondition(try taskDueDay(task(["due_date":"2026-11-06T12:00:00Z"])) == "2026-11-06")
precondition(try taskDueDay(task(["due_date":"2026-02-30"])) == nil)
precondition(try taskDueDay(task(["due_date":"unknown"])) == nil)
precondition(try taskDueDay(task([:])) == nil)
precondition(try !taskHasRecordedBlocker(task(["blocked_reason":"  "]),nil))
precondition(try taskHasRecordedBlocker(task(["blocked_reason":"Waiting for parts"]),nil))
precondition(try taskHasRecordedBlocker(task([:]),PlanningFacts(task_id:"synthetic",waiting_on:"Approval")))
print("PASS Today helpers: completion boundaries, valid/missing/invalid deadlines and recorded blockers")
'''
# Throwing work must happen outside precondition's non-throwing autoclosure.
checks=checks.replace('precondition(', 'try check(')
checks='func check(_ value: Bool) throws { precondition(value) }\n'+checks
with tempfile.TemporaryDirectory(prefix='juno-today-') as tmp:
    path=Path(tmp);(path/'main.swift').write_text(models+functions+checks)
    subprocess.run(['xcrun','swiftc','-swift-version','5',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
