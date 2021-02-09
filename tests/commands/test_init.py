import zipfile
from pathlib import Path

from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import MockContainer


def download_file(url: str, destination: Path) -> None:
    if url != "https://github.com/QuantConnect/Lean/archive/master.zip":
        return

    destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(destination, "w") as archive:
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
}
        """.strip())


def test_init_should_abort_when_config_file_already_exists(mock_container: MockContainer) -> None:
    (Path.cwd() / mock_container.config["default_lean_config_file_name"]).touch()

    result = CliRunner().invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_should_abort_when_data_directory_already_exists(mock_container: MockContainer) -> None:
    (Path.cwd() / mock_container.config["default_data_directory_name"]).mkdir()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_should_prompt_for_confirmation_when_directory_not_empty(mock_container: MockContainer) -> None:
    (Path.cwd() / "my-custom-file.txt").touch()

    result = CliRunner().invoke(lean, ["init"], input="n\n")

    assert result.exit_code != 0
    assert "continue?" in result.output


def test_init_should_prompt_for_default_language_when_not_set_yet(mock_container: MockContainer) -> None:
    mock_container.http_client_mock.download_file.side_effect = download_file

    mock_container.cli_config_manager_mock.default_language.get_value.return_value = None
    mock_container.cli_config_manager_mock.default_language.allowed_values = ["python", "csharp"]
    mock_container.lean_config_manager_mock.clean_lean_config.return_value = '{ "key": "value" }'

    runner = CliRunner()
    result = runner.invoke(lean, ["init"], input="csharp\n")

    assert result.exit_code == 0

    mock_container.cli_config_manager_mock.default_language.set_value.assert_called_once_with("csharp")


def test_init_should_create_data_directory_from_repo(mock_container: MockContainer) -> None:
    mock_container.http_client_mock.download_file.side_effect = download_file

    mock_container.cli_config_manager_mock.default_language.get_value.return_value = "python"
    mock_container.lean_config_manager_mock.clean_lean_config.return_value = '{ "key": "value" }'

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code == 0

    readme_path = Path.cwd() / mock_container.config["default_data_directory_name"] / "equity" / "readme.md"
    assert readme_path.exists()

    with open(readme_path) as readme_file:
        assert readme_file.read() == "# This is just a test"


def test_init_should_create_clean_config_file_from_repo(mock_container: MockContainer) -> None:
    mock_container.http_client_mock.download_file.side_effect = download_file

    mock_container.cli_config_manager_mock.default_language.get_value.return_value = "python"
    mock_container.lean_config_manager_mock.clean_lean_config.return_value = '{ "key": "value" }'

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code == 0

    mock_container.lean_config_manager_mock.clean_lean_config.assert_called_once_with("""
{
  // this configuration file works by first loading all top-level
  // configuration items and then will load the specified environment
  // on top, this provides a layering affect. environment names can be
  // anything, and just require definition in this file. There's
  // two predefined environments, 'backtesting' and 'live', feel free
  // to add more!

  "environment": "backtesting", // "live-paper", "backtesting", "live-interactive", "live-interactive-iqfeed"
}
        """.strip())

    config_path = Path.cwd() / mock_container.config["default_lean_config_file_name"]
    assert config_path.exists()
    assert config_path.read_text() == '{ "key": "value" }'
