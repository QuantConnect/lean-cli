from pathlib import Path

from click.testing import CliRunner

from lean.constants import DEFAULT_CONFIG_FILE
from lean.main import lean
from tests.test_helpers import create_fake_lean_cli_project


def test_backtest_aborts_if_lean_config_not_available() -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / DEFAULT_CONFIG_FILE).unlink()

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Algorithm"])

    assert result.exit_code != 0


def test_backtest_aborts_if_project_does_not_exist() -> None:
    create_fake_lean_cli_project()

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0


def test_backtest_aborts_if_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / "Empty Project").mkdir()

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Empty Project"])

    assert result.exit_code != 0


def test_backtest_should_create_directory_for_output() -> None:
    create_fake_lean_cli_project()

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    backtests_dir = (Path.cwd() / "Python Project" / "backtests")
    assert backtests_dir.exists()
    assert next(backtests_dir.iterdir(), None) is not None
