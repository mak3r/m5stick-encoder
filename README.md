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
# Bootstrap the project venv (one time per clone)
python3 -m venv .venv
.venv/bin/pip install --upgrade pip ruff pytest

# Host-side dev loop
.venv/bin/pytest -q
.venv/bin/ruff check src/ tests/

# Flash and upload to device (firmware persona is recommended — see /firmware)
./tools/flash.sh    # esptool: erase + write MicroPython firmware
./tools/upload.sh   # mpremote: copy src/ to device
./tools/repl.sh     # mpremote: open REPL
```

The common dev commands are also wrapped in a `Makefile`; run `make help`
to see them. Frequently used:

```bash
make test           # pytest -q
make lint           # ruff check src/ tests/
make sim            # launch the host simulator (see below)
```

### Quick start: try the encoder on your desktop

After bootstrapping the venv, run:

```bash
make sim
```

A tkinter window opens approximating the 240x135 landscape display at 4x
scale. The keyboard map is shown in the help overlay:

- `[` or `a` — BTN A (scroll wheel left)
- `]` or `b` — BTN B (scroll wheel right)
- `space` — PWR (tap = select letter, double-tap = backspace, hold ~1 s = toggle ENC/DEC)

No device required.

The project ships an empty `.venv/` policy: it's gitignored and rebuilt locally per the steps above. Global `pip` / `pipx` / `brew install` are intentionally off the allowlist for Claude Code subagents — the venv is the only sanctioned tool path so that automated work is reproducible and contained.

## Personas

Three Claude Code personas drive this project:

- **developer** (`.claude/agents/developer.md`) — autonomous subagent that picks up `phase-1` issues, writes code + tests, opens PRs
- **test** (`.claude/agents/test.md`) — autonomous subagent that writes host-runnable pytest cases against mock display + synthetic events
- **firmware** (`.claude/commands/firmware.md`) — interactive slash command that adopts the firmware role in the current Claude session; talks to the human while flashing and uploading to a real M5StickC PLUS

Invoke them via:

```text
/watch-work developer           # one phase-1 issue, then stop
/watch-work developer 30        # 30 minutes of autonomous developer work
/watch-work developer 2         # for a specific issue: /watch-work developer 2
/watch-work test                # same patterns for the test persona
/firmware                       # adopt firmware persona for an interactive flash/upload session
```

Phase 2–6 issues are intentionally underspecified and labeled `needs-plan`. The developer persona refuses to implement them without a fresh `/plan` session with a human first.

## Flashing and uploading to the device

These steps require `esptool.py` and `mpremote` on your PATH (`pipx install esptool mpremote`).

### 1. Flash stock MicroPython

```bash
tools/flash.sh /dev/tty.usbserial-XXXX firmware/ESP32_GENERIC-20260406-v1.28.0.bin
```

The script erases flash, writes the firmware at 115200 baud (FTDI-safe speed), and appends an entry to `firmware/manifest.txt`.

### 2. Upload app code and vendored shims

```bash
tools/upload.sh [port]          # port defaults to mpremote auto-detect
```

The script:
1. Runs `.venv/bin/pytest -q` — refuses to upload if any test fails
2. Pushes `vendor/` shims to `:lib/` on the device (provides `typing`, `dataclasses`, `enum`, `collections.abc`)
3. Uploads `src/encoder/`, `src/hw/`, `src/ui/` (excluding `display_mock.py`), and `src/main.py`
4. Runs `import main` as a smoke test — fails on `ImportError`, tolerates `NotImplementedError`

### 3. Open a REPL

```bash
tools/repl.sh [port]            # Ctrl-X to exit
```

### Recovery

If the device is unresponsive after a flash, hold **BTN A** while powering on to skip `main.py` and drop to REPL, then run `tools/repl.sh` to inspect.

## License

Apache-2.0. See [LICENSE](./LICENSE).
