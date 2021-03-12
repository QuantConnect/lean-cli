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
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


def create_fake_environment(name: str, live_mode: bool) -> None:
    path = Path.cwd() / "lean.json"

    config = path.read_text()
    config = config.replace("{", f"""
{{
    "environments": {{
        "{name}": {{
            "live-mode": {str(live_mode).lower()}
        }}
    }},
    """)

    path.write_text(config)


def test_live_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_live_aborts_when_environment_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "fake-environment"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_environment_has_live_mode_set_to_false() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("backtesting", False)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "backtesting"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/live").resolve())


def test_live_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper", "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[2].relative_to(Path("Python Project/custom").resolve())


def test_live_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with("quantconnect/lean", "latest")
    lean_runner.run_lean.assert_called_once_with("live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_live_passes_custom_version_to_lean_runner() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper", "--version", "3"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "3",
                                                 None)


def test_live_aborts_when_version_invalid() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    docker_manager.tag_exists.return_value = False

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper", "--version", "3"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("version_option,update_flag,update_check_expected", [(None, True, False),
                                                                              (None, False, True),
                                                                              ("3", True, False),
                                                                              ("3", False, False),
                                                                              ("latest", True, False),
                                                                              ("latest", False, True)])
def test_live_checks_for_updates(update_manager_mock: mock.Mock,
                                 version_option: Optional[str],
                                 update_flag: bool,
                                 update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []
    if version_option is not None:
        options.extend(["--version", version_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["live", "Python Project", "live-paper", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with("quantconnect/lean")
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
