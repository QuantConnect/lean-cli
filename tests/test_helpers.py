from pathlib import Path

from lean.commands.create_project import (DEFAULT_CSHARP_MAIN, DEFAULT_CSHARP_NOTEBOOK, DEFAULT_PYTHON_MAIN,
                                          DEFAULT_PYTHON_NOTEBOOK)
from lean.constants import DEFAULT_CONFIG_FILE, DEFAULT_DATA_DIR


def create_fake_lean_cli_project() -> None:
    """Create a directory structure similar to the one created by `lean init` with a Python and C# project."""
    (Path.cwd() / DEFAULT_DATA_DIR).mkdir()

    with open(Path.cwd() / DEFAULT_CONFIG_FILE, "w+") as config_file:
        config_file.write(f"""
{{
    "data-folder": "{DEFAULT_DATA_DIR}"
}}
        """)

    files = {
        (Path.cwd() / "Python Project" / "main.py"): DEFAULT_PYTHON_MAIN,
        (Path.cwd() / "Python Project" / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (Path.cwd() / "CSharp Project" / "Main.cs"): DEFAULT_CSHARP_MAIN,
        (Path.cwd() / "CSharp Project" / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
    }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as file:
            file.write(content)
