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
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.commands.build import CUSTOM_ENGINE_IMAGE, CUSTOM_FOUNDATION_IMAGE, CUSTOM_RESEARCH_IMAGE
from lean.container import container
from lean.models.docker import DockerImage


def create_fake_repositories() -> None:
    lean_dir = Path.cwd() / "Lean"
    alpha_streams_dir = Path.cwd() / "AlphaStreams"

    for name in ["DockerfileLeanFoundation", "DockerfileLeanFoundationARM", "Dockerfile", "DockerfileJupyter"]:
        path = lean_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w+", encoding="utf-8") as file:
            file.write("""
FROM ubuntu
RUN true
            """.strip())

    alpha_streams_dir.mkdir()


dockerfiles_seen = []


def build_image(root: Path, dockerfile: Path, target_image: DockerImage) -> None:
    dockerfiles_seen.append(dockerfile.read_text(encoding="utf-8").strip())


def test_build_compiles_lean_and_alpha_streams_sdk() -> None:
    create_fake_repositories()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    assert docker_manager.run_image.call_count == 2


@mock.patch("platform.machine")
@pytest.mark.parametrize("architecture,file", [("x86_64", "DockerfileLeanFoundation"),
                                               ("arm64", "DockerfileLeanFoundationARM"),
                                               ("aarch64", "DockerfileLeanFoundationARM")])
def test_build_builds_foundation_image(machine: mock.Mock, architecture: str, file: str) -> None:
    create_fake_repositories()

    machine.return_value = architecture

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / file

    docker_manager.build_image.assert_any_call(Path.cwd(), dockerfile, CUSTOM_FOUNDATION_IMAGE)
    assert dockerfile.read_text(encoding="utf-8").strip() == """
FROM ubuntu
RUN true
    """.strip()


def test_build_builds_engine_image_based_on_custom_foundation_image() -> None:
    create_fake_repositories()

    docker_manager = mock.Mock()
    docker_manager.build_image.side_effect = build_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / "Dockerfile"

    docker_manager.build_image.assert_any_call(Path.cwd(), dockerfile, CUSTOM_ENGINE_IMAGE)
    assert f"""
FROM {CUSTOM_FOUNDATION_IMAGE}
RUN true
    """.strip() in dockerfiles_seen


def test_build_builds_research_image_based_on_custom_engine_image() -> None:
    create_fake_repositories()

    docker_manager = mock.Mock()
    docker_manager.build_image.side_effect = build_image
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / "DockerfileJupyter"

    docker_manager.build_image.assert_any_call(Path.cwd(), dockerfile, CUSTOM_RESEARCH_IMAGE)
    assert f"""
FROM {CUSTOM_ENGINE_IMAGE}
RUN true
    """.strip() in dockerfiles_seen


def test_build_aborts_when_invalid_root_directory_passed() -> None:
    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code != 0
