#!/usr/bin/env python3
"""Build a separate component-only executable; never build/install/start a miner."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCES = ('algo/qhash/qhash-cpu.c', 'algo/deqode/deqode.c',
           'algo/deqode/deqode-stern.c', 'algo/sha/sha256-hash.c', 'algo/sha/sph_sha2.c', 'malloc-huge.c')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    if platform.system() != 'Linux':
        parser.error('This native component build currently requires Linux; no WSL environment is started automatically.')
    if out.exists() or out.is_relative_to(source):
        parser.error('Choose a new output directory outside the miner source')
    if not (source / 'cpuminer-config.h').is_file():
        parser.error('Use a separately prepared/configured source tree; this tool does not configure an installed miner')
    pins = json.loads((ROOT / 'kernel-sources.json').read_text())
    for name, expected in pins['sha256'].items():
        if digest(source / name) != expected:
            parser.error('Pinned kernel source mismatch: ' + name)
    out.mkdir(parents=True)
    binary = out / 'qtc-offline-kernels'
    flags = ['-std=gnu11', '-O2', '-mno-sha', '-ffunction-sections', '-fdata-sections',
             '-I' + str(source), '-Wl,--gc-sections']
    command = ['gcc', *flags, str(ROOT/'offline-kernels.c'),
               *(str(source / name) for name in SOURCES), '-lm', '-o', str(binary)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (out / 'build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit('Offline component build failed; see build.log')
    manifest = {'schema': 1, 'scope': 'offline algorithm components, not full mining',
                'binary_sha256': digest(binary), 'harness_sha256': digest(ROOT/'offline-kernels.c'),
                'upstream_commit': pins['upstream_commit'], 'source_sha256': pins['sha256'],
                'compiler': subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0],
                'flags': [flag for flag in flags if not flag.startswith('-I')] + ['-lm'], 'no_rpc_or_service_calls': True}
    (out / 'build-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Built standalone offline components: ' + str(binary))


if __name__ == '__main__':
    main()
