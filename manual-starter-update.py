#!/usr/bin/env python3
"""Check/prepare a compatible custom kit. Installation and rollback require explicit actions.

Only the Python miner launcher can be replaced. No node/miner executable, wallet,
settings, service unit or service state is changed. The only RPC is getblockchaininfo
to the local testnet, with redirects and proxies disabled.
"""
import argparse
import ast
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent
TEMPLATE_SHA = '4bfc2ba189cd7b2bdc5d1535e65115ad458a02362f28472350f3cf577ca5d497'
MARKER = "base = Path.home() / 'qubitcoin-community-testnet'"
TASKS = ('qhash-cpu', 'deqode')


class UpdateError(ValueError):
    """Safe, fixed diagnostics without credentials or raw RPC/service output."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise UpdateError(message)


def owned_file(path, root, private=False):
    require(not path.is_symlink() and path.resolve().is_relative_to(root), 'Unexpected file link or path')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid(), 'Expected a user-owned regular file')
    if private:
        require(info.st_mode & 0o077 == 0, 'Private file permissions need review')
    return path.read_bytes()


def template(base, binary_relative='miner-source/qubitcoin-miner'):
    data = (ROOT / 'start-miner.py').read_bytes()
    require(sha(data) == TEMPLATE_SHA, 'Launcher template differs from this reviewed update tool')
    text = data.decode('utf8')
    require(text.count(MARKER) == 1, 'Launcher base is not unique')
    relative = str(base.relative_to(Path.home().resolve()))
    candidate = text.replace(MARKER, 'base = Path.home() / ' + repr(relative), 1)
    binary_marker = "miner = str(base / 'miner-source/qubitcoin-miner')"
    require(candidate.count(binary_marker) == 1, 'Launcher executable selection is not unique')
    candidate = candidate.replace(binary_marker, 'miner = str(base / ' + repr(binary_relative) + ')', 1)
    ast.parse(candidate)
    namespace = {'__name__': '_preflight_only'}
    exec(compile(text, '<reviewed launcher validators>', 'exec'), namespace)
    return candidate.encode('utf8'), namespace


def service_command(name):
    result = subprocess.run(['systemctl', 'show', name, '--property=ExecStart,MainPID', '--no-pager'],
                            capture_output=True, text=True, timeout=8, check=True)
    return result.stdout


def check_service(name, task, launcher, reader):
    require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_.@-]+\.service', name)
            and 'testnet' in name.lower() and 'main' not in name.lower(), 'Select a testnet miner service explicitly')
    raw = reader(name)
    match = re.search(r'argv\[\]=(.*?)\s*;', raw)
    require(match is not None, 'Service command format is not supported')
    args = shlex.split(match.group(1))
    require(str(launcher) in args, 'Service does not invoke the expected Python launcher')
    index = args.index(str(launcher))
    require(index in (1, 2) and re.fullmatch(r'python3(?:\.\d+)?', Path(args[0]).name)
            and (index == 1 or args[1] == '-u'), 'Unexpected launcher interpreter/options')
    accepted = [['--task', task], ['--task=' + task]]
    if task == 'qhash-cpu':
        accepted.append([])
    require(args[index + 1:] in accepted, 'Unexpected task arguments; no service is modified')
    return raw


def sha_file(path):
    return sha(path.read_bytes())


def selected_binary(source, base):
    """Read a static executable selection without running the old launcher."""
    tree = ast.parse(source.decode('utf8'))
    values = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'miner' for target in node.targets)]
    require(len(values) == 1, 'Existing miner executable selection is not a single supported static path')
    def path_value(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return Path(node.value)
        if isinstance(node, ast.Name) and node.id == 'base':
            return base
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return path_value(node.left) / path_value(node.right)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in ('str', 'Path') and len(node.args) == 1 and not node.keywords):
            return path_value(node.args[0])
        raise UpdateError('Existing miner executable path is dynamic; keep the existing starter for review')
    binary = path_value(values[0])
    if not binary.is_absolute():
        binary = base / binary
    require(binary.name == 'qubitcoin-miner' and binary.resolve().is_relative_to(base)
            and binary.is_file() and binary.stat().st_uid == os.getuid(),
            'Existing miner executable must be a user-owned file inside this installation')
    return binary


def read_chain(base):
    cookie = owned_file(base / 'data/testnet/.cookie', base, private=True).decode().strip()
    require(':' in cookie and '\n' not in cookie, 'Local cookie format is invalid')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    payload = json.dumps({'jsonrpc': '1.0', 'id': 'kit-read-only-check',
                          'method': 'getblockchaininfo', 'params': []}).encode()
    request = urllib.request.Request('http://127.0.0.1:18452', data=payload,
              headers={'Content-Type': 'application/json',
                       'Authorization': 'Basic ' + base64.b64encode(cookie.encode()).decode()})
    with opener.open(request, timeout=10) as response:
        data = json.load(response)
    require(data.get('error') is None and isinstance(data.get('result'), dict), 'Read-only RPC check failed')
    return data['result'].get('chain')


def inspect(base, services, service_reader=service_command, chain_reader=read_chain):
    base = Path(base).expanduser().absolute()
    home = Path.home().resolve()
    require(base != home and not base.is_symlink() and base.resolve().is_relative_to(home), 'Choose an installed folder inside your own home')
    base = base.resolve()
    require(base.is_dir() and base.stat().st_uid == os.getuid(), 'Installed folder must belong to this user')
    require(set(services) <= set(TASKS) and 'qhash-cpu' in services
            and len(set(services.values())) == len(services), 'Select distinct task services')
    launcher = base / 'bin/start-miner.py'
    files = {'bin/start-miner.py': owned_file(launcher, base)}
    directory = launcher.parent
    if not os.access(directory, os.W_OK | os.X_OK):
        info = directory.stat()
        message = 'The starter folder is not writable; no update was installed'
        if info.st_uid == 0 and info.st_gid == 0 and info.st_mode & 0o777 == 0o755:
            command = shlex.join(['sudo', '/usr/bin/chown', '--no-dereference', '--',
                                  f'{os.getuid()}:{os.getgid()}', str(directory)])
            message += '\nIts administrator-owned folder can be returned to your user with:\n' + command
            message += '\nThis changes only the folder owner, not its files. Then reopen the update menu'
        else:
            message += '; its ownership/permissions need administrator review'
        raise UpdateError(message)
    binary = selected_binary(files['bin/start-miner.py'], base)
    binary_relative = str(binary.relative_to(base))
    binary_sha256 = sha_file(binary)
    candidate, validators = template(base, binary_relative)
    settings_path = base / 'miner-settings.json'
    if settings_path.exists():
        files['miner-settings.json'] = owned_file(settings_path, base)
    settings = json.loads(files.get('miner-settings.json', b'{}'))
    files['mining-address.txt'] = owned_file(base / 'mining-address.txt', base)
    address = files['mining-address.txt'].decode().strip()
    require(bool(address), 'Mining address file is empty')
    allowed = os.sched_getaffinity(0)
    workers, last_workers, running_binary_checks = {}, {}, {}
    for task, service in services.items():
        command = check_service(service, task, launcher, service_reader)
        pid = re.search(r'(?m)^MainPID=(\d+)\s*$', command)
        running_binary_checks[task] = bool(pid and int(pid.group(1)))
        if pid and int(pid.group(1)):
            require(sha_file(Path('/proc') / pid.group(1) / 'exe') == binary_sha256,
                    'Running miner differs from the selected executable; review before updating')
        workers[task], _ = validators['task_settings'](settings, task)
        validators['resource_settings'](settings, task, allowed)
        name = 'miner-local.json' if task == 'qhash-cpu' else 'miner-deqode-local.json'
        files[name] = owned_file(base / name, base, private=True)
        config = json.loads(files[name])
        from urllib.parse import urlsplit
        url = urlsplit(config.get('url', ''))
        require(config.get('algo') == task and config.get('coinbase-addr') == address,
                'Existing task/payout settings do not match the supported layout')
        require(url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost', '::1')
                and url.port == 18452 and url.path in ('', '/') and not url.username
                and not url.query and not url.fragment, 'Expected local testnet RPC on port 18452')
        last_workers[task] = config.get('threads') if type(config.get('threads')) is int else None
    require(chain_reader(base) == 'test', 'The local RPC did not confirm the test chain')
    return {'base': str(base), 'services': services, 'chain': 'test',
            'configured_workers': workers, 'last_config_workers': last_workers,
            'worker_counts_differ': workers != last_workers,
            'miner_binary_relative': binary_relative, 'miner_binary_sha256': binary_sha256,
            'running_binary_checks': running_binary_checks,
            'files_sha256': {name: sha(data) for name, data in files.items()},
            'candidate_sha256': sha(candidate), '_files': files, '_candidate': candidate}


def prepare(state):
    base = Path(state['base'])
    directory = Path(tempfile.mkdtemp(prefix='manual-kit-update.', dir=base))
    directory.chmod(0o700)
    for name, data in state['_files'].items():
        path = directory / 'original' / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o600)
    (directory / 'new-start-miner.py').write_bytes(state['_candidate'])
    (directory / 'new-start-miner.py').chmod(0o700)
    plan = {key: value for key, value in state.items() if not key.startswith('_')}
    plan.update(schema=1, created_at_utc=datetime.now(timezone.utc).isoformat())
    (directory / 'plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf8')
    (directory / 'plan.json').chmod(0o600)
    return directory


def replace_launcher(base, data):
    destination = base / 'bin/start-miner.py'
    owned_file(destination, base)
    fd, name = tempfile.mkstemp(prefix='.qtc-starter.', dir=destination.parent)
    try:
        os.fchmod(fd, 0o700)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)


def apply_prepared(directory, rollback=False, inspector=inspect):
    directory = Path(directory).expanduser().absolute()
    require(not directory.is_symlink() and directory.is_dir()
            and directory.name.startswith('manual-kit-update.'), 'Choose the prepared private update directory')
    require(directory.stat().st_uid == os.getuid() and directory.stat().st_mode & 0o077 == 0,
            'Prepared directory must be private and owned by this user')
    plan = json.loads(owned_file(directory / 'plan.json', directory, private=True))
    base = directory.parent.resolve()
    require(plan.get('schema') == 1 and plan.get('base') == str(base), 'Prepared plan belongs to another installation')
    current = inspector(base, plan['services'])
    require(current['miner_binary_relative'] == plan.get('miner_binary_relative')
            and current['miner_binary_sha256'] == plan.get('miner_binary_sha256'),
            'Miner executable selection changed or this plan predates executable-preservation checks; prepare again')
    require(current['files_sha256'].get('miner-settings.json') == plan['files_sha256'].get('miner-settings.json'),
            'Settings changed after preparation; prepare and review again')
    old = owned_file(directory / 'original/bin/start-miner.py', directory, private=True)
    new = owned_file(directory / 'new-start-miner.py', directory, private=True)
    require(sha(old) == plan['files_sha256']['bin/start-miner.py']
            and sha(new) == plan['candidate_sha256'] == current['candidate_sha256'], 'Prepared file checksum mismatch')
    active = current['files_sha256']['bin/start-miner.py']
    expected, target = (sha(new), old) if rollback else (sha(old), new)
    if active == sha(target):
        return 'Already at the requested launcher version; nothing replaced.'
    require(active == expected, 'Installed launcher changed after preparation; refusing overwrite')
    replace_launcher(base, target)
    return 'Launcher restored.' if rollback else 'Launcher installed. Current miner processes are unchanged; settings and services were not edited.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path)
    parser.add_argument('--qhash-service')
    parser.add_argument('--deqode-service')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--prepare', action='store_true')
    actions.add_argument('--install-prepared', type=Path)
    actions.add_argument('--rollback-prepared', type=Path)
    args = parser.parse_args()
    try:
        require(os.name == 'posix' and hasattr(os, 'sched_getaffinity') and os.getuid() != 0,
                'Run inside Linux/Ubuntu as the original normal user, not root')
        if args.install_prepared or args.rollback_prepared:
            require(not (args.base or args.qhash_service or args.deqode_service), 'Do not mix prepared actions with a new base/service selection')
            print(apply_prepared(args.install_prepared or args.rollback_prepared, bool(args.rollback_prepared)))
            return
        require(args.base and args.qhash_service, '--base and --qhash-service are required')
        services = {'qhash-cpu': args.qhash_service}
        if args.deqode_service:
            services['deqode'] = args.deqode_service
        state = inspect(args.base, services)
        print('Compatible layout and test chain confirmed. Configured workers for next start:', json.dumps(state['configured_workers']))
        if state['worker_counts_differ']:
            print('REVIEW: configured workers differ from the last miner configs. Existing settings will be preserved.')
        if args.prepare:
            print('Prepared private update:', prepare(state))
            print('The installed launcher has not been replaced. Review the guide before --install-prepared.')
        else:
            print('Read-only check completed. No files or service states changed. Use --prepare only when ready.')
    except UpdateError as error:
        parser.exit(2, 'STOP: ' + str(error) + '. Keep your existing installation and backups.\n')
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        parser.exit(2, 'STOP: compatibility check or requested action failed. Keep the existing installation and private backups; do not run fresh setup as a workaround.\n')


if __name__ == '__main__':
    main()
