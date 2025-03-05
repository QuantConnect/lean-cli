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
from unittest import mock

import json5
import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.components.util.xml_manager import XMLManager
from lean.components import reserved_names, output_reserved_names
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.api import QCLanguage
from lean.models.json_module import JsonModule
from lean.models.utils import DebuggingMethod
from lean.models.docker import DockerImage
from tests.conftest import initialize_container
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


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

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {})


def test_backtest_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once()
    args, _ = container.lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[3].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", "Python Project/custom"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           Path.cwd() / "Python Project" / "custom",
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {})

@pytest.mark.parametrize("output_name", reserved_names + output_reserved_names)
def test_backtest_fails_when_given_is_invalid(output_name: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", f"Python Project/custom/{output_name}"])

    assert result.output == f"Usage: lean backtest [OPTIONS] PROJECT\nTry 'lean backtest --help' for help.\n\nError: Invalid value for '--output': Directory 'Python Project/custom/{output_name}' is not a valid path.\n"

def test_backtest_calls_lean_runner_with_release_mode() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project", "--release"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("CSharp Project/Main.cs").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           True,
                                                           False,
                                                           {},
                                                           {})


def test_backtest_calls_lean_runner_with_detach() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--detach"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           True,
                                                           {},
                                                           {})


def test_backtest_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    container.lean_runner.run_lean.assert_not_called()


def test_backtest_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    container.lean_runner.run_lean.assert_not_called()


def test_backtest_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()
    docker_manager = mock.Mock()
    # refresh so we assert we are called once
    initialize_container(docker_manager)

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {})


def test_backtest_passes_custom_image_to_lean_runner_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           DockerImage(name="custom/lean", tag="123"),
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {})


def test_backtest_passes_custom_image_to_lean_runner_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           DockerImage(name="custom/lean", tag="456"),
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {})


@pytest.mark.parametrize("python_venv", ["Custom-venv",
                                         "/Custom-venv",
                                         None])
def test_backtest_passes_custom_python_venv_to_lean_runner_when_given_as_option(python_venv: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--python-venv", python_venv])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once()
    args, _ = container.lean_runner.run_lean.call_args

    if python_venv:
        assert args[0]["python-venv"] == "/Custom-venv"
    else:
        assert "python-venv" not in args[0]


def _ensure_rider_debugger_config_files_exist(project_dir: Path) -> None:
    # Old debugger configs
    if container.platform_manager.is_host_windows():
        rider_global_dir = Path("~/AppData/Roaming/JetBrains").expanduser()
    elif container.platform_manager.is_host_macos():
        rider_global_dir = Path("~/Library/Application Support/JetBrains").expanduser()
    else:
        rider_global_dir = Path("~/.config/JetBrains").expanduser()
    rider_old_debugger_config_file = rider_global_dir / "Rider" / "options" / "debugger.xml"
    _generate_file(rider_old_debugger_config_file, f"""
    <application>
        <component name="XDebuggerSettings">
            <debuggers>
                <debugger id="dotnet_debugger">
                    <configuration>
                        <option name="sshCredentials">
                            <option value="&lt;credentials HOST=&quot;localhost&quot; PORT=&quot;2222&quot; USERNAME=&quot;root&quot; PRIVATE_KEY_FILE=&quot;C:/Users/jhona/.lean/ssh/key&quot; USE_KEY_PAIR=&quot;true&quot; USE_AUTH_AGENT=&quot;false&quot; /&gt;"/>
                        </option>
                    </configuration>
                </debugger>
            </debuggers>
        </component>
    </application>
                    """)

    # New debugger configs
    rider_config_dir = project_dir / ".idea" / f".idea.{project_dir.name}.dir" / ".idea"
    rider_ssh_configs_file_path = rider_config_dir / "sshConfigs.xml"
    _generate_file(rider_ssh_configs_file_path, f"""
    <project version="4">
        <component name="SshConfigs">
            <configs>
                <sshConfig id="dotnet_debugger" host="localhost" port="2222" username="root" keyPath="{Path('.lean/ssh/key').expanduser()}" useOpenSSHConfig="true"/>
            </configs>
        </component>
    </project>
            """)


@pytest.mark.parametrize("value,debugging_method", [("pycharm", DebuggingMethod.PyCharm),
                                                    ("PyCharm", DebuggingMethod.PyCharm),
                                                    ("ptvsd", DebuggingMethod.PTVSD),
                                                    ("PTVSD", DebuggingMethod.PTVSD),
                                                    ("vsdbg", DebuggingMethod.VSDBG),
                                                    ("VSDBG", DebuggingMethod.VSDBG),
                                                    ("debugpy", DebuggingMethod.DebugPy),
                                                    ("DebugPy", DebuggingMethod.DebugPy),
                                                    ("rider", DebuggingMethod.Rider),
                                                    ("Rider", DebuggingMethod.Rider)])
def test_backtest_passes_correct_debugging_method_to_lean_runner(value: str, debugging_method: DebuggingMethod) -> None:
    create_fake_lean_cli_directory()

    project_dir = Path.cwd() / "Python Project"

    if debugging_method == DebuggingMethod.Rider:
        _ensure_rider_debugger_config_files_exist(project_dir)

    result = CliRunner().invoke(lean, ["backtest", project_dir.name, "--debug", value])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           debugging_method,
                                                           False,
                                                           False,
                                                           {},
                                                           {})


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
            <mapping local-root="$PROJECT_DIR$" remote-root="/Lean/Launcher/bin/Debug" />
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

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--debug", "pycharm"])

    assert result.exit_code == 1

    workspace_xml = XMLManager().parse(workspace_xml_path.read_text(encoding="utf-8"))
    assert workspace_xml.find(".//mapping[@remote-root='/LeanCLI']") is not None
    assert workspace_xml.find(".//mapping[@remote-root='/Lean/Launcher/bin/Debug']") is None


