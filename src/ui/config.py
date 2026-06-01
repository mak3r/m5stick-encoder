"""Optional runtime configuration loaded from a JSON file.

Consumers pass the parsed dict to helpers like ``btn_b_scroll_ms()``.
Missing keys fall back to the compiled-in defaults so the device still
works with no config file present.
"""

import json

from ui.buttons import BTN_B_REPEAT_DELAY_MS, BTN_B_SCROLL_MS

_CONFIG_PATH = "config.json"


def load_config(path: str = _CONFIG_PATH) -> dict:
    """Read *path* and return its parsed JSON, or {} if the file is absent."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def btn_b_scroll_ms(cfg: dict) -> int:
    return int(cfg.get("btn_b_scroll_ms", BTN_B_SCROLL_MS))


def btn_b_repeat_delay_ms(cfg: dict) -> int:
    return int(cfg.get("btn_b_repeat_delay_ms", BTN_B_REPEAT_DELAY_MS))
