"""Flash persistence for cipher setup (algorithm + keyword key).

All functions accept injectable paths so tests can use tmp directories
without touching the device filesystem. On first boot, missing files
return safe defaults.
"""

_DEFAULT_KEY = "KEY"
_DEFAULT_ALGO = "rot13"


def load_key(path: str = "key.txt") -> str:
    try:
        with open(path) as f:
            k = f.read().strip().upper()
            return k if k else _DEFAULT_KEY
    except OSError:
        return _DEFAULT_KEY


def save_key(key: str, path: str = "key.txt") -> None:
    with open(path, "w") as f:
        f.write(key.upper())


def load_setup(
    key_path: str = "key.txt",
    algo_path: str = "cipher_algo.txt",
) -> tuple[str, str]:
    """Return (algorithm, key) from flash, falling back to defaults."""
    key = load_key(key_path)
    try:
        with open(algo_path) as f:
            algo = f.read().strip()
            if not algo:
                algo = _DEFAULT_ALGO
    except OSError:
        algo = _DEFAULT_ALGO
    return algo, key


def save_setup(
    algorithm: str,
    key: str,
    key_path: str = "key.txt",
    algo_path: str = "cipher_algo.txt",
) -> None:
    """Persist algorithm and key to flash."""
    save_key(key, key_path)
    with open(algo_path, "w") as f:
        f.write(algorithm)
