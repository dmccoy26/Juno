"""Decode real isolated planning responses with the exact native Swift models."""
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_schedules import ScheduleTests
from sqlalchemy import select
from juno.models import TaskDockSnapshot


def main():
    ScheduleTests.setUpClass();case=ScheduleTests()
    try:
        case.setUp()
        case.save(tasks=[{'task_id':'dean','minutes':45,'dean':True,'employee':'Alex','capability':'Fictional confirmed training','independent':True}])
        with case.factory() as session:
            snapshot=session.scalar(select(TaskDockSnapshot).where(TaskDockSnapshot.owner_id==case.actor.owner_id))
            items=list(snapshot.items)
            items[0]={**items[0],'planning_details':{'room':{'state':'provided','value':'ARTS 121','origin':'reviewed'},'impact':{'state':'unknown','value':None},'blockers':{'state':'none','value':None}}}
            snapshot.items=items;session.commit()
        state=case.client.get('/v1/planning').json();plan=case.plan()
        with tempfile.TemporaryDirectory(prefix='juno-planning-native-') as temp:
            folder=Path(temp)
            (folder/'state.json').write_text(json.dumps(state));(folder/'plan.json').write_text(json.dumps(plan,default=str))
            case.schedule()
            schedules=case.client.get('/v1/schedules').json();availability=case.windows()
            (folder/'schedules.json').write_text(json.dumps(schedules));(folder/'availability.json').write_text(json.dumps(availability,default=str))
            types=(ROOT/'desktop/Planning.swift').read_text().split('struct PlanningWorkspace: View',1)[0]
            types += 'func integrationDay'+(ROOT/'desktop/Integrations.swift').read_text().split('func integrationDay',1)[1].split('struct IntegrationsWorkspace',1)[0]
            types += (ROOT/'desktop/Schedules.swift').read_text().split('func scheduleKind',1)[0]
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
let request=plan.tasks.first { $0.task_id == "dean" }!
precondition(request.requestField("room")?.display == "ARTS 121")
precondition(request.requestField("blockers")?.display == "Explicitly none")
precondition(request.request_questions?.first?.key == "impact")
precondition(request.request_questions?.count == 1)
precondition(request.taskdock_saved_at != nil)
let schedule=try decoder.decode(ScheduleRecord.self,from:Data(contentsOf:root.appendingPathComponent("schedules.json")))
let windows=try decoder.decode(AvailabilityRecord.self,from:Data(contentsOf:root.appendingPathComponent("availability.json")))
precondition(schedule.people.first?.status=="active")
precondition(schedule.rules.count==3 && !windows.windows.isEmpty)
precondition(windows.people.first?.name=="Alex")
let encoded=try JSONSerialization.jsonObject(with:JSONEncoder().encode(state)) as! [String:Any]
precondition(encoded["workspace_id"] as? String=="fictional")
print("PASS exact native planning models decode isolated API facts, estimates, unknown employee availability and constraint questions")
''')
            subprocess.run(['xcrun','swiftc','-swift-version','5',str(folder/'main.swift'),'-o',str(folder/'check')],check=True)
            subprocess.run([str(folder/'check'),str(folder)],check=True)
    finally:
        case.tearDown();ScheduleTests.tearDownClass()

if __name__=='__main__':main()
