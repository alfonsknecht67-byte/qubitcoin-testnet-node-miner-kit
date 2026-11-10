# Update an existing testnet miner

Use this guided menu if you already have a compatible kit-derived testnet miner,
including an installation in a different folder. **You carry out every step yourself.**

This updates the **miner starter**, not the miner's calculation engine or the node.
Your wallet, blockchain, worker settings, service names and existing miner executable
are kept. Running nodes and miners are not stopped or restarted by this update.

## 1. Download and open Ubuntu

Download the [current GitHub source ZIP](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/archive/refs/heads/main.zip).
Extract its contents directly into `C:\qtc-testnet-kit`. The file `update-miner.py`
must be directly inside that folder. Previously downloaded ZIPs do not update themselves.

Open the **same Ubuntu distribution and Linux user** that you used for your existing
testnet installation. Do not run this menu as root or with `sudo`.

## 2. Open the update menu

In Ubuntu, paste this one command:

```bash
python3 /mnt/c/qtc-testnet-kit/update-miner.py
```

## 3. Follow the menu

1. Choose **Check and update an existing miner**.
2. Select your installation from the numbered list. If it is not listed, choose
   **Enter a different installation folder** and enter its full path, for example
   `~/qubitcoin-testnet`.
3. The menu identifies matching miner services and checks your files, existing settings
   and the local testnet. Review the worker counts displayed for the next start.
4. Choose **Create backup and prepare the new launcher**. The backup remains private
   inside your existing installation. Preparation alone does not replace the starter.
5. When ready, type **UPDATE** to replace the starter. Press Enter instead to stop
   after preparation and keep the existing starter.

Custom code edits in your old starter are backed up, not merged. The menu installs
the current kit starter adapted to your folder. Exit if you need to retain other
custom starter behavior.

No personal hash, machine-specific backup name, manual source editing or AI assistance
is needed. Empty input or **Q** exits menu selections. If a check prints **STOP**, do
not run fresh setup as a workaround; read the reason and keep your installation intact.

## 4. After the update

The new starter is used at the **next normal miner start**. Current miner processes
continue with their existing settings. This menu deliberately does not restart them.
CPU-set and deqode-memory settings are available but are not applied automatically.
The read-only resource planner remains optional; it does not change a running miner.

To confirm your nodes/miners are still running, you can display their status without
changing anything:

```bash
systemctl list-units --all --type=service --plain --no-legend --no-pager |
  awk 'tolower($1) ~ /qubitcoin|qtc/ {print $1, $3, $4}'
```

## Restore the old starter if needed

Open the same update menu and choose **Restore a previously backed-up launcher**.
Select the backup and type **RESTORE**. Only the starter is restored; no wallet,
settings, service unit or running process is changed. If settings or files have
changed since preparation, the tool stops rather than overwriting them blindly.

## Which existing installations are supported?

The menu checks a defined compatible layout, rather than guessing how arbitrary
software was installed:

- A user-owned folder inside your Linux home, with `bin/start-miner.py` and
  `miner-source/qubitcoin-miner`.
- Existing task configs, `mining-address.txt` and the node cookie under `data/testnet`.
- Local HTTP RPC on port **18452**, confirmed as the **test** chain by the read-only
  `getblockchaininfo` call. Proxies and redirects are disabled for that request.
- One identifiable QHash service and optionally one deqode service using that Python
  starter. The service names must identify testnet; no service units are edited.

Missing/ambiguous services, different RPC layouts, mainnet, inaccessible files or
unexpected launch arguments cause a clear stop. This is not a general-purpose node
migration or a clean-machine installation test. Automated tests use disposable layouts
and simulated services/RPC; a complete independent user update remains to be confirmed.

Backups can contain private local miner credentials. Keep the backup folder private;
share neither its contents nor node cookies/private keys. No private wallet files are
copied by the update tool.

<details>
<summary>Advanced: check or prepare with explicit folder/service names</summary>

`manual-starter-update.py` exposes the same checked workflow without the menu. By
default it performs only read-only checks. `--prepare` creates a private backup and
candidate. `--install-prepared DIRECTORY` explicitly installs the prepared starter;
`--rollback-prepared DIRECTORY` restores it. Use `--help` for arguments. The menu
is the recommended route for normal users.

</details>
