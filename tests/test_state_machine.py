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


def test_pwr_double_cycles_algorithm():
    app = make_app()
    assert app.state.algorithm == "rot13"
    changed = app.handle(ButtonEvent.PWR_DOUBLE)
    assert changed is True
    assert app.state.algorithm == "keyword"


def test_pwr_double_clears_buffers():
    app = make_app()
    app.handle(ButtonEvent.BTN_A_PRESS)  # adds A → N
    assert app.state.in_buf == "A"
    app.handle(ButtonEvent.PWR_DOUBLE)
    assert app.state.in_buf == ""
    assert app.state.out_buf == ""


def test_pwr_long_is_noop_when_not_keyword():
    app = make_app()
    assert app.state.algorithm == "rot13"
    changed = app.handle(ButtonEvent.PWR_LONG)
    assert changed is False
    assert app.state.editing_key is False


def test_pwr_long_enters_key_edit_when_keyword():
    from encoder.keyword import KeywordCipher

    state = State(algorithm="keyword")
    app = App(state, {"keyword": KeywordCipher()})
    changed = app.handle(ButtonEvent.PWR_LONG)
    assert changed is True
    assert app.state.editing_key is True


def test_pwr_long_preloads_current_key_into_key_buf():
    from encoder.keyword import KeywordCipher

    state = State(algorithm="keyword", cipher_key="SECRET")
    app = App(state, {"keyword": KeywordCipher("SECRET")})
    app.handle(ButtonEvent.PWR_LONG)
    assert app.state.key_buf == "SECRET"


def _make_keyword_app(key="KEY", on_save_key=None, **state_kwargs):
    from encoder.keyword import KeywordCipher

    state = State(algorithm="keyword", cipher_key=key, **state_kwargs)
    return App(state, {"keyword": KeywordCipher(key)}, on_save_key=on_save_key)


def test_key_edit_a_press_appends_letter():
    app = _make_keyword_app()
    app.handle(ButtonEvent.PWR_LONG)  # enter edit mode, key_buf = "KEY"
    app.state.key_buf = ""  # start fresh
    app.state.wheel_idx = 0  # A
    changed = app.handle(ButtonEvent.BTN_A_PRESS)
    assert changed is True
    assert app.state.key_buf == "A"


def test_key_edit_a_double_deletes_last():
    app = _make_keyword_app()
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = "AB"
    app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert app.state.key_buf == "A"


def test_key_edit_a_double_noop_on_empty():
    app = _make_keyword_app()
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = ""
    changed = app.handle(ButtonEvent.BTN_A_DOUBLE)
    assert changed is False
    assert app.state.key_buf == ""


def test_key_edit_a_long_confirms_and_exits():
    saved = []
    app = _make_keyword_app(on_save_key=saved.append)
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = "SECRET"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.editing_key is False
    assert app.state.cipher_key == "SECRET"
    assert app.state.key_buf == ""
    assert saved == ["SECRET"]


def test_key_edit_a_long_empty_buf_keeps_old_key():
    app = _make_keyword_app(key="HELLO")
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = ""
    app.handle(ButtonEvent.BTN_A_LONG)
    assert app.state.cipher_key == "HELLO"


def test_key_edit_pwr_long_cancels():
    app = _make_keyword_app()
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = "PARTIAL"
    changed = app.handle(ButtonEvent.PWR_LONG)
    assert changed is True
    assert app.state.editing_key is False
    assert app.state.key_buf == ""
    assert app.state.cipher_key == "KEY"  # unchanged


def test_key_edit_wheel_still_works():
    app = _make_keyword_app()
    app.handle(ButtonEvent.PWR_LONG)
    app.state.wheel_idx = 5
    app.handle(ButtonEvent.BTN_B_PRESS)
    assert app.state.wheel_idx == 4
    app.handle(ButtonEvent.PWR_SHORT)
    assert app.state.wheel_idx == 5


def test_pwr_double_cycles_rot13_to_keyword_to_rot13():
    app = make_app()
    assert app.state.algorithm == "rot13"
    app.handle(ButtonEvent.PWR_DOUBLE)
    assert app.state.algorithm == "keyword"
    app.handle(ButtonEvent.PWR_DOUBLE)
    assert app.state.algorithm == "rot13"


def test_key_edit_updates_cipher_instance():
    from encoder.keyword import KeywordCipher

    kw = KeywordCipher("OLD")
    state = State(algorithm="keyword", cipher_key="OLD")
    app = App(state, {"keyword": kw})
    app.handle(ButtonEvent.PWR_LONG)
    app.state.key_buf = "NEW"
    app.handle(ButtonEvent.BTN_A_LONG)
    assert kw.key == "NEW"


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
