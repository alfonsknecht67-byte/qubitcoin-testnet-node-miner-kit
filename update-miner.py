#!/usr/bin/env python3
"""Guided, manual update of an existing compatible testnet miner launcher."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('manual_starter_update', ROOT/'manual-starter-update.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def choose(title, items, ask=input, say=print):
    say(title)
    for index, (label, _) in enumerate(items, 1):
        say(f'  [{index}] {label}')
    say('  [Q] Exit without further changes')
    while True:
        value = ask('Choose a number: ').strip()
        if value.lower() in ('', 'q'):
            return None
        if value.isdigit() and 1 <= int(value) <= len(items):
            return items[int(value)-1][1]
        say('Please enter one of the listed numbers, or Q.')


def installations(home):
    candidates = []
    for base in home.iterdir():
        try:
            if (base.is_dir() and not base.is_symlink()
                and (base/'bin/start-miner.py').is_file()
                and (base/'miner-source/qubitcoin-miner').is_file()):
                candidates.append(base)
        except OSError:
            continue
    return sorted(candidates, key=lambda p: p.name)


def select_installation(home, ask=input, say=print):
    items = [(str(path), path) for path in installations(home)]
    items.append(('Enter a different installation folder', 'manual'))
    value = choose('Which existing testnet installation do you want to check?', items, ask, say)
    if value == 'manual':
        typed = ask('Installed folder (for example ~/qubitcoin-testnet; Q to exit): ').strip()
        return None if typed.lower() in ('', 'q') else Path(typed).expanduser().absolute()
    return value


def list_services():
    result = subprocess.run(['systemctl','list-unit-files','--type=service','--no-legend','--no-pager'],
                            capture_output=True,text=True,timeout=10,check=True)
    return [line.split()[0] for line in result.stdout.splitlines()
            if line.split() and 'testnet' in line.split()[0].lower()
            and 'main' not in line.split()[0].lower()]


def identify_services(base, names, reader=None):
    reader = reader or m.service_command
    found = {task: [] for task in m.TASKS}
    launcher = base/'bin/start-miner.py'
    for name in names:
        raw = reader(name)
        if str(launcher) not in raw:
            continue
        matched = False
        for task in m.TASKS:
            try:
                m.check_service(name, task, launcher, lambda _: raw)
            except m.UpdateError:
                continue
            found[task].append(name); matched = True
        m.require(matched, 'An existing testnet service uses unsupported launcher arguments')
    m.require(len(found['qhash-cpu']) == 1 and len(found['deqode']) <= 1,
              'Could not identify exactly one QHash service and at most one deqode service')
    return {task: names[0] for task,names in found.items() if names}


def update_flow(base, names, ask=input, say=print, reader=None):
    services = identify_services(base, names, reader)
    say('\nStep 1 of 3: checking your existing testnet setup...')
    state = m.inspect(base, services)
    say('Testnet confirmed. Your node, wallet, miner executable and settings will be kept.')
    for task,count in state['configured_workers'].items():
        say(f'  {task}: {count} configured worker(s) at the next start')
    if state['worker_counts_differ']:
        say('REVIEW: these settings differ from the last miner launch. Exit if this was not intended.')
    action = choose('\nStep 2 of 3: prepare a private backup?',
                    [('Create backup and prepare the new launcher', 'prepare')], ask, say)
    if action is None:
        return
    directory = m.prepare(state)
    say('Private backup and prepared launcher: '+str(directory))
    say('\nStep 3 of 3: replace only the miner launcher.')
    say('Custom edits in the old starter are backed up, not merged into the new kit starter.')
    say('Running nodes/miners continue. No service will be restarted and no settings will be changed.')
    if ask('Type UPDATE to install, or press Enter to keep the prepared backup only: ').strip() != 'UPDATE':
        say('Not installed. Your existing launcher remains in place; the private backup is kept.')
        return
    say(m.apply_prepared(directory))
    say('Done. The new launcher is available for the next normal miner start.')
    say('Optional CPU/RAM recommendations remain separate; this update does not apply them.')


def restore_flow(base, ask=input, say=print):
    items = []
    for directory in base.glob('manual-kit-update.*'):
        try:
            plan = json.loads(m.owned_file(directory/'plan.json', directory, private=True))
            if plan.get('base') == str(base.resolve()):
                label = str(plan.get('created_at_utc','date unavailable'))+' — '+directory.name
                items.append((label,directory))
        except (OSError,ValueError):
            continue
    m.require(bool(items),'No compatible prepared backup was found in this installation')
    selected = choose('Choose the launcher backup to restore:',sorted(items,reverse=True),ask,say)
    if selected is None:
        return
    say('Only the launcher will be restored. No wallet, settings or service state will change.')
    if ask('Type RESTORE to continue, or press Enter to cancel: ').strip() == 'RESTORE':
        say(m.apply_prepared(selected,rollback=True))
    else:
        say('Restoration cancelled.')


def main(ask=input,say=print):
    try:
        m.require(os.name=='posix' and hasattr(os,'sched_getaffinity') and os.getuid()!=0,
                  'Run this menu inside your existing Ubuntu as the original normal user')
        say('QUBITCOIN TESTNET — GUIDED MINER LAUNCHER UPDATE')
        say('This updates the starter only. It does not rebuild or restart your node or miner.')
        action = choose('What would you like to do?',
                        [('Check and update an existing miner','update'),
                         ('Restore a previously backed-up launcher','restore')],ask,say)
        if action is None:
            return
        base = select_installation(Path.home().resolve(),ask,say)
        if base is None:
            return
        if action=='restore':
            restore_flow(base,ask,say)
        else:
            update_flow(base.resolve(),list_services(),ask,say)
    except m.UpdateError as error:
        say('STOP: '+str(error)+'.')
        say('Keep your existing installation and backups. See MANUAL-UPDATE.md; do not run fresh setup as a workaround.')
        return 2
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        say('STOP: a check could not be completed. Keep your private backups and existing installation; see MANUAL-UPDATE.md.')
        return 2
    except (EOFError,KeyboardInterrupt):
        say('\nMenu closed. Any prepared private backup is kept.')
        return 0


if __name__=='__main__':raise SystemExit(main())
