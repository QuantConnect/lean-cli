from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import MockContainer


def assert_python_project_exists() -> None:
    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "main.py") as file:
        assert "class MyFirstProject(QCAlgorithm)" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert '"language": "python"' in file.read()


def assert_csharp_project_exists() -> None:
    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "Main.cs").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "Main.cs") as file:
        assert "class MyFirstProject : QCAlgorithm" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert '"language": "csharp"' in file.read()


def test_create_project_should_create_python_project_when_language_python(mock_container: MockContainer) -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


def test_create_project_should_create_csharp_project_when_language_csharp(mock_container: MockContainer) -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "csharp", "My First Project"])

    assert result.exit_code == 0

    assert_csharp_project_exists()


def test_create_project_should_create_python_project_when_default_language_set_to_python(
        mock_container: MockContainer) -> None:
    mock_container.cli_config_manager_mock.default_language.get_value.return_value = "python"

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


def test_create_project_should_fail_when_default_language_not_set_and_language_not_given(
        mock_container: MockContainer) -> None:
    mock_container.cli_config_manager_mock.default_language.get_value.return_value = None

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code != 0


def test_create_project_should_abort_when_project_already_exists(mock_container: MockContainer) -> None:
    (Path.cwd() / "My First Project").mkdir()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code != 0


def test_create_project_should_create_subdirectories(mock_container: MockContainer) -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Category/My First Project"])

    assert result.exit_code == 0
    assert (Path.cwd() / "My First Category" / "My First Project").exists()
