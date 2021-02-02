from click.testing import CliRunner

from lean.main import lean


def test_lean_shows_help_when_called_without_arguments() -> None:
    runner = CliRunner()

    result = runner.invoke(lean, [])

    assert result.exit_code == 0
    assert "Usage: lean [OPTIONS] COMMAND [ARGS]..." in result.output


def test_lean_shows_help_when_called_with_help_option() -> None:
    runner = CliRunner()

    result = runner.invoke(lean, ["--help"])

    assert result.exit_code == 0
    assert "Usage: lean [OPTIONS] COMMAND [ARGS]..." in result.output


def test_lean_shows_error_when_running_unknown_command() -> None:
    runner = CliRunner()

    result = runner.invoke(lean, ["this-command-does-not-exist"])

    assert result.exit_code != 0
    assert "No such command" in result.output
