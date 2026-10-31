#!/usr/bin/env bash
# Update helper files and miner units only. Never start/stop/restart any service.
set -Eeuo pipefail
umask 077
KIT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE="$HOME/qubitcoin-community-testnet"
if (( EUID == 0 )); then echo 'Run as the normal Ubuntu user, not root.'; exit 1; fi
[[ -d "$BASE/bin" && -x "$BASE/bin/node-cli" && -x "$BASE/miner-source/qubitcoin-miner" ]] || {
 echo 'Existing community kit not found. Use FRESH-INSTALL.md; do not delete wallets.'; exit 1;
}
[[ $(stat -c %u "$BASE") == "$EUID" ]] || { echo 'Kit directory must belong to this user.'; exit 1; }
for name in start-miner.py miner-unit.py testnet-monitor.py; do
 [[ -f "$KIT_DIR/$name" ]] || { echo 'Extract the complete current source kit.'; exit 1; }
done
# Preflight settings and generated units before changing installed helpers.
python3 - "$BASE" "$KIT_DIR" <<'PY'
import importlib.util, json, sys
from pathlib import Path
base, source = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('launcher', source/'start-miner.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
settings = json.loads((base/'miner-settings.json').read_text()) if (base/'miner-settings.json').exists() else {}
for task in m.TASKS: m.task_settings(settings, task)
PY
backup=$(mktemp -d "$BASE/dual-task-backup.XXXXXX")
for name in start-miner.py testnet-monitor.py; do
 [[ ! -f "$BASE/bin/$name" ]] || cp -p "$BASE/bin/$name" "$backup/$name"
done
for task in qhash-cpu deqode; do
 unit=qubitcoin-community-testnet-miner.service
 log=miner.log
 if [[ "$task" == deqode ]]; then unit=qubitcoin-community-testnet-deqode.service; log=miner-deqode.log; fi
 if [[ -e "$BASE/$log" ]]; then
  [[ -f "$BASE/$log" && ! -L "$BASE/$log" && $(stat -c %u "$BASE/$log") == "$EUID" ]] || {
   echo 'Log ownership/type needs repair; no log was overwritten.'; exit 1;
  }
 else
  install -m 600 /dev/null "$BASE/$log"
 fi
 python3 "$KIT_DIR/miner-unit.py" "$task" > "$backup/$unit.new"
 if [[ -f "/etc/systemd/system/$unit" ]]; then
  sudo cp -p "/etc/systemd/system/$unit" "$backup/$unit.before"
 fi
done
if [[ ! -f "$BASE/miner-settings.json" ]]; then
 printf '{"threads":1,"affinity":"auto","tasks":{"deqode":{"threads":1,"affinity":"off"}}}\n' > "$BASE/miner-settings.json"
fi
install -m 700 "$KIT_DIR/start-miner.py" "$BASE/bin/start-miner.py"
install -m 700 "$KIT_DIR/testnet-monitor.py" "$BASE/bin/testnet-monitor.py"
for unit in qubitcoin-community-testnet-miner.service qubitcoin-community-testnet-deqode.service; do
 sudo install -m 644 "$backup/$unit.new" "/etc/systemd/system/$unit"
done
sudo systemd-analyze verify /etc/systemd/system/qubitcoin-community-testnet-miner.service /etc/systemd/system/qubitcoin-community-testnet-deqode.service
sudo systemctl daemon-reload
printf 'Updated. Backups: %s\n' "$backup"
echo 'No service was started, stopped, enabled or restarted. Existing miner settings and logs were preserved.'
echo 'Read DUAL-TASK.md before starting either task. Node and wallet were not replaced.'
