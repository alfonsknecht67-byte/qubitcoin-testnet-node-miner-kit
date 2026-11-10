# Fresh installation: testnet node and patched CPU miner

> **Already running a testnet node? Check before updating.** The automatic update route supports the standard kit at `~/qubitcoin-community-testnet`, using `qubitcoin-community-testnet-*` service names, in the same Ubuntu distribution and Linux user used for installation. Different folders or custom testnet service names are **not automatically migrated**. If that is your setup, do not run the start-menu, setup or update scripts to migrate it. Keep your existing node, miner and wallet. Read [Existing-installation check](UPDATE-CHECK.md) first.


## Open the start menu (new or existing installation)

Download the [current source ZIP](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/archive/refs/heads/main.zip), extract its contents to `C:\qtc-testnet-kit`, then run this **inside Ubuntu**:

```bash
bash /mnt/c/qtc-testnet-kit/start-testnet.sh
```

With a new installation, this runs the guided setup and then opens the menu. With an existing kit, it opens the installed menu or offers to update missing/outdated menu helpers first (type `UPDATE`). Downloading a ZIP alone does not update an installed kit. Keep the existing installation and wallet; do not uninstall them.

The menu lets you start/stop qhash, deqode or both. Choose `6` and confirm `YES` to stop both miners and leave the node running. Opening the menu does not start mining. `Q` closes the menu without stopping anything. Start/stop choices affect the current session, not the services' startup settings. Older versioned release ZIPs do not contain this entry point; use the current source ZIP above.


Use this route if you have never installed the kit. An existing node does not need reinstalling for an affinity update: use [UPDATING.md](miner-affinity-fix/UPDATING.md).

## 1. Get the current source kit

Download [the current source ZIP](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/archive/refs/heads/main.zip), extract it, and place the contents in `C:\qtc-testnet-kit`. This is the updated main branch, not an older release ZIP. Inspect the files before running them. `setup-testnet.sh` and the `miner-affinity-fix` folder must both be present.

## 2. Prepare Ubuntu / WSL2

Follow [START-HERE.md, steps 2–3](START-HERE.md#2-install-ubuntu-inside-windows) for Windows 11 and Ubuntu 26.04. If Ubuntu is already installed, do not reinstall WSL. Run the next command **inside Ubuntu**, not PowerShell. Never delete wallet folders, unregister WSL or stop another node to make room for this kit.

## 3. Run the fresh installer

```bash
bash /mnt/c/qtc-testnet-kit/setup-testnet.sh
```

Type `TESTNET` when asked. The installer downloads pinned official node and miner sources, applies the CPU-node adaptation **and the core-first miner affinity fix**, runs the placement tests, builds locally and creates a separate testnet wallet. A first build can take 15–60 minutes or longer. Logs stay under `~/qubitcoin-community-testnet/logs`.

The default is one mining worker. At the final prompt, choose `QHASH`, `DEQODE`, `BOTH`, or press Enter for node-only. See [DUAL-TASK.md](DUAL-TASK.md) for per-task settings and monitor controls. The installer refuses to overwrite an existing directory/service or use occupied testnet ports. If it stops, preserve the directory and error; do not delete everything and retry blindly.

## 4. Select your worker count

Edit the durable settings (no wallet keys or RPC passwords belong here):

```bash
nano ~/qubitcoin-community-testnet/miner-settings.json
```

For example, begin with a small count:

```json
{"threads": 2, "affinity": "auto"}
```

`auto` uses allowed physical cores first, then SMT siblings. `off` delegates placement to Linux (`--cpu-affinity 0`). Changes take effect at the next miner start. Stop only the kit's miner, edit settings, then start it when ready:

```bash
sudo systemctl stop qubitcoin-community-testnet-miner.service
# Edit miner-settings.json before starting again.
sudo systemctl start qubitcoin-community-testnet-miner.service
```

The node remains running. To save CPU, leave the miner stopped. Do not run a second competing miner for a comparison. Settings persist across starts; generated `miner-local.json` is not the place to edit worker count.

## 5. Verify

```bash
~/qubitcoin-community-testnet/bin/node-cli getblockchaininfo
systemctl is-active qubitcoin-community-testnet-miner.service
tail -n 30 ~/qubitcoin-community-testnet/miner.log
```

Look for the startup worker count and affinity messages. For scaling problems, follow [SCALING.md](miner-affinity-fix/SCALING.md). Neither 100% utilization nor higher throughput is guaranteed by the affinity patch.

## Existing or partly deleted installation?

Use the update route for an intact installation. If files were manually removed but services or wallets remain, do not run destructive cleanup commands: the fresh installer intentionally stops so those can be checked first. Keep wallet backups private. This kit is unofficial and the full fresh installation still needs validation on a second clean Windows machine.
