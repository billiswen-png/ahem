"""Explicitly restart the demo agent and trigger a backup; no reboot required."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
from meeting_host.enterprise_backup import restore
from meeting_host.security import load_kek

p=argparse.ArgumentParser()
p.add_argument('--runtime',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
domain=f'gui/{os.getuid()}'
server=domain+'/local.ahem.enterprise-demo';backup=domain+'/local.ahem.enterprise-backup'
def status(target):return subprocess.check_output(['launchctl','print',target],text=True)
def number(text,key):
    found=re.search(r'^\s*'+key+r' = (\d+)$',text,re.M)
    return int(found.group(1)) if found else None
before=number(status(server),'pid');assert before
start=time.perf_counter()
subprocess.run(['launchctl','kill','SIGTERM',server],check=True)
after=None
for _ in range(150):
    after=number(status(server),'pid')
    if after and after!=before:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8891/',timeout=1) as response:
                if response.status==200:break
        except OSError:pass
    time.sleep(.2)
else:raise SystemExit('Demo agent did not recover within 30 seconds')
recovery=round(time.perf_counter()-start,3)
runs=number(status(backup),'runs') or 0
subprocess.run(['launchctl','kickstart',backup],check=True)
for _ in range(150):
    result=status(backup)
    if (number(result,'runs') or 0)>runs and '\tstate = not running\n' in result:
        assert number(result,'last exit code')==0
        break
    time.sleep(.2)
else:raise SystemExit('Backup did not finish within 30 seconds')
key=load_kek()
files=sorted((args.runtime/'managed-backups').glob('ahem-snapshot-*.enc'))
assert len(files)>=2
counts=[restore(file,key) for file in files]
report={'server_before_pid':before,'server_after_pid':after,'http_status':200,'recovery_seconds':recovery,
    'backup_exit_code':0,'backup_runs':number(result,'runs'),'backup_interval_seconds':3600,
    'verified_backup_count':len(files),'verified_meetings_per_backup':counts,
    'reboot_tested':False,'note':'LaunchAgents run after macOS user login; no physical reboot was performed.'}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
