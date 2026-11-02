"""Prepare an isolated native interaction lab; never read the work database or credentials."""
import argparse,json,os,plistlib,shutil,subprocess,sys
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend/src'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('app',type=Path);parser.add_argument('--name',default='mission10')
    args=parser.parse_args()
    if not args.name.isalnum():parser.error('Use an alphanumeric lab name.')
    root=ROOT/'.local'/('native-lab-'+args.name)
    if root.exists():raise SystemExit('Lab already exists. Choose a new name; existing evidence/data is preserved.')
    root.mkdir(mode=0o700);state=root/'state';state.mkdir(mode=0o700)
    (state/'shared-host').mkdir(mode=0o700)
    (state/'shared-host/settings.json').write_text(json.dumps({'enabled':False,'port':0}))
    env={**os.environ,'JUNO_DATA_ROOT':str(state)}
    subprocess.run([sys.executable,str(ROOT/'scripts/dev_database.py'),'start'],env=env,check=True)
    url=subprocess.check_output([sys.executable,str(ROOT/'scripts/dev_database.py'),'url'],env=env,text=True).strip()
    os.environ['JUNO_DATABASE_URL']=url
    from alembic import command
    from alembic.config import Config
    from juno.database import engine_for,sessions
    from juno.auth import provision
    from juno.models import TaskDockSnapshot,TaskDockState,now
    from juno.api import create_app
    from fastapi.testclient import TestClient
    command.upgrade(Config(str(ROOT/"backend/alembic.ini")),"head")
    engine=engine_for(url)
    with sessions(engine)() as session:
        actor,token=provision(session,'Student Test interaction lab')
        session.commit();owner={'owner_id':actor.owner_id,'device_id':actor.id}
    identity=state/'desktop-owner.json';identity.write_text(json.dumps(owner));identity.chmod(0o600)
    with sessions(engine)() as session:
        fields=['issue_description','requested_outcome','building','room','equipment','requester','contact','impact','reported_priority','troubleshooting','blockers','dependencies']
        tasks=[]
        for index,title in enumerate(['Student Test tablet problem','Student Test printer parts','Student Test research','Student Test completed issue']):
            facts={key:{'state':'unknown','value':None} for key in fields}
            facts['issue_description']={'state':'provided','value':'Fictional issue for native interaction checks.','origin':'Synthetic fixture','updated_at':'2026-11-01T15:00:00Z'}
            facts['room']={'state':'provided','value':'ARTS 121','origin':'Synthetic fixture'}
            facts['blockers']={'state':'provided','value':'Waiting for fictional parts'} if index==1 else {'state':'none','value':None}
            tasks.append({'id':'student-test-'+str(index),'title':title,'description':'Fictional request only.','priority':index%3+1,'behavior':'completed' if index==3 else 'open','due_date':'2026-11-02','planning_details':facts,'planning_readiness':{'state':'needs_information','missing':['impact'],'staffing_review_required':True}})
        snapshot=TaskDockSnapshot(owner_id=actor.owner_id,origin='http://127.0.0.1:18114',info={'api_version':'1','workspace_id':'student-test-workspace','device_id':'student-test-device','capabilities':{'read_tasks':True,'controlled_sharing':True},'sharing_version':1,'sharing':{'controlled':True,'channels':['title','status','priority','dates','description'],'planning_fields':fields},'definitions':{'statuses':[],'categories':[],'custom_fields':[],'priorities':[{'value':1,'name':'High'},{'value':2,'name':'Normal'},{'value':3,'name':'Low'}]}},items=tasks,sources=[],snapshot='student-test-revision',fetched_at=now())
        session.add(snapshot);session.flush();session.add(TaskDockState(owner_id=actor.owner_id,active_id=snapshot.id));session.commit()
    with TestClient(create_app(engine)) as client:
        client.headers['Authorization']='Bearer '+token
        def rule(kind,name,a,b,days):return {'id':kind+name,'kind':kind,'name':name,'location':name if kind=='classroom_busy' else '', 'start_date':'2026-11-01','end_date':'2026-12-10','days':days,'start_time':a,'end_time':b}
        result=client.put('/v1/schedules',json={'expected_revision':0,'rules':[rule('work','','09:00','17:00',[0,1,2,3,4]),rule('room','ARTS 121','07:00','21:00',list(range(7))),rule('staff_available','Student Test Alex','09:00','17:00',[0,1,2,3,4]),rule('classroom_busy','ARTS 121','09:00','10:45',[0,2])],'people':[{'name':'Student Test Alex','status':'active','weekly_limit_minutes':1200},{'name':'Student Test Candidate','status':'candidate','weekly_limit_minutes':1200}],'exceptions':[]})
        assert result.status_code==200,result.text
        for text in ['Student Test saved memory','Student Test other memory']:
            result=client.post('/v1/memories',json={'text':text,'source':'Synthetic lab','confidence':'confirmed'});assert result.status_code==201,result.text
        result=client.post('/v1/conversations',json={'title':'Student Test conversation'});assert result.status_code==201,result.text
    engine.dispose()
    app=root/'Juno Lab.app';shutil.copytree(args.app.resolve(),app,symlinks=True)
    info_path=app/'Contents/Info.plist';info=plistlib.loads(info_path.read_bytes())
    assert info.get('JunoPackaged') is not True,'Lab requires a development app.'
    info.update(CFBundleIdentifier='com.dmccoy.juno.lab.'+args.name,CFBundleName='Juno Lab',CFBundleDisplayName='Juno Lab',JunoTestDataRoot=str(state),JunoReleaseVersion='0.1.0-preview.12-lab')
    info_path.write_bytes(plistlib.dumps(info))
    subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
    print('Isolated native lab: '+str(app))
    print('Only synthetic records; shared hosting disabled; separate preferences and Keychain namespace.')

if __name__=='__main__':main()
