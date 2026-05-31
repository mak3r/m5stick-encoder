"""Verify vendor shims and src modules import cleanly under MicroPython.

Run with:
    micropython tools/mpy_import_check.py

Requires MICROPYPATH to include (or will inject) the repo-relative
``vendor`` and ``src`` directories.  Run from the repo root.
"""

import sys

# Insert vendor and src at the front of sys.path so shims shadow the
# MicroPython builtins that share the same name (collections, etc.).
_repo_vendor = "vendor"
_repo_src = "src"

if _repo_vendor not in sys.path:
    sys.path.insert(0, _repo_vendor)
if _repo_src not in sys.path:
    sys.path.insert(0, _repo_src)

_imports = [
    # vendor shims
    "typing",
    "dataclasses",
    "enum",
    "collections",
    "collections.abc",
    # src modules that depend on the shims
    "encoder",
    "ui.state",
    "ui.buttons",
]

_failed = []

for _name in _imports:
    try:
        __import__(_name)
        print("PASS " + _name)
    except Exception as _e:
        print("FAIL " + _name + " : " + str(_e))
        _failed.append(_name)

print("")
if _failed:
    print("FAILED: " + str(len(_failed)) + " of " + str(len(_imports)))
    sys.exit(1)
else:
    print("ALL PASSED (" + str(len(_imports)) + ")")
    sys.exit(0)
