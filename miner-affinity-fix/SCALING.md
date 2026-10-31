# CPU scaling: what the fix changes and how to check the rest

## Confirmed source findings

At pinned miner revision `62b3d51395ce2e2bda0d4ca56368842f4c11b6a9`:

- `cpu-miner.c`, option `t`, accepts a requested count up to 9999. Its startup loop creates `opt_n_threads` pthreads and exits with an error on creation failure; there is no fixed 40-worker cap.
- Original default placement used consecutive logical CPU IDs. The included patch reads the allowed CPU set and topology, placing distinct cores before SMT siblings. It also checks each binding result. This fixes a demonstrated placement error, not every cause of a throughput plateau.
- `algo/qhash/qhash-cpu.c` allocates a thread-local simulation state (`static __thread`); `algo/deqode/deqode-mine.c` maintains a separate thread-local solver state. These files do not show a single global solver lock serializing all workers. Shared work/stats synchronization still exists in the miner; this is not proof of ideal scaling.
- The kit's original `start-miner.py` rewrote `threads: 1` on every start. The updated launcher reads `miner-settings.json` instead. This issue applies to this kit's launcher, not automatically to someone starting the upstream miner manually with `-t`.
- Default worker scheduling uses low-priority/idle policies in `miner_thread`. Host load, WSL scheduling and hardware resources can affect throughput. The patch does not change priority or implement NUMA memory placement.

Source: [thread creation and option parsing](https://github.com/super-quantum/qubitcoin-miner/blob/62b3d51395ce2e2bda0d4ca56368842f4c11b6a9/cpu-miner.c), [qhash CPU](https://github.com/super-quantum/qubitcoin-miner/blob/62b3d51395ce2e2bda0d4ca56368842f4c11b6a9/algo/qhash/qhash-cpu.c), [deqode](https://github.com/super-quantum/qubitcoin-miner/blob/62b3d51395ce2e2bda0d4ca56368842f4c11b6a9/algo/deqode/deqode-mine.c).

## Read-only diagnosis

For an already running kit miner, inside Ubuntu:

```bash
pid=$(systemctl show qubitcoin-community-testnet-miner.service --property=MainPID --value)
python3 ~/qubitcoin-community-testnet/bin/diagnose-miner.py "$pid" --seconds 5
```

For a standalone miner, pass its known PID to `python3 miner-affinity-fix/diagnose.py PID`. The script reads topology, per-thread affinity and CPU-time deltas, and the process's cgroup v2 quota/cpuset including ancestors. It does not change affinity, send signals, start miners or read credentials, wallet files, payout addresses or command lines. Output contains local process/topology details: review it before sharing; do not publish another person's report by default.

A process-wide `taskset -pc PID` result does not verify every worker's affinity. A thread shown at ~100% in Linux top consumes about one logical CPU. Forty busy workers on eighty logical CPUs can therefore display about 50% aggregate CPU. That alone does not establish a missing socket or demonstrate whether SMT improves throughput. More than the logical CPU count merely oversubscribes the machine.

If a higher thread count creates more workers but total hashrate stays flat, inspect **all worker rows** and the startup worker count. A second terminal window does not select another socket. A cgroup root quota of `max` alone does not prove there are no limits in the miner's own cgroup or the Windows host.

## Controlled comparison

Only at a planned miner stop/start, compare the same binary/algorithm/work source and a stable time interval: a small count, the visible physical-core count, then the allowed logical-CPU count. Compare total hashrate, not one worker's rate; qhash hashes/s and deqode work rates are not interchangeable. Allow warmup and do not compare across changing task parameters. Compare `auto` with `off` if guest topology is suspect. Keep host load stable. Stop rather than increase worker counts if temperatures or responsiveness are a concern.

No throughput measurement from a dual-socket host is included. The residual 50% symptom cannot honestly be called solved until the affected machine's worker activity and total throughput are measured.
