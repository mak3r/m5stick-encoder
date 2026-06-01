#!/usr/bin/env bash
# Flash stock M5Stack MicroPython firmware to an M5StickC PLUS over USB.
# Usage: tools/flash.sh <port> <firmware.bin>
# Example: tools/flash.sh /dev/tty.usbserial-XXXX firmware/ESP32_GENERIC-20260406-v1.28.0.bin

set -euo pipefail

PORT="${1:-}"
FIRMWARE="${2:-}"

if [[ -z "$PORT" || -z "$FIRMWARE" ]]; then
    echo "Usage: $0 <port> <firmware.bin>" >&2
    exit 1
fi

if [[ ! -e "$PORT" ]]; then
    echo "error: port not found: $PORT" >&2
    exit 1
fi

if [[ ! -f "$FIRMWARE" ]]; then
    echo "error: firmware file not found: $FIRMWARE" >&2
    exit 1
fi

if ! command -v esptool.py &>/dev/null; then
    echo "error: esptool.py not found on PATH — install with: pipx install esptool" >&2
    exit 1
fi

BIN_SHA256=$(shasum -a 256 "$FIRMWARE" | awk '{print $1}')
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
MANIFEST="$(dirname "$0")/../firmware/manifest.txt"

echo "==> Erasing flash on $PORT ..."
esptool.py --chip esp32 --port "$PORT" --baud 115200 erase_flash

echo "==> Writing $FIRMWARE ..."
esptool.py --chip esp32 --port "$PORT" --baud 115200 write_flash 0x1000 "$FIRMWARE"

mkdir -p "$(dirname "$MANIFEST")"
echo "${TIMESTAMP} ${BIN_SHA256} ${PORT} script-invoked:$(basename "$FIRMWARE")" >> "$MANIFEST"
echo "==> Logged to $MANIFEST"
echo "==> Done. Power-cycle the device and verify MicroPython starts."