@pytest.mark.parametrize("value", ["ptvsd", "debugpy"])
def test_backtest_auto_updates_outdated_python_vscode_debug_config(value) -> None:
    create_fake_lean_cli_directory()

    lean_config_manager = container.lean_config_manager
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    launch_json_path = Path.cwd() / "Python Project" / ".vscode" / "launch.json"
    _generate_file(launch_json_path, json.dumps({
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
                        "remoteRoot": "/Lean/Launcher/bin/Debug"
                    },
                    {
                        "localRoot": str(lean_cli_root_dir / "Library"),
                        "remoteRoot": "/Library"
                    }
                ]
            }
        ]
    }))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--debug", value])

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
                "remoteRoot": "/LeanCLI"
            },
            {
                "localRoot": str(lean_cli_root_dir / "Library"),
                "remoteRoot": "/Library"
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
            "processId": "${command:pickRemoteProcess}",
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

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project", "--debug", "vsdbg"])

    assert result.exit_code == 0

    launch_json = json.loads(launch_json_path.read_text(encoding="utf-8"))
    assert len(launch_json["configurations"]) == 1
    assert launch_json["configurations"][0] == {
        "name": "Debug with Lean CLI",
        "request": "attach",
        "type": "coreclr",
        "processId": "1",
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

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project", "--debug", "rider"])

    assert result.exit_code == 1

    for dir_name in [".idea.CSharp Project", ".idea.CSharp Project.dir"]:
        workspace_xml_path = Path.cwd() / "CSharp Project" / ".idea" / dir_name / ".idea" / "workspace.xml"
        workspace_xml = XMLManager().parse(workspace_xml_path.read_text(encoding="utf-8"))
        assert workspace_xml.find(".//configuration[@name='Debug with Lean CLI']") is None


def test_backtest_auto_creates_rider_debug_config_if_not_there_yet() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path.cwd() / "CSharp Project"
    (project_dir / "Main.cs").touch()

    rider_config_dir = project_dir / ".idea" / f".idea.{project_dir.name}.dir" / ".idea"
    rider_ssh_configs_file_path = rider_config_dir / "sshConfigs.xml"
    if rider_ssh_configs_file_path.exists():
        rider_ssh_configs_file_path.unlink()

    result = CliRunner().invoke(lean, ["backtest", project_dir.name, "--debug", "rider"])

    # The command should fail because we recommend to restart rider after creating the debug configuration
    assert result.exit_code == 1

    rider_ssh_configs_file_path = rider_config_dir / "sshConfigs.xml"
    assert rider_ssh_configs_file_path.is_file()

    debugger_root = XMLManager().parse(rider_ssh_configs_file_path.read_text(encoding="utf-8"))
    assert debugger_root.find(
        f".//component[@name='SshConfigs']/configs/sshConfig[@id='dotnet_debugger'][@host='localhost'][@port='2222'][@username='root'][@keyPath='{Path('~/.lean/ssh/key').expanduser()}']") is not None


def test_backtest_auto_creates_rider_debug_config_entry_if_not_there_yet() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path.cwd() / "My CSharp Project"
    container.project_manager.create_new_project(project_dir, QCLanguage.CSharp)
    (project_dir / "Main.cs").touch()

    rider_config_dir = project_dir / ".idea" / f".idea.{project_dir.name}.dir" / ".idea"
    rider_ssh_configs_file_path = rider_config_dir / "sshConfigs.xml"
    _generate_file(rider_ssh_configs_file_path, """
<project version="4">
  <component name="SshConfigs">
    <configs>
    </configs>
  </component>
</project>
""")

    result = CliRunner().invoke(lean, ["backtest", project_dir.name, "--debug", "rider"])

    # The command should fail because we recommend to restart rider after creating the debug configuration
    assert result.exit_code == 1

    rider_ssh_configs_file_path = rider_config_dir / "sshConfigs.xml"
    assert rider_ssh_configs_file_path.is_file()

    debugger_root = XMLManager().parse(rider_ssh_configs_file_path.read_text(encoding="utf-8"))
    assert debugger_root.find(
        f".//component[@name='SshConfigs']/configs/sshConfig[@id='dotnet_debugger'][@host='localhost'][@port='2222'][@username='root'][@keyPath='{Path('~/.lean/ssh/key').expanduser()}']") is not None


def test_backtest_auto_updates_outdated_csharp_csproj() -> None:
    create_fake_lean_cli_directory()

    csproj_path = Path.cwd() / "CSharp Project" / "CSharp Project.csproj"
    _generate_file(csproj_path, """
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net9.0</TargetFramework>
        <OutputPath>bin/$(Configuration)</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
    <ItemGroup>
        <PackageReference Include="QuantConnect.Lean" Version="2.5.11940"/>
    </ItemGroup>
</Project>
    """)

    result = CliRunner().invoke(lean, ["backtest", "CSharp Project"])

    assert result.exit_code == 0

    csproj = XMLManager().parse(csproj_path.read_text(encoding="utf-8"))
    assert csproj.find(".//PropertyGroup/DefaultItemExcludes") is not None


def test_backtest_updates_lean_config_when_download_data_flag_given() -> None:
    create_fake_lean_cli_directory()

    _generate_file(Path.cwd() / "lean.json", """
{
    // data-folder documentation
    "data-folder": "data",
    "data-provider": "not api data provider"
}
        """)

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

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--data-provider-historical", "QuantConnect",
                                       "--data-purchase-limit", "1000"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once()
    args, _ = container.lean_runner.run_lean.call_args

    assert args[0]["data-purchase-limit"] == 1000


def test_backtest_ignores_data_purchase_limit_when_not_using_api_data_provider() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--data-purchase-limit", "1000"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once()
    args, _ = container.lean_runner.run_lean.call_args

    assert "data-purchase-limit" not in args[0]


def test_backtest_adds_python_libraries_path_to_lean_config() -> None:
    create_fake_lean_cli_directory()

    lean_config_manager = container.lean_config_manager
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()
    project_path = lean_cli_root_dir / "Python Project"
    library_path = lean_cli_root_dir / "Library/Python Library"

    library_manager = container.library_manager
    library_manager.add_lean_library_to_project(project_path, library_path, False)

    result = CliRunner().invoke(lean, ["backtest", str(project_path)])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once()
    args, _ = container.lean_runner.run_lean.call_args

    lean_config = args[0]
    expected_library_path = (Path("/") / library_path.relative_to(lean_cli_root_dir)).as_posix()

    assert expected_library_path in lean_config.get('python-additional-paths')


def test_backtest_calls_lean_runner_with_extra_docker_config() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["backtest", "Python Project",
                                       "--extra-docker-config",
                                       '{"device_requests": [{"count": -1, "capabilities": [["compute"]]}],'
                                       '"volumes": {"extra/path": {"bind": "/extra/path", "mode": "rw"}}}'])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {
                                                               "device_requests": [
                                                                   {"count": -1, "capabilities": [["compute"]]}
                                                               ],
                                                               "volumes": {
                                                                   "extra/path": {"bind": "/extra/path", "mode": "rw"}
                                                               }
                                                           },
                                                           {})


def test_backtest_calls_lean_runner_with_paths_to_mount() -> None:
    create_fake_lean_cli_directory()

    with mock.patch.object(JsonModule, "get_paths_to_mount", return_value={"some-config": "/path/to/file.json"}):
        result = CliRunner().invoke(lean, ["backtest", "Python Project", "--data-provider-historical", "QuantConnect"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "backtesting",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {"some-config": "/path/to/file.json"})
