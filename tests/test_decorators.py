from pathlib import Path

from click.testing import CliRunner

from lean.constants import DEFAULT_LEAN_CONFIG_FILE
from lean.decorators import local_command


def test_local_command_should_abort_if_lean_config_not_available() -> None:
    @local_command
    def my_command() -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(my_command)

    assert result.exit_code != 0


def test_local_command_should_do_nothing_if_default_config_available() -> None:
    (Path.cwd() / DEFAULT_LEAN_CONFIG_FILE).touch()

    @local_command
    def my_command() -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(my_command)

    assert result.exit_code == 0


def test_local_command_should_do_nothing_if_config_option_given() -> None:
    (Path.cwd() / "custom-config.json").touch()

    @local_command
    def my_command() -> None:
        pass

    runner = CliRunner()
    result = runner.invoke(my_command, ["--config", "custom-config.json"])

    assert result.exit_code == 0
