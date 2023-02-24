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
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest import mock
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from lean.click import DateParameter, LeanCommand, PathParameter
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


@patch("platform.platform", lambda: "OS")
def test_lean_command_enables_verbose_logging_when_verbose_option_given() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        pass

    logger = mock.Mock()
    container.logger = logger

    result = CliRunner().invoke(command, ["--verbose"])

    assert result.exit_code == 0

    assert logger.debug_logging_enabled


def test_lean_command_sets_default_lean_config_path_when_lean_config_option_given() -> None:
    create_fake_lean_cli_directory()

    @click.command(cls=LeanCommand, requires_lean_config=True)
    def command() -> None:
        pass

    lean_config_manager = mock.Mock()
    lean_config_manager.get_cli_root_directory = mock.MagicMock(return_value=Path.cwd())
    container.lean_config_manager = lean_config_manager

    with (Path.cwd() / "custom-config.json").open("w+", encoding="utf-8") as file:
        file.write("{}")

    result = CliRunner().invoke(command, ["--lean-config", "custom-config.json"])

    assert result.exit_code == 0

    lean_config_manager.set_default_lean_config_path.assert_called_once_with(Path.cwd() / "custom-config.json")


def test_lean_command_fails_when_lean_config_not_available() -> None:
    @click.command(cls=LeanCommand, requires_lean_config=True)
    def command() -> None:
        pass

    os.chdir(Path.home())

    result = CliRunner().invoke(command)

    assert result.exit_code != 0


def test_lean_command_parses_unknown_options() -> None:
    given_ctx: Optional[click.Context] = None

    @click.command(cls=LeanCommand, allow_unknown_options=True)
    @click.pass_context
    def command(ctx: click.Context, **kwargs) -> None:
        nonlocal given_ctx
        given_ctx = ctx

    result = CliRunner().invoke(command, ["--key1", "value1", "abc", "--key2=value2", "def", "--key3", "", "ghi"])

    assert result.exit_code == 0

    assert given_ctx is not None
    assert given_ctx.params == {
        "key1": "value1",
        "key2": "value2",
        "key3": ""
    }


def test_lean_command_checks_for_cli_updates() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        pass

    update_manager = mock.Mock()
    container.update_manager = update_manager

    result = CliRunner().invoke(command)

    assert result.exit_code == 0

    update_manager.warn_if_cli_outdated.assert_called_once()


def test_lean_command_does_not_check_for_cli_updates_when_command_raises() -> None:
    @click.command(cls=LeanCommand)
    def command() -> None:
        raise RuntimeError("Oops")

    update_manager = mock.Mock()
    container.update_manager = update_manager

    result = CliRunner().invoke(command)

    assert result.exit_code != 0

    update_manager.warn_if_cli_outdated.assert_not_called()


def test_path_parameter_fails_when_input_not_valid_path() -> None:
    @click.command()
    @click.argument("arg", type=PathParameter(exists=False, file_okay=True, dir_okay=True))
    def command(arg: Path) -> None:
        pass

    path_manager = mock.Mock()
    path_manager.is_cli_path_valid.return_value = False
    container.path_manager = path_manager

    result = CliRunner().invoke(command, ["invalid-path.txt"])

    assert result.exit_code != 0


def test_path_parameter_fails_when_input_not_existent_and_exists_required() -> None:
    @click.command()
    @click.argument("arg", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
    def command(arg: Path) -> None:
        pass

    result = CliRunner().invoke(command, ["fake-file.txt"])

    assert result.exit_code != 0


def test_path_parameter_fails_when_input_is_file_and_file_not_okay() -> None:
    @click.command()
    @click.argument("arg", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
    def command(arg: Path) -> None:
        pass

    (Path.cwd() / "empty-file.txt").touch()

    result = CliRunner().invoke(command, ["empty-file.txt"])

    assert result.exit_code != 0


def test_path_parameter_fails_when_input_is_directory_and_directory_not_okay() -> None:
    @click.command()
    @click.argument("arg", type=PathParameter(exists=True, file_okay=True, dir_okay=False))
    def command(arg: Path) -> None:
        pass

    (Path.cwd() / "Empty Directory").mkdir()

    result = CliRunner().invoke(command, ["Empty Directory"])

    assert result.exit_code != 0


@pytest.mark.parametrize("input", ["20201231", "2020-12-31"])
def test_date_parameter_returns_datetime_object(input: str) -> None:
    given_arg: Optional[datetime] = None

    @click.command()
    @click.argument("arg", type=DateParameter())
    def command(arg: datetime) -> None:
        nonlocal given_arg
        given_arg = arg

    result = CliRunner().invoke(command, [input])

    assert result.exit_code == 0

    assert given_arg is not None
    assert given_arg.year == 2020
    assert given_arg.month == 12
    assert given_arg.day == 31


@pytest.mark.parametrize("input", ["20203112", "2020-31-12", "yyyymmdd", "this is invalid input"])
def test_date_parameter_fails_when_input_not_formatted_as_yyyymmdd(input: str) -> None:
    @click.command()
    @click.argument("arg", type=DateParameter())
    def command(arg: datetime) -> None:
        pass

    result = CliRunner().invoke(command, [input])

    assert result.exit_code != 0
