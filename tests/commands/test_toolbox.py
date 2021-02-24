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

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_project


def test_toolbox_runs_engine_container() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == "quantconnect/lean"
    assert args[1] == "latest"


def test_toolbox_adds_destination_dir_pointing_to_data_directory_to_entrypoint() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "--destination-dir" in kwargs["entrypoint"]
    assert str(Path.cwd() / "data") in kwargs["volumes"]

    destination_dir = kwargs["entrypoint"][kwargs["entrypoint"].index("--destination-dir") + 1]
    assert kwargs["volumes"][str(Path.cwd() / "data")]["bind"] == destination_dir


def test_toolbox_adds_help_to_entrypoint_when_toolbox_help_option_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--toolbox-help"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "--help" in kwargs["entrypoint"]


def test_toolbox_adds_extra_options_to_entrypoint() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--option1=value1", "--option2", "value2"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    entrypoint = " ".join(kwargs["entrypoint"])
    assert "--option1 value1" in entrypoint
    assert "--option2 value2" in entrypoint


def test_toolbox_aborts_when_destination_dir_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--destination-dir", "data"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_not_called()


@pytest.mark.parametrize("option", ["--source-dir", "--source-meta-dir"])
def test_toolbox_mounts_directory_as_volume_when_directory_option_given(option) -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    path = Path.cwd() / "data-directory"
    path.mkdir()

    result = CliRunner().invoke(lean, ["toolbox", option, "data-directory"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert option in kwargs["entrypoint"]
    assert str(path) in kwargs["volumes"]
    assert kwargs["volumes"][str(path)]["bind"].endswith(option.lstrip("--"))


@pytest.mark.parametrize("option", ["--source-dir", "--source-meta-dir"])
def test_toolbox_aborts_when_directory_option_given_with_non_existent_directory(option) -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", option, "fake-directory"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_not_called()


@pytest.mark.parametrize("option", ["--source-dir", "--source-meta-dir"])
def test_toolbox_aborts_when_directory_option_given_with_file(option) -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    (Path.cwd() / "file.txt").touch()

    result = CliRunner().invoke(lean, ["toolbox", option, "file.txt"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_not_called()


def test_toolbox_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with("quantconnect/lean", "latest")
    docker_manager.run_image.assert_called_once()


def test_toolbox_runs_custom_version() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--version", "3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == "quantconnect/lean"
    assert args[1] == "3"


def test_toolbox_aborts_when_version_invalid() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    docker_manager.tag_exists.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox", "--version", "3"])

    assert result.exit_code != 0

    docker_manager.run_lean.assert_not_called()


def test_toolbox_aborts_when_run_image_fails() -> None:
    create_fake_lean_cli_project()

    def run_image(*args, **kwargs) -> None:
        raise RuntimeError("Oops")

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["toolbox"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()
