"""Exercise the entry point in disposable homes; never run real services/setup."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
for case in ('fresh', 'old', 'current', 'cancel', 'partial', 'failed-update'):
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp)
        kit = home / 'download'
        kit.mkdir()
        base = home / 'qubitcoin-community-testnet'
        calls = home / 'calls'
        (kit / 'start-testnet.sh').write_bytes((ROOT / 'start-testnet.sh').read_bytes())
        monitor = "from pathlib import Path\nimport os\nwith open(os.environ['CALLS'],'a') as f: f.write('monitor\\n')\n"
        (kit / 'testnet-monitor.py').write_text(monitor)
        for name in ('start-miner.py', 'miner-unit.py'):
            (kit / name).write_text('# current helper\n')
        installer = '''#!/usr/bin/env bash
set -eu
echo INSTALL >> "$CALLS"
mkdir -p "$HOME/qubitcoin-community-testnet/bin"
cp "$KIT/testnet-monitor.py" "$HOME/qubitcoin-community-testnet/bin/testnet-monitor.py"
'''
        (kit / 'setup-testnet.sh').write_text(installer)
        (kit / 'update-dual-task.sh').write_text(
            'exit 9\n' if case == 'failed-update' else installer.replace('INSTALL', 'UPDATE'))
        (kit / 'repair-log-permissions.sh').write_text('echo REPAIR >> "$CALLS"\n')
        if case != 'fresh':
            (base / 'bin').mkdir(parents=True)
            (base / 'wallet-marker').write_text('preserve wallet')
            if case != 'partial':
                (base / 'miner-source').mkdir()
                for name in ('bin/node-cli', 'miner-source/qubitcoin-miner'):
                    p = base / name
                    p.write_text('#!/bin/sh\nexit 0\n')
                    p.chmod(0o700)
            if case == 'current':
                for name in ('testnet-monitor.py', 'start-miner.py'):
                    (base / 'bin' / name).write_bytes((kit / name).read_bytes())
        fake = home / 'fake-bin'
        fake.mkdir()
        ctl = fake / 'systemctl'
        ctl.write_text('#!/bin/sh\n[ "$*" = "cat qubitcoin-community-testnet-deqode.service" ] || exit 98\nexit 0\n')
        ctl.chmod(0o700)
        env = dict(os.environ, HOME=str(home), KIT=str(kit), CALLS=str(calls),
                   PATH=str(fake) + ':' + os.environ['PATH'])
        result = subprocess.run(['bash', str(kit / 'start-testnet.sh')], env=env,
                                input='\n' if case == 'cancel' else 'UPDATE\n',
                                text=True, capture_output=True)
        expected = {'fresh': 'INSTALL\nmonitor\n', 'old': 'UPDATE\nmonitor\n',
                    'current': 'monitor\n', 'cancel': '', 'partial': '', 'failed-update': ''}[case]
        assert (calls.read_text() if calls.exists() else '') == expected, (case, result.stderr)
        assert (result.returncode == 0) == (case not in ('partial', 'failed-update')), case
        if case != 'fresh':
            assert (base / 'wallet-marker').read_text() == 'preserve wallet'
print('PASS: fresh setup, old/current menu, cancellation, partial install and update failure; all setup/services mocked.')
