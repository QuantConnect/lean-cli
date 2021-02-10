from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean
from lean.container import container


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


def test_create_project_creates_python_project_when_language_python() -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


def test_create_project_creates_csharp_project_when_language_csharp() -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "csharp", "My First Project"])

    assert result.exit_code == 0

    assert_csharp_project_exists()


def test_create_project_creates_python_project_when_default_language_set_to_python() -> None:
    container.cli_config_manager().default_language.set_value("python")

    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code == 0

    assert_python_project_exists()


def test_create_project_aborts_when_default_language_not_set_and_language_not_given() -> None:
    result = CliRunner().invoke(lean, ["create-project", "My First Project"])

    assert result.exit_code != 0


def test_create_project_aborts_when_project_already_exists() -> None:
    (Path.cwd() / "My First Project").mkdir()

    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code != 0


def test_create_project_creates_subdirectories() -> None:
    result = CliRunner().invoke(lean, ["create-project", "--language", "python", "My First Category/My First Project"])

    assert result.exit_code == 0

    assert (Path.cwd() / "My First Category" / "My First Project").exists()
