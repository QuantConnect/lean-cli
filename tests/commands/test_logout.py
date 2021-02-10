from click.testing import CliRunner

from lean.commands import lean
from lean.container import container


def test_logout_should_clear_credentials_storage() -> None:
    container.cli_config_manager().user_id.set_value("123")
    assert container.credentials_storage().file.exists()

    result = CliRunner().invoke(lean, ["logout"])

    assert result.exit_code == 0

    assert not container.credentials_storage().file.exists()
