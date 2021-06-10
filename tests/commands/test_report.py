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
from lean.components.config.storage import Storage
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


@pytest.fixture(autouse=True)
def setup_backtest_results() -> None:
    """A pytest fixture which creates a backtest results file before every test."""
    create_fake_lean_cli_directory()

    results_path = Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("w+", encoding="utf-8") as file:
        file.write("{}")


def run_image(image: DockerImage, **kwargs) -> bool:
    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    results_path = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Results")

    output_file = Path(results_path) / Path(config["report-destination"]).name
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w+", encoding="utf-8") as file:
        file.write("<html></html>")

    return True


def test_report_runs_lean_container() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE


def test_report_runs_report_creator() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["working_dir"] == "/Lean/Report/bin/Debug"
    assert kwargs["entrypoint"][0] == "dotnet"
    assert kwargs["entrypoint"][1] == "QuantConnect.Report.dll"


def test_report_mounts_report_config() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Report/bin/Debug/config.json" for mount in kwargs["mounts"]])


def test_report_mounts_data_directory() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Lean/Data" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Lean/Data")
    assert key == str(Path.cwd() / "data")


def test_report_mounts_output_directory() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Results" for volume in kwargs["volumes"].values()])


def test_report_mounts_given_backtest_data_source_file() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--strategy-version", "1.2.3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == "/Lean/Report/bin/Debug/backtest-data-source-file.json"][0]
    assert mount["Source"] == str(Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "results.json")


def test_report_finds_backtest_data_source_file_when_directory_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00",
                                       "--strategy-version", "1.2.3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == "/Lean/Report/bin/Debug/backtest-data-source-file.json"][0]
    assert mount["Source"] == str(Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "results.json")


def test_report_mounts_live_data_source_file_when_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--live-results",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--strategy-version", "1.2.3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = [m for m in kwargs["mounts"] if m["Target"] == "/Lean/Report/bin/Debug/live-data-source-file.json"][0]
    assert mount["Source"] == str(Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "results.json")


def test_report_uses_project_directory_as_strategy_name_when_strategy_name_not_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-name"] == "Python Project"


def test_report_uses_given_strategy_name() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--strategy-name", "My Strategy"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-name"] == "My Strategy"


def test_report_uses_description_from_config_when_strategy_description_not_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("description", "My description")

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-description"] == "My description"


def test_report_uses_given_strategy_description() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--strategy-description", "My strategy description"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-description"] == "My strategy description"


def test_report_uses_given_strategy_version() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--strategy-version", "1.2.3"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-version"] == "1.2.3"


def test_report_uses_given_blank_name_version_description_when_not_given_and_backtest_not_stored_in_project() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    with (Path.cwd() / "results.json").open("w+", encoding="utf-8") as file:
        file.write("{}")

    result = CliRunner().invoke(lean, ["report", "results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    config_mount = [mount for mount in kwargs["mounts"] if mount["Target"] == "/Lean/Report/bin/Debug/config.json"][0]
    config = json.loads(Path(config_mount["Source"]).read_text(encoding="utf-8"))

    assert config["strategy-name"] == ""
    assert config["strategy-version"] == ""
    assert config["strategy-description"] == ""


def test_report_writes_to_report_html_when_no_report_destination_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    assert (Path.cwd() / "report.html").is_file()


def test_report_writes_to_given_report_destination() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--report-destination", "path/to/report.html"])

    assert result.exit_code == 0

    assert (Path.cwd() / "path" / "to" / "report.html").is_file()


def test_report_aborts_when_report_destination_already_exists() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    output_path = Path.cwd() / "path" / "to" / "report.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w+", encoding="utf-8") as file:
        file.write("<h1>My strategy</h1>")

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--report-destination", "path/to/report.html"])

    assert result.exit_code != 0

    assert output_path.read_text(encoding="utf-8") == "<h1>My strategy</h1>"


def test_report_overwrites_report_destination_when_overwrite_flag_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    output_path = Path.cwd() / "path" / "to" / "report.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w+", encoding="utf-8") as file:
        file.write("<h1>My strategy</h1>")

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--report-destination", "path/to/report.html",
                                       "--overwrite"])

    assert result.exit_code == 0

    assert output_path.read_text(encoding="utf-8") != "<h1>My strategy</h1>"


def test_report_aborts_when_run_image_fails() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()


def test_report_forces_update_when_update_option_given() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean,
                                ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    docker_manager.run_image.assert_called_once()


def test_report_runs_custom_image_when_set_in_config() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="123")


def test_report_runs_custom_image_when_given_as_option() -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["report",
                                       "Python Project/backtests/2020-01-01_00-00-00/results.json",
                                       "--image", "custom/lean:456"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="456")


@pytest.mark.parametrize("image_option,update_flag,update_check_expected", [(None, True, False),
                                                                            (None, False, True),
                                                                            ("custom/lean:3", True, False),
                                                                            ("custom/lean:3", False, False),
                                                                            (DEFAULT_ENGINE_IMAGE, True, False),
                                                                            (DEFAULT_ENGINE_IMAGE, False, True)])
def test_report_checks_for_updates(update_manager_mock: mock.Mock,
                                   image_option: Optional[str],
                                   update_flag: bool,
                                   update_check_expected: bool) -> None:
    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.docker_manager.override(providers.Object(docker_manager))

    options = []
    if image_option is not None:
        options.extend(["--image", image_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["report", "Python Project/backtests/2020-01-01_00-00-00/results.json", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
