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


def test_set_sanitizes_an_unsupported_key_with_a_warning() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    api_client.object_store.exists.return_value = False
    initialize_container(api_client_to_use=api_client)
    file_path = str(Path.joinpath(Path.cwd(), "lean.json"))

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "trade log: AI & Cloud.csv", file_path])

    assert result.exit_code == 0
    assert "Key 'trade log: AI & Cloud.csv' is not supported: unsupported characters ':', '&'. Keys may only contain" in " ".join(result.output.split())
    assert "Using 'trade log_ AI _ Cloud.csv' instead" in " ".join(result.output.split())
    assert "will be overwritten" not in result.output
    api_client.object_store.exists.assert_called_once_with('trade log_ AI _ Cloud.csv', 'abc')
    with open(file_path, "rb") as file:
        container.api_client.object_store.set.assert_called_once_with('trade log_ AI _ Cloud.csv', file.read(), 'abc')


def test_set_warns_when_the_sanitized_key_overwrites_an_existing_object() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    api_client.object_store.exists.return_value = True
    initialize_container(api_client_to_use=api_client)
    file_path = str(Path.joinpath(Path.cwd(), "lean.json"))

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "report (1).csv", file_path])

    assert result.exit_code == 0
    assert "'report _1_.csv' already exists and will be overwritten" in " ".join(result.output.split())
    container.api_client.object_store.set.assert_called_once_with('report _1_.csv', mock.ANY, 'abc')


def test_set_keeps_a_supported_key_silently() -> None:
    create_fake_lean_cli_project("test", "python")
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    initialize_container(api_client_to_use=api_client)
    file_path = str(Path.joinpath(Path.cwd(), "lean.json"))

    result = CliRunner().invoke(lean, ["cloud", "object-store", "set", "folder/trade_log-2024.csv", file_path])

    assert result.exit_code == 0
    assert "is not supported" not in result.output
    api_client.object_store.exists.assert_not_called()
    container.api_client.object_store.set.assert_called_once_with('folder/trade_log-2024.csv', mock.ANY, 'abc')
