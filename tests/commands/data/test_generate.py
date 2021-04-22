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
from typing import Optional
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.constants import ENGINE_IMAGE
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


def test_data_generate_runs_engine_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE
    assert args[1] == "latest"


def test_data_generate_adds_destination_dir_pointing_to_data_directory_to_entrypoint() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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
    container.docker_manager.override(providers.Object(docker_manager))

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
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE, "latest")
    docker_manager.run_image.assert_called_once()


def test_data_generate_runs_custom_version() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean,
                                ["data", "generate", "--start", "20200101", "--symbol-count", "1", "--version", "3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE
    assert args[1] == "3"


def test_data_generate_aborts_when_version_invalid() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.tag_exists.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean,
                                ["data", "generate", "--start", "20200101", "--symbol-count", "1", "--version", "3"])

    assert result.exit_code != 0

    docker_manager.run_lean.assert_not_called()


def test_data_generate_aborts_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()


@pytest.mark.parametrize("version_option,update_flag,update_check_expected", [(None, True, False),
                                                                              (None, False, True),
                                                                              ("3", True, False),
                                                                              ("3", False, False),
                                                                              ("latest", True, False),
                                                                              ("latest", False, True)])
def test_data_generate_checks_for_updates(update_manager_mock: mock.Mock,
                                          version_option: Optional[str],
                                          update_flag: bool,
                                          update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []
    if version_option is not None:
        options.extend(["--version", version_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["data", "generate", "--start", "20200101", "--symbol-count", "1", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
