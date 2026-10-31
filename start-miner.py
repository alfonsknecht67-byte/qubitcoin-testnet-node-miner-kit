#!/usr/bin/env python3
"""Cookie authentication stays local; no credentials in command-line arguments."""
import json
import os
from pathlib import Path

base = Path.home() / 'qubitcoin-community-testnet'
# Durable operator settings; RPC credentials and payout stay separate and local.
settings_path = base / 'miner-settings.json'
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
threads = settings.get('threads', 1)
if type(threads) is not int or not 1 <= threads <= 9999:
    raise SystemExit('miner-settings.json: threads must be an integer from 1 to 9999')
affinity = settings.get('affinity', 'auto')
if affinity not in ('auto', 'off'):
    raise SystemExit('miner-settings.json: affinity must be auto or off')
user, password = (base / 'data/testnet/.cookie').read_text().strip().split(':', 1)
address = (base / 'mining-address.txt').read_text().strip()
os.umask(0o077)
config = base / 'miner-local.json'
options = {'algo': 'qhash-cpu', 'threads': threads,
    'url': 'http://127.0.0.1:18452', 'user': user, 'pass': password,
    'coinbase-addr': address, 'no-stratum': True, 'no-color': True, 'hash-meter': True}
if affinity == 'off':
    options['cpu-affinity'] = '0'
config.write_text(json.dumps(options))
config.chmod(0o600)
miner = str(base / 'miner-source/qubitcoin-miner')
os.execv(miner, [miner, '--config=' + str(config)])
