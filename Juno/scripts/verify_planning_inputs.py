"""Check native task-editor validation, including deliberately unknown estimates."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'desktop/Planning.swift').read_text()
function='func planningInputIssue'+source.split('func planningInputIssue',1)[1].split('struct PlanningWorkspace',1)[0]
checks=r'''
precondition(planningInputIssue(estimate:"",actual:"",check:"") == nil)
precondition(planningInputIssue(estimate:" 45 ",actual:"0",check:"2028-02-29") == nil)
precondition(planningInputIssue(estimate:"",actual:"30",check:"2026-11-02") == nil)
precondition(planningInputIssue(estimate:"4",actual:"",check:"") != nil)
precondition(planningInputIssue(estimate:"2401",actual:"",check:"") != nil)
precondition(planningInputIssue(estimate:"unknown",actual:"",check:"") != nil)
precondition(planningInputIssue(estimate:"45",actual:"-1",check:"") != nil)
precondition(planningInputIssue(estimate:"45",actual:"10001",check:"") != nil)
precondition(planningInputIssue(estimate:"45",actual:"",check:"2026-02-29") != nil)
precondition(planningInputIssue(estimate:"45",actual:"",check:"11/2/2026") != nil)
print("PASS planning editor: unknown estimates, numeric bounds and strict blocker dates")
'''
with tempfile.TemporaryDirectory(prefix='juno-planning-inputs-') as tmp:
    path=Path(tmp);(path/'main.swift').write_text('import Foundation\n'+function+checks)
    subprocess.run(['xcrun','swiftc',str(path/'main.swift'),'-o',str(path/'check')],check=True)
    subprocess.run([str(path/'check')],check=True)
