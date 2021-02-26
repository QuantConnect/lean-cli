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

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.project_manager import ProjectManager
from tests.test_helpers import create_fake_lean_cli_project


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
