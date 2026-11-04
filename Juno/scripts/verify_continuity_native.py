"""Exact native carry/Dean wire models, including null-preserving source basis."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_planning_continuity import ContinuityTests


def main():
    if not os.environ.get('JUNO_TEST_ADMIN_URL'):raise SystemExit('Set an isolated PostgreSQL test URL.')
    ContinuityTests.setUpClass();case=ContinuityTests()
    try:
        case.setUp();case.diary()
        source=case.client.get('/v1/planning/carry-forward?day=2030-01-06').json()
        intent={k:source[k] for k in ('diary_id','diary_revision','planning_revision','workspace_id','snapshot_id')}|{'task_id':'dean','source_quote':'Fictional tomorrow','changes':{'resume':'Native reviewed handoff'}}
        review=case.client.post('/v1/planning/carry-forward/preview',json=intent).json()
        with __import__('fastapi.testclient',fromlist=['TestClient']).TestClient(case.app) as other:
            other.headers['Authorization']='Bearer '+case.other_token
            empty=other.get('/v1/planning/weekly?day=2030-01-06').json()['basis']
        weekly=case.client.get('/v1/planning/weekly?day=2030-01-06').json();saved=case.client.get('/v1/planning/weekly-draft/2030-01-06').json()
        planning=(ROOT/'desktop/Planning.swift').read_text().split('struct PlanningWorkspace:',1)[0].replace('import SwiftUI','import Foundation')
        companion=(ROOT/'desktop/Companion.swift').read_text();types=companion[companion.index('struct CarryTaskChoice:'):companion.index('struct DailyBriefItem:')]
        with tempfile.TemporaryDirectory(prefix='juno-continuity-native-') as temporary:
            folder=Path(temporary)
            for name,value in [('source',source),('review',review),('weekly',weekly),('saved',saved),('empty-basis',empty)]: (folder/(name+'.json')).write_text(json.dumps(value))
            (folder/'main.swift').write_text(planning+'\n'+types+r'''
let root=URL(fileURLWithPath:CommandLine.arguments[1]);let decoder=JSONDecoder()
func load<T:Decodable>(_ name:String,_ type:T.Type)throws->T { try decoder.decode(type,from:Data(contentsOf:root.appendingPathComponent(name+".json"))) }
let source=try load("source",CarrySource.self),review=try load("review",CarryPreview.self),weekly=try load("weekly",WeeklyPlanningDraft.self),saved=try load("saved",SavedDeanDraft.self)
precondition(source.tasks.contains{$0.id=="dean"} && source.diary_revision>0)
precondition(review.rows.first?.after=="Native reviewed handoff")
precondition(weekly.basis.diaries.count==1 && weekly.missing_diary_dates.count==6)
precondition(saved.revision==0 && !saved.exists)
let empty=try load("empty-basis",WeeklyBasis.self)
let encodedEmpty=try JSONSerialization.jsonObject(with:JSONEncoder().encode(empty)) as! [String:Any]
precondition(encodedEmpty["snapshot_id"] is NSNull && encodedEmpty["workspace_id"] is NSNull && encodedEmpty["taskdock_saved_at"] is NSNull)
let basis=try JSONSerialization.jsonObject(with:JSONEncoder().encode(weekly.basis))
let body:[String:Any] = ["operation_id":UUID().uuidString,"expected_revision":0,"text":"Student Test native reviewed Dean text","basis":basis]
try JSONSerialization.data(withJSONObject:body).write(to:root.appendingPathComponent("save-body.json"))
if FileManager.default.fileExists(atPath:root.appendingPathComponent("receipt.json").path) {
 let receipt=try load("receipt",DeanSaveReceipt.self),reopened=try load("reopened",SavedDeanDraft.self)
 precondition(receipt.revision==1 && reopened.text=="Student Test native reviewed Dean text")
}
print("PASS exact native carry/weekly models and source-basis round trip")
''')
            subprocess.run(['xcrun','swiftc','-swift-version','5',str(folder/'main.swift'),'-o',str(folder/'verify')],check=True)
            subprocess.run([str(folder/'verify'),str(folder)],check=True)
            response=case.client.put('/v1/planning/weekly-draft/2030-01-06',json=json.loads((folder/'save-body.json').read_text()));assert response.status_code==200,response.text
            (folder/'receipt.json').write_text(json.dumps(response.json()));(folder/'reopened.json').write_text(json.dumps(case.client.get('/v1/planning/weekly-draft/2030-01-06').json()))
            subprocess.run([str(folder/'verify'),str(folder)],check=True)
    finally:case.tearDown();ContinuityTests.tearDownClass()

if __name__=='__main__':main()
