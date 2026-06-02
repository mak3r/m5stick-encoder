"""Flash persistence for cipher setup (algorithm + per-cipher keys).

All functions accept injectable paths so tests can use tmp directories
without touching the device filesystem. On first boot, missing files
return safe defaults.

Key files are per-cipher so switching algorithms does not clobber another
cipher's saved key:
  key.txt         — keyword cipher key (default "KEY")
  caesar_key.txt  — caesar cipher key  (default "D")
  cipher_algo.txt — last selected algorithm name
"""

_DEFAULT_KEY = "KEY"
_DEFAULT_CAESAR_KEY = "D"
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
    """Persist algorithm and keyword key to flash."""
    save_key(key, key_path)
    with open(algo_path, "w") as f:
        f.write(algorithm)


def load_caesar_key(path: str = "caesar_key.txt") -> str:
    """Return the saved Caesar cipher key letter, defaulting to 'D'."""
    try:
        with open(path) as f:
            k = f.read().strip().upper()
            return k[0] if k else _DEFAULT_CAESAR_KEY
    except OSError:
        return _DEFAULT_CAESAR_KEY


def save_caesar_key(key: str, path: str = "caesar_key.txt") -> None:
    """Persist the Caesar cipher key letter to flash."""
    with open(path, "w") as f:
        f.write(key[0].upper() if key else _DEFAULT_CAESAR_KEY)


def save_algorithm(algo: str, path: str = "cipher_algo.txt") -> None:
    """Persist the active algorithm name to flash without touching any key file."""
    with open(path, "w") as f:
        f.write(algo)
