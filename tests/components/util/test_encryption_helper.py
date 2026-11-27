from pathlib import Path

import pytest

from lean.components.config.storage import Storage
from lean.components.util.encryption_helper import _validate_key_state_for_local_project


def _make_key(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_validate_key_state_accepts_identical_key_at_another_path() -> None:
    registered = _make_key(Path.cwd() / "registered.txt", "same-key-content")
    copy = _make_key(Path.cwd() / "copy.txt", "same-key-content")
    config = Storage(str(Path.cwd() / "config.json"))
    config.set("encryption-key-path", str(registered))

    _validate_key_state_for_local_project(config, copy)


def test_validate_key_state_rejects_different_key() -> None:
    registered = _make_key(Path.cwd() / "registered.txt", "key-one")
    other = _make_key(Path.cwd() / "other.txt", "key-two")
    config = Storage(str(Path.cwd() / "config.json"))
    config.set("encryption-key-path", str(registered))

    with pytest.raises(RuntimeError, match="is different from the one provided"):
        _validate_key_state_for_local_project(config, other)


def test_validate_key_state_rejects_when_registered_key_is_missing() -> None:
    other = _make_key(Path.cwd() / "other.txt", "key-two")
    config = Storage(str(Path.cwd() / "config.json"))
    config.set("encryption-key-path", str(Path.cwd() / "gone.txt"))

    with pytest.raises(RuntimeError, match="is different from the one provided"):
        _validate_key_state_for_local_project(config, other)
