# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

from lean.components.config.storage import Storage


def test_get_reads_key_from_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.get("key") == "value"


def test_get_returns_default_when_key_not_set() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.get("key2", "my-default") == "my-default"


def test_set_overrides_values_in_existing_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))
    storage.set("key", "new-value")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"key": "new-value"}


def test_set_creates_new_file_when_file_does_not_exist() -> None:
    path = Path.cwd() / "config.json"

    storage = Storage(str(path))
    storage.set("key", "value")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"key": "value"}


def test_has_returns_true_when_key_exists_in_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert storage.has("key")


def test_has_returns_false_when_key_does_not_exist_in_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))

    assert not storage.has("key2")


def test_has_returns_false_when_file_does_not_exist() -> None:
    path = Path.cwd() / "config.json"

    storage = Storage(str(path))

    assert not storage.has("key")


def test_clear_deletes_file() -> None:
    path = Path.cwd() / "config.json"
    with path.open("w+", encoding="utf-8") as file:
        file.write('{ "key": "value" }')

    storage = Storage(str(path))
    storage.clear()

    assert not path.exists()
