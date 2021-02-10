from pathlib import Path
from unittest import mock

from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_project


def test_backtest_should_call_lean_runner_to_backtest_given_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 version=None)


def test_backtest_should_run_backtest_with_default_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_should_run_backtest_with_custom_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean,
                                ["backtest", "Python Project/main.py", "--output", "Python Project/custom-backtests"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/custom-backtests").resolve())


def test_backtest_should_abort_when_project_does_not_exist() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_should_abort_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_should_force_update_when_update_option_given() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py", "--update"])

    assert result.exit_code == 0

    lean_runner.force_update.assert_called_once()
    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 version=None)


def test_backtest_should_pass_version_on_to_lean_runner() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py", "--version", "3"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 version=3)
