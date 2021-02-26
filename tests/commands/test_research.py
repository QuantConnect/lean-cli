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
from typing import Optional
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_project


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


def test_research_runs_research_container() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == "quantconnect/research"
    assert args[1] == "latest"


def test_research_mounts_config_file() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Launcher/bin/Debug/Notebooks/config.json" for mount in kwargs["mounts"]])


def test_research_adds_required_keys_to_project_config() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == "/Lean/Launcher/bin/Debug/Notebooks/config.json"][0]

    with open(mount["Source"]) as file:
        config = json.load(file)

    for key in ["composer-dll-directory", "messaging-handler", "job-queue-handler", "api-handler"]:
        assert key in config


def test_research_adds_credentials_to_project_config() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    container.cli_config_manager().user_id.set_value("123")
    container.cli_config_manager().api_token.set_value("456")

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == "/Lean/Launcher/bin/Debug/Notebooks/config.json"][0]

    with open(mount["Source"]) as file:
        config = json.load(file)

    assert config["job-user-id"] == "123"
    assert config["api-access-token"] == "456"


def test_research_mounts_data_directory() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "data") in kwargs["volumes"]


def test_research_mounts_project_directory() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "Python Project") in kwargs["volumes"]


def test_research_exposes_8888_when_no_port_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"] == {"8888": "8888"}


def test_research_exposes_custom_port_when_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project", "--port", "1234"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"] == {"8888": "1234"}


@mock.patch("webbrowser.open")
def test_research_opens_browser_when_container_started(open) -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "on_run" in kwargs
    kwargs["on_run"]()

    open.assert_called_once_with("http://localhost:8888/")


def test_research_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with("quantconnect/research", "latest")
    docker_manager.run_image.assert_called_once()


def test_research_runs_custom_version() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project", "--version", "3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == "quantconnect/research"
    assert args[1] == "3"


def test_research_aborts_when_version_invalid() -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    docker_manager.tag_exists.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["research", "Python Project", "--version", "3"])

    assert result.exit_code != 0

    docker_manager.run_lean.assert_not_called()


@pytest.mark.parametrize("version_option,update_flag,update_check_expected", [(None, True, False),
                                                                              (None, False, True),
                                                                              ("3", True, False),
                                                                              ("3", False, False),
                                                                              ("latest", True, False),
                                                                              ("latest", False, True)])
def test_research_checks_for_updates(update_manager_mock: mock.Mock,
                                     version_option: Optional[str],
                                     update_flag: bool,
                                     update_check_expected: bool) -> None:
    create_fake_lean_cli_project()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    options = []
    if version_option is not None:
        options.extend(["--version", version_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["research", "Python Project", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with("quantconnect/research")
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
