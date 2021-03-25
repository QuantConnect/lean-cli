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
from datetime import datetime
from pathlib import Path

from lean.commands.create_project import (DEFAULT_CSHARP_MAIN, DEFAULT_CSHARP_NOTEBOOK, DEFAULT_PYTHON_MAIN,
                                          DEFAULT_PYTHON_NOTEBOOK)
from lean.models.api import QCLanguage, QCLiveResults, QCProject


def create_fake_lean_cli_directory() -> None:
    """Creates a directory structure similar to the one created by `lean init` with a Python and a C# project."""
    (Path.cwd() / "data").mkdir()

    with open(Path.cwd() / "lean.json", "w+") as config_file:
        config_file.write("""
{
    // data-folder documentation
    "data-folder": "data"
}
        """)

    files = {
        (Path.cwd() / "Python Project" / "main.py"): DEFAULT_PYTHON_MAIN.replace("$NAME$", "PythonProject"),
        (Path.cwd() / "Python Project" / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (Path.cwd() / "Python Project" / "config.json"): json.dumps({
            "algorithm-language": "Python",
            "parameters": {}
        }),
        (Path.cwd() / "CSharp Project" / "Main.cs"): DEFAULT_CSHARP_MAIN.replace("$NAME$", "CSharpProject"),
        (Path.cwd() / "CSharp Project" / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
        (Path.cwd() / "CSharp Project" / "config.json"): json.dumps({
            "algorithm-language": "CSharp",
            "parameters": {}
        })
    }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as file:
            file.write(content)


def create_api_project(id: int, name: str) -> QCProject:
    """Creates a fake API project response."""
    return QCProject(
        projectId=id,
        organizationId="123",
        name=name,
        description="Description",
        modified=datetime.now(),
        created=datetime.now(),
        language=QCLanguage.Python,
        collaborators=[],
        leanVersionId=10500,
        leanPinnedToMaster=True,
        parameters=[],
        liveResults=QCLiveResults(eStatus="Unknown"),
        libraries=[]
    )
