#!/usr/bin/env bash
set -euo pipefail
base=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
target="$PWD/miner-affinity-source"
revision=62b3d51395ce2e2bda0d4ca56368842f4c11b6a9
if [[ -e "$target" ]]; then
  printf '%s\n' 'Destination already exists; choose a fresh working directory.' >&2
  exit 1
fi
git clone https://github.com/super-quantum/qubitcoin-miner.git "$target"
cd "$target"
git checkout --detach "$revision"
[[ $(git rev-parse HEAD) == "$revision" ]]
git apply --check "$base/linux-core-first.patch"
git apply "$base/linux-core-first.patch"
cc -std=gnu11 -Wall -Wextra -Werror tests/affinity-test.c -o affinity-test
./affinity-test
autoreconf -fi
./configure --enable-tasks=qhash-cpu,deqode CFLAGS='-O2 -march=native -mno-sha' LIBS='-lcurl -lz -lssl -lcrypto'
make -j"${BUILD_JOBS:-2}"
printf '%s\n' 'Build complete. No miner or node was started or replaced.'
