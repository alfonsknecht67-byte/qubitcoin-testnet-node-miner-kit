"""Run the upgrade helper against a disposable kit and mocked privileged commands."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as temp:
    home=Path(temp);base=home/'qubitcoin-community-testnet';bin=base/'bin'
    bin.mkdir(parents=True);(base/'miner-source').mkdir()
    for p in [bin/'node-cli',base/'miner-source/qubitcoin-miner']:
        p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o700)
    (bin/'start-miner.py').write_text('# original launcher\n')
    (base/'miner-settings.json').write_text('{"threads":3,"affinity":"off"}')
    (base/'miner.log').write_text('existing private log remains\n')
    fake=home/'fake-bin';fake.mkdir()
    sudo=fake/'sudo'
    sudo.write_text("""#!/usr/bin/env python3
import json,os,sys,subprocess
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['MOCK_LOG'],'a') as f: f.write(json.dumps(args)+'\\n')
if args[0]=='install':
    target=Path(os.environ['MOCK_ETC'])/Path(args[-1]).name
    target.parent.mkdir(exist_ok=True)
    sys.exit(subprocess.run(args[:-1]+[str(target)]).returncode)
if args[0]=='cp': sys.exit(0)
if args[0]=='systemd-analyze' and args[1]=='verify': sys.exit(0)
if args==['systemctl','daemon-reload']: sys.exit(0)
raise SystemExit('unexpected privileged command: '+repr(args))
""")
    sudo.chmod(0o700)
    env=dict(os.environ,HOME=str(home),PATH=str(fake)+':'+os.environ['PATH'],
             MOCK_ETC=str(home/'fake-etc'),MOCK_LOG=str(home/'commands'))
    settings=(base/'miner-settings.json').read_bytes()
    for _ in range(2):
        subprocess.run(['bash',str(root/'update-dual-task.sh')],env=env,check=True,capture_output=True)
    assert (base/'miner-settings.json').read_bytes()==settings
    assert (base/'miner.log').read_text()=='existing private log remains\n'
    assert (base/'miner-deqode.log').stat().st_mode & 0o777==0o600
    assert (bin/'node-cli').read_text()=='#!/bin/sh\nexit 0\n'
    assert (bin/'testnet-monitor.py').exists()
    for name in ['qubitcoin-community-testnet-miner.service','qubitcoin-community-testnet-deqode.service']:
        assert (home/'fake-etc'/name).exists()
    calls=[json.loads(x) for x in (home/'commands').read_text().splitlines()]
    assert not any(x[0]=='systemctl' and x[1]!='daemon-reload' for x in calls)
print('PASS: upgrade twice preserves settings/logs/node wrapper, creates two units and performs no miner/service starts; sudo mocked.')
