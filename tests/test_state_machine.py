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


def test_pwr_short_from_zero_wraps_to_25():
    app = make_app(wheel_idx=0)
    changed = app.handle(ButtonEvent.PWR_SHORT)
    assert changed is True
    assert app.state.wheel_idx == 25


def test_pwr_short_decrements_within_range():
    app = make_app(wheel_idx=5)
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.wheel_idx == 4


def test_btn_b_from_25_wraps_to_0():
    app = make_app(wheel_idx=25)
    changed = app.handle(ButtonEvent.BTN_B_PRESS)
    assert changed is True
    assert app.state.wheel_idx == 0


def test_btn_b_increments_within_range():
    app = make_app(wheel_idx=5)
    app.handle(ButtonEvent.BTN_B_PRESS)
    assert app.state.wheel_idx == 6


def _type_word(app: App, word: str) -> None:
    """Drive the wheel to each letter via BTN_B then commit with BTN_A."""
    for ch in word:
        target = ord(ch) - ord("A")
        while app.state.wheel_idx != target:
            app.handle(ButtonEvent.BTN_B_PRESS)
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


def test_pwr_double_pops_one_from_each_buf():
    app = make_app()
    _type_word(app, "HELLO")
    changed = app.handle(ButtonEvent.PWR_DOUBLE)
    assert changed is True
    assert app.state.in_buf == "HELL"
    assert app.state.out_buf == "URYY"


def test_pwr_double_on_empty_is_noop():
    app = make_app()
    changed = app.handle(ButtonEvent.PWR_DOUBLE)
    assert changed is False
    assert app.state.in_buf == ""
    assert app.state.out_buf == ""


def test_pwr_long_toggles_enc_to_dec_and_swaps_bufs():
    app = make_app()
    _type_word(app, "HELLO")
    changed = app.handle(ButtonEvent.PWR_LONG)
    assert changed is True
    assert app.state.mode == "DEC"
    # Previous out_buf becomes new in_buf; re-derived under DEC, rot13 is
    # self-inverse so out_buf lands back at the original plaintext.
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"


def test_pwr_long_round_trip_swaps_and_redrives():
    app = make_app()
    _type_word(app, "HELLO")
    assert app.state.mode == "ENC"
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"

    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"

    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.mode == "ENC"
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"


def test_pwr_long_on_empty_buffers_only_toggles_mode():
    app = make_app()
    changed = app.handle(ButtonEvent.PWR_LONG)
    assert changed is True
    assert app.state.mode == "DEC"
    assert app.state.in_buf == ""
    assert app.state.out_buf == ""


def test_pwr_long_toggles_dec_to_enc():
    app = make_app(mode="DEC")
    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.mode == "ENC"


def test_pwr_long_preserves_wheel_idx_and_algorithm():
    app = make_app(wheel_idx=7)
    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.wheel_idx == 7
    assert app.state.algorithm == "rot13"


def test_sequence_type_hello_then_toggle_swaps():
    app = make_app()
    _type_word(app, "HELLO")
    assert app.state.in_buf == "HELLO"
    assert app.state.out_buf == "URYYB"
    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "URYYB"
    assert app.state.out_buf == "HELLO"


def test_mutating_events_return_true():
    app = make_app()
    assert app.handle(ButtonEvent.BTN_A_PRESS) is True
    assert app.handle(ButtonEvent.BTN_B_PRESS) is True
    assert app.handle(ButtonEvent.PWR_SHORT) is True
    assert app.handle(ButtonEvent.PWR_DOUBLE) is True
    assert app.handle(ButtonEvent.PWR_LONG) is True


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
    # Switch to DEC: PWR_LONG swaps out_buf into in_buf and re-derives via
    # decode() under the new mode.
    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.mode == "DEC"
    assert app.state.in_buf == "XX"
    assert app.state.out_buf == "YY"
    app.handle(ButtonEvent.BTN_A_PRESS)
    assert app.state.in_buf == "XXA"
    assert app.state.out_buf == "YYY"
