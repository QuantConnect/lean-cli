import tempfile
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from responses import RequestsMock

from lean.commands import lean
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


def test_init_aborts_when_config_file_already_exists() -> None:
    (Path.cwd() / "lean.json").touch()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_aborts_when_data_directory_already_exists() -> None:
    (Path.cwd() / "data").mkdir()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_prompts_for_confirmation_when_directory_not_empty() -> None:
    (Path.cwd() / "my-custom-file.txt").touch()

    result = CliRunner().invoke(lean, ["init"], input="n\n")

    assert result.exit_code != 0
    assert "continue?" in result.output


def test_init_prompts_for_default_language_when_not_set_yet() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    assert container.cli_config_manager().default_language.get_value() == "csharp"


def test_init_creates_data_directory_from_repo() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    readme_path = Path.cwd() / "data" / "equity" / "readme.md"
    assert readme_path.exists()

    with open(readme_path) as readme_file:
        assert readme_file.read() == "# This is just a test"


def test_init_creates_clean_config_file_from_repo() -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    config_path = Path.cwd() / "lean.json"
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


@pytest.mark.parametrize("file", ["QuantConnect.Algorithm.CSharp.csproj",
                                  ".idea/workspace.xml",
                                  ".vscode/launch.json"])
def test_init_creates_extra_files_supporting_autocompletion_and_debugging(file: str) -> None:
    result = CliRunner().invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    assert (Path.cwd() / file).exists()
