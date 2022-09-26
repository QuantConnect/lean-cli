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
from lean.components.config.storage import Storage
from lean.components.util.library_manager import LibraryManager
from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager
from tests.test_helpers import create_fake_lean_cli_directory


def _create_library_manager() -> LibraryManager:
    cache_storage = Storage(str(Path("~/.lean/cache").expanduser()))
    lean_config_manager = LeanConfigManager(mock.Mock(),
                                            mock.Mock(),
                                            mock.Mock(),
                                            mock.Mock(),
                                            cache_storage)
    path_manager = PathManager(PlatformManager())

    return LibraryManager(mock.Mock(), lean_config_manager, path_manager)


@pytest.mark.parametrize("path, expected_result", [
    (Path("Library/Python Library"), True),
    (Path("Library/CSharp Library"), True),
    (Path("Python Project"), False),
    (Path("CSharp Project"), False),
    (Path("Library/Python Library/main.py"), False),
    (Path("NonExistingDirectory"), False)
])
def test_is_lean_library_returns_true_when_path_is_a_library_directory(path: Path, expected_result: bool) -> None:
    create_fake_lean_cli_directory()

    library_manager = _create_library_manager()
    result = library_manager.is_lean_library(Path.cwd() / path)

    assert result == expected_result


@pytest.mark.parametrize("project_depth", range(1, 11))
def test_get_csharp_lean_library_path_for_csproj_file(project_depth: int) -> None:
    create_fake_lean_cli_directory()

    library_dir_relative_to_cli = Path("Library/CSharp Library")
    library_dir = Path.cwd() / library_dir_relative_to_cli
    project_dir = Path.cwd() / Path("/".join([f"Subdir{i}" for i in range(project_depth)])) / "CSharp Project"

    library_manager = _create_library_manager()
    csproj_file_path = library_manager.get_csharp_lean_library_path_for_csproj_file(project_dir, library_dir)

    # 'csproj_file_path' should contain:
    # ('project_depth' + 1) ../ parts (to go from the project dir to the cli root dir),
    # plus 'Library/CSharp Library/CSharp Project.csproj' (2 more parts),
    # plus the csproj file name (1 more part)
    expected_csproj_file_path = \
        Path("/".join(".." for i in range(project_depth + 1))) / library_dir_relative_to_cli / "CSharp Library.csproj"
    assert csproj_file_path == expected_csproj_file_path


def test_get_library_path_for_project_config_file() -> None:
    create_fake_lean_cli_directory()

    library_dir = Path.cwd() / "Library" / "CSharp Library"

    library_manager = _create_library_manager()
    library_reference = library_manager.get_library_path_for_project_config_file(library_dir)

    assert library_reference == library_dir.relative_to(Path.cwd())
