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
from re import sub

from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import create_fake_lean_cli_directory


def assert_project_exists(path: str) -> None:
    project_dir = (Path.cwd() / path)

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()

    class_name = ''.join(sub(r"([_\-])+", " ", path).title().replace(" ", ""))

    with open(project_dir / "main.py") as file:
        if path.startswith("Library/"):
            assert f"class {class_name}" in file.read()
        else:
            assert f"class {class_name}(QCAlgorithm)" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert json.load(file)["metadata"]["kernelspec"]["language"] == "python"

    with open(project_dir / "config.json") as file:
        assert json.load(file)["algorithm-language"] == "Python"


def assert_project_does_not_exist(path: str) -> None:
    project_dir = (Path.cwd() / path)
    assert not project_dir.exists()


def test_delete_project_deletes_project_directory() -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    assert_project_exists(path)
    result = CliRunner().invoke(lean, ["delete-project", path])

    assert result.exit_code == 0

    assert_project_does_not_exist(path)
