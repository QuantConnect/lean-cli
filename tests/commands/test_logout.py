from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean
from lean.constants import CREDENTIALS_FILE, GLOBAL_CONFIG_DIR


def get_credentials_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_DIR / CREDENTIALS_FILE


def test_logout_should_delete_credentials_file() -> None:
    with open(get_credentials_path(), "w+") as file:
        file.write("{}")

    runner = CliRunner()
    result = runner.invoke(lean, ["logout"])

    assert result.exit_code == 0
    assert not get_credentials_path().exists()
