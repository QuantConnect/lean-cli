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

import json5
import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.util.xml_manager import XMLManager
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.api import QCMinimalOrganization
from lean.models.config import DebuggingMethod
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


def _generate_file(file: Path, content: str) -> None:
    """Writes to a file, which is created if it doesn't exist yet, and normalized the content before doing so.

    :param file: the file to write to
    :param content: the content to write to the file
    """
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w+", encoding="utf-8") as file:
        file.write(content.strip() + "\n")


def test_backtest_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None)


def test_backtest_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[3].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[3].relative_to(Path("Python Project/custom").resolve())


def test_backtest_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None)


def test_backtest_passes_custom_image_to_lean_runner_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="123"),
                                                 None)


def test_backtest_passes_custom_image_to_lean_runner_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="456"),
                                                 None)


@pytest.mark.parametrize("value,debugging_method", [("pycharm", DebuggingMethod.PyCharm),
                                                    ("PyCharm", DebuggingMethod.PyCharm),
                                                    ("ptvsd", DebuggingMethod.PTVSD),
                                                    ("PTVSD", DebuggingMethod.PTVSD),
                                                    ("vsdbg", DebuggingMethod.VSDBG),
                                                    ("VSDBG", DebuggingMethod.VSDBG),
                                                    ("rider", DebuggingMethod.Rider),
                                                    ("Rider", DebuggingMethod.Rider)])
def test_backtest_passes_correct_debugging_method_to_lean_runner(value: str, debugging_method: DebuggingMethod) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py", "--debug", value])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 debugging_method)


@pytest.mark.parametrize("image_option,update_flag,update_check_expected", [(None, True, False),
                                                                            (None, False, True),
                                                                            ("custom/lean:3", True, False),
                                                                            ("custom/lean:3", False, False),
                                                                            (DEFAULT_ENGINE_IMAGE, True, False),
                                                                            (DEFAULT_ENGINE_IMAGE, False, True)])
