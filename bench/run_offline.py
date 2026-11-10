#!/usr/bin/env python3
"""Dry-run by default. Execute only the separately built offline kernel harness."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
TASKS = ('qhash-cpu', 'deqode')
sys.path.insert(0, str(ROOT.parent))
from resource_plan import detect


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_build(directory):
    binary = directory / 'qtc-offline-kernels'
    manifest = json.loads((directory / 'build-manifest.json').read_text())
    if digest(binary) != manifest['binary_sha256'] or digest(ROOT/'offline-kernels.c') != manifest['harness_sha256']:
        raise ValueError('Offline benchmark executable/source hash mismatch')
    if manifest['source_sha256'] != json.loads((ROOT/'kernel-sources.json').read_text())['sha256']:
        raise ValueError('Kernel provenance mismatch')
    return binary.resolve(), manifest


def validate_sample(data, task, rounds):
    multiplier, unit = (1, 'circuit_simulations') if task == 'qhash-cpu' else (32, 'syndromes_processed')
    if (data.get('task') != task or data.get('unit') != unit
        or type(data.get('units')) is not int or data['units'] != rounds * multiplier
        or data.get('correctness_checks') is not True
        or type(data.get('seconds')) not in (int, float)
        or not math.isfinite(data['seconds']) or data['seconds'] <= 0
        or not isinstance(data.get('fixture'), str) or not data['fixture']):
        raise ValueError('Invalid or incomplete component benchmark result')
    if task == 'deqode' and (type(data.get('validated_witnesses')) is not int or data['validated_witnesses'] < 1):
        raise ValueError('No validated solver witnesses')
    if task == 'qhash-cpu' and (type(data.get('checksum')) not in (int, float) or not math.isfinite(data['checksum'])):
        raise ValueError('Invalid circuit checksum')
    return data


def run_case(binary, task, cpus, rounds, runner=subprocess.run):
    nice, taskset = shutil.which('nice'), shutil.which('taskset')
    if not nice or not taskset:
        raise ValueError('Linux nice and taskset are required; nothing is installed automatically')
    def worker(cpu):
        cmd = [nice, '-n', '19', taskset, '-c', str(cpu), str(binary), task, str(rounds)]
        result = runner(cmd, capture_output=True, text=True, timeout=120, check=True)
        return validate_sample(json.loads(result.stdout), task, rounds)
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
        samples = list(pool.map(worker, cpus))
    wall = time.perf_counter() - start
    if len({(s['fixture'], s['unit']) for s in samples}) != 1:
        raise ValueError('Incompatible fixtures in one comparison')
    units = sum(s['units'] for s in samples)
    return {'workers': len(cpus), 'cpu_ids': cpus, 'rounds_per_worker': rounds,
            'fixture': samples[0]['fixture'], 'unit': samples[0]['unit'],
            'units': units, 'wall_seconds': wall, 'units_per_wall_second': units / wall,
            'samples': samples}


def summarize(cases):
    result = []
    signatures = {(x['fixture'], x['unit'], x['rounds_per_worker']) for x in cases}
    if len(signatures) != 1:
        raise ValueError('Cannot compare different task fixtures, units or work sizes')
    baseline = [x['units_per_wall_second'] for x in cases if x['workers'] == 1]
    for workers in sorted({x['workers'] for x in cases}):
        rows = [x for x in cases if x['workers'] == workers]
        rates = [x['units_per_wall_second'] for x in rows]
        median = statistics.median(rates)
        result.append({'workers': workers, 'median_units_per_wall_second': median,
                       'min_units_per_wall_second': min(rates), 'max_units_per_wall_second': max(rates),
                       'speedup_vs_one_worker': median / statistics.median(baseline) if baseline else None,
                       'short_samples': any(x['wall_seconds'] < 0.25 for x in rows)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', required=True, type=Path)
    parser.add_argument('--task', required=True, choices=TASKS)
    parser.add_argument('--cpus', help='Comma-separated allowed CPU IDs; does not change any running process')
    parser.add_argument('--workers', default='1', help='Comma-separated worker counts, e.g. 1,2,4')
    parser.add_argument('--rounds', default=8, type=int)
    parser.add_argument('--repeat', default=3, type=int)
    parser.add_argument('--run', action='store_true', help='Explicitly execute isolated components')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        workers = [int(x) for x in args.workers.split(',')]
        cpus = [int(x) for x in args.cpus.split(',')] if args.cpus else detect()['core_representatives']
        if (not cpus or len(set(cpus)) != len(cpus) or any(c < 0 for c in cpus)
            or not workers or len(set(workers)) != len(workers)
            or any(w < 1 or w > min(len(cpus), 32) for w in workers)
            or not 1 <= args.rounds <= 10000 or not 1 <= args.repeat <= 10):
            raise ValueError('Invalid CPU/worker/repeat/round limits')
        if args.output and args.output.exists():
            raise ValueError('Output already exists; choose a new private result file')
        plan = {'dry_run': not args.run, 'task': args.task, 'workers': workers,
                'cpu_ids': cpus[:max(workers)], 'rounds_per_worker': args.rounds, 'repeat': args.repeat,
                'scope': 'Circuit simulation or decoder components only, not complete PoW or mining hashrate'}
        if not args.run:
            print(json.dumps(plan, indent=2))
            return
        if platform.system() != 'Linux' or not hasattr(os, 'sched_getaffinity'):
            raise ValueError('Execution requires Linux; no WSL environment is started automatically')
        if not set(cpus) <= set(os.sched_getaffinity(0)):
            raise ValueError('Requested CPUs exceed this process allowed CPU set')
        binary, manifest = verify_build(args.build_dir.resolve())
        cases = [run_case(binary, args.task, cpus[:count], args.rounds)
                 for _ in range(args.repeat) for count in workers]
        result = {'schema': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  **plan, 'build': manifest, 'cases': cases, 'summary': summarize(cases),
                  'limits': ['Component rates are not mining hashrate or reward estimates.',
                             'Includes process startup and correctness checks in wall time.',
                             'Other running workloads and temperatures affect measurements.',
                             'Fixed small deqode fixture is not the current testnet sizing.',
                             'Tasks are measured separately; no combined hashpower comparison.']}
        text = json.dumps(result, indent=2, allow_nan=False)+'\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(text)
        print(text)
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(2, 'Offline benchmark failed: ' + type(error).__name__ + '; no miner/service was controlled.\n')


if __name__ == '__main__':
    main()
