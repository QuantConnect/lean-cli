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

from click.testing import CliRunner

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_directory


def assert_python_project_exists() -> None:
    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "main.py") as file:
        assert "class MyFirstProject(QCAlgorithm)" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert json.load(file)["metadata"]["kernelspec"]["language"] == "python"

    with open(project_dir / "config.json") as file:
        assert json.load(file)["algorithm-language"] == "Python"


def assert_csharp_project_exists() -> None:
    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "Main.cs").exists()
    assert (project_dir / "research.ipynb").exists()
    assert (project_dir / "config.json").exists()

    with open(project_dir / "Main.cs") as file:
        assert "class MyFirstProject : QCAlgorithm" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert json.load(file)["metadata"]["kernelspec"]["language"] == "csharp"

    with open(project_dir / "config.json") as file:
        assert json.load(file)["algorithm-language"] == "CSharp"


def test_create_project_creates_python_project_when_language_python() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


def test_create_project_creates_csharp_project_when_language_csharp() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["create-project", "--language", "csharp", "My First Project"])

    assert result.exit_code == 0

    assert_csharp_project_exists()


def test_create_project_creates_python_project_when_default_language_set_to_python() -> None:
    create_fake_lean_cli_directory()

    container.cli_config_manager().default_language.set_value("python")

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


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
