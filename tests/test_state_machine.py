from encoder.rot13 import Rot13Cipher
from ui.app import App
from ui.events import ButtonEvent
from ui.state import State


def make_app(**state_kwargs) -> App:
    return App(State(**state_kwargs), {"rot13": Rot13Cipher()})


def test_initial_state_defaults():
    s = State()
    assert s.mode == "ENC"
    assert s.algorithm == "rot13"
    assert s.wheel_idx == 0
    assert s.in_buf == ""
    assert s.out_buf == ""


def test_btn_a_appends_letter_and_transforms():
    app = make_app(wheel_idx=0)  # A
    changed = app.handle(ButtonEvent.BTN_A_PRESS)
    assert changed is True
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "N"


def test_btn_a_appends_to_existing_buf():
    app = make_app(wheel_idx=5)  # F
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.in_buf == "F"
    assert app.state.out_buf == "S"


def test_pwr_short_increments_from_zero():
    app = make_app(wheel_idx=0)
    changed = app.handle(ButtonEvent.PWR_SHORT)
    assert changed is True
    assert app.state.wheel_idx == 1


def test_pwr_short_from_25_wraps_to_0():
    app = make_app(wheel_idx=25)
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.wheel_idx == 0


def test_pwr_short_increments_within_range():
    app = make_app(wheel_idx=5)
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.wheel_idx == 6


def test_btn_b_from_zero_wraps_to_25():
    app = make_app(wheel_idx=0)
    changed = app.handle(ButtonEvent.BTN_B_PRESS)
    assert changed is True
    assert app.state.wheel_idx == 25


def test_btn_b_decrements_within_range():
    app = make_app(wheel_idx=5)
    app.handle(ButtonEvent.BTN_B_PRESS)
    assert app.state.wheel_idx == 4


def _type_word(app: App, word: str) -> None:
    """Drive the wheel to each letter via PWR_SHORT then commit with BTN_A_PRESS."""
    for ch in word:
        target = ord(ch) - ord("A")
        while app.state.wheel_idx != target:
            app.handle(ButtonEvent.PWR_SHORT)
        app.handle(ButtonEvent.BTN_A_PRESS)


def test_btn_a_enc_appends_plain_and_cipher():
    app = make_app()
    _type_word(app, "HELLO")
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"


def test_btn_a_single_letter_enc():
    app = make_app(wheel_idx=0)  # A
    changed = app.handle(ButtonEvent.BTN_A_PRESS)
    assert changed is True
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "N"


def test_btn_a_dec_appends_cipher_and_plain():
    app = make_app(mode="DEC", wheel_idx=13)  # N → A under rot13
    changed = app.handle(ButtonEvent.BTN_A_PRESS)
    assert changed is True
    assert app.state.in_buf == "N"
    assert app.state.out_buf == "A"


def test_btn_a_double_pops_one_from_each_buf():
    app = make_app()
    _type_word(app, "HELLO")
    changed = app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert changed is True
    assert app.state.in_buf == "HELL"
    assert app.state.out_buf == "URYY"


def test_btn_a_double_on_empty_is_noop():
    app = make_app()
    changed = app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert changed is False
    assert app.state.in_buf == ""
    assert app.state.out_buf == ""


def test_btn_a_long_toggles_enc_to_dec_and_swaps_bufs():
    app = make_app()
    _type_word(app, "HELLO")
    changed = app.handle(ButtonEvent.BTN_A_LONG)
    assert changed is True
    assert app.state.mode == "DEC"
    # Previous out_buf becomes new in_buf; re-derived under DEC, rot13 is
    # self-inverse so out_buf lands back at the original plaintext.
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"


def test_btn_a_long_round_trip_swaps_and_redrives():
    app = make_app()
    _type_word(app, "HELLO")
    assert app.state.mode == "ENC"
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"

    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"

    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "ENC"
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"


def test_btn_a_long_on_empty_buffers_only_toggles_mode():
    app = make_app()
    changed = app.handle(ButtonEvent.BTN_A_LONG)
    assert changed is True
    assert app.state.mode == "DEC"
    assert app.state.in_buf == ""
    assert app.state.out_buf == ""


def test_btn_a_long_toggles_dec_to_enc():
    app = make_app(mode="DEC")
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "ENC"


def test_btn_a_long_preserves_wheel_idx_and_algorithm():
    app = make_app(wheel_idx=7)
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.wheel_idx == 7
    assert app.state.algorithm == "rot13"


def test_sequence_type_hello_then_toggle_swaps():
    app = make_app()
    _type_word(app, "HELLO")
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"


def test_mutating_events_return_true():
    app = make_app()
    assert app.handle(ButtonEvent.BTN_A_PRESS) is True
    assert app.handle(ButtonEvent.BTN_A_DOUBLE) is True
    assert app.handle(ButtonEvent.BTN_B_PRESS) is True
    assert app.handle(ButtonEvent.PWR_SHORT) is True
    assert app.handle(ButtonEvent.BTN_A_LONG) is True


