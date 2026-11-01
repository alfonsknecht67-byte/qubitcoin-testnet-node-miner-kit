#!/usr/bin/env bash
# One entry point for a fresh setup or the installed two-task monitor.
set -Eeuo pipefail
KIT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE="$HOME/qubitcoin-community-testnet"
if (( EUID == 0 )); then echo 'Run as your normal Ubuntu user, not root.'; exit 1; fi
for name in setup-testnet.sh update-dual-task.sh repair-log-permissions.sh start-miner.py miner-unit.py testnet-monitor.py; do
  [[ -f "$KIT_DIR/$name" ]] || { echo 'Extract the complete current source kit first.'; exit 1; }
done
if [[ -L "$BASE" ]]; then echo 'The installed directory is a symbolic link. Ask for help before updating.'; exit 1; fi
if [[ ! -e "$BASE" ]]; then
  bash "$KIT_DIR/setup-testnet.sh"
else
  [[ -x "$BASE/bin/node-cli" && -x "$BASE/miner-source/qubitcoin-miner" ]] || {
    echo 'An existing or incomplete installation was found. Nothing was overwritten.'
    echo 'Keep the wallet directory and ask for help with the original setup error.'; exit 1;
  }
  update_needed=0
  for name in start-miner.py testnet-monitor.py; do
    cmp -s "$KIT_DIR/$name" "$BASE/bin/$name" || update_needed=1
  done
  systemctl cat qubitcoin-community-testnet-deqode.service >/dev/null 2>&1 || update_needed=1
  if (( update_needed )); then
    echo 'The installed menu/task helpers need an update from this downloaded kit.'
    echo 'This preserves the node, wallet, worker settings and log contents.'
    echo 'No node or miner is started, stopped or restarted by the helper update.'
    read -r -p 'Type UPDATE to install the menu/task helpers, or Enter to cancel: ' answer
    [[ "$answer" == UPDATE ]] || { echo 'Cancelled. Nothing changed.'; exit 0; }
    if [[ -e "$BASE/miner.log" && ( ! -O "$BASE/miner.log" || ! -r "$BASE/miner.log" ) ]]; then
      bash "$KIT_DIR/repair-log-permissions.sh"
    fi
    bash "$KIT_DIR/update-dual-task.sh"
  fi
fi
echo 'Opening the two-task monitor. Opening it does not start mining.'
exec python3 "$BASE/bin/testnet-monitor.py"
