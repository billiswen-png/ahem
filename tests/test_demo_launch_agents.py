import importlib.util
from pathlib import Path
import plistlib

spec=importlib.util.spec_from_file_location('demo_agents',Path(__file__).resolve().parents[1]/'scripts/install_local_demo_agents.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def test_agent_plans_preserve_venv_and_no_credentials():
    server,backup=module.plans('/tmp/repo','/tmp/private-demo','/tmp/venv/bin/python')
    assert server['ProgramArguments'][0]=='/tmp/venv/bin/python'
    assert server['KeepAlive'] is True and server['ProgramArguments'][-1]=='--demo-mode'
    assert backup['StartInterval']==3600 and '--apply' in backup['ProgramArguments']
    assert '--interval' not in backup['ProgramArguments']
    assert backup['Umask']==63 and backup['ProcessType']=='Background'
    for job in (server,backup):
        assert plistlib.loads(plistlib.dumps(job))==job
        assert set(job['EnvironmentVariables'])=={'PYTHONPATH','AHEM_KEK_FILE','PYTHONUNBUFFERED'}
        assert 'TOKEN' not in repr(job)
