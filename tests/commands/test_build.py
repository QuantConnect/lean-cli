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

from lean.commands import lean
from lean.container import container
from lean.models.docker import DockerImage
from lean.constants import CUSTOM_FOUNDATION, CUSTOM_RESEARCH, CUSTOM_ENGINE
from tests.conftest import initialize_container
from tests.test_helpers import create_fake_lean_cli_directory

CUSTOM_FOUNDATION_IMAGE = DockerImage(name=CUSTOM_FOUNDATION, tag="latest")
CUSTOM_ENGINE_IMAGE = DockerImage(name=CUSTOM_ENGINE, tag="latest")
CUSTOM_RESEARCH_IMAGE = DockerImage(name=CUSTOM_RESEARCH, tag="latest")


@pytest.fixture(autouse=True)
def create_fake_cli_directory() -> None:
    create_fake_lean_cli_directory()


def create_fake_repositories() -> None:
    lean_dir = Path.cwd() / "Lean"

    for name in ["DockerfileLeanFoundation", "DockerfileLeanFoundationARM", "Dockerfile", "DockerfileJupyter"]:
        path = lean_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w+", encoding="utf-8") as file:
            file.write("""
FROM ubuntu
RUN true
            """.strip())


dockerfiles_seen = []


def build_image(root: Path, dockerfile: Path, target_image: DockerImage) -> None:
    dockerfiles_seen.append(dockerfile.read_text(encoding="utf-8").strip())


def test_build_compiles_lean() -> None:
    create_fake_repositories()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    assert docker_manager.run_image.call_count == 1


@mock.patch("platform.machine")
@pytest.mark.parametrize("architecture,file", [("x86_64", "DockerfileLeanFoundation"),
                                               ("arm64", "DockerfileLeanFoundationARM"),
                                               ("aarch64", "DockerfileLeanFoundationARM")])
def test_build_builds_foundation_image(machine: mock.Mock, architecture: str, file: str) -> None:
    create_fake_repositories()

    machine.return_value = architecture

    docker_manager = mock.Mock()
    initialize_container(docker_manager)

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
    container.docker_manager = docker_manager

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
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code == 0

    dockerfile = Path.cwd() / "Lean" / "DockerfileJupyter"

    docker_manager.build_image.assert_any_call(Path.cwd(), dockerfile, CUSTOM_RESEARCH_IMAGE)
    assert f"""
FROM {CUSTOM_ENGINE_IMAGE}
RUN true
    """.strip() in dockerfiles_seen


def test_build_uses_current_directory_as_root_directory_when_root_not_given() -> None:
    create_fake_repositories()

    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["build"])

    assert result.exit_code == 0

    assert docker_manager.build_image.call_count == 3


def test_build_aborts_when_invalid_root_directory_passed() -> None:
    docker_manager = mock.Mock()
    container.docker_manager = docker_manager

    result = CliRunner().invoke(lean, ["build", "."])

    assert result.exit_code != 0


@mock.patch("platform.machine")
@pytest.mark.parametrize("architecture,foundation_file", [("x86_64", "DockerfileLeanFoundation"),
                                                          ("arm64", "DockerfileLeanFoundationARM"),
                                                          ("aarch64", "DockerfileLeanFoundationARM")])
def test_build_uses_custom_tag_when_given(machine: mock.Mock, architecture: str, foundation_file: str) -> None:
    create_fake_repositories()

    machine.return_value = architecture

    docker_manager = mock.Mock()
    initialize_container(docker_manager)
    docker_manager.build_image.side_effect = build_image

    result = CliRunner().invoke(lean, ["build", ".", "--tag", "my-tag"])

    assert result.exit_code == 0

    foundation_dockerfile = Path.cwd() / "Lean" / foundation_file
    engine_dockerfile = Path.cwd() / "Lean" / "Dockerfile"
    research_dockerfile = Path.cwd() / "Lean" / "DockerfileJupyter"

    foundation_image = DockerImage(name="lean-cli/foundation", tag="my-tag")
    engine_image = DockerImage(name="lean-cli/engine", tag="my-tag")
    research_image = DockerImage(name="lean-cli/research", tag="my-tag")

    docker_manager.build_image.assert_any_call(Path.cwd(), foundation_dockerfile, foundation_image)
    docker_manager.build_image.assert_any_call(Path.cwd(), engine_dockerfile, engine_image)
    docker_manager.build_image.assert_any_call(Path.cwd(), research_dockerfile, research_image)

    assert f"""
FROM {foundation_image}
RUN true
    """.strip() in dockerfiles_seen

    assert f"""
FROM {engine_image}
RUN true
    """.strip() in dockerfiles_seen
