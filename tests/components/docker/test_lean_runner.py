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

import docker.types
import pytest

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.output_config_manager import OutputConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage
from lean.components.docker.lean_runner import LeanRunner
from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.project_manager import ProjectManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import DEFAULT_ENGINE_IMAGE, LEAN_ROOT_PATH, DEFAULT_DATA_DIRECTORY_NAME
from lean.models.utils import DebuggingMethod
from lean.models.docker import DockerImage
from lean.models.modules import NuGetPackage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def _generate_file(file: Path, content: str) -> None:
    """Writes to a file, which is created if it doesn't exist yet, and normalizes the content before doing so.

    :param file: the file to write to
    :param content: the content to write to the file
    """
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w+", encoding="utf-8") as file:
        file.write(content.strip() + "\n")


def create_lean_runner(docker_manager: mock.Mock) -> LeanRunner:
    logger = mock.Mock()
    logger.debug_logging_enabled = False

    cli_config_manager = mock.Mock()
    cli_config_manager.user_id.get_value.return_value = "123"
    cli_config_manager.api_token.get_value.return_value = "456"

    project_config_manager = ProjectConfigManager(XMLManager())

    cache_storage = Storage(str(Path("~/.lean/cache").expanduser()))
    lean_config_manager = LeanConfigManager(logger,
                                            cli_config_manager,
                                            project_config_manager,
                                            mock.Mock(),
                                            cache_storage)
    output_config_manager = OutputConfigManager(lean_config_manager)

    module_manager = mock.Mock()
    module_manager.get_installed_packages.return_value = [NuGetPackage(name="QuantConnect.Brokerages", version="1.0.0")]

    xml_manager = XMLManager()
    platform_manager = PlatformManager()
    path_manager = PathManager(lean_config_manager, platform_manager)
    project_manager = ProjectManager(logger,
                                     project_config_manager,
                                     lean_config_manager,
                                     path_manager,
                                     xml_manager,
                                     platform_manager,
                                     cli_config_manager,
                                     docker_manager)

    return LeanRunner(logger,
                      project_config_manager,
                      lean_config_manager,
                      output_config_manager,
                      docker_manager,
                      module_manager,
                      project_manager,
                      TempManager(),
                      xml_manager)


@pytest.mark.parametrize("release", [False, True])
def test_run_lean_compiles_csharp_project_in_correct_configuration(release: bool) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         release,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    build_command = next((cmd for cmd in kwargs["commands"] if cmd.startswith("dotnet build")), None)
    assert build_command is not None

    assert f"Configuration={'Release' if release else 'Debug'}" in build_command


def test_run_lean_runs_lean_container_detached() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         True)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs.get("detach", False)


def test_run_lean_runs_lean_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE
    assert any(cmd for cmd in kwargs["commands"] if cmd.endswith("dotnet QuantConnect.Lean.Launcher.dll"))


def test_run_lean_mounts_config_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == f"{LEAN_ROOT_PATH}/config.json" for mount in kwargs["mounts"]])


def test_run_lean_mounts_data_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Lean/Data" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Lean/Data")
    assert key == str(Path.cwd() / "data")


def test_run_lean_mounts_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Results" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Results")
    assert key == str(Path.cwd() / "output")


def test_run_lean_mounts_storage_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Storage" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Storage")
    assert key == str(Path.cwd() / "storage")


def test_run_lean_creates_output_directory_when_not_existing_yet() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    assert (Path.cwd() / "output").is_dir()


def test_lean_runner_copies_code_to_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    source_content = (Path.cwd() / "Python Project" / "main.py").read_text(encoding="utf-8")
    copied_content = (Path.cwd() / "output" / "code" / "main.py").read_text(encoding="utf-8")
    assert source_content == copied_content


def test_run_lean_compiles_python_project() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    build_command = next((cmd for cmd in kwargs["commands"] if cmd.startswith("""if [ -d '/LeanCLI' ];
            then
                python -m compileall""")), None)
    assert build_command is not None

def test_run_lean_mounts_project_directory_when_running_python_algorithm() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "Python Project") in kwargs["volumes"]


def test_run_lean_exposes_5678_when_debugging_with_ptvsd() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.PTVSD,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"]["5678"] == "5678"


def test_run_lean_sets_image_name_when_debugging_with_vsdbg() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.VSDBG,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["name"] == "lean_cli_vsdbg"


