"""Compile Concur Helper's real encoder and round-trip through Juno's reader.

Uses a disposable UserDefaults suite and synthetic observations; never opens Concur.
"""
from pathlib import Path
import tempfile
import subprocess
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT.parent/'Concur Helper/Sources/ConcurHelper/JunoExport.swift'
sys.path.insert(0,str(ROOT/'backend/src'))
from juno.purchasing_export import read
from juno.purchasing import parse_reports
with tempfile.TemporaryDirectory(prefix='juno-helper-contract-') as folder:
    p=Path(folder)
    source=HELPER.read_text().replace('UserDefaults.standard','UserDefaults(suiteName: "juno.synthetic.export.contract")!')
    stubs='''
struct ReconciliationJob { let start:String; let end:String }
struct Expense { let id:String;let merchant:String;let date:String;let amount:String;let currency:String;let status:String }
'''
    main='''
let observation=ReportObservation(sourceStatus:"Pending external validation",observedAt:"2026-11-18T10:00:00Z",title:"Synthetic October PCARD",periodStart:"2026-10-01",periodEnd:"2026-10-31",currency:"USD",total:"-18.14",allocationState:"verified",orgTotals:[OrgTotal(org:"30405",amount:"-18.14")])
let expense=Expense(id:"credit",merchant:"Synthetic credit",date:"2026-10-30",amount:"-18.14",currency:"USD",status:"missing_receipt")
func run(_ success:Bool)->ExportRun { ExportRun(operation:"scan",startedAt:Date(timeIntervalSince1970:1794990000),endedAt:Date(timeIntervalSince1970:1794990060),outcome:success ? "success" : "failure",coverage:["concur":success ? .complete : .failed,"orders":.notSearched],signInState:"not_required") }
for success in [true,false] {
 let export=JunoExport(reportURL:"https://private.invalid/report",job:nil,observation:observation,expenses:[expense],verified:[],uncertain:[],runs:[run(success)])
 try export.write(to:URL(fileURLWithPath:CommandLine.arguments[1]+(success ? "/success.json" : "/failure.json")))
}
let statusRun=ExportRun(operation:"read_report_status",startedAt:Date(timeIntervalSince1970:1794990000),endedAt:Date(timeIntervalSince1970:1794990060),outcome:"success",coverage:["concur":.complete,"pcard":.notSearched],signInState:"not_required")
let statusExport=JunoExport(reportURL:"https://private.invalid/report",job:nil,observation:observation,expenses:[],verified:[],uncertain:[],runs:[statusRun])
try statusExport.write(to:URL(fileURLWithPath:CommandLine.arguments[1]+"/report.json"))
UserDefaults(suiteName:"juno.synthetic.export.contract")!.removePersistentDomain(forName:"juno.synthetic.export.contract")
'''
    (p/'main.swift').write_text(source+stubs+main)
    subprocess.run(['xcrun','swiftc',str(p/'main.swift'),'-o',str(p/'encode')],check=True)
    subprocess.run([str(p/'encode'),str(p)],check=True)
    raw=(p/'success.json').read_text();rows,meta=read(raw)
    assert rows[0]['amount']=='-18.14'
    assert meta['reports'][0]['source_status']=='Pending external validation'
    assert parse_reports(raw)[0]['org_totals']==[{'org':'30405','amount':'-18.14'}]
    assert 'private.invalid' not in raw
    rows,meta=read((p/'failure.json').read_text())
    assert rows is None and meta['runs'][0]['outcome']=='failure'
    rows,status=read((p/'report.json').read_text())
    assert rows is None and status['runs'][0]['operation']=='read_report_status'
    print('PASS real Swift helper encoder → Juno: signed credit, exact status, verified allocation, failed-scan preservation, private URL excluded')
