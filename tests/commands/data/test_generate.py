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

from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.commands import lean
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory
from tests.conftest import initialize_container

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def test_data_generate_runs_engine_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE


def test_data_generate_adds_destination_dir_pointing_to_data_directory_to_entrypoint() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "--destination-dir" in kwargs["entrypoint"]
    assert str(Path.cwd() / "data") in kwargs["volumes"]

    destination_dir = kwargs["entrypoint"][kwargs["entrypoint"].index("--destination-dir") + 1]
    assert kwargs["volumes"][str(Path.cwd() / "data")]["bind"] == destination_dir


def test_data_generate_adds_parameters_to_entrypoint() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["data", "generate",
                                       "--start", "20200101",
                                       "--end", "20200201",
                                       "--symbol-count", "1",
                                       "--security-type", "Crypto",
                                       "--resolution", "Daily",
                                       "--data-density", "Sparse",
                                       "--market", "bitfinex"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "--start 20200101" in " ".join(kwargs["entrypoint"])
    assert "--end 20200201" in " ".join(kwargs["entrypoint"])
    assert "--symbol-count 1" in " ".join(kwargs["entrypoint"])
    assert "--security-type Crypto" in " ".join(kwargs["entrypoint"])
    assert "--resolution Daily" in " ".join(kwargs["entrypoint"])
    assert "--data-density Sparse" in " ".join(kwargs["entrypoint"])
    assert "--market bitfinex" in " ".join(kwargs["entrypoint"])


def test_data_generate_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    initialize_container(docker_manager_to_use=docker_manager)

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    docker_manager.run_image.assert_called_once()


def test_data_generate_runs_custom_image_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    initialize_container(docker_manager_to_use=docker_manager)

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean,
                                ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="123")


def test_data_generate_runs_custom_image_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    initialize_container(docker_manager_to_use=docker_manager)

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean,
                                ["data", "generate",
                                 "--start", "20200101",
                                 "--symbol-count", "1",
                                 "--image", "custom/lean:456"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="456")


def test_data_generate_aborts_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False
    initialize_container(docker_manager_to_use=docker_manager)

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()


def test_data_generate_tickers() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "2", "--tickers", "SPY,AAPL"])

    assert result.exit_code == 0
