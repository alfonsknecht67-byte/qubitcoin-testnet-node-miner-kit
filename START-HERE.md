# Qubitcoin Testnet: your first node and CPU miner

**Beginner guide for Windows 11 + Ubuntu 26.04 on WSL2**  
Prepared 30 October 2026. This kit follows a specific, pinned testnet software version.

You do not need to be a programmer. Read one step, do it, then move to the next. If a step fails, stop there and ask for help in the **Qubitcoin Bubble Map & Research group**. Do not delete a wallet or try random repair commands.

## What you will set up

- A **node**: a program that connects to the testnet, downloads blocks and checks them.
- A **separate testnet wallet**: where any rewards from your mining are recorded.
- Optionally, a **CPU miner using one thread**: it tries to find qhash / Task 0 blocks using your normal processor. No NVIDIA GPU or CUDA is required.
- Two background services: once installed, the node and enabled miner start when this Ubuntu distribution starts and restart after failures.

The node also validates deqode / Task 1 blocks received from the network. This guide does **not** start deqode mining. Installing both tasks in the miner does not mean both are being mined.

**These are testnet coins, not mainnet QTC.** This testnet may change or reset. Finding a block is random; no reward or time-to-reward is guaranteed.

### Before you begin

Use a Windows 11 PC with an Intel or AMD x86-64 processor supporting AVX2 and AES, preferably at least 8 GB RAM and 20 GB free disk space. This kit does not target Windows-on-ARM or Apple Silicon. A computer that does not meet the helper's checks needs a different build; ask for help.

Keep a laptop plugged in and ventilated. Mining adds processor load and electricity use. One thread is the starting point, not a request to use the whole CPU.

This kit includes a **community CPU adaptation for the node**. It is not an official signed CPU-node installer. The readable patch and helper scripts are included for inspection. They reproduce the source adaptations used by the running community testnet installation; the packaged installer has not been independently run from beginning to end on a second clean Windows machine. Ask for guided help if you are unsure.

## 1. Put the complete kit in one folder

Download the ZIP supplied with this guide. In Windows File Explorer:

1. Right-click the ZIP and choose **Extract All**.
2. Put its contents in a folder named **`C:\qtc-testnet-kit`**.
3. Open that folder. You should see `setup-testnet.sh`, `start-miner.py`, `cpu-node.patch` and this guide directly inside it.

If you see another folder inside the first one, open it and move the contents up one level. Do not run anything from inside the compressed ZIP.

## 2. Install Ubuntu inside Windows

Ubuntu runs alongside Windows through **WSL**. You do not have to replace Windows or repartition your disk.

1. Open the Windows Start menu.
2. Type **PowerShell**.
3. Right-click it and choose **Run as administrator**.
4. Paste this command, then press Enter:

```powershell
wsl --install -d Ubuntu-26.04
```

If Windows asks to restart, save your work and restart. Do not start a second installation while the first is still running.

**Already using WSL or running a mainnet node?** Do not uninstall anything, unregister a distribution or run `wsl --shutdown`. Installing another node is not a reason to stop the existing one. Ask for help if the Ubuntu version is already present or you are unsure which distribution contains your mainnet node.

