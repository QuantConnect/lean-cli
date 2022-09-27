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

import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.container import container
from lean.models.utils import LeanLibraryReference
from tests.test_helpers import create_fake_lean_cli_directory, create_fake_lean_cli_directory_with_subdirectories


def _assert_library_reference_was_added_to_project_config_file(project_dir: Path, library_dir: Path) -> None:
    project_config = container.project_config_manager().get_project_config(project_dir)
    project_libraries = project_config.get("libraries")

    assert len(project_libraries) == 1

    library_reference = LeanLibraryReference(**project_libraries[0])

    assert library_reference.name == library_dir.name
    assert library_reference.path == library_dir


def _assert_library_reference_was_added_to_csharp_project_csproj_file(project_dir: Path, library_dir: Path) -> None:
    project_csproj_file = container.project_manager().get_csproj_file_path(project_dir)
    library_reference = container.library_manager().get_csharp_lean_library_path_for_csproj_file(project_dir,
                                                                                                 library_dir)

    xml_manager = container.xml_manager()
    csproj_tree = xml_manager.parse(project_csproj_file.read_text(encoding="utf-8"))

    assert any(Path(project_reference.get("Include")) == library_reference
               for project_reference in csproj_tree.findall('.//ProjectReference'))


def test_adds_library_reference_to_python_project_config_file() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path("Python Project")
    library_dir = Path("Library/Python Library")

    result = CliRunner().invoke(lean, ["library", "add", str(project_dir), str(library_dir)])

    assert result.exit_code == 0

    _assert_library_reference_was_added_to_project_config_file(project_dir, library_dir)


@pytest.mark.parametrize("project_depth", range(5))
def test_adds_library_reference_to_csharp_project_config_file(project_depth: int) -> None:
    create_fake_lean_cli_directory_with_subdirectories(project_depth)

    project_dir = Path("/".join(f"Subdir{i}" for i in range(project_depth))) / "CSharp Project"
    library_dir = Path("Library/CSharp Library")

    result = CliRunner().invoke(lean, ["library", "add", str(project_dir), str(library_dir), "--no-local"])

    assert result.exit_code == 0

    _assert_library_reference_was_added_to_project_config_file(project_dir, library_dir)
    _assert_library_reference_was_added_to_csharp_project_csproj_file(project_dir, library_dir)


@pytest.mark.parametrize("project_dir", [
    "Non Existing Directory",
    "CSharp Project/Main.cs",
    "."
])
def test_library_add_fails_when_project_directory_is_not_valid(project_dir: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["library", "add", project_dir, "Library/CSharp Library", "--no-local"])

    assert result.exit_code != 0


@pytest.mark.parametrize("library_dir", [
    "CSharp Project",
    "Non Existing Directory",
    "CSharp Project/Main.cs"
])
def test_library_add_fails_when_library_directory_is_not_valid(library_dir: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["library", "add", "CSharp Project", library_dir, "--no-local"])

    assert result.exit_code != 0

