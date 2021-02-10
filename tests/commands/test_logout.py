from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean
from lean.config import Config
from lean.container import container


def test_logout_deletes_credentials_storage_file() -> None:
    container.cli_config_manager().user_id.set_value("123")
    assert Path(Config.credentials_config_file).exists()

    result = CliRunner().invoke(lean, ["logout"])

    assert result.exit_code == 0

    assert not Path(Config.credentials_config_file).exists()
