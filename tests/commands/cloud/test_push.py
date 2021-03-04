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
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


def test_cloud_push_pushes_all_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once()
    args, kwargs = push_manager.push_projects.call_args

    assert set(args[0]) == {Path.cwd() / "Python Project", Path.cwd() / "CSharp Project"}


def test_cloud_push_pushes_single_project_when_project_option_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])


def test_cloud_push_aborts_when_given_directory_is_not_lean_project() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_aborts_when_given_directory_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()
