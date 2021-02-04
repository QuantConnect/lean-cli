from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.constants import DEFAULT_CONFIG_FILE
from lean.main import lean
from tests.test_helpers import create_fake_lean_cli_project


@mock.patch("lean.commands.backtest.run_image")
def test_backtest_aborts_if_lean_config_not_available(run_image) -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / DEFAULT_CONFIG_FILE).unlink()

    run_image.return_value = True, ""

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Algorithm"])

    assert result.exit_code != 0


@mock.patch("lean.commands.backtest.run_image")
def test_backtest_aborts_if_project_does_not_exist(run_image) -> None:
    create_fake_lean_cli_project()

    run_image.return_value = True, ""

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0


@mock.patch("lean.commands.backtest.run_image")
def test_backtest_aborts_if_project_does_not_contain_algorithm_file(run_image) -> None:
    create_fake_lean_cli_project()
    (Path.cwd() / "Empty Project").mkdir()

    run_image.return_value = True, ""

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Empty Project"])

    assert result.exit_code != 0


@mock.patch("lean.commands.backtest.run_image")
def test_backtest_should_create_directory_for_output(run_image) -> None:
    create_fake_lean_cli_project()

    run_image.return_value = True, ""

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    backtests_dir = (Path.cwd() / "Python Project" / "backtests")
    assert backtests_dir.exists()
    assert next(backtests_dir.iterdir(), None) is not None


@mock.patch("lean.commands.backtest.run_image")
def test_backtest_should_fail_if_running_docker_image_fails(run_image) -> None:
    create_fake_lean_cli_project()

    run_image.return_value = False, ""

    runner = CliRunner()
    result = runner.invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 1
