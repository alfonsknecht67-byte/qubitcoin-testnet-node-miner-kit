# Validation status

## Completed locally

- Bash syntax check of the complete installer: `bash -n setup-testnet.sh`.
- Python syntax check of `start-miner.py`.
- Apply the CPU patch to clean files from the pinned upstream node revision.
- Compare the patched files with the CPU source used by the community's running node: all three files match exactly.
- Confirm that installation targets a new testnet directory and refuses an occupied directory, existing service or occupied testnet ports.
- Inspect the seven original kit files for personal names, user-specific paths, embedded wallet material and credentials. The HTML contains no external automatically loaded resources or JavaScript.

## Not yet established

- A complete installation on a second clean Windows + Ubuntu 26.04 system.
- Broad CPU/platform compatibility or independent code review by the Qubitcoin team.
- An official signature, security audit or malware-free certification.

Automated source checks are included in `.github/workflows/source-checks.yml`. The checks validate source packaging and patch applicability; they do not install software on the reader's machine or certify safety.

## Additional participant report and log fix

A participant reported installation from the published ZIP on another PC: wallet RPC worked and node/miner services were active. Reading the miner log failed because systemd had created it as root. This is not yet independent confirmation of mining throughput on that PC. Version rc.4 fixes new-install log ownership and supplies a non-destructive repair helper. Automated checks cover private mode 600, ownership, append/read access and helper syntax.

## 31 October: integrated fresh install and persistent worker settings

The fresh installer now applies the existing pinned miner affinity patch and executes its placement tests before building the miner. The launcher defaults to one worker and reads durable `miner-settings.json` for an explicit worker count and auto/off affinity. Added read-only worker/cgroup diagnostics and a dedicated fresh-install guide.

Validation: shell syntax; package checksums; launcher tests with synthetic local data and mocked exec (default count, persistent counts, affinity opt-out and rejected invalid settings); clean pinned-source affinity patch applicability and placement tests. No nodes or miners were started, stopped or signalled during this update. A full second-machine install and dual-socket throughput measurement remain outstanding.

## Dual-task helper update

Added separate qhash/deqode services, per-task settings/configs/logs, an interactive testnet-only monitor and a backup-preserving helper update. No algorithm or consensus changes. Tests exercise legacy settings, explicit task settings, same-task locking with cross-task independence, config permissions, private credential handling through config rather than command arguments, whitelisted service actions, paused/stale rate display and two repeated mocked helper upgrades. The upgrade test redirects privileged writes to a temporary fake service directory and rejects any start/stop/restart command. Full independent clean installation and sustained simultaneous mining remain unverified.

## Unified start-menu entry point

Added start-testnet.sh for both fresh and existing installations. It runs fresh setup only when the installed directory is absent; incomplete existing installations stop without overwriting them. Missing/outdated helpers require UPDATE before using the existing backup-preserving updater. Current installations open the monitor directly. Tests cover fresh setup, existing/current helpers, cancellation, partial installs and update failure in disposable homes with setup, updater and service commands mocked. No live node or miner was controlled. This does not replace the outstanding clean-machine end-to-end validation.

## 10 November 2026: resource planning and offline components

Added read-only CPU/RAM recommendations, optional per-task CPU sets and deqode pattern-list
memory settings in the future launcher. Existing settings retain their behavior. Planning
does not apply settings, disable another task, or reserve exclusive host resources.

Validation on Linux x86_64 with GCC: all 22 new unittest methods passed, covering SMT/core
selection, sparse/high CPU IDs, cgroup v2 CPU/memory bounds, low/unknown RAM, disjoint CPU
sets, rejected settings, mocked affinity/exec, malformed measurements, fixture separation,
executable hash checks, dry-run defaults and repeated-result summaries. The existing
launcher, dual-task, helper-upgrade and entry-point tests also passed with service actions
mocked. Windows passed the 18 portable methods; 4 Linux-specific launcher methods were
explicitly skipped there and executed successfully on Linux.

Built a separate native executable from pinned upstream QHash CPU simulation, deqode
instance/solver and SHA-256 sources. Native correctness/smoke runs passed for both tasks,
with one/two separate benchmark processes and two repeats. QHash checks zero-angle
expectations, finite bounds and repeatability; every reported deqode witness is checked
for Pauli weight and syndrome consistency. The executable links no network/submission
entry points. It does not contain the miner main or access a node/wallet.

These short smoke measurements are flagged as short samples and do not establish a
mining speedup. The benchmark measures circuit simulations or syndromes processed, not
full mining hashrate, consensus acceptance, blocks or rewards. Test fixture parameters
are fixed and do not represent current live testnet sizing. No running node, miner,
configuration or service was changed, restarted or signalled during validation.

## Guided manual update for compatible custom folders

Added `update-miner.py` as a one-command menu and `manual-starter-update.py` as
its checked backend. The menu identifies an existing folder and matching task
services, checks the local test chain with read-only `getblockchaininfo`, displays
configured worker counts, creates a private backup and requires `UPDATE` before
replacing only the launcher. `RESTORE` restores the backed-up launcher. No node or
miner executable, wallet, settings, unit definition or service state is edited.

Validation: 14 backend unittest methods and 7 menu unittest methods, in addition
to the existing 22 resource/benchmark methods and earlier kit checks. Covered
read-only checks, mainnet/external-RPC rejection, incorrect service arguments and
payout mismatch, private backups, symlink/tampering rejection, settings/launcher
changes between preparation and installation, atomic replacement and rollback.
The full menu was exercised with cancellation and confirmed installation in
disposable homes; services and RPC were simulated, and all non-launcher files
were checked unchanged. No real user installation was updated by these tests.

The supported layout and remaining independent user-validation boundary are
documented in `MANUAL-UPDATE.md`. This does not claim compatibility with arbitrary
node layouts, other RPC ports, custom launcher behavior or mainnet migrations.
