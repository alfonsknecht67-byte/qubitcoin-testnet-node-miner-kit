# Validation

Date: 2026-10-31. Base: official miner commit `62b3d51395ce2e2bda0d4ca56368842f4c11b6a9`.

Passed:

- Patch applicability against a fresh archive of the exact upstream commit.
- Standalone placement tests built with GCC, `-Wall -Wextra -Werror`, AddressSanitizer and UndefinedBehaviorSanitizer.
- Synthetic SMT layouts, including a 40-core/80-logical-CPU model, duplicate core IDs on different packages, nonadjacent siblings, more than two siblings, and sparse CPU IDs above 63.
- Selection limited to the test process's inherited CPU set; oversubscribed workers cycle through selected CPUs.
- Explicit repeating affinity mask and empty-mask handling in the mapping helper.
- A temporary one-CPU restriction applied only to the standalone test process, followed by restoration of that test process's original CPU set.
- Shell syntax validation of `build.sh`.
- Full qhash-cpu/deqode build on Linux/WSL2, using `-O2 -march=x86-64-v3 -maes -mno-sha`.
- Built miner `--help` exits successfully and lists both CPU algorithms; shared libraries resolve.
- Publication files checked for operator names, wallet addresses, credentials and local installation paths; none included.

An initial full-build attempt omitted `-maes` and failed in unrelated upstream AES code. The corrected complete build passed. This compiler flag correction is not part of the affinity patch.

Not established:

- A hashrate improvement on a dual-socket system.
- A general explanation for flat throughput as worker count increases.
- Accurate host NUMA topology exposure by WSL2.
- Native Windows compilation (the Windows worker-affinity branch is unchanged).

No mining benchmark or network submission was performed. Running miners, nodes, wallets, services and security settings were not changed. The update is source-only; no executable or raw machine log is included in the publication.
