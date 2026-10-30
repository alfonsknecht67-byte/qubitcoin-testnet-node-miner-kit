# Security and privacy

This is community testnet tooling, not an official signed distribution. Read the scripts and patch before running them. The installer requests `sudo` for Ubuntu dependencies and two explicitly named testnet services; building source still executes upstream build scripts.

No prebuilt node/miner binary, private wallet, authentication cookie, API token or secret is distributed. Network requests are to Ubuntu's configured package repositories, the official public GitHub source repositories, and the stated testnet peer. The guide can be read without running the installer.

Wallet keys stay on the participant's machine. A wallet backup contains secrets: never upload it, the seed, `.cookie`, `miner-local.json`, or unreviewed logs/screenshots. This kit does not ask for anyone's mainnet keys or configure remote RPC access.

SHA-256 files identify bytes; they do not prove trustworthy authorship or absence of malicious code. Independent review and reproducible tests are encouraged. Keep testnet data separate, and verify current upstream guidance before using an old release.

For a public issue, include only a sanitized error and the affected step/version. For a suspected vulnerability, do not post credentials or an exploit against another participant. Open a minimal issue asking how to arrange private review.
