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

from unittest import mock
from pathlib import Path
from click.testing import CliRunner

from lean.commands import lean
from lean.container import container
from tests.conftest import initialize_container
from tests.test_helpers import create_fake_lean_cli_project

def test_set_sets_value_when_path_is_given() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    initialize_container(api_client_to_use=api_client)

    file_path = Path.joinpath(Path.cwd(), "lean.json")
    assert (file_path).exists()
    file_path = str(file_path)

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "test-key", file_path])
    assert result.exit_code == 0
    with open(file_path, "rb") as file:
        bytes_data: bytes = file.read()
        container.api_client.object_store.set.assert_called_once_with('test-key', bytes_data, 'abc')


def test_set_prints_the_warnings_the_api_returns() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    api_client.object_store.set.return_value = {
        "success": True,
        "key": "trade log_ AI _ Cloud.csv",
        "warnings": ["Key 'trade log: AI &amp; Cloud.csv' is not supported: unsupported characters ':', '&'. "
                     "Using 'trade log_ AI _ Cloud.csv' instead"]
    }
    initialize_container(api_client_to_use=api_client)
    file_path = str(Path.joinpath(Path.cwd(), "lean.json"))

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "trade log: AI & Cloud.csv", file_path])

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Key 'trade log: AI & Cloud.csv' is not supported: unsupported characters ':', '&'. " \
           "Using 'trade log_ AI _ Cloud.csv' instead" in output
    with open(file_path, "rb") as file:
        container.api_client.object_store.set.assert_called_once_with('trade log: AI & Cloud.csv', file.read(), 'abc')


def test_set_prints_no_warning_when_the_api_returns_none() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    api_client.object_store.set.return_value = {"success": True, "key": "folder/trade_log-2024.csv", "warnings": []}
    initialize_container(api_client_to_use=api_client)
    file_path = str(Path.joinpath(Path.cwd(), "lean.json"))

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "folder/trade_log-2024.csv", file_path])

    assert result.exit_code == 0
    assert "is not supported" not in result.output
    container.api_client.object_store.set.assert_called_once_with('folder/trade_log-2024.csv', mock.ANY, 'abc')
