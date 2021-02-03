from pathlib import Path

from click.testing import CliRunner

from lean.constants import GLOBAL_CONFIG_DIR, CREDENTIALS_FILE_NAME
from lean.main import lean


def get_credentials_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_DIR / CREDENTIALS_FILE_NAME


def test_logout_deletes_credentials() -> None:
    with open(get_credentials_path(), "w+") as file:
        file.write("{}")

    runner = CliRunner()
    result = runner.invoke(lean, ["logout"])

    assert result.exit_code == 0
    assert not get_credentials_path().exists()
