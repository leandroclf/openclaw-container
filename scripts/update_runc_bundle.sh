#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="${BUNDLE_DIR:-$HOME/.local/share/openclaw-runc/bundle}"
RUNC_ROOT="${RUNC_ROOT:-$HOME/.local/share/openclaw-rootless/runc-root}"
OPENCLAW_NPM_SPEC="${OPENCLAW_NPM_SPEC:-openclaw@latest}"
GEMINI_NPM_SPEC="${GEMINI_NPM_SPEC:-@google/gemini-cli@latest}"

mkdir -p \
  "$BUNDLE_DIR/rootfs/bin" \
  "$BUNDLE_DIR/rootfs/dev/pts" \
  "$BUNDLE_DIR/rootfs/dev/shm" \
  "$BUNDLE_DIR/rootfs/etc/ssl/certs" \
  "$BUNDLE_DIR/rootfs/home/node" \
  "$BUNDLE_DIR/rootfs/lib" \
  "$BUNDLE_DIR/rootfs/lib64" \
  "$BUNDLE_DIR/rootfs/proc" \
  "$BUNDLE_DIR/rootfs/sys" \
  "$BUNDLE_DIR/rootfs/tmp/openclaw" \
  "$BUNDLE_DIR/rootfs/usr/bin" \
  "$BUNDLE_DIR/rootfs/usr/lib" \
  "$BUNDLE_DIR/rootfs/usr/local"

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -e "$src" ]; then
    cp -a "$src" "$dst"
  fi
}

copy_if_exists /bin/bash "$BUNDLE_DIR/rootfs/bin/"
copy_if_exists /usr/bin/node "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/npm "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/npx "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/env "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/printf "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/dirname "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/bin/which "$BUNDLE_DIR/rootfs/usr/bin/"
copy_if_exists /usr/lib/node_modules "$BUNDLE_DIR/rootfs/usr/lib/"
copy_if_exists /lib/x86_64-linux-gnu "$BUNDLE_DIR/rootfs/lib/"
copy_if_exists /lib64/ld-linux-x86-64.so.2 "$BUNDLE_DIR/rootfs/lib64/"
copy_if_exists /etc/ssl/certs "$BUNDLE_DIR/rootfs/etc/ssl/"

cat >"$BUNDLE_DIR/rootfs/etc/passwd" <<'EOF'
node:x:1000:1000:node:/home/node:/bin/bash
EOF

cat >"$BUNDLE_DIR/rootfs/etc/group" <<'EOF'
node:x:1000:
EOF

cat >"$BUNDLE_DIR/rootfs/etc/nsswitch.conf" <<'EOF'
hosts: files dns
passwd: files
group: files
EOF

chmod 1777 "$BUNDLE_DIR/rootfs/tmp"
chmod 700 "$BUNDLE_DIR/rootfs/tmp/openclaw"

NPM_CONFIG_PREFIX="$BUNDLE_DIR/rootfs/usr/local" \
  npm install -g "$OPENCLAW_NPM_SPEC" "$GEMINI_NPM_SPEC" >/tmp/openclaw-runc-update.log 2>&1

cd "$BUNDLE_DIR"
rm -f "$BUNDLE_DIR/config.json"
runc spec --rootless >/dev/null

python3 - "$BUNDLE_DIR/config.json" "$@" <<'PY'
import json
import pathlib
import sys

config_path = pathlib.Path(sys.argv[1])
command = sys.argv[2:]
if not command:
    command = ["/usr/local/bin/openclaw", "--version"]

config = json.loads(config_path.read_text())
config["process"]["args"] = command
config["process"]["terminal"] = False
config["process"]["env"] = [
    "HOME=/home/node",
    "TMPDIR=/tmp",
    "XDG_RUNTIME_DIR=/tmp",
]
config["linux"]["cgroupsPath"] = ""
config["root"]["readonly"] = False
config["mounts"] = [
    mount for mount in config.get("mounts", [])
    if mount.get("destination") != "/dev/pts"
]
config["hooks"] = {}
config_path.write_text(json.dumps(config, indent=2))
PY

runc --root "$RUNC_ROOT" --rootless true run -b "$BUNDLE_DIR" openclaw-runc
