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

import pytest

from lean.components.docker.csharp_compiler import CSharpCompiler
from lean.components.util.temp_manager import TempManager
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def run_image(image: DockerImage, **kwargs) -> bool:
    volumes = kwargs.get("volumes")

    assert len(volumes) == 1
    compile_dir = Path(list(volumes)[0])

    csproj_file = Path(kwargs.get("entrypoint")[-1])

    for extension in ["dll", "pdb"]:
        path = compile_dir / "bin" / "Debug" / f"{csproj_file.stem}.{extension}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    return True


def create_csharp_compiler(docker_manager: mock.Mock) -> CSharpCompiler:
    return CSharpCompiler(mock.Mock(), docker_manager, TempManager())


def test_compile_csharp_project_runs_dotnet_build_in_docker() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", ENGINE_IMAGE)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE
    assert "dotnet build" in " ".join(kwargs["entrypoint"])


def test_compile_csharp_project_raises_when_dotnet_build_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False

    compiler = create_csharp_compiler(docker_manager)

    with pytest.raises(Exception):
        compiler.compile_csharp_project(Path.cwd() / "CSharp Project", ENGINE_IMAGE)

    docker_manager.run_image.assert_called_once()


def test_compile_csharp_project_only_mounts_files_from_given_project() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", ENGINE_IMAGE)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    volumes = kwargs["volumes"]
    assert len(volumes) == 1
    compile_dir = Path(list(volumes)[0])

    assert (compile_dir / "Main.cs").exists()
    assert not (compile_dir / "main.py").exists()


@pytest.mark.parametrize("extension", ["dll", "pdb"])
def test_compile_csharp_project_copies_generated_files_to_project_bin(extension: str) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", ENGINE_IMAGE)

    assert (Path.cwd() / "CSharp Project" / "bin" / "Debug" / f"CSharp Project.{extension}").exists()


def test_compile_csharp_project_disables_dotnet_telemetry() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", ENGINE_IMAGE)

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["environment"]["DOTNET_CLI_TELEMETRY_OPTOUT"] == "true"
