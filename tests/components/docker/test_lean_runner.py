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

import tempfile
from pathlib import Path
from unittest import mock

import pytest

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.docker.lean_runner import LeanRunner
from lean.components.util.temp_manager import TempManager
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.models.config import DebuggingMethod
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def create_csharp_compiler() -> mock.Mock:
    compile_dir = Path(tempfile.mkdtemp())
    (compile_dir / "bin" / "Debug").mkdir(parents=True)
    (compile_dir / "bin" / "Debug" / "LeanCLI.dll").touch()

    csharp_compiler = mock.Mock()
    csharp_compiler.compile_csharp_project.return_value = (compile_dir / "bin" / "Debug" / "LeanCLI.dll")

    return csharp_compiler


def create_lean_runner(docker_manager: mock.Mock, csharp_compiler: mock.Mock = create_csharp_compiler()) -> LeanRunner:
    cli_config_manager = mock.Mock()
    cli_config_manager.user_id.get_value.return_value = "123"
    cli_config_manager.api_token.get_value.return_value = "456"

    return LeanRunner(mock.Mock(),
                      csharp_compiler,
                      LeanConfigManager(cli_config_manager, ProjectConfigManager()),
                      docker_manager,
                      TempManager())


def test_run_lean_compiles_csharp_project() -> None:
    create_fake_lean_cli_directory()

    csharp_compiler = create_csharp_compiler()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager, csharp_compiler)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    csharp_compiler.compile_csharp_project.assert_called_once()


def test_run_lean_fails_when_csharp_compilation_fails() -> None:
    create_fake_lean_cli_directory()

    def compile_csharp_project(*args) -> None:
        raise RuntimeError("Oops")

    csharp_compiler = mock.Mock()
    csharp_compiler.compile_csharp_project.side_effect = compile_csharp_project

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager, csharp_compiler)

    with pytest.raises(Exception):
        lean_runner.run_lean("backtesting",
                             Path.cwd() / "CSharp Project" / "Main.cs",
                             Path.cwd() / "output",
                             ENGINE_IMAGE,
                             None)


def test_run_lean_runs_lean_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE


def test_run_lean_mounts_config_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Launcher/bin/Debug/config.json" for mount in kwargs["mounts"]])


def test_run_lean_mounts_data_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

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

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

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

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         "latest",
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Storage" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Storage")
    assert key == str(Path.cwd() / "Python Project" / "storage")


def test_run_lean_creates_output_directory_when_not_existing_yet() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    assert (Path.cwd() / "output").is_dir()


def test_run_lean_mounts_project_directory_when_running_python_algorithm() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert str(Path.cwd() / "Python Project") in kwargs["volumes"]


def test_run_lean_mounts_dll_and_pdb_when_running_csharp_algorithm() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any(["CSharp Project.dll" in mount["Target"] for mount in kwargs["mounts"]])
    assert any(["CSharp Project.pdb" in mount["Target"] for mount in kwargs["mounts"]])


@mock.patch("platform.system")
def test_run_lean_adds_internal_host_when_running_linux(system) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    system.return_value = "Linux"

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "extra_hosts" in kwargs


@mock.patch("platform.system")
def test_run_lean_does_not_add_internal_host_when_not_running_linux(system) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    system.return_value = "Windows"

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         None)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert "extra_hosts" not in kwargs


def test_run_lean_exposes_5678_when_debugging_with_ptvsd() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "Python Project" / "main.py",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.PTVSD)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"]["5678"] == "5678"


def test_run_lean_sets_image_name_when_debugging_with_vsdbg() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.VSDBG)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["name"] == "lean_cli_vsdbg"


def test_run_lean_exposes_ssh_when_debugging_with_rider() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = True

    lean_runner = create_lean_runner(docker_manager)

    lean_runner.run_lean("backtesting",
                         Path.cwd() / "CSharp Project" / "Main.cs",
                         Path.cwd() / "output",
                         ENGINE_IMAGE,
                         DebuggingMethod.Rider)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["ports"]["22"] == "2222"


def test_run_lean_raises_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False

    lean_runner = create_lean_runner(docker_manager)

    with pytest.raises(Exception):
        lean_runner.run_lean("backtesting",
                             Path.cwd() / "Python Project" / "main.py",
                             Path.cwd() / "output",
                             ENGINE_IMAGE,
                             DebuggingMethod.PTVSD)

    docker_manager.run_image.assert_called_once()
