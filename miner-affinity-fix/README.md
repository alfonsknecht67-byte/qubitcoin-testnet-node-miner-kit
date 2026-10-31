# Linux CPU affinity: physical cores before SMT siblings

Unofficial community patch for the Qubitcoin CPU miner. Applies to upstream commit `62b3d51395ce2e2bda0d4ca56368842f4c11b6a9`.

## Problem

The original Linux default assigns workers to consecutive logical CPU numbers. On systems where adjacent logical CPUs are SMT siblings, a partial worker count can occupy both siblings of some cores while leaving other physical cores unused. CPU numbering varies, so assuming that even-numbered CPUs always represent distinct cores is not a general solution.

## Change

- Read the process's allowed CPU set with `sched_getaffinity`.
- Read package/core IDs from Linux sysfs. Assign one allowed logical CPU per distinct physical core before assigning additional SMT siblings.
- Use dynamic CPU sets, including CPU IDs above 63 and 1023.
- Bind each worker using `pthread_self()` and report binding failures.
- Preserve the existing repeating 64-bit semantics and numeric CPU order for a non-default `--cpu-affinity` mask, intersected with the allowed CPU set.
- Keep `--cpu-affinity 0` as the existing opt-out. Reuse selected CPUs if more workers than selected logical CPUs are requested, with a warning.
- If topology data is unavailable, warn and retain allowed CPU-number order. Do not guess topology.

This affects the shared Linux worker placement used by qhash-cpu and deqode. It does not change hashing, proof-of-work rules, rewards, network settings, scheduling priority, or Windows-native affinity code. This is not a NUMA memory-placement policy.

## Scope and limitations

The fix addresses worker placement. It does not establish the cause of every utilization or throughput plateau, guarantee higher hashrate, or make SMT equivalent to additional physical cores. WSL exposes a virtual topology, which may differ from the host's physical socket/NUMA layout. Opening another terminal does not itself select another CPU socket.

A hardware throughput improvement has not been measured. Compare sustained throughput with identical algorithms, task parameters, work source and measurement duration before drawing conclusions.

## Build in a separate directory

Requires Linux/WSL2, GCC/G++, Git, make, autoconf, automake, libtool, pkg-config and the upstream miner's development libraries (curl, OpenSSL, Jansson, GMP and zlib).

Download this folder, inspect `build.sh` and `linux-core-first.patch`, then run:

```sh
bash build.sh
```

The script creates a new `miner-affinity-source` directory, checks out the exact upstream revision, applies the patch, runs the placement tests and builds qhash-cpu/deqode. It never installs, starts, stops or replaces a miner or node. It refuses to reuse an existing destination.

The resulting program is `miner-affinity-source/qubitcoin-miner`. Deployment is a separate operator action; retain the previous binary and configuration for rollback.

## Validation

See [VALIDATION.md](VALIDATION.md). Synthetic tests contain no operator-specific configuration, addresses or logs.

## License

Miner patch and tests: GPL-2.0-or-later, consistent with the upstream miner. Existing upstream notices remain unchanged.
