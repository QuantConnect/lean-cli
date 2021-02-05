import zipfile
from pathlib import Path

import responses
from click.testing import CliRunner

from lean.commands.init import remove_section_from_config
from lean.constants import DEFAULT_CONFIG_FILE, DEFAULT_DATA_DIR
from lean.main import lean


def create_fake_archive() -> None:
    """Create a fake archive and mock the request to the url which contains the Lean repository."""
    with zipfile.ZipFile("/tmp/archive.zip", "w") as archive:
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

  // algorithm class selector
  "algorithm-type-name": "BasicTemplateFrameworkAlgorithm",

  // Algorithm language selector - options CSharp, Python
  "algorithm-language": "CSharp",

  //Physical DLL location
  "algorithm-location": "QuantConnect.Algorithm.CSharp.dll",
  //"algorithm-location": "../../../Algorithm.Python/BasicTemplateFrameworkAlgorithm.py",

  //Research notebook
  //"composer-dll-directory": ".",

  // engine
  "data-folder": "../../../Data/",

  // debugging configuration - options for debugging-method LocalCmdLine, VisualStudio, PTVSD, PyCharm
  "debugging": false,
  "debugging-method": "LocalCmdline",

  // handlers
  "log-handler": "QuantConnect.Logging.CompositeLogHandler",
  "messaging-handler": "QuantConnect.Messaging.Messaging",
  "job-queue-handler": "QuantConnect.Queues.JobQueue",
  "api-handler": "QuantConnect.Api.Api",
  "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
  "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
  "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
  "alpha-handler": "QuantConnect.Lean.Engine.Alphas.DefaultAlphaHandler",
  "data-channel-provider": "DataChannelProvider",
  "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
  "data-aggregator": "QuantConnect.Lean.Engine.DataFeeds.AggregationManager"
}
        """.strip())

    with open("/tmp/archive.zip", "rb") as archive:
        responses.add(responses.GET, "https://github.com/QuantConnect/Lean/archive/master.zip", archive.read())


def test_remove_section_from_config_removes_section_containing_given_key_from_given_json() -> None:
    config = """
{
    // Doc 1
    "key1": "value1",
    
    // Doc 2
    "key2": "value2",
    
    // Doc 3
    "key3": "value3"
}
    """.strip()

    expected_output = """
{
    // Doc 1
    "key1": "value1",

    // Doc 3
    "key3": "value3"
}
    """.strip()

    assert remove_section_from_config(config, "key2") == expected_output


def test_init_aborts_if_config_file_already_exists() -> None:
    (Path.cwd() / DEFAULT_CONFIG_FILE).touch()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_aborts_if_data_directory_already_exists() -> None:
    (Path.cwd() / DEFAULT_DATA_DIR).mkdir()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code != 0


def test_init_prompts_for_confirmation_if_directory_not_empty() -> None:
    (Path.cwd() / "my-custom-file.txt").touch()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"], input="n\n")

    assert result.exit_code != 0
    assert "continue?" in result.output


@responses.activate
def test_init_should_create_data_directory_from_repo() -> None:
    create_fake_archive()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code == 0

    readme_path = Path.cwd() / DEFAULT_DATA_DIR / "equity" / "readme.md"
    assert readme_path.exists()

    with open(readme_path) as readme_file:
        assert readme_file.read() == "# This is just a test"


@responses.activate
def test_init_should_create_config_file_from_repo_and_should_remove_unnecessary_keys() -> None:
    create_fake_archive()

    runner = CliRunner()
    result = runner.invoke(lean, ["init"])

    assert result.exit_code == 0

    config_path = Path.cwd() / DEFAULT_CONFIG_FILE
    assert config_path.exists()

    with open(config_path) as config_file:
        assert config_file.read().strip() == f"""
{{
  // this configuration file works by first loading all top-level
  // configuration items and then will load the specified environment
  // on top, this provides a layering affect. environment names can be
  // anything, and just require definition in this file. There's
  // two predefined environments, 'backtesting' and 'live', feel free
  // to add more!

  // engine
  "data-folder": "{DEFAULT_DATA_DIR}",

  // handlers
  "log-handler": "QuantConnect.Logging.CompositeLogHandler",
  "messaging-handler": "QuantConnect.Messaging.Messaging",
  "job-queue-handler": "QuantConnect.Queues.JobQueue",
  "api-handler": "QuantConnect.Api.Api",
  "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
  "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
  "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
  "alpha-handler": "QuantConnect.Lean.Engine.Alphas.DefaultAlphaHandler",
  "data-channel-provider": "DataChannelProvider",
  "object-store": "QuantConnect.Lean.Engine.Storage.LocalObjectStore",
  "data-aggregator": "QuantConnect.Lean.Engine.DataFeeds.AggregationManager"
}}
        """.strip()
