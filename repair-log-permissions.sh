#!/usr/bin/env bash
# Repair an existing kit installation without restarting anything or truncating logs.
set -euo pipefail
if (( EUID == 0 )); then echo 'Run as your normal Ubuntu user, not as root.'; exit 1; fi
BASE="$HOME/qubitcoin-community-testnet"
LOG="$BASE/miner.log"
if [[ ! -d "$BASE" || -L "$BASE" || -L "$LOG" ]]; then
  echo 'Expected a normal community testnet directory and log file. Ask for help.'; exit 1
fi
if [[ -e "$LOG" ]]; then
  [[ -f "$LOG" ]] || { echo 'The log path is not a regular file. Ask for help.'; exit 1; }
  sudo chown "$(id -u):$(id -g)" -- "$LOG"
  chmod 600 "$LOG"
else
  install -m 600 /dev/null "$LOG"
fi
echo 'Miner log permissions repaired. No service was stopped and no log was erased.'
echo 'Read it with: tail -n 20 ~/qubitcoin-community-testnet/miner.log'
