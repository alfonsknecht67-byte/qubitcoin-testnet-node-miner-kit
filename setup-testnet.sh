#!/usr/bin/env bash
# Community testnet setup for Ubuntu 26.04 on x86-64 WSL2.
# Installs only into a new, dedicated testnet directory and two named services.
set -Eeuo pipefail
umask 077
KIT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE="$HOME/qubitcoin-community-testnet"
NODE_REV=6c4f95a4c9b8975526fc7cb2eb32c721ab178cde
MINER_REV=62b3d51395ce2e2bda0d4ca56368842f4c11b6a9
NODE_SERVICE=qubitcoin-community-testnet-node.service
MINER_SERVICE=qubitcoin-community-testnet-miner.service
STEP=checks
trap 'printf "\nSetup stopped during: %s.\nDo not delete any wallet folders. Ask for help with the error above.\n" "$STEP" >&2' ERR

if (( EUID == 0 )); then echo 'Run this as your normal Ubuntu user, not as root.'; exit 1; fi
source /etc/os-release
if [[ ${ID:-} != ubuntu || ${VERSION_ID:-} != 26.04 ]]; then
  echo 'This helper targets Ubuntu 26.04. Ask for help before using another release.'; exit 1
fi
if [[ $(uname -m) != x86_64 ]]; then echo 'This kit is for Intel/AMD x86-64 PCs, not ARM.'; exit 1; fi
for feature in avx2 aes; do
  if ! grep -qw "$feature" /proc/cpuinfo; then echo "CPU feature $feature is missing. Ask for a compatible build."; exit 1; fi
done
if [[ $(ps -p 1 -o comm=) != systemd ]]; then
  echo 'systemd is not active. Stop here and ask for WSL setup help; do not shut down another running node.'; exit 1
fi
if [[ "$BASE" =~ [[:space:]] ]]; then echo 'The Ubuntu home path must not contain spaces for this helper.'; exit 1; fi
if [[ -e "$BASE" ]]; then
  echo "The testnet folder already exists: $BASE"
  echo 'Nothing was overwritten. Use the status/start instructions, or ask for help resuming a partial setup.'; exit 1
fi
if systemctl cat "$NODE_SERVICE" >/dev/null 2>&1 || systemctl cat "$MINER_SERVICE" >/dev/null 2>&1; then
  echo 'A community testnet service already exists. Nothing was overwritten.'; exit 1
fi
if ss -ltnH | awk '{print $4}' | grep -Eq ':(18452|18453)$'; then
  echo 'A required testnet port is already in use. Do not stop another node; ask for help.'; exit 1
fi
[[ -f "$KIT_DIR/cpu-node.patch" && -f "$KIT_DIR/start-miner.py" && -f "$KIT_DIR/miner-affinity-fix/linux-core-first.patch" ]] || { echo 'Extract the complete kit before running setup.'; exit 1; }
echo 'This installs a separate Qubitcoin TESTNET node and a one-thread CPU miner.'
echo 'It uses a community CPU-node patch, not an official signed CPU-node release.'
echo 'Source revisions are pinned. No CUDA, Telegram credentials or seed phrase is required.'
echo 'The first build can take 15–60 minutes or longer. Keep this window open.'
read -r -p 'Type TESTNET to continue: ' answer
[[ "$answer" == TESTNET ]] || { echo 'Cancelled.'; exit 0; }

STEP='installing build tools'
sudo apt-get update
sudo apt-get install -y build-essential autoconf automake libtool pkg-config git python3 \
  libevent-dev libboost-dev libsqlite3-dev libcurl4-openssl-dev libssl-dev \
  libjansson-dev libgmp-dev zlib1g-dev
mkdir -m 700 "$BASE" "$BASE/logs" "$BASE/data" "$BASE/bin"
# systemd opens StandardOutput=append files as root before switching user.
# Pre-create the file as the participant so it remains private AND readable.
install -m 600 /dev/null "$BASE/miner.log"
LOGS="$BASE/logs"

STEP='downloading pinned node source'
echo '[1/6] Downloading the node source…'
git init -q "$BASE/node-source"
git -C "$BASE/node-source" remote add origin https://github.com/super-quantum/qubitcoin.git
git -C "$BASE/node-source" fetch --depth 1 origin "$NODE_REV" >"$LOGS/node-download.log" 2>&1
git -C "$BASE/node-source" -c advice.detachedHead=false checkout --detach FETCH_HEAD >>"$LOGS/node-download.log" 2>&1
git -C "$BASE/node-source" apply --check "$KIT_DIR/cpu-node.patch"
git -C "$BASE/node-source" apply "$KIT_DIR/cpu-node.patch"

STEP='building CPU node and wallet'
echo '[2/6] Building the CPU node and SQLite wallet. This is the longest step…'
cd "$BASE/node-source"
./autogen.sh >"$LOGS/node-build.log" 2>&1
./configure --without-gui --disable-tests --disable-bench --disable-fuzz-binary \
  --disable-shared --with-pic --enable-wallet --with-sqlite=yes --without-bdb >>"$LOGS/node-build.log" 2>&1
make -j2 >>"$LOGS/node-build.log" 2>&1

