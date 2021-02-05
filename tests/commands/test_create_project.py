from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean


def test_create_project_should_create_python_project() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code == 0

    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "main.py") as file:
        assert "class MyFirstProject(QCAlgorithm)" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert '"language": "python"' in file.read()


def test_create_project_should_create_csharp_project() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["create-project", "--language", "csharp", "My First Project"])

    assert result.exit_code == 0

    project_dir = (Path.cwd() / "My First Project")

    assert project_dir.exists()
    assert (project_dir / "Main.cs").exists()
    assert (project_dir / "research.ipynb").exists()

    with open(project_dir / "Main.cs") as file:
        assert "public class MyFirstProject : QCAlgorithm" in file.read()

    with open(project_dir / "research.ipynb") as file:
        assert '"language": "csharp"' in file.read()


def test_create_project_should_abort_if_project_already_exists() -> None:
    (Path.cwd() / "My First Project").mkdir()

    runner = CliRunner()
    result = runner.invoke(lean, ["create-project", "--language", "python", "My First Project"])

    assert result.exit_code != 0


def test_create_project_should_create_subdirectories() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["create-project", "--language", "python", "My First Category/My First Project"])

    assert result.exit_code == 0
    assert (Path.cwd() / "My First Category" / "My First Project").exists()
