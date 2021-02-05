from click.testing import CliRunner

from lean.commands import lean
from lean.config.global_config import user_id_option


def test_config_get_should_update_the_value_of_the_option_with_the_given_key_with_the_given_value() -> None:
    user_id_option.set_value("12345")

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", user_id_option.key, "54321"])

    assert result.exit_code == 0
    assert user_id_option.get_value() == "54321"


def test_config_set_should_fail_when_no_option_with_given_key_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", "this-option-does-not-exist", "value"])

    assert result.exit_code != 0
