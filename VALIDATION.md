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
