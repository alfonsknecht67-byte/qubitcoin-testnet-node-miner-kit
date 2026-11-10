# Qubitcoin Testnet — Node & CPU Miner Kit

## Choose your operating system

Use the same kit source for both paths:
- [Windows 10/11 with current WSL2](PLATFORMS.md#windows)
- [Native Ubuntu Linux](PLATFORMS.md#ubuntu-linux)

Ubuntu 26.04, x86-64, AVX2/AES and systemd are the actual installer requirements.
Windows 11 is not a hard requirement. Platform prerequisites and complete-install
test coverage are separate; see PLATFORMS.md.


> **Already running a testnet node?** Read [Existing-installation check](UPDATE-CHECK.md) first. The standard helper update targets `~/qubitcoin-community-testnet` and `qubitcoin-community-testnet-*` services. For a compatible existing miner in another folder, use the [guided miner update](MANUAL-UPDATE.md): select the installation, check, back up and explicitly confirm the starter replacement. Do not use fresh setup or the standard helper updater to migrate a custom layout. Keep your existing node and wallet.


## Update your existing miner with the guided menu

Download the current source ZIP and open your existing Ubuntu as its normal user.
Run:

```bash
python3 /mnt/c/qtc-testnet-kit/update-miner.py
```

Choose the installation, review the checks, create the backup and confirm the update.
The menu supports compatible kit-derived custom folders as well as the standard layout.
It updates only the starter; nodes, wallets, settings and running miners are retained.
See [the short step-by-step guide](MANUAL-UPDATE.md), including restoration from backup.

## Resource planning and offline component benchmarks

The new resource planner is **read-only**. Run it from the extracted source kit:

```bash
python3 resource_plan.py
python3 resource_plan.py --profile balanced --tasks qhash-cpu,deqode
```

It recommends worker counts using the process's allowed CPUs, visible physical-core topology,
available RAM and cgroup v2 limits when available. It leaves a CPU/RAM allowance for the node
and system where possible. It never writes `miner-settings.json`, changes running affinity,
starts/stops services or creates a wallet. WSL topology describes what Linux can see, which
need not match the host's physical layout. Unknown topology/RAM is explicitly flagged.

The output's `suggested_settings` can be reviewed for a **future** miner start. The updated
launcher accepts optional per-task `cpu-set` arrays and a deqode `deqode-memory-mib` value.
CPU sets for both configured tasks must be disjoint, available to the launching process and
large enough for their worker counts. CPU IDs above 63 are supported. Existing settings
without these keys keep their old behavior. An absent task is **not** automatically disabled;
if the plan cannot accommodate both tasks, do not leave an old second miner running unnoticed.
Pinning applies only to a newly launched miner process; an unrestricted other process can
still use those CPUs. Deqode's memory value budgets its pattern lists per worker, **not total RAM**.
All memory allowances are estimates, not enforced process limits.

The offline benchmark uses the pinned upstream CPU circuit and deqode decoder components.
It is a **separate executable**, with fixed public fixtures, correctness checks and no miner
main, networking, RPC, wallet access or block submission. Building requires Linux, GCC and
the usual configured miner source/header dependencies. Use a separate source tree; no
configuration, build or binary replacement is performed in an installed kit:

```bash
python3 bench/build_offline.py --source /path/to/separate/configured-miner-source --output /path/to/new/offline-build
# Preview only; default execution is disabled:
python3 bench/run_offline.py --build-dir /path/to/new/offline-build --task qhash-cpu --workers 1,2
# Deliberately execute low-priority, CPU-pinned standalone benchmark processes:
python3 bench/run_offline.py --build-dir /path/to/new/offline-build --task qhash-cpu --workers 1,2 --rounds 64 --repeat 3 --run --output qhash-component-results.json
python3 bench/run_offline.py --build-dir /path/to/new/offline-build --task deqode --workers 1,2 --rounds 1000 --repeat 3 --run --output deqode-component-results.json
```

Select worker counts that fit your machine. Builds and result files refuse overwrites.
The harness source, upstream kernel sources and executable are checked by hashes.
Reports retain compiler flags, fixed fixture IDs, repeated measurements and sample ranges.
Short measurements are flagged; startup and correctness-check time is included in wall time.
QHash is measured in circuit simulations/s; deqode in processed syndromes/s. These are
**component measurements, not complete mining hashrate, accepted blocks or reward estimates**.
The small fixed deqode fixture is not live testnet sizing. Do not add or directly compare
the two task rates. Shared workloads, thermal state and quotas affect results; this update
does not establish or promise a throughput improvement. Nothing is applied to existing
installations merely by downloading the kit.

## Open the start menu (new or existing installation)

Download the [current source ZIP](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/archive/refs/heads/main.zip), extract its contents to `C:\qtc-testnet-kit`, then run this **inside Ubuntu**:

```bash
bash /mnt/c/qtc-testnet-kit/start-testnet.sh
```

With a new installation, this runs the guided setup and then opens the menu. With an existing kit, it opens the installed menu or offers to update missing/outdated menu helpers first (type `UPDATE`). Downloading a ZIP alone does not update an installed kit. Keep the existing installation and wallet; do not uninstall them.

The menu lets you start/stop qhash, deqode or both. Choose `6` and confirm `YES` to stop both miners and leave the node running. Opening the menu does not start mining. `Q` closes the menu without stopping anything. Start/stop choices affect the current session, not the services' startup settings. Older versioned release ZIPs do not contain this entry point; use the current source ZIP above.


**Unofficial community guide Â· Windows with WSL2 or native Ubuntu 26.04 Â· CPU-only Â· release candidate**

A source-based setup kit for a separate Qubitcoin testnet node and an optional CPU miner. Mining is optional: choose qhash-cpu, deqode or both, starting with one worker per task on a fresh installation. No CUDA or prebuilt executable is included. This project is not an official Qubitcoin release and is not endorsed by the Qubitcoin team.

## New: mine qhash-cpu and deqode separately or together

**[Dual-task setup and update guide](DUAL-TASK.md)** — one node and wallet, two independently controlled CPU miner services. Includes per-task settings, separate private configs/logs, and a local start/stop monitor. Existing installations can update the helpers without rebuilding/restarting the node. Updating never starts mining automatically.

## Latest miner update: Linux CPU affinity fix

**[CPU affinity fix: physical cores first, then SMT siblings](miner-affinity-fix/README.md)**

Improves default worker placement on Linux/WSL2 and reports CPU-binding failures. Built successfully and tested offline with qhash-cpu and deqode. A hashrate improvement on dual-socket hardware has not yet been measured.

- **[Fresh installation: node + patched CPU miner](FRESH-INSTALL.md)**
- **[Diagnose worker counts and scaling](miner-affinity-fix/SCALING.md)**
- **[Update without reinstalling your node](miner-affinity-fix/UPDATING.md)**
- **[Tests and known limitations](miner-affinity-fix/VALIDATION.md)**

The current source installer applies this patch automatically for fresh installations. Older release ZIPs are unchanged; use the current-source fresh-install link above. Existing nodes can keep using the separate miner update.

## Read before downloading

- **[Beginner guide](START-HERE.md)** â€” readable directly on GitHub, with step-by-step instructions.
- **[Browser-friendly guide](https://alfonsknecht67-byte.github.io/qubitcoin-testnet-node-miner-kit/)** â€” the same instructions as a static website, once Pages deployment is enabled.
- **[Versioned downloads](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/releases)** â€” download a release ZIP, not a changing development snapshot.
- **[What was tested](VALIDATION.md)** and **[security / privacy notes](SECURITY.md)**.

## What the helper actually does

1. Checks the Ubuntu release, CPU features, available ports and existing kit files/services.
2. Asks for the explicit word `TESTNET` before installation.
3. Installs build dependencies from Ubuntu's package repositories using `sudo`.
4. Downloads the two official upstream repositories at exact pinned revisions.
5. Applies the readable community CPU-node patch and builds locally.
6. Creates a separate testnet directory, SQLite wallet and a node service plus two optional miner services.
7. Asks separately before enabling one-thread CPU mining.

There is no telemetry, seed collection, developer donation address, remote-control service or Telegram token in this kit. Cookie authentication is read locally and written to a permission-restricted miner configuration. The helper does not run `curl | bash`, modify a mainnet wallet, shut down WSL or automatically update its source.

## Inspect the code

- [setup-testnet.sh](setup-testnet.sh): every installation command.
- [start-miner.py](start-miner.py): local authentication and one-thread qhash-cpu configuration.
- [cpu-node.patch](cpu-node.patch): the complete CPU adaptation, rather than an opaque replacement binary.
- [UPSTREAM.json](UPSTREAM.json): exact source commits and their repositories.
- [SHA256SUMS.txt](SHA256SUMS.txt): hashes of the published source files.

## Important test status

The CPU adaptations have operated in a community testnet installation. Syntax, patch applicability and privacy checks are independently repeatable. **The complete packaged installer has not yet been run end-to-end on a second clean Windows PC.** Treat this as a release candidate and ask for guided help if needed. Passing automated checks is not a malware-free certificate or proof of general compatibility.

Test coins are not mainnet QTC. Testnets may reset. Mining is optional and does not guarantee rewards. For questions, use this repository's Issues or the Qubitcoin Bubble Map & Research group. Never attach private wallet files or credentials.

## Verify a downloaded release

The release includes a separate SHA-256 file for the ZIP. In PowerShell, run `Get-FileHash .\Qubitcoin-Testnet-Community-Kit-v0.1.0-rc.4.zip -Algorithm SHA256` and compare it to the published digest. A matching hash proves the downloaded file matches that release; it does not establish that the software is safe.

## License

Community helper scripts and guide: MIT, copyright 2026 Qubitcoin Testnet Community contributors. Upstream notices are preserved in [COPYING-Qubitcoin.txt](COPYING-Qubitcoin.txt). Source projects retain their own licenses.

## v0.1.0-rc.4 log-permissions fix

The installer now creates `miner.log` as the normal Ubuntu user with mode 600 before systemd starts the miner. Existing installations can use [repair-log-permissions.sh](repair-log-permissions.sh) without reinstalling, stopping services or losing logs. The troubleshooting section includes manual repair commands.
