"""Decode isolated daily briefing responses with Juno's exact native models."""
import json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend/src'),str(ROOT/'backend/tests')]
from test_daily_brief import DailyBriefTests


def main():
    if not os.environ.get('JUNO_TEST_ADMIN_URL'):raise SystemExit('Use an isolated test PostgreSQL admin URL; skipped tests are not a pass.')
    DailyBriefTests.setUpClass();case=DailyBriefTests()
    try:
        case.setUp();case.save(tasks=[{'task_id':'dean','minutes':45,'dean':True,'resume':'Saved cable-test handoff'}]);value=case.brief('2030-01-04')
        source=(ROOT/'desktop/Companion.swift').read_text();types=source[source.index('struct DailyBriefItem:'):source.index('struct CheckInWorkspace:')]
        with tempfile.TemporaryDirectory(prefix='juno-daily-native-') as temporary:
            folder=Path(temporary);(folder/'brief.json').write_text(json.dumps(value));(folder/'main.swift').write_text('import Foundation\n'+types+r'''
let value=try JSONDecoder().decode(DailyBrief.self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
precondition(value.next_day=="2030-01-07" && value.has_scheduled_workday)
precondition(value.recommended_task_id=="dean" && value.alternatives.count==1)
precondition(value.alternatives.first?.resume=="Saved cable-test handoff")
precondition(value.guidance["employee_work"]?.first?.contains("inactivity")==true)
precondition(dailyBriefTime("2030-01-07T15:00:00Z")=="9:00 AM")
precondition(dailyBriefTime("2030-07-08T19:30:00+00:00")=="2:30 PM")
precondition(dailyBriefTime("not-a-time")=="Time unavailable")
print("PASS native daily briefing models, continuity and 12-hour Chicago times")
''');subprocess.run(['xcrun','swiftc','-swift-version','5',str(folder/'main.swift'),'-o',str(folder/'verify')],check=True);subprocess.run([str(folder/'verify'),str(folder/'brief.json')],check=True)
    finally:case.tearDown();DailyBriefTests.tearDownClass()

if __name__=='__main__':main()
