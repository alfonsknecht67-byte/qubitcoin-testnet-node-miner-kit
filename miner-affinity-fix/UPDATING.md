# Updating without reinstalling the node

**Never installed before? Use [Fresh installation](../FRESH-INSTALL.md). This page is for an existing node/miner.**

This patch changes only the miner's Linux CPU placement. No node reinstall, wallet migration, blockchain download or WSL reset is needed.

## Option A: patch a separate copy of existing miner source

This avoids downloading the upstream source again. Keep the original source/binary untouched. Make a separate local clone or copy of the exact upstream revision, apply `linux-core-first.patch`, and rebuild using the original CPU-compatible build settings. Run the included placement tests first. See README.md for prerequisites and the pinned revision.

For a clean Git checkout at the pinned revision:

```sh
git apply --check /path/to/linux-core-first.patch
git apply /path/to/linux-core-first.patch
cc -std=gnu11 -Wall -Wextra -Werror tests/affinity-test.c -o affinity-test
./affinity-test
autoreconf -fi
./configure --enable-tasks=qhash-cpu,deqode CFLAGS='-O2 -march=native -mno-sha' LIBS='-lcurl -lz -lssl -lcrypto'
make -j2
```

`-march=native` targets the build machine; build on the intended machine or deliberately select compatible CPU features. Keep any other required existing build options. The upstream tree also compiles unrelated algorithms, some of which require AES compiler support.

## Option B: fresh isolated source build

Use `build.sh` from this folder. This downloads the upstream source once and creates a separate build directory. It does not modify the installed miner.

## Trying the new binary

After a successful build, the operator can choose a convenient time to end the old miner normally and start the separately built program with the same algorithm, worker count and existing configuration. Do not run competing old/new miners together for a throughput comparison. Keep the previous executable for immediate rollback. Node and wallet services need no changes. Any service executable-path change is a separate, deliberate operator action.

No prebuilt executable is published in this source-only update. A Linux executable must match the intended CPU and system libraries.

## Diagnostic alternative before installing a fix

On the original miner, `--cpu-affinity 0` disables its worker pinning and leaves placement to Linux. This can be tried at a planned miner restart; it does not itself force one worker per physical core. Applying an external CPU mask while leaving the original miner's own pinning enabled is not a reliable substitute. Changing each running worker's affinity is possible but is more intrusive and is not automated here.

A second terminal window does not select a second socket. The topology and scheduler, not the terminal window, determine CPU placement.
