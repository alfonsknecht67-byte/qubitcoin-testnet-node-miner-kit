#!/usr/bin/env python3
"""Read-only recommendations. Never installs settings or controls a service."""
import argparse
import json
import math
import os
from pathlib import Path

TASKS = ('qhash-cpu', 'deqode')
MIB = 1024 * 1024


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return None


def detect():
    warnings = []
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    cpus = allowed if allowed is not None else list(range(os.cpu_count() or 1))
    cores = []
    topology_complete = allowed is not None
    for cpu in cpus:
        base = Path('/sys/devices/system/cpu') / f'cpu{cpu}' / 'topology'
        package, core = read_text(base / 'physical_package_id'), read_text(base / 'core_id')
        if package is None or core is None:
            topology_complete = False
        cores.append((cpu, package, core))
    representatives = []
    seen = set()
    for cpu, package, core in cores:
        key = (package, core) if topology_complete else cpu
        if key not in seen:
            seen.add(key)
            representatives.append(cpu)
    if not topology_complete:
        warnings.append('Physical core topology unavailable: using logical CPU count conservatively; no physical-core claim.')
    if allowed is None:
        warnings.append('Allowed CPU set unavailable on this platform: CPU pinning is not suggested.')
    available = None
    info = read_text('/proc/meminfo') or ''
    for line in info.splitlines():
        if line.startswith('MemAvailable:'):
            available = int(line.split()[1]) * 1024
    quota = None
    # Inspect this process's cgroup v2 and its ancestors, without writing to them.
    cg_root = Path('/sys/fs/cgroup')
    cg_paths = [cg_root]
    for line in (read_text('/proc/self/cgroup') or '').splitlines():
        if line.startswith('0::'):
            relative = Path(line[3:].lstrip('/'))
            if '..' not in relative.parts:
                current = cg_root / relative
                while current != cg_root and current.is_relative_to(cg_root):
                    cg_paths.append(current)
                    current = current.parent
    for cg in set(cg_paths):
        raw = read_text(cg / 'cpu.max')
        if raw:
            amount, period = raw.split()
            if amount != 'max':
                q = int(amount) / int(period)
                quota = q if quota is None else min(quota, q)
        limit, used = read_text(cg / 'memory.max'), read_text(cg / 'memory.current')
        if limit and limit != 'max':
            if used is None:
                warnings.append('Cgroup memory limit found without current usage; available memory is uncertain.')
            else:
                remaining = max(0, int(limit) - int(used))
                available = remaining if available is None else min(available, remaining)
    if os.name == 'posix' and read_text(cg_root / 'cgroup.controllers') is None:
        warnings.append('Cgroup v2 limits unavailable; legacy/container limits may require operator review.')
    if available is None:
        warnings.append('Available RAM unknown: memory recommendation is provisional.')
    return {'allowed_cpus': allowed, 'core_representatives': representatives,
            'topology_complete': topology_complete, 'cpu_quota': quota,
            'available_memory_bytes': available, 'warnings': warnings}


def recommend(resources, tasks=TASKS, profile='background', workers=None):
    if not tasks or len(set(tasks)) != len(tasks) or any(t not in TASKS for t in tasks):
        raise ValueError('Select qhash-cpu, deqode, or both once each')
    if profile not in ('background', 'balanced'):
        raise ValueError('Unknown profile')
    cores = resources['core_representatives']
    if not cores or len(set(cores)) != len(cores) or any(type(c) is not int or c < 0 for c in cores):
        raise ValueError('Invalid CPU inventory')
    allowed = resources['allowed_cpus']
    if allowed is not None and not set(cores) <= set(allowed):
        raise ValueError('Core inventory exceeds allowed CPUs')
    quota = resources.get('cpu_quota')
    if quota is not None and (type(quota) not in (int, float) or not math.isfinite(quota) or quota <= 0):
        raise ValueError('Invalid CPU quota')
    capacity = len(cores) if quota is None else min(len(cores), max(1, math.floor(quota)))
    # Leave a CPU capacity unit for node/system when possible; never promise exclusivity.
    fraction = 0.5 if profile == 'background' else 0.75
    budget = min(max(1, math.floor(capacity * fraction)), max(1, capacity - 1))
    if workers is not None:
        if type(workers) is not int or not 1 <= workers <= budget:
            raise ValueError(f'Workers must be within the selected profile budget (1..{budget})')
        budget = workers
    available = resources.get('available_memory_bytes')
    if available is not None and (type(available) is not int or available < 0):
        raise ValueError('Invalid available memory')
    reserve = None if available is None else max(512 * MIB, available // 4)
    memory_budget = None if available is None else max(0, available - reserve)
    # Planning allowances, NOT upper bounds on actual process memory.
    estimates = {'qhash-cpu': 16 * MIB, 'deqode': 192 * MIB}
    selected, memory_used = {t: [] for t in tasks}, 0
    for cpu in cores[:budget]:
        fitting = [t for t in tasks if memory_budget is None or memory_used + estimates[t] <= memory_budget]
        if not fitting:
            break
        task = min(fitting, key=lambda t: (len(selected[t]), tasks.index(t)))
        selected[task].append(cpu)
        memory_used += estimates[task]
    warnings = list(resources.get('warnings', []))
    if capacity == 1:
        warnings.append('One CPU capacity unit: no dedicated node/system core can be reserved.')
    if quota is not None and quota < 1:
        warnings.append('Fractional CPU quota: even one worker shares limited CPU time.')
    if memory_budget is None:
        warnings.append('Unknown RAM: review memory before applying any recommendation.')
        # Unknown RAM never leads to a many-worker recommendation.
        first = next(t for t in tasks if selected[t])
        selected = {t: selected[t][:1] if t == first else [] for t in tasks}
        memory_used = estimates[first]
    settings = {'tasks': {}}
    for task, chosen in selected.items():
        if chosen:
            entry = {'threads': len(chosen), 'affinity': 'off'}
            if allowed is not None:
                entry['cpu-set'] = chosen
            if task == 'deqode':
                entry['deqode-memory-mib'] = 64
            settings['tasks'][task] = entry
    inactive = [t for t in tasks if not selected[t]]
    if inactive:
        warnings.append('Insufficient profile budget for: ' + ', '.join(inactive) + '. An absent task is NOT disabled automatically.')
    warnings.append('Memory figures are estimates, not enforced limits. Plan covers these task miners only; other processes still share resources.')
    return {'schema': 1, 'profile': profile, 'read_only': True,
            'suggested_settings': settings, 'inactive_tasks': inactive,
            'cpu_budget': budget, 'workers_recommended': sum(len(x) for x in selected.values()),
            'reserved_capacity_units': max(0, capacity - sum(len(x) for x in selected.values())),
            'memory_reserve_bytes': reserve, 'estimated_worker_memory_bytes': memory_used,
            'resources': resources, 'warnings': warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks', default=','.join(TASKS))
    parser.add_argument('--profile', choices=('background', 'balanced'), default='background')
    parser.add_argument('--workers', type=int)
    args = parser.parse_args()
    try:
        result = recommend(detect(), tuple(args.tasks.split(',')), args.profile, args.workers)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Cannot recommend settings: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
