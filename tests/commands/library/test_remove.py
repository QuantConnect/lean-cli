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

from pathlib import Path, PurePosixPath

import pytest
from click.testing import CliRunner
from lxml import etree

from lean.commands import lean
from lean.container import container
from lean.models.api import QCLanguage
from lean.models.utils import LeanLibraryReference
from tests.test_helpers import create_fake_lean_cli_directory, create_fake_lean_cli_directory_with_subdirectories


def _assert_project_config_file_has_library_reference(project_dir: Path, library_dir: Path) -> None:
    project_config = container.project_config_manager().get_project_config(project_dir)
    project_libraries = project_config.get("libraries")

    assert len([library for library in project_libraries if LeanLibraryReference(**library).path == library_dir]) == 1


def _add_library_to_project_config(project_dir: Path, library_dir: Path) -> None:
    library_manager = container.library_manager()

    assert not library_manager.add_lean_library_reference_to_project(project_dir, library_dir)
    _assert_project_config_file_has_library_reference(project_dir, library_dir)


def _assert_library_reference_was_removed_from_project_config_file(project_dir: Path, library_dir: Path) -> None:
    project_config = container.project_config_manager().get_project_config(project_dir)
    project_libraries = project_config.get("libraries")

    assert len([library for library in project_libraries if LeanLibraryReference(**library).path == library_dir]) == 0


def _assert_csharp_project_csproj_file_has_library_reference(project_dir: Path, library_dir: Path) -> None:
    project_csproj_file = container.project_manager().get_csproj_file_path(project_dir)

    xml_manager = container.xml_manager()
    csproj_tree = xml_manager.parse(project_csproj_file.read_text(encoding="utf-8"))

    library_config = container.project_config_manager().get_project_config(library_dir)
    library_language = library_config.get("algorithm-language")

    if library_language == "Python":
        assert not any(str(library_dir) in project_reference.get("Include")
                       for project_reference in csproj_tree.findall('.//ProjectReference'))
    else:
        library_reference = container.library_manager().get_csharp_lean_library_path_for_csproj_file(project_dir,
                                                                                                     library_dir)

        assert any(project_reference.get("Include") == library_reference
                   for project_reference in csproj_tree.findall('.//ProjectReference'))


def _add_library_to_csharp_project_csproj_file(project_dir: Path, library_dir: Path) -> None:
    library_manager = container.library_manager()
    library_reference = library_manager.get_csharp_lean_library_path_for_csproj_file(project_dir, library_dir)

    project_manager = container.project_manager()
    project_csproj_file = project_manager.get_csproj_file_path(project_dir)

    xml_manager = container.xml_manager()
    csproj_tree = xml_manager.parse(project_csproj_file.read_text(encoding="utf-8"))

    last_item_group = csproj_tree.find(".//ItemGroup[last()]")
    if last_item_group is None:
        last_item_group = etree.SubElement(csproj_tree.find(".//Project"), "ItemGroup")
    last_item_group.append(etree.fromstring(f'<ProjectReference Include="{library_reference}" />'))

    project_csproj_file.write_text(xml_manager.to_string(csproj_tree), encoding="utf-8")

    _assert_csharp_project_csproj_file_has_library_reference(project_dir, library_dir)


def _assert_library_reference_was_removed_from_csharp_project_csproj_file(project_dir: Path, library_dir: Path) -> None:
    project_csproj_file = container.project_manager().get_csproj_file_path(project_dir)

    xml_manager = container.xml_manager()
    csproj_tree = xml_manager.parse(project_csproj_file.read_text(encoding="utf-8"))

    library_config = container.project_config_manager().get_project_config(library_dir)
    library_language = library_config.get("algorithm-language")

    if library_language == "Python":
        assert not any(str(library_dir) in project_reference.get("Include")
                       for project_reference in csproj_tree.findall('.//ProjectReference'))
    else:
        library_reference = container.library_manager().get_csharp_lean_library_path_for_csproj_file(project_dir,
                                                                                                     library_dir)
        assert not any(project_reference.get("Include") == library_reference
                       for project_reference in csproj_tree.findall('.//ProjectReference'))


def test_remove_library_reference_from_python_project() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path("Python Project")
    library_dir = Path("Library/Python Library")
    _add_library_to_project_config(project_dir, library_dir)

    result = CliRunner().invoke(lean, ["library", "remove", str(project_dir), str(library_dir)])

    assert result.exit_code == 0

    _assert_library_reference_was_removed_from_project_config_file(project_dir, library_dir)


@pytest.mark.parametrize("project_depth, library_language", [
    *[(i, QCLanguage.CSharp) for i in range(5)],
    *[(i, QCLanguage.Python) for i in range(5)],
])
def test_remove_library_reference_from_csharp_project(project_depth: int, library_language: QCLanguage) -> None:
    create_fake_lean_cli_directory_with_subdirectories(project_depth)

    project_dir = Path("/".join(f"Subdir{i}" for i in range(project_depth))) / "CSharp Project"
    library_dir = Path("Library/CSharp Library" if library_language == QCLanguage.CSharp else "Library/Python Library")
    _add_library_to_project_config(project_dir, library_dir)
    _add_library_to_csharp_project_csproj_file(project_dir, library_dir)

    result = CliRunner().invoke(lean, ["library", "remove", str(project_dir), str(library_dir), "--no-local"])

    assert result.exit_code == 0

    _assert_library_reference_was_removed_from_project_config_file(project_dir, library_dir)
    _assert_library_reference_was_removed_from_csharp_project_csproj_file(project_dir, library_dir)


@pytest.mark.parametrize("project_dir", [
    "Non Existing Directory",
    "CSharp Project/Main.cs",
    "."
])
def test_library_remove_fails_when_project_directory_is_not_valid(project_dir: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["library", "remove", project_dir, "Library/CSharp Library", "--no-local"])

    assert result.exit_code != 0
