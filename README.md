# Qubitcoin Testnet — Node & CPU Miner Kit

**Unofficial community guide Â· Windows 11 + Ubuntu 26.04 / WSL2 Â· CPU-only Â· release candidate**

A source-based setup kit for a separate Qubitcoin testnet node and an optional CPU miner. The default mining setup uses qhash-cpu with one worker. No CUDA or prebuilt executable is included. This project is not an official Qubitcoin release and is not endorsed by the Qubitcoin team.

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
6. Creates a separate testnet directory, SQLite wallet and two named systemd services.
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