def test_backtest_checks_for_updates(update_manager_mock: mock.Mock,
                                     image_option: Optional[str],
                                     update_flag: bool,
                                     update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []
    if image_option is not None:
        options.extend(["--image", image_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["backtest", "Python Project", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()


def test_backtest_auto_updates_outdated_python_pycharm_debug_config() -> None:
    create_fake_lean_cli_directory()

    workspace_xml_path = Path.cwd() / "Python Project" / ".idea" / "workspace.xml"
    _generate_file(workspace_xml_path, """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RunManager" selected="Python Debug Server.Debug with Lean CLI">
    <configuration name="Debug with Lean CLI" type="PyRemoteDebugConfigurationType" factoryName="Python Remote Debug">
      <module name="LEAN" />
      <option name="PORT" value="6000" />
      <option name="HOST" value="localhost" />
      <PathMappingSettings>
        <option name="pathMappings">
          <list>
            <mapping local-root="$PROJECT_DIR$" remote-root="/LeanCLI" />
          </list>
        </option>
      </PathMappingSettings>
      <option name="REDIRECT_OUTPUT" value="true" />
      <option name="SUSPEND_AFTER_CONNECT" value="true" />
      <method v="2" />
    </configuration>
    <list>
      <item itemvalue="Python Debug Server.Debug with Lean CLI" />
    </list>
  </component>
</project>
        """)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--debug", "pycharm"])

    assert result.exit_code == 1

    workspace_xml = XMLManager().parse(workspace_xml_path.read_text(encoding="utf-8"))
    assert workspace_xml.find(".//mapping[@remote-root='/LeanCLI']") is None
    assert workspace_xml.find(".//mapping[@remote-root='/Lean/Launcher/bin/Debug']") is not None


def test_backtest_auto_updates_outdated_python_vscode_debug_config() -> None:
    create_fake_lean_cli_directory()

    launch_json_path = Path.cwd() / "Python Project" / ".vscode" / "launch.json"
    _generate_file(launch_json_path, """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug with Lean CLI",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/LeanCLI"
                }
            ]
        }
    ]
}
        """)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--debug", "ptvsd"])

    assert result.exit_code == 0

    launch_json = json.loads(launch_json_path.read_text(encoding="utf-8"))
    assert len(launch_json["configurations"]) == 1
    assert launch_json["configurations"][0] == {
        "name": "Debug with Lean CLI",
        "type": "python",
        "request": "attach",
        "connect": {
            "host": "localhost",
            "port": 5678
        },
        "pathMappings": [
            {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "/Lean/Launcher/bin/Debug"
            }
        ]
    }


@pytest.mark.parametrize("config", [
    """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug with Lean CLI",
            "request": "attach",
            "type": "mono",
            "address": "localhost",
            "port": 55556
        }
    ]
}
    """,
    """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug with Lean CLI",
            "request": "attach",
            "type": "coreclr",
            "processId": "1",
            "pipeTransport": {
                "pipeCwd": "${workspaceRoot}",
                "pipeProgram": "docker",
                "pipeArgs": ["exec", "-i", "lean_cli_vsdbg"],
                "debuggerPath": "/root/vsdbg/vsdbg",
                "quoteArgs": false
            },
            "logging": {
                "moduleLoad": false
            }
        }
    ]
}
    """
])
def test_backtest_auto_updates_outdated_csharp_vscode_debug_config(config: str) -> None:
    create_fake_lean_cli_directory()

    launch_json_path = Path.cwd() / "CSharp Project" / ".vscode" / "launch.json"
    _generate_file(launch_json_path, config)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project", "--debug", "vsdbg"])

    assert result.exit_code == 0

    launch_json = json.loads(launch_json_path.read_text(encoding="utf-8"))
    assert len(launch_json["configurations"]) == 1
    assert launch_json["configurations"][0] == {
        "name": "Debug with Lean CLI",
        "request": "attach",
        "type": "coreclr",
        "processId": "${command:pickRemoteProcess}",
        "pipeTransport": {
            "pipeCwd": "${workspaceRoot}",
            "pipeProgram": "docker",
            "pipeArgs": ["exec", "-i", "lean_cli_vsdbg"],
            "debuggerPath": "/root/vsdbg/vsdbg",
            "quoteArgs": False
        },
        "logging": {
            "moduleLoad": False
        }
    }


def test_backtest_auto_updates_outdated_csharp_rider_debug_config() -> None:
    create_fake_lean_cli_directory()

    for dir_name in [".idea.CSharp Project", ".idea.CSharp Project.dir"]:
        _generate_file(Path.cwd() / "CSharp Project" / ".idea" / dir_name / ".idea" / "workspace.xml", """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RunManager">
    <configuration name="Debug with Lean CLI" type="ConnectRemote" factoryName="Mono Remote" show_console_on_std_err="false" show_console_on_std_out="false" port="55556" address="localhost">
      <option name="allowRunningInParallel" value="false" />
      <option name="listenPortForConnections" value="false" />
      <option name="selectedOptions">
        <list />
      </option>
      <method v="2" />
    </configuration>
  </component>
</project>
        """)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project", "--debug", "rider"])

    assert result.exit_code == 1

    for dir_name in [".idea.CSharp Project", ".idea.CSharp Project.dir"]:
        workspace_xml_path = Path.cwd() / "CSharp Project" / ".idea" / dir_name / ".idea" / "workspace.xml"
        workspace_xml = XMLManager().parse(workspace_xml_path.read_text(encoding="utf-8"))
        assert workspace_xml.find(".//configuration[@name='Debug with Lean CLI']") is None


def test_backtest_updates_lean_config_when_download_data_flag_given() -> None:
    create_fake_lean_cli_directory()

    _generate_file(Path.cwd() / "lean.json", """
{
    // data-folder documentation
    "data-folder": "data",
    "data-provider": "not api data provider"
}
        """)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    api_client = mock.Mock()
    api_client.organizations.get_all.return_value = [
        QCMinimalOrganization(id="abc", name="abc", type="type", ownerName="You", members=1, preferred=True)
    ]
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--download-data"])

    assert result.exit_code == 0

    config = json5.loads((Path.cwd() / "lean.json").read_text(encoding="utf-8"))
    assert config["data-provider"] == "QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider"
    assert config["map-file-provider"] == "QuantConnect.Data.Auxiliary.LocalZipMapFileProvider"
    assert config["factor-file-provider"] == "QuantConnect.Data.Auxiliary.LocalZipFactorFileProvider"


def test_backtest_passes_data_purchase_limit_to_lean_runner() -> None:
    create_fake_lean_cli_directory()

    _generate_file(Path.cwd() / "lean.json", """
{
    // data-folder documentation
    "data-folder": "data",
    "data-provider": "QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider"
}
        """)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--data-purchase-limit", "1000"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    assert args[0]["data-purchase-limit"] == 1000


def test_backtest_ignores_data_purchase_limit_when_not_using_api_data_provider() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--data-purchase-limit", "1000"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    assert "data-purchase-limit" not in args[0]
