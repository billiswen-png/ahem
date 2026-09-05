"""Install macOS user LaunchAgents for this local demo; never overwrite jobs."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

LABELS=('local.ahem.enterprise-demo','local.ahem.enterprise-backup')


def plans(repo, runtime, python):
    repo=Path(repo).resolve();runtime=Path(runtime).resolve()
    python=os.path.abspath(python)  # Preserve venv symlink path.
    common={'WorkingDirectory':str(repo),'EnvironmentVariables':{'PYTHONPATH':str(repo/'src'),
        'AHEM_KEK_FILE':str(runtime/'kek'),'PYTHONUNBUFFERED':'1'},'Umask':63,'RunAtLoad':True,
        'ThrottleInterval':30}
    server={**common,'Label':LABELS[0],'ProgramArguments':[python,'-m','meeting_host.enterprise',
        '--identities',str(runtime/'identities.json'),'--database',str(runtime/'enterprise.db'),
        '--port','8891','--demo-mode'],'KeepAlive':True,'ExitTimeOut':15,
        'StandardOutPath':str(runtime/'service-logs/server.out.log'),
        'StandardErrorPath':str(runtime/'service-logs/server.err.log')}
    backup={**common,'Label':LABELS[1],'ProgramArguments':[python,'-m','meeting_host.enterprise_backup',
        'maintain','--source',str(runtime/'enterprise.db'),'--destination',str(runtime/'managed-backups'),
        '--retention-days','7','--keep-at-least','2','--apply'],'StartInterval':3600,
        'ProcessType':'Background','Nice':10,
        'StandardOutPath':str(runtime/'service-logs/backup.out.log'),
        'StandardErrorPath':str(runtime/'service-logs/backup.err.log')}
    return [server,backup]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--python',default=sys.executable)
    p.add_argument('--install',action='store_true')
    args=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    if sys.platform!='darwin':raise SystemExit('macOS only')
    runtime=args.runtime
    if runtime.is_symlink() or not runtime.is_dir() or runtime.stat().st_mode & 0o077:
        raise SystemExit('Runtime must be an existing private directory')
    for name in ('identities.json','kek','enterprise.db'):
        path=runtime/name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise SystemExit('Required runtime file missing or not private: '+name)
    jobs=plans(repo,runtime,args.python)
    if not args.install:
        for job in jobs:print(job['Label'], 'validated; interval=',job.get('StartInterval','keep-alive'))
        return
    directory=Path.home()/'Library/LaunchAgents'
    directory.mkdir(parents=True,exist_ok=True)
    targets=[directory/(job['Label']+'.plist') for job in jobs]
    if any(p.exists() or p.is_symlink() for p in targets):raise SystemExit('Existing job: refusing overwrite')
    for name in ('managed-backups','service-logs'):
        path=runtime/name
        if path.is_symlink():raise SystemExit('Private directory cannot be a symlink')
        path.mkdir(mode=0o700,exist_ok=True)
        if path.stat().st_mode & 0o077:raise SystemExit('Private directory permissions required')
    # Preparation is separate from loading so failures remain visible.
    for target,job in zip(targets,jobs):
        fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as f:plistlib.dump(job,f)
        subprocess.run(['plutil','-lint',str(target)],check=True)
    for target in targets:
        subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(target)],check=True)
    print('Installed two user agents; login-session startup, hourly backup; verify launchctl and output logs separately.')


if __name__=='__main__':main()
