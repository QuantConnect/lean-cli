from pathlib import Path

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

    for file in [Path.cwd() / "Python Project" / "main.py", Path.cwd() / "CSharp Project" / "Main.cs"]:
        file.parent.mkdir(parents=True)
        file.touch()
