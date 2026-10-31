"""Read-only source/package checks; does not run the installer or miner."""
import ast
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
subprocess.run(['bash', '-n', str(ROOT / 'setup-testnet.sh')], check=True)
subprocess.run(['bash', '-n', str(ROOT / 'repair-log-permissions.sh')], check=True)
ast.parse((ROOT / 'start-miner.py').read_text())
subprocess.run(['bash', '-n', str(ROOT / 'update-dual-task.sh')], check=True)
for helper in ('miner-unit.py', 'testnet-monitor.py'):
    ast.parse((ROOT / helper).read_text())
for line in (ROOT / 'SHA256SUMS.txt').read_text().splitlines():
    digest, name = line.split('  ', 1)
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT), 'Checksum path escapes repository'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
for name in ('index.html', 'START-HERE.html'):
    text = (ROOT / name).read_text()
    assert not re.search(r'<(?:script|iframe)\b', text, re.I), name
    assert not re.search(r'<(?:img|link)\b[^>]*(?:src|href)\s*=', text, re.I), name
settings = (ROOT / 'setup-testnet.sh').read_text()
assert '--enable-wallet' in settings and '--with-sqlite=yes' in settings
assert '-mno-sha' in settings and 'rm -rf' not in settings and 'killall' not in settings
assert "fallback.get('threads', 1)" in (ROOT / 'start-miner.py').read_text()
assert settings.index('git apply "$KIT_DIR/miner-affinity-fix/linux-core-first.patch"') < settings.index('./autogen.sh >"$LOGS/miner-build.log"')
assert './affinity-test >"$LOGS/affinity-test.log"' in settings
ast.parse((ROOT / 'miner-affinity-fix/diagnose.py').read_text())
for test in ('test-launcher.py', 'test-dual-task.py', 'test-upgrade.py'):
    subprocess.run(['python3', str(ROOT / test)], check=True)
assert 'install -m 600 /dev/null "$BASE/miner.log"' in settings
assert settings.index('install -m 600 /dev/null "$BASE/miner.log"') < settings.index('bash "$KIT_DIR/update-dual-task.sh"')
with tempfile.TemporaryDirectory(prefix='testnet-log-check-') as temp:
    logfile = Path(temp) / 'miner.log'
    subprocess.run(['install', '-m', '600', '/dev/null', str(logfile)], check=True)
    assert logfile.stat().st_uid == os.getuid()
    assert logfile.stat().st_mode & 0o777 == 0o600
    with logfile.open('a') as stream:
        stream.write('log permission check\n')
    assert logfile.read_text() == 'log permission check\n'
upstream = json.loads((ROOT / 'UPSTREAM.json').read_text())
revision = upstream['node']['commit']
assert re.fullmatch(r'[0-9a-f]{40}', revision)
assert 'NODE_REV=' + revision in settings
assert 'MINER_REV=' + upstream['miner']['commit'] in settings
with tempfile.TemporaryDirectory(prefix='testnet-patch-check-') as temp:
    clean = Path(temp)
    for name in ('src/Makefile.am', 'src/crypto/qhash.cpp', 'src/crypto/qhash.h'):
        target = clean / name
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://raw.githubusercontent.com/super-quantum/qubitcoin/{revision}/{name}'
        with urllib.request.urlopen(url, timeout=30) as response:
            target.write_bytes(response.read())
    subprocess.run(['git', 'apply', '--check', str(ROOT / 'cpu-node.patch')], cwd=clean, check=True)
print('PASS: syntax, checksums, HTML resources, isolation settings and CPU patch applicability.')
print('Scope: source/package checks only; not a clean-machine installation or security certification.')