If the command is not recognized or installation gets stuck, stop and use the official [Ubuntu WSL installation guide](https://ubuntu.com/wsl/docs/latest/howto/install-ubuntu-wsl2/) or [Microsoft WSL instructions](https://learn.microsoft.com/en-us/windows/wsl/install).

## 3. Open Ubuntu and create its login

Search the Windows Start menu for **Ubuntu 26.04** and open it. Alternatively, use this in PowerShell:

```powershell
wsl -d Ubuntu-26.04
```

At the first launch, Ubuntu asks for a new username and password. Choose a simple lowercase username and remember the password.

**Nothing appears when you type the password—not even dots. This is normal.** Type it and press Enter. This is your Ubuntu login password, not a Qubitcoin seed phrase or wallet key.

From this point, commands labelled **Ubuntu** go in the Ubuntu window, not in PowerShell. Paste with a right-click or Ctrl+Shift+V if normal Ctrl+V does not work.

## 4. Start the guided testnet setup

In **Ubuntu**, paste:

```bash
bash /mnt/c/qtc-testnet-kit/setup-testnet.sh
```

The helper checks the computer, confirms that its dedicated testnet folder and service names are unused, and checks that its ports are free. It refuses to overwrite an existing setup.

When it asks for confirmation, type:

```text
TESTNET
```

It may ask for your Ubuntu password to install build tools and the two new testnet services. Again, no characters appear while typing it.

The helper downloads the official node and miner sources at the exact revisions listed below, applies the supplied CPU-node patch, builds the programs, enables wallet support and creates the separate testnet wallet. It uses an isolated directory:

```text
~/qubitcoin-community-testnet
```

It does not use your mainnet data directory, mainnet wallet or existing mainnet service. Do not change that isolation by copying a mainnet configuration into the testnet folder.

**Allow 15–60 minutes or longer for the first build.** A quiet screen does not necessarily mean it stopped: detailed build output is saved in the new testnet folder's `logs` directory. Keep Ubuntu open. If an error stops setup, copy the error and ask for help; the helper deliberately does not overwrite a partially created setup on a second run.

## 5. Decide whether to mine

Near the end, the helper asks whether to start CPU mining. Type **YES** to start one qhash-cpu mining thread, or just press Enter to operate a node without mining.

A node without a miner still helps by independently checking and sharing testnet blocks. CPU mining is optional.

Wait for **`Setup complete.`** before continuing.

## 6. Check that your node is connected and synchronized

In **Ubuntu**, run:

```bash
~/qubitcoin-community-testnet/bin/node-cli getblockchaininfo
```

Look for:

- `"chain": "test"` — this is the testnet.
- Equal numbers for `blocks` and `headers`.
- `"initialblockdownload": false` — the node has finished its initial download.
- `verificationprogress` close to `1`.

The exact block number changes as the testnet grows. Do not expect the number shown in someone else's screenshot.

Now check peer connections:

```bash
~/qubitcoin-community-testnet/bin/node-cli getconnectioncount
```

You want **at least 1**. If it stays at zero, mining cannot properly participate in the network. Ask the group for the current testnet peer. The peer in this kit is `54.158.147.24:42070`, verified for the setup described here; it can change later. No router port-forwarding is needed just to make outbound connections.

## 7. Check that your CPU miner is working

If you chose mining, run:

```bash
tail -n 20 ~/qubitcoin-community-testnet/miner.log
```

Look for a message similar to:

```text
1 of ... miner threads started using 'qhash-cpu' algorithm
Thread 0, CPU ...: ... h/s
```

The numbers will depend on your computer. A recent positive rate shows the miner is doing work. The node must also have a peer and be synchronized. Repeated RPC errors are not normal mining progress.

You do not need to find a block immediately. Mining is a search, so long waits without a reward are possible.

## 8. See your separate testnet wallet

```bash
~/qubitcoin-community-testnet/bin/node-cli -rpcwallet=cpu-testnet getwalletinfo
```

- `balance`: rewards or other funds that are already spendable.
- `immature_balance`: mined rewards that are recorded but still locked by the maturity rule.
- `unconfirmed_balance`: transactions not yet confirmed.
- `txcount`: the number of wallet transactions—not the number of coins.

The wallet starts empty. A block reward is only earned if a block you find is accepted and remains in the active chain.

**Why is Balance still zero after a reward?** This pinned testnet uses a 100-block coinbase maturity rule. Its wallet shows the reward as mature at 101 confirmations, including the reward block. For example, a reward in block 28 appears as mature when the chain reaches height 128, provided that block remains in the active chain. This depends on blocks, not a fixed number of hours.

The wallet lives locally in Ubuntu. It is not automatically connected to the homepage's webwallet or an exchange.

## 9. Keep the node running

For a simple test session, keep the Ubuntu window open and run:

```bash
sleep infinity
```

Leave that window open while you use other Windows applications. Use a second Ubuntu window for status commands. Ctrl+C ends the waiting command; it is not the command for gracefully stopping the node.

The services start automatically **when this Ubuntu distribution starts**. This guide does not create a Windows login task to start WSL. After a Windows restart, open Ubuntu again. A sleeping or powered-off PC does not participate. A continuously available machine is more useful than one that sleeps frequently.

## 10. Pause or resume CPU mining

Pause mining for the current session:

```bash
sudo systemctl stop qubitcoin-community-testnet-miner.service
```

The node can continue running. Resume mining with:

```bash
sudo systemctl start qubitcoin-community-testnet-miner.service
```

If you enabled mining during setup, it is configured to start again with Ubuntu. A temporary pause is not a permanent disable.

If you chose node-only setup and later want to enable mining, ask for help enabling its startup dependency as well; do not rerun the installer over the existing wallet.

## 11. Stop and start safely

Before deliberately closing your test session or shutting down Windows, stop these **testnet services only**:

```bash
sudo systemctl stop qubitcoin-community-testnet-miner.service qubitcoin-community-testnet-node.service
```

To start them again if mining was enabled:

```bash
sudo systemctl start qubitcoin-community-testnet-node.service
```

To check whether the services are running:

```bash
systemctl is-active qubitcoin-community-testnet-node.service qubitcoin-community-testnet-miner.service
```

`active` means running. A miner intentionally left disabled in a node-only setup may show `inactive`.

Do not use commands that stop every `qubitcoind` process or shut down all WSL distributions. Those could interrupt a separate mainnet installation.

## 12. Back up the testnet wallet

While the node is running:

```bash
~/qubitcoin-community-testnet/bin/node-cli -rpcwallet=cpu-testnet backupwallet "$HOME/qubitcoin-testnet-wallet-backup.dat"
```

That backup contains wallet secrets. Keep it private. Do not post it, your seed, private keys, authentication cookie or `miner-local.json` in Telegram. Never substitute your mainnet wallet for the testnet wallet.

## If something does not work

**“No such file or directory” at step 4:** check that the ZIP is fully extracted to `C:\qtc-testnet-kit` and the scripts are not inside an extra nested folder.

**“systemd is not active”:** ask for help updating/configuring WSL. Do not run `wsl --shutdown` on a machine hosting another node without planning the interruption.

**“Method not found” for wallet commands:** wallet support is missing from that binary. This helper explicitly builds SQLite wallet support; ask for help rather than trying to import a mainnet wallet.

**“Could not connect to server”:** check the node service with `systemctl is-active`. Make sure you are using the guide's `node-cli`, which selects the correct testnet directory and RPC port.

**“Permission denied” when reading `miner.log`:** early kit versions could let systemd create a root-owned log. The node and miner may still be running. Version v0.1.0-rc.4 pre-creates a private, user-owned log. For an existing installation, run these in Ubuntu; no reinstall or service restart is needed:

```bash
sudo chown "$(id -u):$(id -g)" "$HOME/qubitcoin-community-testnet/miner.log"
chmod 600 "$HOME/qubitcoin-community-testnet/miner.log"
tail -n 20 "$HOME/qubitcoin-community-testnet/miner.log"
```

Alternatively, use the `repair-log-permissions.sh` included in the new ZIP. Do not delete the existing testnet folder or wallet and do not rerun setup over it.

**“Illegal instruction”:** the binary does not match the CPU's supported instructions. This helper builds locally and disables SHA CPU instructions, matching the tested CPU approach. Stop and report the error if it still occurs.

**No rewards yet:** a positive hashrate is not a promise of an immediate block. Check peer connectivity and synchronization first.

**No Telegram command works:** this kit does not install a Telegram bot. `/testnet` commands belong to the community's existing monitoring bot and do not automatically show your new personal node.

For support, share your Ubuntu version, the step number and the exact error. Review any logs or screenshots first and remove credentials. A clear report helps the team reproduce problems.

## What this kit does—and what was checked

- Node revision: `6c4f95a4c9b8975526fc7cb2eb32c721ab178cde` from the official `super-quantum/qubitcoin` repository, plus the supplied community CPU patch.
- Miner revision: `62b3d51395ce2e2bda0d4ca56368842f4c11b6a9` from `super-quantum/qubitcoin-miner`.
- SQLite wallet support; CPU miner built for the local CPU with SHA CPU instructions disabled.
- Dedicated RPC: `127.0.0.1:18452`; dedicated local peer-listening port: `18453`; outbound developer peer: `54.158.147.24:42070`.
- Helper shell syntax, Python launcher syntax and application of the CPU patch to the pinned source are checked separately. The installer itself has not been run end-to-end on a second clean PC. The node/miner adaptations are based on the functioning community setup and are not a substitute for broad platform testing.
- No Mainnet upgrade, automatic source updates, firewall changes, WSL shutdown, remote monitoring, seed export or Telegram integration.

Before following an old copy, ask the group whether this is still the recommended testnet version and peer. Testnet protocols can change.

## Sources

- [Ubuntu on WSL installation](https://ubuntu.com/wsl/docs/latest/howto/install-ubuntu-wsl2/)
- [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Official Qubitcoin source](https://github.com/super-quantum/qubitcoin/tree/6c4f95a4c9b8975526fc7cb2eb32c721ab178cde)
- [Official miner source](https://github.com/super-quantum/qubitcoin-miner/tree/62b3d51395ce2e2bda0d4ca56368842f4c11b6a9)
- [Proof-of-work task documentation](https://github.com/super-quantum/qubitcoin/blob/6c4f95a4c9b8975526fc7cb2eb32c721ab178cde/doc/pow-tasks.md)

The helper scripts are provided as community testnet tooling without a warranty. Qubitcoin's original MIT license is included in `COPYING-Qubitcoin.txt`.
