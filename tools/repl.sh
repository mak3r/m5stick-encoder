#!/usr/bin/env bash
# Open a MicroPython REPL over USB to a connected M5StickC PLUS.
# Usage: tools/repl.sh [port]
# If port is omitted, mpremote auto-selects the first detected device.
# Press Ctrl-X to exit the REPL.

set -euo pipefail

PORT="${1:-}"

if ! command -v mpremote &>/dev/null; then
    echo "error: mpremote not found on PATH — install with: pipx install mpremote" >&2
    exit 1
fi

if [[ -n "$PORT" ]]; then
    exec mpremote connect "$PORT" repl
else
    exec mpremote repl
fi
