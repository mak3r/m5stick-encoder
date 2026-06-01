#!/usr/bin/env bash
# Prepare a fresh M5StickC PLUS for first upload by removing UIFlow 2 bloat.
# Run `make prep` once on a stock device before running `make upload`.
# Usage: tools/device_prep.sh [port]
# If port is omitted, mpremote auto-selects the first detected device.
#
# Safe to re-run: all deletes are no-ops when files are already absent.

set -euo pipefail

PORT="${1:-}"

if ! command -v mpremote &>/dev/null; then
    echo "error: mpremote not found on PATH — install with: pipx install mpremote" >&2
    exit 1
fi

MPR="mpremote"
if [[ -n "$PORT" ]]; then
    MPR="mpremote connect $PORT"
fi

echo "==> Removing UIFlow 2 resource bloat (~280 KB) ..."

# Delete UIFlow JPEG assets under /flash/res/stickcplus/ and /flash/res/img/.
# mpremote has no recursive rm, so list known files explicitly.
RES_JPGS=(
    ":/flash/res/stickcplus/wifi_empty.jpg"
    ":/flash/res/stickcplus/wifi_good.jpg"
    ":/flash/res/stickcplus/wifi_bad.jpg"
    ":/flash/res/stickcplus/cloud_connected.jpg"
    ":/flash/res/stickcplus/cloud_disconnected.jpg"
    ":/flash/res/stickcplus/mode_app.jpg"
    ":/flash/res/stickcplus/mode_run.jpg"
    ":/flash/res/stickcplus/mode_develop.jpg"
    ":/flash/res/stickcplus/title.jpg"
    ":/flash/res/stickcplus/title_custom.jpg"
    ":/flash/res/stickcplus/boot.jpg"
    ":/flash/res/stickcplus/boot_custom.jpg"
    ":/flash/res/stickcplus/avatar.jpg"
    ":/flash/res/stickcplus/unknown.jpg"
    ":/flash/res/img/avatar.jpg"
)
for f in "${RES_JPGS[@]}"; do
    $MPR resume exec "
import os
try:
    os.remove('${f#:}')
    print('removed ${f#:}')
except OSError:
    pass
" 2>/dev/null || true
done

# Remove now-empty subdirectories (ignore errors if non-empty or already gone).
for d in ":/flash/res/stickcplus" ":/flash/res/img" ":/flash/res" ":/flash/apps"; do
    $MPR resume exec "
import os
try:
    os.rmdir('${d#:}')
    print('rmdir ${d#:}')
except OSError:
    pass
" 2>/dev/null || true
done

# Remove misc UIFlow files.
for f in ":/flash/apps/helloworld.py" ":/flash/README.md"; do
    $MPR resume exec "
import os
try:
    os.remove('${f#:}')
    print('removed ${f#:}')
except OSError:
    pass
" 2>/dev/null || true
done

echo "==> Asserting >= 150 KB free on /flash ..."
FREE_KB=$($MPR resume exec "
import os
st = os.statvfs('/flash')
free_bytes = st[0] * st[3]
print(free_bytes // 1024)
" 2>/dev/null | grep -E '^[0-9]+$' | tail -1)

if [[ -z "$FREE_KB" ]]; then
    echo "error: could not read statvfs from device" >&2
    exit 1
fi

echo "==> Free space: ${FREE_KB} KB"
if [[ "$FREE_KB" -lt 150 ]]; then
    echo "error: only ${FREE_KB} KB free — expected >= 150 KB after cleanup" >&2
    exit 1
fi

echo "==> Setting boot_option=0 (app mode) ..."
$MPR resume exec "import esp32; nvs = esp32.NVS('uiflow'); nvs.set_u8('boot_option', 0); nvs.commit()"

echo "==> Device prep complete. Run 'make upload' to deploy the app."
