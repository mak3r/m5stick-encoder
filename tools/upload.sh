#!/usr/bin/env bash
# Upload src/ and vendored shims to a connected M5StickC PLUS running UIFlow 2.
# Usage: tools/upload.sh [port]
# If port is omitted, mpremote auto-selects the first detected device.
#
# Run `make prep` once on a fresh device before first upload.
# It removes UIFlow 2 resource bloat (~280 KB) and ensures >= 150 KB free space.
#
# The device must be in USB mode before running this script.
# From the UIFlow 2 launch screen: BtnB → BtnB → BtnA.
#
# UIFlow 2 mounts the user filesystem at /flash/ and requires `mpremote resume`
# so the startup menu does not intercept the connection.

set -euo pipefail

PORT="${1:-}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v mpremote &>/dev/null; then
    echo "error: mpremote not found on PATH — install with: pipx install mpremote" >&2
    exit 1
fi

# Gate: host tests must pass before pushing anything to the device.
# Exit code 5 (no tests collected) is treated as a failure, not a pass.
echo "==> Running host tests ..."
PYTEST_EXIT=0
"$REPO_ROOT/.venv/bin/pytest" -q || PYTEST_EXIT=$?
if [[ $PYTEST_EXIT -ne 0 ]]; then
    echo "error: pytest exited $PYTEST_EXIT — fix tests before uploading" >&2
    exit 1
fi

MPR="mpremote"
if [[ -n "$PORT" ]]; then
    MPR="mpremote connect $PORT"
fi

# UIFlow 2: user filesystem lives under /flash/
# Use `resume` on every mpremote call so UIFlow's startup menu is bypassed.

# Create /flash/libs/ on the device (ignore error if it already exists).
echo "==> Ensuring :/flash/libs/ exists on device ..."
$MPR resume mkdir :/flash/libs 2>/dev/null || true

# Deploy vendor shims to :/flash/libs/ (skip the README).
echo "==> Uploading vendor shims to :/flash/libs/ ..."
$MPR resume cp "$REPO_ROOT/vendor/typing.py" :/flash/libs/typing.py
$MPR resume cp "$REPO_ROOT/vendor/dataclasses.py" :/flash/libs/dataclasses.py
$MPR resume cp "$REPO_ROOT/vendor/enum.py" :/flash/libs/enum.py
# collections is a package — copy the directory.
$MPR resume mkdir :/flash/libs/collections 2>/dev/null || true
$MPR resume cp "$REPO_ROOT/vendor/collections/__init__.py" :/flash/libs/collections/__init__.py
$MPR resume cp "$REPO_ROOT/vendor/collections/abc.py" :/flash/libs/collections/abc.py

# Remove stale MicroPython bytecode BEFORE uploading .py files.
# UIFlow 2 compiles .py → .mpy on first import and may store the compiled
# file alongside the source (e.g. /flash/ui/key_store.mpy). MicroPython
# prefers .mpy over .py when both exist, so a stale .mpy from an older
# version of a file will shadow the freshly uploaded .py. Clearing them
# first ensures the new source is always what gets loaded.
echo "==> Clearing stale MicroPython bytecode (.mpy / __pycache__) ..."
$MPR resume exec "
import os

def rm_bytecode(path):
    try:
        entries = os.listdir(path)
    except OSError:
        return
    for name in entries:
        full = path + '/' + name
        if name.endswith('.mpy'):
            try:
                os.remove(full)
                print('removed', full)
            except OSError:
                pass
        elif name == '__pycache__':
            try:
                for sub in os.listdir(full):
                    try:
                        os.remove(full + '/' + sub)
                    except OSError:
                        pass
                os.rmdir(full)
                print('rmdir', full)
            except OSError:
                pass

for d in ('/flash/encoder', '/flash/hw', '/flash/ui', '/flash'):
    rm_bytecode(d)
" 2>&1 || true

# Deploy app code by explicit subtree, excluding test-only files.
echo "==> Uploading app code ..."
$MPR resume mkdir :/flash/encoder 2>/dev/null || true
for f in "$REPO_ROOT"/src/encoder/*.py; do
    $MPR resume cp "$f" ":/flash/encoder/$(basename "$f")"
done
$MPR resume mkdir :/flash/hw 2>/dev/null || true
for f in "$REPO_ROOT"/src/hw/*.py; do
    $MPR resume cp "$f" ":/flash/hw/$(basename "$f")"
done

# Upload ui/ files individually so display_mock.py is excluded.
$MPR resume mkdir :/flash/ui 2>/dev/null || true
for f in "$REPO_ROOT"/src/ui/*.py; do
    [[ "$(basename "$f")" == "display_mock.py" ]] && continue
    $MPR resume cp "$f" ":/flash/ui/$(basename "$f")"
done

$MPR resume cp "$REPO_ROOT/src/main.py" :/flash/main.py

# Deploy .vlw smooth fonts to /flash/res/font/ if the fonts/ directory has any.
if compgen -G "$REPO_ROOT/fonts/*.vlw" > /dev/null 2>&1; then
    echo "==> Uploading fonts to :/flash/res/font/ ..."
    $MPR resume mkdir :/flash/res 2>/dev/null || true
    $MPR resume mkdir :/flash/res/font 2>/dev/null || true
    for f in "$REPO_ROOT"/fonts/*.vlw; do
        $MPR resume cp "$f" ":/flash/res/font/$(basename "$f")"
    done
fi

# Deploy config.json to device root if present locally; skip silently if absent.
if [[ -f "$REPO_ROOT/config.json" ]]; then
    echo "==> Deploying config.json ..."
    $MPR resume cp "$REPO_ROOT/config.json" :/flash/config.json
fi

# Configure boot_option=0 so the device runs main.py directly on power-on
# (skips the UIFlow startup menu and WiFi setup).
echo "==> Setting boot_option=0 (app mode) ..."
$MPR resume exec "import esp32; nvs = esp32.NVS('uiflow'); nvs.set_u8('boot_option', 0); nvs.commit()"

# Smoke test: accept NotImplementedError (imports resolved) but fail on ImportError.
# UIFlow 2 with `resume` keeps a live Python session, so app modules loaded by
# UIFlow's startup code are cached in sys.modules.  Evict them first so the
# freshly uploaded .py files are actually imported rather than the stale cached
# versions.
echo "==> Running smoke test (import main) ..."
SMOKE_OUT=$($MPR resume exec "
import sys
for _k in list(sys.modules.keys()):
    if _k == 'main' or _k.startswith('ui') or _k.startswith('encoder') or _k.startswith('hw'):
        del sys.modules[_k]
import main
" 2>&1) || true
if echo "$SMOKE_OUT" | grep -q "ImportError"; then
    echo "error: smoke test raised ImportError:" >&2
    echo "$SMOKE_OUT" >&2
    exit 1
fi
echo "$SMOKE_OUT"
echo "==> Upload complete."
echo ""
echo "Power-cycle the device to start the new code:"
echo "  Hold the power button for 6 seconds until the screen goes dark, then press it once to boot."
