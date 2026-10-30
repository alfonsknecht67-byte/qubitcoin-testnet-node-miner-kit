#!/usr/bin/env python3
"""Cookie authentication stays local; no credentials in command-line arguments."""
import json
import os
from pathlib import Path

base = Path.home() / 'qubitcoin-community-testnet'
user, password = (base / 'data/testnet/.cookie').read_text().strip().split(':', 1)
address = (base / 'mining-address.txt').read_text().strip()
os.umask(0o077)
config = base / 'miner-local.json'
config.write_text(json.dumps({'algo': 'qhash-cpu', 'threads': 1,
    'url': 'http://127.0.0.1:18452', 'user': user, 'pass': password,
    'coinbase-addr': address, 'no-stratum': True, 'no-color': True, 'hash-meter': True}))
config.chmod(0o600)
miner = str(base / 'miner-source/qubitcoin-miner')
os.execv(miner, [miner, '--config=' + str(config)])
