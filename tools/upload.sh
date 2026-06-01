#!/usr/bin/env bash
# Upload src/ and vendored shims to a connected M5StickC PLUS running MicroPython.
# Usage: tools/upload.sh [port]
# If port is omitted, mpremote auto-selects the first detected device.

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

# Create /lib on the device (ignore error if it already exists).
echo "==> Ensuring :lib/ exists on device ..."
$MPR mkdir :lib 2>/dev/null || true

# Deploy vendor shims to :lib/ (skip the README).
echo "==> Uploading vendor shims to :lib/ ..."
$MPR cp "$REPO_ROOT/vendor/typing.py" :lib/typing.py
$MPR cp "$REPO_ROOT/vendor/dataclasses.py" :lib/dataclasses.py
$MPR cp "$REPO_ROOT/vendor/enum.py" :lib/enum.py
# collections is a package — copy the directory.
$MPR mkdir :lib/collections 2>/dev/null || true
$MPR cp "$REPO_ROOT/vendor/collections/__init__.py" :lib/collections/__init__.py
$MPR cp "$REPO_ROOT/vendor/collections/abc.py" :lib/collections/abc.py

# Deploy app code by explicit subtree, excluding test-only files.
echo "==> Uploading app code ..."
$MPR cp -r "$REPO_ROOT/src/encoder" :encoder
$MPR cp -r "$REPO_ROOT/src/hw" :hw

# Upload ui/ files individually so display_mock.py is excluded.
$MPR mkdir :ui 2>/dev/null || true
for f in "$REPO_ROOT"/src/ui/*.py; do
    [[ "$(basename "$f")" == "display_mock.py" ]] && continue
    $MPR cp "$f" ":ui/$(basename "$f")"
done

$MPR cp "$REPO_ROOT/src/main.py" :main.py

# Smoke test: accept NotImplementedError (imports resolved) but fail on ImportError.
echo "==> Running smoke test (import main) ..."
SMOKE_OUT=$($MPR exec "import main" 2>&1) || true
if echo "$SMOKE_OUT" | grep -q "ImportError"; then
    echo "error: smoke test raised ImportError:" >&2
    echo "$SMOKE_OUT" >&2
    exit 1
fi
echo "$SMOKE_OUT"
echo "==> Upload complete. Power-cycle the device to start the app."
