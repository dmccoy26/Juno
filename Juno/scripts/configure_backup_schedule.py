"""Install an hourly per-user launchd job for an already configured Juno backup."""
import argparse,json,os,plistlib,subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True);args=parser.parse_args()
    config=args.config.resolve();json.loads(config.read_text());settings=config.parent
    program=settings/'automatic_backup.py';python=settings/'runtime/bin/python'
    if not program.is_file() or not python.is_file():parser.error('Prepare the backup script/runtime first.')
    logs=Path.home()/'Library/Logs/Juno Backups';logs.mkdir(parents=True,exist_ok=True,mode=0o700)
    agents=Path.home()/'Library/LaunchAgents';agents.mkdir(parents=True,exist_ok=True)
    label='com.dmccoy.juno.backup';plist=agents/(label+'.plist')
    data={'Label':label,'ProgramArguments':[str(python),str(program),'--config',str(config)],'RunAtLoad':True,'StartInterval':3600,'ProcessType':'Background','LowPriorityIO':True,'Nice':10,'Umask':63,'StandardOutPath':str(logs/'backup.log'),'StandardErrorPath':str(logs/'backup-error.log'),'WorkingDirectory':str(settings)}
    plist.write_bytes(plistlib.dumps(data));plist.chmod(0o600)
    domain='gui/'+str(os.getuid())
    subprocess.run(['launchctl','bootout',domain+'/'+label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(['launchctl','bootstrap',domain,str(plist)],check=True)
    print('Installed hourly Juno backup LaunchAgent with a run at login/load. No SMB credentials or secrets in the plist.')


if __name__=='__main__':main()
