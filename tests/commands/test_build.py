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
import platform
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.commands.build import CUSTOM_ENGINE_IMAGE, CUSTOM_FOUNDATION_IMAGE, CUSTOM_RESEARCH_IMAGE
from lean.container import container


def create_lean_repository() -> None:
    lean_dir = Path.cwd() / "Lean"

    for name in ["DockerfileLeanFoundation", "DockerfileLeanFoundationARM", "Dockerfile", "DockerfileJupyter"]:
        path = lean_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w+", encoding="utf-8") as file:
            file.write("""
FROM ubuntu
RUN true
            """.strip())


def test_build_compiles_lean() -> None:
    create_lean_repository()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "Lean"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()


def test_build_does_not_compile_lean_when_no_compile_passed() -> None:
    create_lean_repository()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "Lean", "--no-compile"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_not_called()


@mock.patch("platform.uname")
@pytest.mark.parametrize("machine,file", [("x86_64", "DockerfileLeanFoundation"),
                                          ("arm64", "DockerfileLeanFoundationARM"),
                                          ("aarch64", "DockerfileLeanFoundationARM")])
def test_build_builds_foundation_image(uname: mock.Mock, machine: str, file: str) -> None:
    create_lean_repository()

    uname.return_value = platform.uname_result("system", "node", "release", "version", machine, "processor")

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "Lean"])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / file

    docker_manager.build_image.assert_any_call(dockerfile, CUSTOM_FOUNDATION_IMAGE)
    assert dockerfile.read_text(encoding="utf-8").strip() == """
FROM ubuntu
RUN true
    """.strip()


def test_build_builds_engine_image_based_on_custom_foundation_image() -> None:
    create_lean_repository()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "Lean"])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / "Dockerfile"

    docker_manager.build_image.assert_any_call(dockerfile, CUSTOM_ENGINE_IMAGE)
    assert dockerfile.read_text(encoding="utf-8").strip() == f"""
FROM {CUSTOM_FOUNDATION_IMAGE}
RUN true
    """.strip()


def test_build_builds_research_image_based_on_custom_engine_image() -> None:
    create_lean_repository()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "Lean"])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / "DockerfileJupyter"

    docker_manager.build_image.assert_any_call(dockerfile, CUSTOM_RESEARCH_IMAGE)
    assert dockerfile.read_text(encoding="utf-8").strip() == f"""
FROM {CUSTOM_ENGINE_IMAGE}
RUN true
    """.strip()


def test_build_aborts_when_invalid_lean_directory_passed() -> None:
    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code != 0
