# vendor/ — MicroPython stdlib shims

These shims allow `src/` to import on stock MicroPython (ESP32 generic build, v1.28.0),
which does not bundle `typing`, `dataclasses`, `enum`, or `collections.abc`.

## Upstream reference

Pinned to micropython-lib commit `8380c7bb8f9e5e5260e9539156742925e00366b2`
(the submodule revision shipped with MicroPython v1.28.0).

micropython-lib did **not** carry `typing`, `dataclasses`, `enum`, or `collections.abc`
at that commit. The shims in this directory are minimal hand-written implementations
verified to cover the symbols used by `src/`.

## License

MIT — matching the MicroPython project license.

## Contents

| File | Symbols provided | Source module in src/ |
|---|---|---|
| `typing.py` | `Protocol`, `runtime_checkable`, `Literal` | `encoder/base.py`, `ui/display.py`, `ui/state.py` |
| `dataclasses.py` | `dataclass`, `field` | `ui/state.py`, `ui/display_mock.py` |
| `enum.py` | `Enum` | `ui/events.py` |
| `collections/abc.py` | `Callable` | `ui/buttons.py` |

## Host pytest isolation

`vendor/` is **not** on the pytest `pythonpath` (which stays `["src"]`). Host tests keep
the real CPython stdlib — in particular `typing.runtime_checkable` isinstance semantics
used by `tests/test_registry.py` and `tests/test_screen_layout.py`.

## Deploying to the device

`tools/upload.sh` (issue #11) copies the shims to `/lib` on the device:

```sh
mpremote mkdir :lib
mpremote cp vendor/typing.py :lib/typing.py
mpremote cp vendor/dataclasses.py :lib/dataclasses.py
mpremote cp vendor/enum.py :lib/enum.py
mpremote cp -r vendor/collections :lib/collections
```

## Recovery with mip

If you need to fetch fresh copies via `mip` on a connected device:

```py
import mip
# No official mip package — use vendor/ copies from this repo.
```
