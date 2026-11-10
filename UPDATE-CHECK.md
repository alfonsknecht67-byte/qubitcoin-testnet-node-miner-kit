# Before updating an existing testnet installation

The current automatic update route supports the **standard community kit layout**:

- Installed folder: `~/qubitcoin-community-testnet`.
- Node service: `qubitcoin-community-testnet-node.service`.
- Task services: `qubitcoin-community-testnet-miner.service` and, after the dual-task update, `qubitcoin-community-testnet-deqode.service`.
- The same Ubuntu distribution and Linux user used for the original installation.

**Other folders and custom testnet service names are not automatically migrated.**
For example, an installation at `~/qubitcoin-testnet` using `qubitcoin-testnet-*`
services is outside this automatic update route. This does not mean its node or
miners have failed or need reinstalling.

## 1. Check the Ubuntu environment

Open the Ubuntu distribution you already use for the kit, as its normal user.
In Ubuntu, run:

```bash
echo "$WSL_DISTRO_NAME"
```

The distribution name may vary; it must be the one containing your existing
installation. The same home-folder name in a different Ubuntu distribution is
not the same installation. Do not create another installation just because the
folder is absent in the current terminal.

## 2. Check the standard kit files

This command only checks files; it does not execute the node or miner:

```bash
if [ -x "$HOME/qubitcoin-community-testnet/bin/node-cli" ] &&
   [ -x "$HOME/qubitcoin-community-testnet/miner-source/qubitcoin-miner" ]; then
  echo "Standard kit files found; check the testnet service names next."
else
  echo "STOP: the standard kit was not found in this Ubuntu/user."
fi
```

If this prints **STOP**, stop the automatic update procedure. Possible causes
include a different Ubuntu distribution, another Linux user, a custom folder or
an incomplete installation. Do not run `setup-testnet.sh` or `start-testnet.sh`
as a migration workaround: the start menu can offer fresh setup when its standard
folder is absent.

## 3. Check installed service names

This displays service names and startup settings, without logs or credentials:

```bash
systemctl list-unit-files --type=service --no-legend --no-pager |
  awk 'tolower($1) ~ /qubitcoin|qtc/ {print $1, $2}'
```

Your existing **testnet** services must match the standard names above. An older
kit may lack the deqode service; the dual-task updater adds that service. A separate
mainnet service can coexist and must remain untouched. Service presence is not
proof of synchronization or current mining activity.

If the testnet services use other names, stop here. The current helper has no
custom-folder or custom-service migration mode. Do not rename directories,
replace a wallet, copy authentication files between installations or substitute
paths in the updater to make it proceed.

## 4. Continue only for a matching standard installation

Download the [current source ZIP](https://github.com/alfonsknecht67-byte/qubitcoin-testnet-node-miner-kit/archive/refs/heads/main.zip)
and extract its contents directly into `C:\qtc-testnet-kit`. Older versioned ZIPs
remain unchanged. The scripts must not be inside an extra nested folder.

Then follow [Update an existing community kit](DUAL-TASK.md#update-an-existing-community-kit).
The helper backs up the installed launchers and service units, preserves existing
settings/logs, and does not start, stop or restart a node or miner. New settings
affect a miner only at its next deliberate start. This helper updates the kit
launchers and units, not the node or miner executable.

## What if my installation does not match?

Keep your existing installation, wallet, settings and running services. You can
use the new read-only resource planner from the downloaded source without installing
it, but its output is only a recommendation and does not update your existing launcher.
An older launcher may not understand the new CPU-set or deqode-memory fields.

A documented, separately tested migration path for custom installations remains
outstanding. Until it exists, this guide deliberately stops rather than presenting
an unverified update command. If requesting help, share service names and nonsecret
paths only; never share cookies, private keys or private miner configuration files.
