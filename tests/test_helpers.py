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

from lean.commands.create_project import (DEFAULT_CSHARP_MAIN, DEFAULT_CSHARP_NOTEBOOK, DEFAULT_PYTHON_MAIN,
                                          DEFAULT_PYTHON_NOTEBOOK)


def create_fake_lean_cli_project() -> None:
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
        (Path.cwd() / "Python Project" / "main.py"): DEFAULT_PYTHON_MAIN.replace("$NAME", "PythonProject"),
        (Path.cwd() / "Python Project" / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (Path.cwd() / "CSharp Project" / "Main.cs"): DEFAULT_CSHARP_MAIN.replace("$NAME", "CSharpProject"),
        (Path.cwd() / "CSharp Project" / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
    }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as file:
            file.write(content)
