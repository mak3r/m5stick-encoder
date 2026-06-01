from ui.key_store import load_key, save_key


def test_load_key_returns_default_when_file_missing(tmp_path):
    path = str(tmp_path / "key.txt")
    assert load_key(path) == "KEY"


def test_save_then_load_round_trips(tmp_path):
    path = str(tmp_path / "key.txt")
    save_key("SECRET", path)
    assert load_key(path) == "SECRET"


def test_save_uppercases_key(tmp_path):
    path = str(tmp_path / "key.txt")
    save_key("secret", path)
    assert load_key(path) == "SECRET"


def test_load_uppercases_stored_value(tmp_path):
    path = str(tmp_path / "key.txt")
    with open(path, "w") as f:
        f.write("hello")
    assert load_key(path) == "HELLO"


def test_load_returns_default_for_empty_file(tmp_path):
    path = str(tmp_path / "key.txt")
    with open(path, "w") as f:
        f.write("   ")
    assert load_key(path) == "KEY"


def test_save_overwrites_existing_key(tmp_path):
    path = str(tmp_path / "key.txt")
    save_key("FIRST", path)
    save_key("SECOND", path)
    assert load_key(path) == "SECOND"
