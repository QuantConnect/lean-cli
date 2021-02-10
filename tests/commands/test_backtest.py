from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_fake_lean_cli_project


def test_backtest_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_backtest_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", "Python Project/custom-backtests"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[2].relative_to(Path("Python Project/custom-backtests").resolve())


def test_backtest_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--update"])

    assert result.exit_code == 0

    lean_runner.force_update.assert_called_once()
    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_backtest_passes_custom_version_to_lean_runner() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--version", "3"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "3",
                                                 None)


@pytest.mark.parametrize("project,editor,debug_method", [("Python Project/main.py", "pycharm", "PyCharm"),
                                                         ("Python Project/main.py", "PyCharm", "PyCharm"),
                                                         ("CSharp Project/Main.cs", "vs", "VisualStudio"),
                                                         ("CSharp Project/Main.cs", "VS", "VisualStudio"),
                                                         ("Python Project/main.py", "vscode", "PTVSD"),
                                                         ("Python Project/main.py", "VSCode", "PTVSD"),
                                                         ("CSharp Project/Main.cs", "vscode", "VisualStudio"),
                                                         ("CSharp Project/Main.cs", "VSCode", "VisualStudio")])
def test_backtest_passes_correct_debug_method_to_lean_runner(project: str, editor: str, debug_method: str) -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", project, "--debug", editor])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path(project).resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 debug_method)