def test_btn_b_long_decrements_wheel():
    app = make_app(wheel_idx=5)
    changed = app.handle(ButtonEvent.BTN_B_LONG)
    assert changed is True
    assert app.state.wheel_idx == 4


def test_btn_b_long_from_zero_wraps_to_25():
    app = make_app(wheel_idx=0)
    changed = app.handle(ButtonEvent.BTN_B_LONG)
    assert changed is True
    assert app.state.wheel_idx == 25


def test_btn_b_long_same_direction_as_btn_b_press():
    app_press = make_app(wheel_idx=10)
    app_long = make_app(wheel_idx=10)
    app_press.handle(ButtonEvent.BTN_B_PRESS)
    app_long.handle(ButtonEvent.BTN_B_LONG)
    assert app_press.state.wheel_idx == app_long.state.wheel_idx


def test_pwr_long_is_always_noop():
    # PWR_LONG intentionally unused: hardware power-off races the event.
    app = make_app()
    assert app.handle(ButtonEvent.PWR_LONG) is False


def test_pwr_double_is_noop_in_encode():
    # No runtime cipher switching — setup is done at boot.
    app = make_app()
    assert app.handle(ButtonEvent.PWR_DOUBLE) is False
    assert app.state.algorithm == "rot13"


def test_btn_a_long_always_toggles_enc_dec_in_encode():
    # BTN_A_LONG toggles ENC↔DEC regardless of cipher — no context-sensitivity.
    from encoder.keyword import KeywordCipher
    state = State(algorithm="keyword", cipher_key="KEY")
    app = App(state, {"rot13": make_app().ciphers["rot13"], "keyword": KeywordCipher()})
    assert app.state.mode == "ENC"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "DEC"


# ---------------------------------------------------------------------------
# setup_cipher screen
# ---------------------------------------------------------------------------

def _make_setup_cipher_app(**state_kwargs):
    """App starting on the cipher-selection screen."""
    from encoder.caesar import CaesarCipher
    from encoder.keyword import KeywordCipher
    state = State(screen="setup_cipher", **state_kwargs)
    return App(state, {
        "rot13": make_app().ciphers["rot13"],
        "keyword": KeywordCipher(),
        "caesar": CaesarCipher(),
    })


def test_setup_cipher_pwr_scrolls_down():
    app = _make_setup_cipher_app(setup_idx=0)
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.setup_idx == 1


def test_setup_cipher_b_scrolls_up():
    app = _make_setup_cipher_app(setup_idx=1)
    app.handle(ButtonEvent.BTN_B_PRESS)
    assert app.state.setup_idx == 0


def test_setup_cipher_scrolling_wraps():
    app = _make_setup_cipher_app(setup_idx=0)
    app.handle(ButtonEvent.BTN_B_PRESS)  # wraps from 0 to last
    assert app.state.setup_idx == len(app.ciphers) - 1


def test_setup_cipher_select_rot13_goes_to_encode():
    app = _make_setup_cipher_app(setup_idx=0)  # rot13 is first
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.screen == "encode"
    assert app.state.algorithm == "rot13"


def test_setup_cipher_select_keyword_goes_to_setup_key():
    from encoder.keyword import KeywordCipher
    state = State(screen="setup_cipher", setup_idx=1, cipher_key="OLD")
    app = App(state, {"rot13": make_app().ciphers["rot13"], "keyword": KeywordCipher()})
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.screen == "setup_key"
    assert app.state.algorithm == "keyword"
    assert app.state.key_buf == "OLD"  # pre-filled from cipher_key


def test_setup_cipher_caesar_is_in_cipher_list():
    app = _make_setup_cipher_app()
    assert "caesar" in app.ciphers


def test_setup_cipher_select_caesar_goes_to_setup_key():
    from encoder.caesar import CaesarCipher
    from encoder.keyword import KeywordCipher
    state = State(screen="setup_cipher", setup_idx=2, caesar_key="F")
    app = App(state, {
        "rot13": make_app().ciphers["rot13"],
        "keyword": KeywordCipher(),
        "caesar": CaesarCipher(),
    })
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.screen == "setup_key"
    assert app.state.algorithm == "caesar"
    assert app.state.key_buf == "F"    # pre-filled from caesar_key, not cipher_key


def test_setup_cipher_caesar_prefill_uses_caesar_key_not_cipher_key():
    from encoder.caesar import CaesarCipher
    from encoder.keyword import KeywordCipher
    state = State(screen="setup_cipher", setup_idx=2, cipher_key="ZEBRA", caesar_key="G")
    app = App(state, {
        "rot13": make_app().ciphers["rot13"],
        "keyword": KeywordCipher(),
        "caesar": CaesarCipher(),
    })
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.key_buf == "G"    # caesar_key, not "ZEBRA"


# ---------------------------------------------------------------------------
# setup_key screen
# ---------------------------------------------------------------------------

def _make_keyword_app(key="KEY", on_save_key=None, **state_kwargs):
    """App on the setup_key screen, pre-loaded with ``key``."""
    from encoder.keyword import KeywordCipher
    state = State(
        algorithm="keyword",
        cipher_key=key,
        screen="setup_key",
        key_buf=key,
        **state_kwargs,
    )
    return App(state, {"keyword": KeywordCipher(key)}, on_save_key=on_save_key)


