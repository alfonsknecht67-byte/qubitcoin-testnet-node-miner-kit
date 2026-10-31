#!/usr/bin/env python3
"""One task per process; separate private configs and a per-task duplicate guard."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile

TASKS = ('qhash-cpu', 'deqode')

def task_settings(settings, task):
    if not isinstance(settings, dict):
        raise ValueError('settings must be a JSON object')
    tasks = settings.get('tasks', {})
    if not isinstance(tasks, dict) or any(k not in TASKS for k in tasks):
        raise ValueError('tasks must contain only qhash-cpu and/or deqode')
    selected = tasks.get(task, {})
    if not isinstance(selected, dict):
        raise ValueError('each task setting must be an object')
    # Old flat settings continue to configure qhash only. deqode starts small.
    fallback = settings if task == 'qhash-cpu' else {}
    threads = selected.get('threads', fallback.get('threads', 1))
    affinity = selected.get('affinity', fallback.get('affinity', 'auto' if task == 'qhash-cpu' else 'off'))
    if type(threads) is not int or not 1 <= threads <= 9999:
        raise ValueError('threads must be an integer from 1 to 9999')
    if affinity not in ('auto', 'off'):
        raise ValueError('affinity must be auto or off')
    return threads, affinity

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=TASKS, default='qhash-cpu')
    args = parser.parse_args(argv)
    base = Path.home() / 'qubitcoin-community-testnet'
    os.umask(0o077)
    settings_path = base / 'miner-settings.json'
    settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
    threads, affinity = task_settings(settings, args.task)
    # Refuse another kit-managed process for the same task, but allow the other task.
    lock = os.open(base / ('miner-' + args.task + '.lock'), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another kit-managed miner is already running for this task')
        os.set_inheritable(lock, True)
        user, password = (base / 'data/testnet/.cookie').read_text().strip().split(':', 1)
        address = (base / 'mining-address.txt').read_text().strip()
        config = base / ('miner-local.json' if args.task == 'qhash-cpu' else 'miner-deqode-local.json')
        options = {'algo': args.task, 'threads': threads,
            'url': 'http://127.0.0.1:18452', 'user': user, 'pass': password,
            'coinbase-addr': address, 'no-stratum': True, 'no-color': True, 'hash-meter': True}
        if affinity == 'off':
            options['cpu-affinity'] = '0'
        # Atomic replacement prevents partial configs; temporary file mode is 600.
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=base,
                                             prefix='.miner-config-', delete=False) as out:
                temp = Path(out.name)
                json.dump(options, out)
            temp.replace(config)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        miner = str(base / 'miner-source/qubitcoin-miner')
        os.execv(miner, [miner, '--config=' + str(config)])
    finally:
        os.close(lock)

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError):
        raise SystemExit('Miner setup failed: check local settings, node cookie, wallet address and task lock. No credentials logged.')
