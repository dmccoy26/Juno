"""Native blocker edits preserve unrelated planning facts and strict due-day semantics."""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[1]
source = (root/'desktop/Planning.swift').read_text()
models = source[source.index('struct PlanningWindow:'):source.index('struct IssueBlockerEditor:')]
# Compile production model code with the Linux-independent Foundation import.
checks = r'''
var a = PlanningFacts(task_id: "a")
a.minutes = 45; a.actual_minutes = 20; a.room = "Fictional room"; a.employee = "Fictional worker"
a.independent = true; a.resume = "Resume at station five"; a.dean = true
let b = PlanningFacts(task_id: "b", minutes: 30)
let original = PlanningRecord(revision: 7, workspace_id: "fictional", reserve_minutes: 90, priority_choice: "a", priority_choice_date: "2026-11-18", windows: [PlanningWindow(start:"2030-01-01T15:00:00Z",end:"2030-01-01T16:00:00Z")], tasks:[a,b])
let edited = original.updatingBlocker(taskID:"a", blocker:"Parts", waitingOn:"Vendor", nextAction:"Request ETA", nextCheck:"2026-11-20")
precondition(edited.revision == 7 && edited.workspace_id == original.workspace_id)
precondition(edited.reserve_minutes == 90 && edited.priority_choice == "a" && edited.priority_choice_date == original.priority_choice_date)
precondition(edited.windows.map(\.id) == original.windows.map(\.id) && edited.tasks.count == 2 && edited.tasks[1] == b)
var expected = a; expected.blocker = "Parts"; expected.waiting_on = "Vendor"; expected.next_action = "Request ETA"; expected.next_check = "2026-11-20"
precondition(edited.tasks[0] == expected && original.tasks[0] == a)
let added = original.updatingBlocker(taskID:"c", blocker:"Approval", waitingOn:"Office", nextAction:"Ask", nextCheck:nil)
precondition(added.tasks.count == 3 && added.tasks[0] == a && added.tasks[1] == b)
let cleared = edited.updatingBlocker(taskID:"a", blocker:"", waitingOn:"", nextAction:"", nextCheck:nil)
precondition(cleared.tasks[0] == a && cleared.tasks[1] == b)
precondition(issueIsOverdue("2026-11-17", today:"2026-11-18"))
precondition(!issueIsOverdue("2026-11-18", today:"2026-11-18"))
precondition(!issueIsOverdue("2026-11-19", today:"2026-11-18"))
precondition(!issueIsOverdue(nil, today:"2026-11-18"))
precondition(!issueIsOverdue("2026-02-30", today:"2026-11-18"))
print("PASS native blocker changes: existing/new/cleared facts, unrelated fields, and overdue dates")
'''
with tempfile.TemporaryDirectory(prefix='juno-blocker-') as tmp:
    path = Path(tmp)
    (path/'main.swift').write_text('import Foundation\n'+models+checks)
    subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
