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
