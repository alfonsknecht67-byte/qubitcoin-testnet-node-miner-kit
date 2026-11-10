# Choose your platform: one Testnet kit

The same source ZIP and program files are used for both paths. Windows 11 is
not a hard requirement: the installer runs in Ubuntu, not in Windows itself.

## Windows

Use an Intel/AMD x86-64 PC and current WSL2 with systemd support. Windows 10 or
Windows 11 can provide WSL2; Canonical's Ubuntu WSL guide specifies Windows 10
21H2 or newer. Hardware virtualization must be available. This Testnet helper
requires Ubuntu 26.04, AVX2 and AES CPU support, and active systemd.

1. Follow [the Windows beginner guide](START-HERE.md) to prepare Ubuntu/WSL2.
   If WSL or another node is already present, keep that installation intact.
2. Extract the current source ZIP into C:\qtc-testnet-kit.
3. Open Ubuntu as its ordinary user and run:

    bash /mnt/c/qtc-testnet-kit/start-testnet.sh

The installer checks Ubuntu, CPU features, systemd, existing kit folders/services
and ports. It refuses an incompatible or conflicting setup. A WSL version number
alone does not prove that systemd is active. Do not restart a running node or
shut down WSL to bypass a failed check.

## Ubuntu Linux

No Windows or WSL is needed. Use native Ubuntu 26.04 on x86-64 with systemd,
AVX2/AES CPU support, internet access and sudo permission for build dependencies
and the kit's own services.

1. Download the same current source ZIP from this repository.
2. Extract its contents into a new folder named qtc-testnet-kit in your home
   directory. Confirm setup-testnet.sh and start-testnet.sh are directly inside.
3. In your normal Ubuntu terminal, run:

    bash "$HOME/qtc-testnet-kit/start-testnet.sh"

For an existing installation, read [UPDATE-CHECK.md](UPDATE-CHECK.md) first.
For a compatible custom installation, the guided starter updater is:

    python3 "$HOME/qtc-testnet-kit/update-miner.py"

The standard installer uses ~/qubitcoin-community-testnet and its named services.
It does not migrate another installation or reuse a mainnet wallet.

## Shared controls and settings

After setup, both paths use the same two-task menu, separate qhash/deqode worker
settings and backup/update procedures. CPU mining is optional.
See [DUAL-TASK.md](DUAL-TASK.md) and [MANUAL-UPDATE.md](MANUAL-UPDATE.md).
Commands containing /mnt/c are Windows/WSL examples; native Ubuntu users should
use the extracted folder under their Linux home directory instead.

## Scope

This describes required runtimes and platform routes. Automated source checks
do not certify an entire clean Windows 10/11 installation, every WSL release or
all hardware combinations. Installer checks remain unchanged; no new operating
system support is claimed merely by changing this guide.

Sources:
- https://documentation.ubuntu.com/wsl/latest/guides/install-ubuntu-wsl2/
- https://learn.microsoft.com/windows/wsl/install
- https://learn.microsoft.com/windows/wsl/systemd
