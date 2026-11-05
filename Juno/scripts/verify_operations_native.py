"""Decode actual synthetic API outputs with exact native operational wire models."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_operations import OperationsTests


def main():
    if not os.environ.get('JUNO_TEST_ADMIN_URL'):raise SystemExit('Set an isolated PostgreSQL test URL.')
    OperationsTests.setUpClass();case=OperationsTests()
    try:
        case.setUp();value=case.link('done')
        brief=case.client.get('/v1/planning/daily-brief?day=2030-01-06').json()
        procedures=case.client.get('/v1/operations/procedures').json();lifecycle=case.client.get('/v1/operations/lifecycle').json()
        source=(ROOT/'desktop/Companion.swift').read_text()
        types=source[source.index('struct DailyBriefItem:'):source.index('struct CheckInWorkspace:')]
        refs=source[source.index('struct ProcedureChoice:'):source.index('struct OperationalSupportingReferences:')]
        with tempfile.TemporaryDirectory(prefix='juno-operations-native-') as temporary:
            folder=Path(temporary)
            for name,data in [('operations',value),('daily',brief),('procedures',procedures),('lifecycle',lifecycle)]: (folder/(name+'.json')).write_text(json.dumps(data))
            (folder/'main.swift').write_text('import Foundation\n'+types+'\n'+refs+r'''
let root=URL(fileURLWithPath:CommandLine.arguments[1]);let decoder=JSONDecoder()
func load<T:Decodable>(_ name:String,_ type:T.Type)throws->T {try decoder.decode(type,from:Data(contentsOf:root.appendingPathComponent(name+".json")))}
let operations=try load("operations",OperationalBrief.self)
precondition(operations.cards.first?.relationship=="reviewed_ids")
precondition(operations.cards.first?.tasks.first?.completed==true)
precondition(operations.cards.first?.verification_state=="unknown")
precondition(operations.evidence.count==2)
let daily=try load("daily",DailyBrief.self)
precondition(daily.operations?.cards.first?.verification_state=="unknown")
let procedures=try load("procedures",ProcedureReferences.self),lifecycle=try load("lifecycle",LifecycleReview.self)
precondition(procedures.items.isEmpty && lifecycle.candidates.isEmpty)
print("PASS native operational/daily/procedure/lifecycle decoding and completed-task-without-recovery distinction")
''')
            subprocess.run(['xcrun','swift',str(folder/'main.swift'),str(folder)],check=True)
    finally:case.tearDown();OperationsTests.tearDownClass()


if __name__=='__main__':main()
