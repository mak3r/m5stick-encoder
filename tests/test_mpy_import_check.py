"""Regression test: mpy_import_check.py fails when a shim is missing.

Runs only when the ``micropython`` unix port is present on PATH; skipped
otherwise (the ``mpy-import`` CI job provides it).
"""

import os
import shutil
import subprocess
import textwrap

import pytest

MPY = shutil.which("micropython")
pytestmark = pytest.mark.skipif(MPY is None, reason="micropython not on PATH")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _micropypath(*dirs: str) -> str:
    return ":".join(os.path.join(REPO, d) for d in dirs)


def test_check_passes_with_vendor_on_path():
    result = subprocess.run(
        [MPY, "tools/mpy_import_check.py"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "MICROPYPATH": _micropypath("src", "vendor")},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_fails_without_vendor_shims(tmp_path):
    # A bare `from typing import X` in a shipped module fails if vendor/ is
    # absent from MICROPYPATH.  Write a minimal probe script so the test is
    # self-contained and doesn't depend on the check script's own path list.
    probe = tmp_path / "probe.py"
    probe.write_text(
        textwrap.dedent("""\
            import sys
            sys.path.insert(0, "src")
            try:
                import typing
                print("PASS typing")
                sys.exit(0)
            except ImportError as e:
                print("FAIL typing : " + str(e))
                sys.exit(1)
        """)
    )
    env = {k: v for k, v in os.environ.items() if k != "MICROPYPATH"}
    result = subprocess.run(
        [MPY, str(probe)],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=env,
    )
    # MicroPython ships no `typing` module — without the vendor shim the import
    # must fail, proving the gate catches this class of bug.
    assert result.returncode != 0, (
        "Expected failure without vendor shim, but micropython imported typing "
        "successfully — MicroPython may now bundle a typing stub."
    )