def test_run_lean_exposes_ssh_when_debugging_with_rider() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({},
                         "backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.Rider,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"]["22"] == "2222"


def test_run_lean_raises_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False

    lean_runner = create_lean_runner(docker_manager)

    with pytest.raises(Exception):
        lean_runner.run_lean({},
                             "backtesting",
                             Path.cwd() / "Python Project" / "main.py",
                             Path.cwd() / "output",
                             ENGINE_IMAGE,
                             DebuggingMethod.PTVSD,
                             False,
                             False)

    docker_manager.run_image.assert_called_once()


@pytest.mark.parametrize("os,root", [
    ("Windows", ""),
    ("Linux", ""),
    ("Darwin", ""),
    ("Windows", "some/directory"),
    ("Linux", "some/directory"),
    ("Darwin", "some/directory"),
    ("Windows", r"C:\Users\user\some_directory"),
    ("Linux", "/home/user/some_directory"),
    ("Darwin", "/Users/user/some_directory")
])
def test_run_lean_mounts_terminal_link_symbol_map_file_from_data_folder(os: str, root: str) -> None:
    from platform import system
    if os != system():
        pytest.skip(f"This test requires {os}")

    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    local_path = Path(root) / "terminal-link-symbol-map.json"

    lean_runner = create_lean_runner(docker_manager)
    lean_runner.run_lean({"terminal-link-symbol-map-file": str(local_path)},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    from lean.container import container
    cli_root_dir = container.lean_config_manager.get_cli_root_directory()
    expected_source = local_path \
        if local_path.is_absolute() \
        else cli_root_dir / DEFAULT_DATA_DIRECTORY_NAME / "symbol-properties" / local_path

    assert any([
        Path(mount["Source"]) == expected_source and
        mount["Target"] == f'/Files/terminal-link-symbol-map-file'
        for mount in kwargs["mounts"]
    ])


def test_run_lean_mounts_transaction_log_file_from_cli_root() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({"transaction-log": "transaction-log.log"},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    from lean.container import container
    cli_root_dir = container.lean_config_manager.get_cli_root_directory()

    assert any([
        Path(mount["Source"]) == Path(f'{cli_root_dir}/transaction-log.log') and
        mount["Target"] == f'/Files/transaction-log'
        for mount in kwargs["mounts"]
    ])


@pytest.mark.parametrize("in_solution", [True, False])
def test_run_lean_compiles_csharp_project_that_is_part_of_a_solution(in_solution: bool) -> None:
    create_fake_lean_cli_directory()

    if in_solution:
        _generate_file(Path.cwd() / "Solution.sln", """
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 16
VisualStudioVersion = 16.0.31605.126
MinimumVisualStudioVersion = 10.0.40219.1
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "CSharp Project", "CSharp Project\CSharp Project.csproj", "{E0B7E0A0-0F0B-4F1A-9F0B-0F0B0F0B0F0B}"
EndProject
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
        Debug|Any CPU = Debug|Any CPU
        Release|Any CPU = Release|Any CPU
    EndGlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution
        {E0B7E0A0-0F0B-4F1A-9F0B-0F0B0F0B0F0B}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {E0B7E0A0-0F0B-4F1A-9F0B-0F0B0F0B0F0B}.Debug|Any CPU.Build.0 = Debug|Any CPU
        {E0B7E0A0-0F0B-4F1A-9F0B-0F0B0F0B0F0B}.Release|Any CPU.ActiveCfg = Release|Any CPU
        {E0B7E0A0-0F0B-4F1A-9F0B-0F0B0F0B0F0B}.Release|Any CPU.Build.0 = Release|Any CPU
    EndGlobalSection
    GlobalSection(SolutionProperties) = preSolution
        HideSolutionNode = FALSE
    EndGlobalSection
EndGlobal
        """)

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    root_dir = Path.cwd()
    lean_runner = create_lean_runner(docker_manager)
    lean_runner.run_lean({},
                         "backtesting",
                         root_dir / "CSharp Project" / "Main.cs",
                         root_dir / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    build_command = next((cmd for cmd in kwargs["commands"] if cmd.startswith("dotnet build")), None)
    assert build_command is not None

    project_dir_str = str(root_dir / "CSharp Project")
    # The volume should be mounted at the solution directory, not the project directory
    if in_solution:
        assert str(root_dir) in kwargs["volumes"]
        assert kwargs["volumes"][str(root_dir)]["bind"] == "/LeanCLI"
        assert project_dir_str not in kwargs["volumes"]
    else:
        assert project_dir_str in kwargs["volumes"]
        assert kwargs["volumes"][project_dir_str]["bind"] == "/LeanCLI"
        assert str(root_dir) not in kwargs["volumes"]


def test_lean_runner_parses_device_requests_from_extra_docker_configs() -> None:
    create_fake_lean_cli_directory()

    run_options = {}
    LeanRunner.parse_extra_docker_config(run_options,
                                         {"device_requests": [{"count": -1, "capabilities": [["compute"]]}]})

    assert "device_requests" in run_options

    device_requests = run_options["device_requests"]
    assert len(device_requests) == 1

    device_request: docker.types.DeviceRequest = device_requests[0]
    assert isinstance(device_request, docker.types.DeviceRequest)
    assert device_request.count == -1
    assert (len(device_request.capabilities) == 1 and
            len(device_request.capabilities[0]) == 1 and
            device_request.capabilities[0][0] == "compute")
    assert device_request.driver == ""
    assert device_request.device_ids == []
    assert device_request.options == {}


def test_lean_runner_parses_volumes_from_extra_docker_configs() -> None:
    create_fake_lean_cli_directory()

    run_options = {
        "volumes": {
            "source/path": {
                "bind": "/target/path",
                "mode": "rw"
            }
        }
    }
    LeanRunner.parse_extra_docker_config(run_options,
                                         {"volumes": {"extra/path": {"bind": "/extra/bound/path", "mode": "rw"}}})

    assert "volumes" in run_options

    volumes = run_options["volumes"]
    assert len(volumes) == 2
    assert "source/path" in volumes
    assert "extra/path" in volumes

    existing_volume = volumes["source/path"]
    assert existing_volume["bind"] == "/target/path"
    assert existing_volume["mode"] == "rw"

    new_volume = volumes["extra/path"]
    assert new_volume["bind"] == "/extra/bound/path"
    assert new_volume["mode"] == "rw"


def test_run_lean_passes_device_requests() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({"transaction-log": "transaction-log.log"},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False,
                         extra_docker_config={"device_requests": [{"count": -1, "capabilities": [["compute"]]}]})

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "device_requests" in kwargs
    assert kwargs["device_requests"] == [docker.types.DeviceRequest(count=-1, capabilities=[["compute"]])]


def test_run_lean_passes_extra_volumes() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean({"transaction-log": "transaction-log.log"},
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False,
                         extra_docker_config={"volumes": {"extra/path": {"bind": "/extra/bound/path", "mode": "rw"}}})

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "volumes" in kwargs
    volumes = kwargs["volumes"]
    assert "extra/path" in volumes
    assert volumes["extra/path"]["bind"] == "/extra/bound/path"
    assert volumes["extra/path"]["mode"] == "rw"


def test_run_lean_mounts_additional_paths() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_config = {
        "transaction-log": "transaction-log.log",
        "environment": "backtesting",
        "environments": {
            "backtesting": {}
        }
    }
    paths_to_mount = {
        "file-to-mount-key": "../some/path/to/mount/file.json",
        "directory-to-mount-key": "../some/path/to/mount"
    }

    lean_runner.run_lean(lean_config,
                         "backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None,
                         False,
                         False,
                         {},
                         paths_to_mount)

    docker_manager.run_image.assert_called_once()
    _, kwargs = docker_manager.run_image.call_args

    assert "mounts" in kwargs
    mounts = kwargs["mounts"]

    def source_to_target(path):
        return f"/Files/{str(Path(path).name)}"

    def path_is_in_mounts(path):
        return any([mount["Source"] == str(Path(path).resolve()) for mount in mounts])

    def path_is_mounted_in_files(path):
        return any([mount["Target"] == source_to_target(path) for mount in mounts])

    assert all([path_is_in_mounts(path) and path_is_mounted_in_files(path) for path in paths_to_mount.values()])

    # The target paths should have been added to the lean config
    lean_config_path = next((mount["Source"] for mount in mounts if mount["Target"].endswith("config.json")), None)
    assert lean_config_path is not None

    # Read temporal lean config
    with open(lean_config_path, "r") as f:
        import json
        lean_config = json.load(f)

    backtesting_env = lean_config["environments"]["backtesting"]

    assert all([key in backtesting_env and backtesting_env[key] == source_to_target(value)
                for key, value in paths_to_mount.items()])
