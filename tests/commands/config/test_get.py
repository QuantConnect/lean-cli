from click.testing import CliRunner

from lean.commands import lean
from lean.container import container


def test_config_get_should_print_the_value_of_the_option_with_the_given_key() -> None:
    container.cli_config_manager().default_language.set_value("python")

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
    result = runner.invoke(lean, ["config", "get", "default-language"])

    assert result.exit_code != 0


def test_config_get_should_fail_when_option_is_credential() -> None:
    container.cli_config_manager().user_id.set_value("123")

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "user-id"])

    assert result.exit_code != 0
    assert "123" not in result.output
