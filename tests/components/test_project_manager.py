from pathlib import Path

import pytest

from lean.components.project_manager import ProjectManager
from tests.test_helpers import create_fake_lean_cli_project


def test_find_algorithm_file_should_return_input_when_input_is_file() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager()
    result = manager.find_algorithm_file(Path.cwd() / "Python Project" / "main.py")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_should_return_main_py_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager()
    result = manager.find_algorithm_file(Path.cwd() / "Python Project")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_should_return_main_cs_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_project()

    manager = ProjectManager()
    result = manager.find_algorithm_file(Path.cwd() / "CSharp Project")

    assert result == Path.cwd() / "CSharp Project" / "Main.cs"


def test_find_algorithm_file_should_raise_error_if_no_algorithm_file_exists() -> None:
    create_fake_lean_cli_project()

    (Path.cwd() / "Empty Project").mkdir()

    manager = ProjectManager()

    with pytest.raises(Exception):
        manager.find_algorithm_file(Path.cwd() / "Empty Project")
