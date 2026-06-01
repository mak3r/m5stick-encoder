"""Tests for hw/buzzer.py host-stub behaviour.

On host (no ``machine`` module) the stub raises RuntimeError for all
playback calls but exposes the ``muted`` attribute correctly.
"""

import pytest


def _import_buzzer():
    """Import hw.buzzer by injecting src/ into sys.path if needed."""
    import importlib

    # src/ is on pytest's pythonpath via pyproject.toml; direct import works.
    return importlib.import_module("hw.buzzer")


def test_stub_loads_without_machine():
    mod = _import_buzzer()
    assert hasattr(mod, "Buzzer")


def test_stub_muted_false_by_default():
    mod = _import_buzzer()
    b = mod.Buzzer()
    assert b.muted is False


def test_stub_muted_true_when_set():
    mod = _import_buzzer()
    b = mod.Buzzer(muted=True)
    assert b.muted is True


def test_stub_beep_commit_raises():
    mod = _import_buzzer()
    b = mod.Buzzer()
    with pytest.raises(RuntimeError):
        b.beep_commit()


def test_stub_beep_backspace_raises():
    mod = _import_buzzer()
    b = mod.Buzzer()
    with pytest.raises(RuntimeError):
        b.beep_backspace()


def test_stub_beep_mode_raises():
    mod = _import_buzzer()
    b = mod.Buzzer()
    with pytest.raises(RuntimeError):
        b.beep_mode()


def test_stub_jingle_boot_raises():
    mod = _import_buzzer()
    b = mod.Buzzer()
    with pytest.raises(RuntimeError):
        b.jingle_boot()


def test_stub_deinit_raises():
    mod = _import_buzzer()
    b = mod.Buzzer()
    with pytest.raises(RuntimeError):
        b.deinit()