STEP='building CPU miner'
echo '[3/6] Building the CPU miner without CUDA or SHA CPU instructions…'
git init -q "$BASE/miner-source"
git -C "$BASE/miner-source" remote add origin https://github.com/super-quantum/qubitcoin-miner.git
git -C "$BASE/miner-source" fetch --depth 1 origin "$MINER_REV" >"$LOGS/miner-download.log" 2>&1
git -C "$BASE/miner-source" -c advice.detachedHead=false checkout --detach FETCH_HEAD >>"$LOGS/miner-download.log" 2>&1
cd "$BASE/miner-source"
git apply --check "$KIT_DIR/miner-affinity-fix/linux-core-first.patch"
git apply "$KIT_DIR/miner-affinity-fix/linux-core-first.patch"
cc -std=gnu11 -Wall -Wextra -Werror tests/affinity-test.c -o affinity-test
./affinity-test >"$LOGS/affinity-test.log" 2>&1
./autogen.sh >"$LOGS/miner-build.log" 2>&1
CFLAGS='-O2 -march=native -mno-sha' LIBS='-lcurl -lz -lssl -lcrypto' \
  ./configure --enable-tasks=qhash-cpu,deqode >>"$LOGS/miner-build.log" 2>&1
make -j2 >>"$LOGS/miner-build.log" 2>&1

STEP='creating isolated testnet configuration'
echo '[4/6] Creating the dedicated testnet configuration…'
cat > "$BASE/data/qubitcoin.conf" <<'CONF'
testnet=1
server=1
[test]
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcport=18452
port=18453
addnode=54.158.147.24:42070
CONF
cat > "$BASE/bin/node-cli" <<'CLI'
#!/usr/bin/env bash
set -euo pipefail
base="$HOME/qubitcoin-community-testnet"
exec "$base/node-source/src/qubitcoin-cli" -testnet -datadir="$base/data" -conf="$base/data/qubitcoin.conf" -rpcport=18452 "$@"
CLI
chmod 700 "$BASE/bin/node-cli"
install -m 700 "$KIT_DIR/start-miner.py" "$BASE/bin/start-miner.py"
install -m 700 "$KIT_DIR/miner-affinity-fix/diagnose.py" "$BASE/bin/diagnose-miner.py"
printf '{"threads": 1, "affinity": "auto"}\n' > "$BASE/miner-settings.json"
chmod 600 "$BASE/miner-settings.json"
USER_NAME=$(id -un)
cat > "$BASE/$NODE_SERVICE" <<UNIT
[Unit]
Description=Qubitcoin Community Testnet Node
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0
[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BASE
ExecStart=$BASE/node-source/src/qubitcoind -testnet -datadir=$BASE/data -conf=$BASE/data/qubitcoin.conf -daemon=0 -printtoconsole=0
Restart=on-failure
RestartSec=10
TimeoutStopSec=180
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
cat > "$BASE/$MINER_SERVICE" <<UNIT
[Unit]
Description=Qubitcoin Community Testnet CPU Miner
After=$NODE_SERVICE
Requires=$NODE_SERVICE
PartOf=$NODE_SERVICE
StartLimitIntervalSec=0
[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BASE
ExecStartPre=$BASE/bin/node-cli -rpcwait -rpcwaittimeout=60 getblockcount
ExecStart=/usr/bin/python3 $BASE/bin/start-miner.py
StandardOutput=append:$BASE/miner.log
StandardError=append:$BASE/miner.log
Restart=always
RestartSec=10
TimeoutStartSec=75
TimeoutStopSec=30
Nice=10
UMask=0077
[Install]
WantedBy=multi-user.target
UNIT
sudo install -m 644 "$BASE/$NODE_SERVICE" "/etc/systemd/system/$NODE_SERVICE"
sudo install -m 644 "$BASE/$MINER_SERVICE" "/etc/systemd/system/$MINER_SERVICE"
sudo systemd-analyze verify "/etc/systemd/system/$NODE_SERVICE" "/etc/systemd/system/$MINER_SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable --now "$NODE_SERVICE"

STEP='creating the separate testnet wallet'
echo '[5/6] Waiting for the node, then creating the separate testnet wallet…'
"$BASE/bin/node-cli" -rpcwait -rpcwaittimeout=180 getblockcount
"$BASE/bin/node-cli" -named createwallet wallet_name=cpu-testnet descriptors=true load_on_startup=true
"$BASE/bin/node-cli" -rpcwallet=cpu-testnet getnewaddress cpu-miner bech32 > "$BASE/mining-address.txt"
chmod 600 "$BASE/mining-address.txt"
echo 'The node is running. It may still be synchronizing with peers.'
echo 'The peer address may change after this kit was published; ask the group if no peer connects.'
read -r -p 'Start CPU mining with ONE thread now? Type YES, or press Enter for node-only: ' mining
if [[ "$mining" == YES ]]; then
  STEP='starting the one-thread miner'
  # This dependency is installed only after the wallet and payout address exist.
  sudo mkdir -p "/etc/systemd/system/$NODE_SERVICE.d"
  printf '[Unit]\nWants=%s\n' "$MINER_SERVICE" > "$BASE/miner-dependency.conf"
  sudo install -m 644 "$BASE/miner-dependency.conf" "/etc/systemd/system/$NODE_SERVICE.d/miner.conf"
  sudo systemctl daemon-reload
  sudo systemctl enable --now "$MINER_SERVICE"
fi
STEP=complete
echo '[6/6] Setup complete.'
echo "Check your node: $BASE/bin/node-cli getblockchaininfo"
echo "Check your wallet: $BASE/bin/node-cli -rpcwallet=cpu-testnet getwalletinfo"
echo "Check mining: tail -n 20 $BASE/miner.log"
echo 'Services start when this Ubuntu WSL distribution starts, not while the computer is off or asleep.'
echo 'For this test session, leave Ubuntu open. Run: sleep infinity'
echo 'Use the guide for stopping, starting, backup and troubleshooting.'
