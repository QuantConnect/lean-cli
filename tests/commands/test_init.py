import tempfile
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from responses import RequestsMock

from lean.commands import lean
from lean.config import Config
from lean.container import container


@pytest.fixture(autouse=True)
def create_fake_archive(requests_mock: RequestsMock) -> None:
    archive_path = Path(tempfile.mkdtemp()) / "archive.zip"

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Lean-master/Data/equity/readme.md", "# This is just a test")
        archive.writestr("Lean-master/Launcher/config.json", """
{
  // this configuration file works by first loading all top-level
  // configuration items and then will load the specified environment
  // on top, this provides a layering affect. environment names can be
  // anything, and just require definition in this file. There's
  // two predefined environments, 'backtesting' and 'live', feel free
  // to add more!

  "environment": "backtesting", // "live-paper", "backtesting", "live-interactive", "live-interactive-iqfeed"

  // data documentation
  "data-folder": "data"
}
        """.strip())

    with open(archive_path, "rb") as archive:
        requests_mock.assert_all_requests_are_fired = False
        requests_mock.add(requests_mock.GET, "https://github.com/QuantConnect/Lean/archive/master.zip", archive.read())


def test_init_should_abort_when_config_file_already_exists() -> None:
    (Path.cwd() / Config.default_lean_config_file_name).touch()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_should_abort_when_data_directory_already_exists() -> None:
    (Path.cwd() / Config.default_data_directory_name).mkdir()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_should_prompt_for_confirmation_when_directory_not_empty() -> None:
    (Path.cwd() / "my-custom-file.txt").touch()

    result = CliRunner().invoke(lean, ["init"], input="n\n")

    assert result.exit_code != 0
    assert "continue?" in result.output


def test_init_should_prompt_for_default_language_when_not_set_yet() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    assert container.cli_config_manager().default_language.get_value() == "csharp"


def test_init_should_create_data_directory_from_repo() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    readme_path = Path.cwd() / Config.default_data_directory_name / "equity" / "readme.md"
    assert readme_path.exists()

    with open(readme_path) as readme_file:
        assert readme_file.read() == "# This is just a test"


def test_init_should_create_clean_config_file_from_repo() -> None:
    runner = CliRunner()
    result = runner.invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    config_path = Path.cwd() / Config.default_lean_config_file_name
    assert config_path.exists()
    assert config_path.read_text() == """
{
  // this configuration file works by first loading all top-level
  // configuration items and then will load the specified environment
  // on top, this provides a layering affect. environment names can be
  // anything, and just require definition in this file. There's
  // two predefined environments, 'backtesting' and 'live', feel free
  // to add more!

  // data documentation
  "data-folder": "data"
}
    """.strip()
