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
from unittest import mock

import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.components.util.project_manager import ProjectManager
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


def assert_python_project_exists(path: str) -> None:
    project_dir = (Path.cwd() / path)

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "main.py") as file:
        if path.startswith("Library/"):
            assert "class MyFirstLibrary" in file.read()
        else:
            assert "class MyFirstProject(QCAlgorithm)" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert json.load(file)["metadata"]["kernelspec"]["language"] == "python"

    with open(project_dir / "config.json") as file:
        assert json.load(file)["algorithm-language"] == "Python"


def assert_csharp_project_exists(path: str) -> None:
    project_dir = (Path.cwd() / path)

    assert project_dir.exists()
    assert (project_dir / "Main.cs").exists()
    assert (project_dir / "Research.ipynb").exists()
    assert (project_dir / "config.json").exists()

    with open(project_dir / "Main.cs") as file:
        if path.startswith("Library/"):
            assert "class MyFirstLibrary" in file.read()
        else:
            assert "class MyFirstProject : QCAlgorithm" in file.read()

    with open(project_dir / "Research.ipynb") as file:
        assert json.load(file)["metadata"]["kernelspec"]["language"] == "C#"

    with open(project_dir / "config.json") as file:
        assert json.load(file)["algorithm-language"] == "CSharp"


@pytest.mark.parametrize("path", ["My First Project", "Library/MyFirstLibrary"])
def test_create_project_creates_python_project_when_language_python(path: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", path])

    assert result.exit_code == 0

    assert_python_project_exists(path)


@pytest.mark.parametrize("path", ["My First Project", "Library/My First Library"])
def test_create_project_creates_csharp_project_when_language_csharp(path: str) -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "csharp", path])

    assert result.exit_code == 0

    assert_csharp_project_exists(path)


def test_create_project_creates_python_project_when_default_language_set_to_python() -> None:
    create_fake_lean_cli_directory()

    container.cli_config_manager.default_language.set_value("python")

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists("My First Project")


def test_create_project_aborts_when_default_language_not_set_and_language_not_given() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code != 0


def test_create_project_aborts_when_project_already_exists() -> None:
    create_fake_lean_cli_directory()

    (Path.cwd() / "My First Project").mkdir()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code != 0


def test_create_project_creates_subdirectories() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Category/My First Project"])

    assert result.exit_code == 0

    assert (Path.cwd() / "My First Category" / "My First Project").exists()


def test_create_project_title_cases_class_name() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "my first project"])

    assert result.exit_code == 0

    with open(Path.cwd() / "my first project" / "main.py") as file:
        assert "class MyFirstProject(QCAlgorithm)" in file.read()


def test_create_project_preserves_capitals_in_class_name() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "my FIRST project"])

    assert result.exit_code == 0

    with open(Path.cwd() / "my FIRST project" / "main.py") as file:
        assert "class MyFIRSTProject(QCAlgorithm)" in file.read()


def test_create_project_aborts_when_path_invalid() -> None:
    create_fake_lean_cli_directory()

    path_manager = mock.Mock()
    path_manager.is_cli_path_valid.return_value = False
    container.path_manager= path_manager

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code != 0


def test_create_project_aborts_creating_python_library_project_when_name_not_identifier() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "Library/My First Project"])

    assert result.exit_code != 0


@pytest.mark.parametrize("language", ["python", "csharp"])
def test_create_project_restores_csharp_project(language: str) -> None:
    create_fake_lean_cli_directory()

    project_name = "Some CSharp Project"

    with mock.patch.object(ProjectManager, "try_restore_csharp_project") as mock_try_restore:
        result = CliRunner().invoke(lean, ["create-project", "--language", language, project_name])

    assert result.exit_code == 0

    if language == "csharp":
        expected_csproj_file_path = Path(project_name).expanduser().resolve() / f'{project_name}.csproj'
        mock_try_restore.assert_called_once_with(expected_csproj_file_path, mock.ANY, False)
    else:
        mock_try_restore.assert_not_called()
