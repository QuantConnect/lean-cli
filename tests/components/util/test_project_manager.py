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

import json
from pathlib import Path
from typing import List

import pytest

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.project_manager import ProjectManager
from tests.test_helpers import create_fake_lean_cli_project


def create_library_project(name: str, project_id: int, libraries: List[int]) -> None:
    config_path = Path.cwd() / "Library" / name / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with config_path.open("w+") as file:
        json.dump({
            "project-id": project_id,
            "libraries": libraries
        }, file)


def test_find_algorithm_file_returns_input_when_input_is_file() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager(ProjectConfigManager())
    result = manager.find_algorithm_file(Path.cwd() / "Python Project" / "main.py")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_returns_main_py_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager(ProjectConfigManager())
    result = manager.find_algorithm_file(Path.cwd() / "Python Project")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_returns_main_cs_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager(ProjectConfigManager())
    result = manager.find_algorithm_file(Path.cwd() / "CSharp Project")

    assert result == Path.cwd() / "CSharp Project" / "Main.cs"


def test_find_algorithm_file_raises_error_when_no_algorithm_file_exists() -> None:
    create_fake_lean_cli_project()

    (Path.cwd() / "Empty Project").mkdir()

    manager = ProjectManager(ProjectConfigManager())

    with pytest.raises(Exception):
        manager.find_algorithm_file(Path.cwd() / "Empty Project")


def test_resolve_project_libraries_returns_paths_of_all_linked_libraries_recursively() -> None:
    create_fake_lean_cli_project()

    create_library_project("Library 1", 1, [2])
    create_library_project("Library 2", 2, [3])
    create_library_project("Library 3", 3, [])

    manager = ProjectManager(ProjectConfigManager())
    dependencies = manager.resolve_project_libraries(Path.cwd() / "Library" / "Library 1")

    assert set(dependencies) == {Path.cwd() / "Library" / "Library 1",
                                 Path.cwd() / "Library" / "Library 2",
                                 Path.cwd() / "Library" / "Library 3"}


def test_resolve_project_libraries_returns_paths_of_all_linked_libraries_when_cyclic_dependencies_exist() -> None:
    create_fake_lean_cli_project()

    create_library_project("Library 1", 1, [2])
    create_library_project("Library 2", 2, [3])
    create_library_project("Library 3", 3, [2])

    manager = ProjectManager(ProjectConfigManager())
    dependencies = manager.resolve_project_libraries(Path.cwd() / "Library" / "Library 1")

    assert set(dependencies) == {Path.cwd() / "Library" / "Library 1",
                                 Path.cwd() / "Library" / "Library 2",
                                 Path.cwd() / "Library" / "Library 3"}


def test_resolve_project_libraries_returns_single_path_when_project_has_no_libraries() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager(ProjectConfigManager())
    dependencies = manager.resolve_project_libraries(Path.cwd() / "Python Project")

    assert dependencies == [Path.cwd() / "Python Project"]


def test_resolve_project_libraries_returns_single_path_when_libraries_dont_exist_locally() -> None:
    create_fake_lean_cli_project()

    create_library_project("Library 1", 1, [3])
    create_library_project("Library 2", 2, [])

    manager = ProjectManager(ProjectConfigManager())
    dependencies = manager.resolve_project_libraries(Path.cwd() / "Library" / "Library 1")

    assert dependencies == [Path.cwd() / "Library" / "Library 1"]


def test_resolve_project_libraries_does_not_return_two_of_the_same_when_self_dependency_exists() -> None:
    create_fake_lean_cli_project()

    create_library_project("Library 1", 1, [1])

    manager = ProjectManager(ProjectConfigManager())
    dependencies = manager.resolve_project_libraries(Path.cwd() / "Library" / "Library 1")

    assert dependencies == [Path.cwd() / "Library" / "Library 1"]
