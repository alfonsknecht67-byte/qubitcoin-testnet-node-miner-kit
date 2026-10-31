# qhash-cpu and deqode: run one or both testnet tasks

The official miner runs one algorithm per process. This kit now provides **two separate services** using the same locally built executable, testnet node, wallet and payout address:

| Task | Service | Log | Generated private config |
|---|---|---|---|
| qhash-cpu / task 0 | `qubitcoin-community-testnet-miner.service` | `miner.log` | `miner-local.json` |
| deqode / task 1 | `qubitcoin-community-testnet-deqode.service` | `miner-deqode.log` | `miner-deqode-local.json` |

Each process requests the correct task templates from the node. This is not a single process automatically switching tasks, and it does not guarantee higher performance or rewards. The node validates both block types even with both miners stopped.

## New installation

Follow [FRESH-INSTALL.md](FRESH-INSTALL.md) using the **current source ZIP**. The installer builds both algorithms and offers `QHASH`, `DEQODE`, `BOTH` or Enter for node-only. Fresh installations start with one worker per selected task. Older release ZIPs are unchanged.

## Update an existing community kit

No new node build, blockchain download, wallet creation or WSL reinstall is needed. Download and extract the current source ZIP into `C:\qtc-testnet-kit` (replace the source-kit files, not your installed wallet directory). Inside Ubuntu:

```bash
bash /mnt/c/qtc-testnet-kit/update-dual-task.sh
```

The helper backs up the installed launcher/monitor and existing service units in a private `dual-task-backup.*` folder, installs the two task services and monitor, and reloads systemd's unit definitions. It preserves existing worker settings and log contents. **It does not start, stop, restart or enable either miner, and does not change the node or wallet.** Existing processes keep running their current code/settings until you choose a stop/start. Use the kit's normal Ubuntu user, not root. This helper targets installations in `~/qubitcoin-community-testnet`; it refuses other layouts.

The pinned build made by this kit already includes deqode. If you replaced that executable with a custom build lacking deqode, rebuild both tasks using the documented affinity build route before enabling deqode. No automatic binary replacement is performed by this helper.

## Configure CPU use before starting

Inside Ubuntu:

```bash
nano "$HOME/qubitcoin-community-testnet/miner-settings.json"
```

For a cautious simultaneous test, use:

```json
{
  "tasks": {
    "qhash-cpu": {"threads": 1, "affinity": "off"},
    "deqode": {"threads": 1, "affinity": "off"}
  }
}
```

Old flat `threads` and `affinity` settings still apply to qhash-cpu. Task-specific settings override them. Without deqode settings, deqode defaults to **one worker and affinity off**; it never inherits an old high qhash worker count. Updating does not reduce your existing qhash count automatically: inspect it before choosing BOTH.

Two separate miners do not coordinate core-first binding. Setting `auto` on both can pin their first workers to the same core. For simultaneous use, begin with affinity off for both so Linux schedules them, or deliberately use separate externally assigned CPU sets if you understand your topology. This is not NUMA/socket optimization.

Both processes compete for CPU/cache/memory and electricity. deqode's solver has a default pattern-list budget of 64 MiB per worker, **not a hard limit on total process memory**; additional solver data and overhead also consume RAM. Start small and measure temperature and responsiveness. Keeping one task stopped is completely valid. Task-specific meter rates must not be added or directly compared as equivalent hashpower.

## Open the monitor

```bash
python3 "$HOME/qubitcoin-community-testnet/bin/testnet-monitor.py"
```

- `1`: start qhash; `2`: stop qhash.
- `3`: start deqode; `4`: stop deqode.
- `5`: start both; `6`: stop both.
- Enter: refresh; `Q`: close monitor without stopping anything.

Every action requires `YES`, and sudo may ask for your Ubuntu password. The monitor shows each service and its own recent worker-rate samples separately. Paused processes are labelled paused; their historical average CPU/rate is not shown as current activity. The controls are restricted to the two named kit miner services and never stop the node or mainnet.

Command-line alternatives:

```bash
# Start both (only when you are ready for the extra CPU load):
sudo systemctl start qubitcoin-community-testnet-miner.service qubitcoin-community-testnet-deqode.service
# Stop both to save CPU; leave the node running:
sudo systemctl stop qubitcoin-community-testnet-miner.service qubitcoin-community-testnet-deqode.service
# Inspect task 1's log:
tail -n 30 "$HOME/qubitcoin-community-testnet/miner-deqode.log"
```

Editing settings takes effect at the next start. To change a running task, stop and then start **only its miner service**; do not restart the node. Starting with systemctl/monitor does not itself enable boot autostart. To deliberately enable deqode on future Ubuntu starts, use `sudo systemctl enable qubitcoin-community-testnet-deqode.service`; `disable` removes that preference. Fresh setup enables only the task(s) explicitly chosen there.

## Verify the second task

```bash
"$HOME/qubitcoin-community-testnet/bin/node-cli" getmininginfo
systemctl status qubitcoin-community-testnet-deqode.service --no-pager
tail -n 30 "$HOME/qubitcoin-community-testnet/miner-deqode.log"
```

The startup log should identify `deqode` / task 1. Finding a block is random; a running service or nonzero meter is not proof that a block has been accepted. Do not paste cookie credentials or private miner configuration files into chat.

## Rollback

The helper prints the backup directory. Stop only the task miners before restoring old helper files/units from that directory. Disable deqode if you enabled it, restore `start-miner.py` and the previous qhash service (`*.before`) if needed, then run `sudo systemctl daemon-reload`. Keep `miner-settings.json`, node data, wallet and logs. The original launcher ignores task-specific settings, so retain an appropriate flat qhash setting if you roll back. If uncertain, leave mining stopped and ask for help; never delete the wallet to undo this update.

## Validation boundary

Automated tests cover separate configs, old/new settings, private permissions, duplicate-task prevention, service commands, paused/stale reporting and a repeated update using mocked privileged commands. Existing qhash/deqode offline algorithm smoke tests apply to the unchanged pinned executable. A full clean installation and sustained simultaneous mining on independent hardware remain to be measured. No running node/miner is stopped, signalled or started by the source/package tests.
