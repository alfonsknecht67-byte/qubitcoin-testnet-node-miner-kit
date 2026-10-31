#!/usr/bin/env python3
"""Render only the two dedicated testnet miner units; no commands are executed."""
import argparse
import os
from pathlib import Path

def render(base, user, task):
    if task not in ('qhash-cpu', 'deqode') or not str(base).startswith('/') or any(c.isspace() or c in '%\\' for c in str(base)):
        raise ValueError('unsupported task or unsafe home path')
    if not user or any(not(c.isalnum() or c in '_-') for c in user):
        raise ValueError('unsupported username')
    log = 'miner.log' if task == 'qhash-cpu' else 'miner-deqode.log'
    return f"""[Unit]
Description=Qubitcoin Community Testnet {task} Miner
After=qubitcoin-community-testnet-node.service
Requires=qubitcoin-community-testnet-node.service
PartOf=qubitcoin-community-testnet-node.service
StartLimitIntervalSec=0
[Service]
Type=simple
User={user}
WorkingDirectory={base}
ExecStartPre={base}/bin/node-cli -rpcwait -rpcwaittimeout=60 getblockcount
ExecStart=/usr/bin/python3 {base}/bin/start-miner.py --task {task}
StandardOutput=append:{base}/{log}
StandardError=append:{base}/{log}
Restart=on-failure
RestartSec=10
TimeoutStartSec=75
TimeoutStopSec=30
Nice=10
UMask=0077
[Install]
WantedBy=multi-user.target
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=('qhash-cpu', 'deqode'))
    args = parser.parse_args()
    import pwd
    print(render(Path.home()/'qubitcoin-community-testnet', pwd.getpwuid(os.getuid()).pw_name, args.task), end='')
