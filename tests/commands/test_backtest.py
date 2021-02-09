from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import create_fake_lean_cli_project, MockContainer


def test_backtest_should_pass_algorithm_file_to_backtest_runner(mock_container: MockContainer) -> None:
    create_fake_lean_cli_project()
    mock_container.project_manager_mock.find_algorithm_file.side_effect = lambda p: p

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py"])

    assert result.exit_code == 0

    mock_container.backtest_runner_mock.run_backtest.assert_called_once_with(Path("Python Project/main.py").resolve(),
                                                                             mock.ANY)


def test_backtest_should_run_backtest_with_default_output_directory(mock_container: MockContainer) -> None:
    create_fake_lean_cli_project()

    mock_container.project_manager_mock.find_algorithm_file.side_effect = lambda p: p

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py"])

    assert result.exit_code == 0

    mock_container.backtest_runner_mock.run_backtest.assert_called_once()
    args, _ = mock_container.backtest_runner_mock.run_backtest.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[1].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_should_run_backtest_with_custom_output_directory(mock_container: MockContainer) -> None:
    create_fake_lean_cli_project()

    mock_container.project_manager_mock.find_algorithm_file.side_effect = lambda p: p

    result = CliRunner().invoke(lean,
                                ["backtest", "Python Project/main.py", "--output", "Python Project/custom-backtests"])

    assert result.exit_code == 0

    mock_container.backtest_runner_mock.run_backtest.assert_called_once()
    args, _ = mock_container.backtest_runner_mock.run_backtest.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[1].relative_to(Path("Python Project/custom-backtests").resolve())


def test_backtest_should_abort_when_project_does_not_exist(mock_container: MockContainer) -> None:
    create_fake_lean_cli_project()

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    mock_container.backtest_runner_mock.run_backtest.assert_not_called()


def test_backtest_should_abort_when_project_does_not_contain_algorithm_file(mock_container: MockContainer) -> None:
    create_fake_lean_cli_project()

    def find_algorithm_file():
        raise RuntimeError("File not found")

    mock_container.project_manager_mock.find_algorithm_file.side_effect = find_algorithm_file

    result = CliRunner().invoke(lean, ["backtest", "Empty Project"])

    assert result.exit_code != 0

    mock_container.backtest_runner_mock.run_backtest.assert_not_called()
