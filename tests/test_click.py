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

import os
from pathlib import Path
from unittest import mock

import click
from click.testing import CliRunner
from dependency_injector import providers

from lean.click import LeanCommand, PathParameter
from lean.container import container


def test_lean_command_enables_verbose_logging_when_verbose_option_given() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        pass

    logger = mock.Mock()
    container.logger.override(providers.Object(logger))

    result = CliRunner().invoke(command, ["--verbose"])

    assert result.exit_code == 0

    logger.enable_debug_logging.assert_called_once()


def test_lean_command_sets_default_lean_config_path_when_lean_config_option_given() -> None:
    @click.command(cls=LeanCommand, requires_cli_project=True)
    def command() -> None:
        pass

    lean_config_manager = mock.Mock()
    container.lean_config_manager.override(providers.Object(lean_config_manager))

    with (Path.cwd() / "custom-config.json").open("w+") as file:
        file.write("{}")

    result = CliRunner().invoke(command, ["--lean-config", "custom-config.json"])

    assert result.exit_code == 0

    lean_config_manager.set_default_lean_config_path.assert_called_once_with(Path.cwd() / "custom-config.json")


def test_lean_command_fails_when_not_executed_in_cli_project() -> None:
    @click.command(cls=LeanCommand, requires_cli_project=True)
    def command() -> None:
        pass

    os.chdir(Path.home())

    result = CliRunner().invoke(command)

    assert result.exit_code != 0


def test_lean_command_checks_for_cli_updates() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        pass

    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))

    result = CliRunner().invoke(command)

    assert result.exit_code == 0

    update_manager.warn_if_cli_outdated.assert_called_once()


def test_lean_command_does_not_check_for_cli_updates_when_command_raises() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        raise RuntimeError("Oops")

    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))

    result = CliRunner().invoke(command)

    assert result.exit_code != 0

    update_manager.warn_if_cli_outdated.assert_not_called()


def test_path_parameter_fails_when_input_not_existent_and_exists_required() -> None:
    @click.command(cls=LeanCommand)
    @click.argument("arg", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
    def command(arg: Path) -> None:
        pass

    result = CliRunner().invoke(command, ["fake-file.txt"])

    assert result.exit_code != 0


def test_path_parameter_fails_when_input_is_file_and_file_not_okay() -> None:
    @click.command(cls=LeanCommand)
    @click.argument("arg", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
    def command(arg: Path) -> None:
        pass

    (Path.cwd() / "empty-file.txt").touch()

    result = CliRunner().invoke(command, ["empty-file.txt"])

    assert result.exit_code != 0


def test_path_parameter_fails_when_input_is_directory_and_directory_not_okay() -> None:
    @click.command(cls=LeanCommand)
    @click.argument("arg", type=PathParameter(exists=True, file_okay=True, dir_okay=False))
    def command(arg: Path) -> None:
        pass

    (Path.cwd() / "Empty Directory").mkdir()

    result = CliRunner().invoke(command, ["Empty Directory"])

    assert result.exit_code != 0
