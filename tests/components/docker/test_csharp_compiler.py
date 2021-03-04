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

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.docker.csharp_compiler import CSharpCompiler
from tests.test_helpers import create_fake_lean_cli_directory


def run_image(image: str, tag: str, **kwargs) -> bool:
    volumes = kwargs.get("volumes")

    assert len(volumes) == 1
    compile_dir = Path(list(volumes)[0])

    dll_path = compile_dir / "bin" / "Debug" / "LeanCLI.dll"
    dll_path.parent.mkdir(parents=True, exist_ok=True)
    dll_path.touch()

    return True


def create_csharp_compiler(docker_manager: mock.Mock) -> CSharpCompiler:
    return CSharpCompiler(mock.Mock(), LeanConfigManager(mock.Mock(), ProjectConfigManager()), docker_manager)


def test_compile_csharp_project_runs_msbuild_in_docker() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", "latest")

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == "quantconnect/lean"
    assert args[1] == "latest"
    assert kwargs["entrypoint"][0] == "msbuild"


def test_compile_csharp_project_raises_when_msbuild_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False

    compiler = create_csharp_compiler(docker_manager)

    with pytest.raises(Exception):
        compiler.compile_csharp_project(Path.cwd() / "CSharp Project", "latest")

    docker_manager.run_image.assert_called_once()


def test_compile_csharp_project_only_mounts_files_from_given_project() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", "latest")

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    volumes = kwargs["volumes"]
    assert len(volumes) == 1
    compile_dir = Path(list(volumes)[0])

    assert (compile_dir / "CSharp Project" / "Main.cs").exists()
    assert not (compile_dir / "Python Project" / "main.py").exists()


def test_compile_csharp_project_copies_generated_dll_to_cli_bin() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image

    compiler = create_csharp_compiler(docker_manager)

    compiler.compile_csharp_project(Path.cwd() / "CSharp Project", "latest")

    assert (Path.cwd() / "bin" / "Debug" / "LeanCLI.dll").exists()
