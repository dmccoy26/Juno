"""Decode real isolated planning responses with the exact native Swift models."""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_planning import PlanningTests


def main():
    PlanningTests.setUpClass();case=PlanningTests()
    try:
        case.setUp()
        case.save(tasks=[{'task_id':'dean','minutes':45,'dean':True,'employee':'Alex','capability':'Fictional confirmed training','independent':True}])
        state=case.client.get('/v1/planning').json();plan=case.plan()
        with tempfile.TemporaryDirectory(prefix='juno-planning-native-') as temp:
            folder=Path(temp)
            (folder/'state.json').write_text(json.dumps(state));(folder/'plan.json').write_text(json.dumps(plan,default=str))
            types=(ROOT/'desktop/Planning.swift').read_text().split('struct PlanningWorkspace: View',1)[0]
            (folder/'main.swift').write_text(types+r'''
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let decoder=JSONDecoder()
let state=try decoder.decode(PlanningRecord.self,from:Data(contentsOf:root.appendingPathComponent("state.json")))
let plan=try decoder.decode(PlanningResult.self,from:Data(contentsOf:root.appendingPathComponent("plan.json")))
precondition(state.revision==1 && state.workspace_id=="fictional")
precondition(state.tasks.first?.minutes==45)
precondition(plan.staff_loads.first?.employee=="Alex")
precondition(plan.staff_loads.first?.available_minutes==nil)
precondition(plan.recommended_task_id==nil)
precondition(plan.tasks.first?.missing.isEmpty==false)
let encoded=try JSONSerialization.jsonObject(with:JSONEncoder().encode(state)) as! [String:Any]
precondition(encoded["workspace_id"] as? String=="fictional")
print("PASS exact native planning models decode isolated API facts, estimates, unknown employee availability and constraint questions")
''')
            subprocess.run(['xcrun','swiftc','-swift-version','5',str(folder/'main.swift'),'-o',str(folder/'check')],check=True)
            subprocess.run([str(folder/'check'),str(folder)],check=True)
    finally:
        case.tearDown();PlanningTests.tearDownClass()

if __name__=='__main__':main()
