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

echo "==> Removing UIFlow 2 resource bloat ..."
# Recursively remove /flash/res/ and /flash/apps/ — UIFlow 2 versions vary in
# what they store there (JPEGs, VLW fonts, manifests, etc.).  upload.sh
# recreates /flash/res/font/ when deploying VLW fonts, so wiping it here is safe.
$MPR resume exec "
import os

def rmtree(path):
    try:
        entries = os.listdir(path)
    except OSError:
        return  # directory doesn't exist; nothing to do
    for name in entries:
        child = path + '/' + name
        try:
            os.remove(child)
            print('removed', child)
        except OSError:
            rmtree(child)
    try:
        os.rmdir(path)
        print('rmdir', path)
    except OSError:
        pass

for top in ('/flash/res', '/flash/apps'):
    rmtree(top)

# Remove misc root-level UIFlow files.
for f in ('/flash/README.md',):
    try:
        os.remove(f)
        print('removed', f)
    except OSError:
        pass
" 2>&1 || true

echo "==> Listing /flash contents and sizes ..."
$MPR resume exec "
import os

def _size(p):
    try:
        st = os.stat(p)
        if st[0] & 0x4000:
            return sum(_size(p + '/' + n) for n in os.listdir(p))
        return st[6]
    except OSError:
        return 0

for name in sorted(os.listdir('/flash')):
    print('{:6d}  {}'.format(_size('/flash/' + name), name))
" 2>&1 || true

echo "==> Asserting >= 150 KB free on /flash ..."
FREE_RAW=$($MPR resume exec "
import os
st = os.statvfs('/flash')
print('statvfs:', st)
# bsize=st[0], frsize=st[1], blocks=st[2], bfree=st[3], bavail=st[4]
# Some UIFlow firmware builds store bavail as a signed int; use bfree (st[3])
# with bsize (st[0]) which is more reliably non-negative on LittleFS.
free_bytes = st[0] * st[3]
if free_bytes < 0:
    # Fallback: bfree may be a large uint32 misread as signed; treat as 0.
    free_bytes = 0
print(free_bytes // 1024)
" 2>&1 || true)

# Extract the last bare integer line (the KB value); statvfs: line is skipped by
# the '^-?[0-9]+$' pattern since it contains non-digit characters.
FREE_KB=$(echo "$FREE_RAW" | tr -d '\r' | grep -E '^[0-9]+$' | tail -1 || true)

echo "$FREE_RAW" | tr -d '\r' | grep 'statvfs:' || true   # always show the tuple

if [[ -z "$FREE_KB" ]]; then
    echo "warning: could not parse free-space from device; continuing anyway" >&2
elif [[ "$FREE_KB" -lt 150 ]]; then
    echo "error: only ${FREE_KB} KB free — expected >= 150 KB after cleanup" >&2
    echo "       Check the listing above for large files and remove them with:" >&2
    echo "       mpremote resume exec \"import os; os.remove('/flash/path/to/file')\"" >&2
    exit 1
else
    echo "==> Free space: ${FREE_KB} KB"
fi

echo "==> Setting boot_option=0 (app mode) ..."
$MPR resume exec "import esp32; nvs = esp32.NVS('uiflow'); nvs.set_u8('boot_option', 0); nvs.commit()"

echo "==> Device prep complete. Run 'make upload' to deploy the app."
