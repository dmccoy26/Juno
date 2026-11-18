"""Compile the actual native report formatter and verify audience isolation."""
from pathlib import Path
import tempfile
import subprocess
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'desktop/Routines.swift').read_text()
models=source[source.index('private struct ConcurReportOrg:'):source.index('struct HelperPeriod:')].replace('private struct','struct')
checks='''
let report=ConcurReportEvidence(id:"example",title:"October PCARD",source_status:"Pending external validation",observed_at:"2026-11-18T10:00:00Z",start:"2026-10-01",end:"2026-10-31",currency:"USD",total:"4841.17",allocation_state:"verified",org_totals:[ConcurReportOrg(org:"30400",amount:"3426.72"),ConcurReportOrg(org:"30405",amount:"1414.45")])
let chair=report.updateText(for:"VISU")
precondition(chair.contains("1,414.45") && !chair.contains("3,426.72") && !chair.contains("4,841.17") && !chair.contains("30400"))
let dean=report.updateText(for:"Dean")
precondition(dean.contains("3,426.72") && dean.contains("4,841.17"))
precondition(!report.updateText(for:"Performing Arts").contains("1,414.45"))
print("PASS native audience formatter: VISU allocation only; Dean full totals; other allocations not inferred")
'''
with tempfile.TemporaryDirectory() as folder:
    p=Path(folder);(p/'main.swift').write_text('import Foundation\nfunc sourceReadDate(_ s:String)->String { s }\n'+models+checks)
    subprocess.run(['xcrun','swiftc',str(p/'main.swift'),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
