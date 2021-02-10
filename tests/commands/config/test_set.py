from click.testing import CliRunner

from lean.commands import lean
from lean.container import container


def test_config_get_should_update_the_value_of_the_option() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", "user-id", "12345"])

    assert result.exit_code == 0

    assert container.cli_config_manager().user_id.get_value() == "12345"


def test_config_set_should_fail_when_no_option_with_given_key_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", "this-option-does-not-exist", "value"])

    assert result.exit_code != 0
