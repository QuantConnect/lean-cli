from click.testing import CliRunner

from lean.commands import lean
from lean.config.global_config import default_language_option, user_id_option


def test_config_get_should_print_the_value_of_the_option_with_the_given_key() -> None:
    default_language_option.set_value("python")

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "default-language"])

    assert result.exit_code == 0
    assert result.output == "python\n"


def test_config_get_should_fail_when_no_option_with_given_key_exists() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "this-option-does-not-exist"])

    assert result.exit_code != 0


def test_config_get_should_fail_when_option_has_no_value() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", default_language_option.key])

    assert result.exit_code != 0


def test_config_get_should_fail_when_option_is_credential() -> None:
    user_id_option.set_value("12345")

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", user_id_option.key])

    assert result.exit_code != 0
