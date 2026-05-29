# m5stick-encoder

An educational secret-code device for kids, built on the [M5StickC PLUS](https://docs.m5stack.com/en/core/m5stickc_plus).
The device shows you the cipher algorithm while you use it — scroll the alphabet, watch each letter transform, and build words letter by letter.

## What it does

Phase 1: ROT13 encrypt and decrypt with a live cipher wheel display.

- `[ENC]` mode: type a letter, see its encrypted output build up
- `[DEC]` mode: type ciphertext, see the plaintext build up
- The full A–Z cipher wheel is visible at all times so the kid can see the algorithm, not just use it

Future phases (placeholder issues only — see GitHub issue list):
- Codeword/keyword cipher
- Share codes between two devices over WiFi / BLE
- Expanded character set (spaces, digits, punctuation)
- Mode switching via resistors on the Grove connector
- Additional algorithms

## Hardware

[M5StickC PLUS](https://shop.m5stack.com/products/m5stickc-plus-esp32-pico-mini-iot-development-kit) — ESP32-PICO, 135×240 ST7789V2 LCD, 3 buttons (A, B, PWR), AXP192 PMIC, 120 mAh battery.

## Controls

- **BTN A** — scroll cipher wheel left
- **BTN B** — scroll cipher wheel right
- **PWR** — short press: select current letter; double-press: backspace; long-press (~1 s): toggle `[ENC]`/`[DEC]` and clear running word

Hold **BTN A** during power-on to skip auto-run and drop to REPL (safety recovery).

## Development

This is a [MicroPython](https://micropython.org) project that runs on M5Stack's official MicroPython firmware for the M5StickC PLUS. The encoder logic is pure Python and host-testable; the UI runs against a `Display` protocol that's mocked in tests.

```bash
# Host-side dev
pip install ruff pytest
pytest tests/
ruff check src/ tests/

# Flash and upload to device (see tools/)
./tools/flash.sh    # esptool: erase + write MicroPython firmware
./tools/upload.sh   # mpremote: copy src/ to device
./tools/repl.sh     # mpremote: open REPL
```

## Personas

This repo uses three Claude Code subagent personas under `.claude/agents/`:
- **developer** — picks up `phase-1` GitHub issues, writes code + tests
- **test** — writes host-runnable pytest cases against mock display + synthetic events
- **firmware** — works interactively with a human to flash and upload to the device

Phase 2–6 issues are intentionally underspecified and labeled `needs-plan`. The developer persona will not implement them without a fresh `/plan` session with a human first.

## License

Apache-2.0. See [LICENSE](./LICENSE).
