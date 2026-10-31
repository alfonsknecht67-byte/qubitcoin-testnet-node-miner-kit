#!/usr/bin/env python3
"""Local community-testnet monitor. Never controls the node or mainnet."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time

BASE = Path.home()/'qubitcoin-community-testnet'
SERVICES = {'qhash-cpu':'qubitcoin-community-testnet-miner.service',
            'deqode':'qubitcoin-community-testnet-deqode.service'}
LOGS = {'qhash-cpu':'miner.log', 'deqode':'miner-deqode.log'}
ACTIONS = {'1':('start',('qhash-cpu',)), '2':('stop',('qhash-cpu',)),
           '3':('start',('deqode',)), '4':('stop',('deqode',)),
           '5':('start',('qhash-cpu','deqode')), '6':('stop',('qhash-cpu','deqode'))}

def command(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=8)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired): return None

def service_status(task):
    raw = command(['systemctl','show',SERVICES[task],'-p','ActiveState','-p','MainPID']) or ''
    fields = dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
    state = fields.get('ActiveState','unavailable')
    try:
        pid = int(fields.get('MainPID','0'))
        if pid > 1:
            proc = Path('/proc')/str(pid)
            args = (proc/'cmdline').read_bytes().split(b'\0')
            config = BASE/('miner-local.json' if task == 'qhash-cpu' else 'miner-deqode-local.json')
            # Do not mislabel an unexpected process as mining.
            if (proc/'exe').resolve() != (BASE/'miner-source/qubitcoin-miner').resolve() or ('--config='+str(config)).encode() not in args:
                return 'starting / unverified', None
            for line in (proc/'status').read_text().splitlines():
                if line.startswith('State:') and line.split(':',1)[1].strip().startswith(('T','t')):
                    return 'paused', pid
            return state, pid
    except (ValueError, OSError): pass
    return state, None

def recent_rate(task, since=0, now=None):
    now = time.time() if now is None else now
    try:
        with (BASE/LOGS[task]).open('rb') as f:
            f.seek(0,2);f.seek(max(0,f.tell()-262144))
            text=f.read().decode(errors='replace')
    except OSError: return None
    samples={}
    for stamp, worker, rate, scale in re.findall(
        r"\[([^\]]+)\] Thread\s+(\d+).*?:\s*([\d.]+)\s*([kMGT]?)h/s", text):
        try:
            ts=datetime.strptime(stamp,'%Y-%m-%d %H:%M:%S').timestamp()
            if ts >= since and 0 <= now-ts <= 30:
                samples[int(worker)] = float(rate)*{'':1,'k':1e3,'M':1e6,'G':1e9,'T':1e12}[scale]
        except ValueError: continue
    return sum(samples.values()) if samples else None

def process_started(pid):
    try:
        stat=(Path('/proc')/str(pid)/'stat').read_text()
        ticks=int(stat[stat.rfind(')')+2:].split()[19])
        boot=int(next(x.split()[1] for x in Path('/proc/stat').read_text().splitlines() if x.startswith('btime ')))
        return boot+ticks/os.sysconf('SC_CLK_TCK')
    except (OSError, ValueError, StopIteration): return time.time()

def show():
    print('QUBITCOIN COMMUNITY TESTNET — TWO-TASK MONITOR')
    raw=command([str(BASE/'bin/node-cli'),'getblockchaininfo'])
    try:
        chain=json.loads(raw or '{}')
        print('Chain:',chain.get('chain','unavailable'),' Block:',chain.get('blocks','?'))
    except ValueError: print('Node RPC unavailable')
    for task in SERVICES:
        state,pid=service_status(task)
        rate=recent_rate(task, process_started(pid)) if pid and state=='active' else None
        # These are task-specific meter units, not comparable aggregate hashpower.
        print(f'{task}: {state}; PID {pid or "—"}; recent worker sum: '+
              (f'{rate:.2f} h/s (miner-reported)' if rate is not None else 'no fresh active sample'))
    try:
        settings=json.loads((BASE/'miner-settings.json').read_text())
        tasks=settings.get('tasks',{})
        counts={t:tasks.get(t,{}).get('threads',settings.get('threads',1) if t=='qhash-cpu' else 1) for t in SERVICES}
        print('Configured workers (next start):',counts)
    except (OSError,ValueError,TypeError,AttributeError):
        print('Configured workers: check miner-settings.json')
    print('Do not add qhash and deqode rates together. Logs remain separate.')
    print('[1] Start qhash  [2] Stop qhash  [3] Start deqode  [4] Stop deqode')
    print('[5] Start both  [6] Stop both  [Enter] Refresh  [Q] Quit')
    print('Actions require YES and may ask for your Ubuntu password. Node is never stopped.')

def control(key):
    if key not in ACTIONS: return False
    verb,tasks=ACTIONS[key]
    args=['systemctl',verb]+[SERVICES[t] for t in tasks]
    if os.geteuid()!=0: args=['sudo']+args
    try: return subprocess.run(args,timeout=90).returncode==0
    except (OSError,subprocess.TimeoutExpired): return False

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true');args=parser.parse_args()
    while True:
        show()
        if args.once: return
        try: key=input('Choose: ').strip().lower()
        except (EOFError,KeyboardInterrupt): return
        if key=='q': return
        if key in ACTIONS:
            verb,tasks=ACTIONS[key]
            if input(f'{verb.upper()} {", ".join(tasks)}? Type YES: ').strip()=='YES':
                print('Completed.' if control(key) else 'Action failed; check service status.')

if __name__=='__main__': main()
