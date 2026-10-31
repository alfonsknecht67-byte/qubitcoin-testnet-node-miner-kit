#!/usr/bin/env python3
"""Read-only local worker/topology sample. Does not read command lines or wallet data."""
import argparse
import json
import os
from pathlib import Path
import time

def snapshot(pid):
    rows = {}
    for task in (Path('/proc') / str(pid) / 'task').iterdir():
        try:
            text = (task / 'stat').read_text()
            fields = text[text.rfind(')') + 2:].split()
            allowed = next(line.split(':', 1)[1].strip() for line in
                           (task / 'status').read_text().splitlines()
                           if line.startswith('Cpus_allowed_list:'))
            rows[int(task.name)] = (int(fields[11]) + int(fields[12]), fields[0],
                                    int(fields[36]), allowed)
        except (OSError, ValueError, StopIteration):
            continue
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pid', type=int, help='PID from systemctl show or your own process list')
    parser.add_argument('--seconds', type=float, default=5)
    args = parser.parse_args()
    if args.pid < 2 or not 1 <= args.seconds <= 30:
        parser.error('PID must exceed 1; sample duration must be 1–30 seconds')
    allowed = sorted(os.sched_getaffinity(args.pid))
    topology = []
    for cpu in allowed:
        base = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology')
        try:
            topology.append((cpu, int((base/'physical_package_id').read_text()),
                             int((base/'core_id').read_text())))
        except (OSError, ValueError):
            pass
    print(json.dumps({'allowed_logical_cpus': allowed, 'visible_cores':
          len({(p, c) for _, p, c in topology}), 'topology_cpu_package_core': topology}))
    # cgroup v2 limits of the actual process, not just the shell's cgroup.
    group = Path(f'/proc/{args.pid}/cgroup').read_text()
    for line in group.splitlines():
        if line.startswith('0::'):
            directory = (Path('/sys/fs/cgroup') / line[3:].lstrip('/')).resolve()
            root = Path('/sys/fs/cgroup').resolve()
            if directory.is_relative_to(root):
                while True:
                    for name in ('cpu.max', 'cpuset.cpus.effective'):
                        try:
                            print(str(directory.relative_to(root) / name),
                                  (directory / name).read_text().strip())
                        except OSError:
                            pass
                    if directory == root:
                        break
                    directory = directory.parent
    first = snapshot(args.pid); start = time.monotonic()
    time.sleep(args.seconds)
    second = snapshot(args.pid); elapsed = time.monotonic() - start
    hz = os.sysconf('SC_CLK_TCK'); total = 0; busy = 0
    print('TID  CPU% (100 = one logical CPU)  STATE  LAST_CPU  ALLOWED_CPUS')
    for tid, (ticks, state, cpu, mask) in sorted(second.items()):
        if tid not in first:
            continue
        usage = max(0, ticks - first[tid][0]) * 100 / hz / elapsed
        total += usage; busy += usage > 50
        print(f'{tid} {usage:7.1f} {state:>5} {cpu:9} {mask}')
    print(f'Total CPU: {total:.1f}% of one logical CPU; busy threads (>50%): {busy}')
    print('WSL topology is guest-visible. This sample does not prove host socket placement.')

if __name__ == '__main__':
    main()
