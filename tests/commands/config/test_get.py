from click.testing import CliRunner

from lean.commands import lean
from lean.config.global_config import user_id_option


def test_config_get_should_print_the_value_of_the_option_with_the_given_key() -> None:
    user_id_option.set_value("12345")

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "user-id"])

    assert result.exit_code == 0
    assert result.output == "12345\n"


def test_config_get_should_fail_if_no_option_with_given_key_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "this-option-does-not-exist"])

    assert result.exit_code != 0


def test_config_get_should_fail_if_option_has_no_value() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", user_id_option.key])

    assert result.exit_code != 0
