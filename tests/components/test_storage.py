import json
from pathlib import Path

from lean.components.storage import Storage


def test_storage_get_should_read_key_from_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.get("key") == "value"


def test_storage_get_should_return_default_when_key_not_set() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.get("key2", "my-default") == "my-default"


def test_storage_set_should_override_values_in_existing_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))
    storage.set("key", "new-value")

    data = json.loads(path.read_text())
    assert data == {"key": "new-value"}


def test_storage_set_should_create_new_file_when_file_does_not_exist() -> None:
    path = Path.cwd() / "config.json"

    storage = Storage(str(path))
    storage.set("key", "value")

    data = json.loads(path.read_text())
    assert data == {"key": "value"}


def test_storage_has_should_return_true_when_key_exists_in_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.has("key")


def test_storage_has_should_return_false_when_key_does_not_exist_in_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert not storage.has("key2")


def test_storage_has_should_return_false_when_file_does_not_exist() -> None:
    path = Path.cwd() / "config.json"

    storage = Storage(str(path))

    assert not storage.has("key")


def test_storage_clear_should_delete_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))
    storage.clear()

    assert not path.exists()