def test_setup_key_a_press_appends_letter():
    app = _make_keyword_app()
    app.state.key_buf = ""
    app.state.wheel_idx = 0  # A
    changed = app.handle(ButtonEvent.BTN_A_PRESS)
    assert changed is True
    assert app.state.key_buf == "A"


def test_setup_key_a_double_deletes_last():
    app = _make_keyword_app()
    app.state.key_buf = "AB"
    app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert app.state.key_buf == "A"


def test_setup_key_a_double_noop_on_empty():
    app = _make_keyword_app()
    app.state.key_buf = ""
    changed = app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert changed is False
    assert app.state.key_buf == ""


def test_setup_key_a_long_confirms_and_goes_to_encode():
    saved = []
    app = _make_keyword_app(on_save_key=saved.append)
    app.state.key_buf = "SECRET"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.screen == "encode"
    assert app.state.cipher_key == "SECRET"
    assert app.state.key_buf == ""
    assert saved == ["SECRET"]


def test_setup_key_empty_buf_keeps_old_key():
    app = _make_keyword_app(key="HELLO")
    app.state.key_buf = ""
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.cipher_key == "HELLO"
    assert app.state.screen == "encode"


def test_setup_key_wheel_still_works():
    app = _make_keyword_app()
    app.state.wheel_idx = 5
    app.handle(ButtonEvent.BTN_B_PRESS)
    assert app.state.wheel_idx == 4
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.wheel_idx == 5


def test_setup_key_updates_cipher_instance():
    from encoder.keyword import KeywordCipher
    kw = KeywordCipher("OLD")
    state = State(algorithm="keyword", cipher_key="OLD", screen="setup_key", key_buf="OLD")
    app = App(state, {"keyword": kw})
    app.state.key_buf = "NEW"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert kw.key == "NEW"


# ---------------------------------------------------------------------------
# setup_key screen — Caesar-specific (max_key_len=1)
# ---------------------------------------------------------------------------

def _make_caesar_app(key="D", on_save_key=None, **state_kwargs):
    """App on the setup_key screen for caesar, pre-loaded with ``key``."""
    from encoder.caesar import CaesarCipher
    state = State(
        algorithm="caesar",
        caesar_key=key,
        screen="setup_key",
        key_buf=key,
        **state_kwargs,
    )
    return App(state, {"caesar": CaesarCipher(key)}, on_save_key=on_save_key)


def test_caesar_setup_key_a_press_sets_single_letter():
    app = _make_caesar_app(key="D")
    app.state.key_buf = ""
    app.state.wheel_idx = 5  # F
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.key_buf == "F"


def test_caesar_setup_key_a_press_replaces_not_appends():
    # key_buf already has one char; pressing A again must replace it.
    app = _make_caesar_app(key="D")
    app.state.key_buf = "D"
    app.state.wheel_idx = 5  # F
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.key_buf == "F"
    assert len(app.state.key_buf) == 1


def test_caesar_setup_key_a_long_updates_caesar_key():
    saved = []
    app = _make_caesar_app(key="D", on_save_key=saved.append)
    app.state.key_buf = "F"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.caesar_key == "F"
    assert app.state.screen == "encode"
    assert app.state.key_buf == ""
    assert saved == ["F"]


def test_caesar_confirm_does_not_touch_cipher_key():
    # Confirming a caesar key must not overwrite the keyword cipher's saved key.
    app = _make_caesar_app(key="D")
    app.state.cipher_key = "ZEBRA"
    app.state.key_buf = "F"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.cipher_key == "ZEBRA"
    assert app.state.caesar_key == "F"


def test_caesar_empty_buf_keeps_old_key():
    app = _make_caesar_app(key="F")
    app.state.key_buf = ""
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.caesar_key == "F"
    assert app.state.screen == "encode"


def test_caesar_cipher_instance_updated_on_confirm():
    from encoder.caesar import CaesarCipher
    ca = CaesarCipher("D")
    state = State(algorithm="caesar", caesar_key="D", screen="setup_key", key_buf="D")
    app = App(state, {"caesar": ca})
    app.state.key_buf = "F"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert ca.key == "F"


def test_app_is_cipher_agnostic_via_protocol_stub():
    """App must use the cipher passed in, not Rot13Cipher directly."""

    class FixedCipher:
        name = "fixed"

        def encode(self, text: str) -> str:
            return "X" * len(text)

        def decode(self, text: str) -> str:
            return "Y" * len(text)

    state = State(algorithm="fixed")
    app = App(state, {"fixed": FixedCipher()})
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "X"
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.in_buf == "AA"
    assert app.state.out_buf == "XX"
    # Switch to DEC: BTN_A_LONG swaps out_buf into in_buf and re-derives via
    # decode() under the new mode.
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "XX"
    assert app.state.out_buf == "YY"
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.in_buf == "XXA"
    assert app.state.out_buf == "YYY"
