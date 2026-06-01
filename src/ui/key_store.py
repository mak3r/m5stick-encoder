"""Flash persistence for the keyword cipher key.

``load_key`` / ``save_key`` are pure functions with an injectable path so
tests can use a tmp directory without touching the device filesystem.
On first boot (no file present) ``load_key`` returns the default key.
"""

_DEFAULT = "KEY"


def load_key(path: str = "/key.txt") -> str:
    try:
        with open(path) as f:
            k = f.read().strip().upper()
            return k if k else _DEFAULT
    except OSError:
        return _DEFAULT


def save_key(key: str, path: str = "/key.txt") -> None:
    with open(path, "w") as f:
        f.write(key.upper())
