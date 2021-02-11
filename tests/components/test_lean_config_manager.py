import os
from pathlib import Path
from unittest import mock

import pytest

from lean.components.lean_config_manager import LeanConfigManager
from lean.models.config import DebuggingMethod
from tests.test_helpers import create_fake_lean_cli_project


def test_get_lean_config_path_returns_closest_config_file() -> None:
    lean_config_path = Path.cwd() / "lean.json"
    cwd_path = Path.cwd() / "sub1" / "sub2" / "sub3"

    lean_config_path.touch()
    cwd_path.mkdir(parents=True)
    os.chdir(cwd_path)

    manager = LeanConfigManager(mock.Mock(), "lean.json")

    assert manager.get_lean_config_path() == lean_config_path


def test_get_lean_config_path_raises_error_when_no_config_file_exists() -> None:
    manager = LeanConfigManager(mock.Mock(), "lean.json")

    with pytest.raises(Exception):
        manager.get_lean_config_path()


def test_get_lean_config_path_returns_default_path_when_set() -> None:
    manager = LeanConfigManager(mock.Mock(), "lean.json")
    manager.set_default_lean_config_path(Path.cwd() / "custom-lean.json")

    assert manager.get_lean_config_path() == Path.cwd() / "custom-lean.json"


def test_get_data_directory_returns_path_to_data_directory_as_configured_in_config() -> None:
    with (Path.cwd() / "lean.json").open("w+") as file:
        file.write('{ "data-folder": "sub1/sub2/sub3/data" }')

    manager = LeanConfigManager(mock.Mock(), "lean.json")

    assert manager.get_data_directory() == Path.cwd() / "sub1" / "sub2" / "sub3" / "data"


def test_get_data_directory_returns_path_to_data_directory_when_config_contains_comments() -> None:
    with (Path.cwd() / "lean.json").open("w+") as file:
        file.write("""
{
    // some comment about the data-folder
    "data-folder": "sub1/sub2/sub3/data"
}
        """)

    manager = LeanConfigManager(mock.Mock(), "lean.json")

    assert manager.get_data_directory() == Path.cwd() / "sub1" / "sub2" / "sub3" / "data"


def test_clean_lean_config_removes_auto_configurable_keys_from_original_config() -> None:
    original_config = """
{
    // this configuration file works by first loading all top-level
    // configuration items and then will load the specified environment
    // on top, this provides a layering affect.environment names can be
    // anything, and just require definition in this file.There's
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
    "job-queue-handler": "QuantConnect.Queues.JobQueue"
}
    """

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    clean_config = manager.clean_lean_config(original_config)

    for key in ["environment",
                "algorithm-type-name", "algorithm-language", "algorithm-location",
                "composer-dll-directory",
                "debugging", "debugging-method"]:
        assert f'"{key}"' not in clean_config

    for key in ["data-folder", "log-handler", "messaging-handler", "job-queue-handler"]:
        assert f'"{key}"' in clean_config


def test_clean_lean_config_removes_documentation_of_removed_keys() -> None:
    original_config = """
{
    // this configuration file works by first loading all top-level
    // configuration items and then will load the specified environment
    // on top, this provides a layering affect.environment names can be
    // anything, and just require definition in this file.There's
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
    "job-queue-handler": "QuantConnect.Queues.JobQueue"
}
    """

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    clean_config = manager.clean_lean_config(original_config)

    assert "// algorithm class selector" not in clean_config
    assert "// Algorithm language selector - options CSharp, Python" not in clean_config
    assert "//Physical DLL location" not in clean_config
    assert "//Research notebook" not in clean_config
    assert "// debugging configuration - options for debugging-method LocalCmdLine, VisualStudio, PTVSD, PyCharm" not in clean_config

    assert "// engine" in clean_config
    assert "// handlers" in clean_config


def test_get_complete_lean_config_returns_dict_with_all_keys_removed_in_clean_lean_config() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("backtesting", Path.cwd() / "Python Project" / "main.py", None)

    for key in ["environment",
                "algorithm-type-name", "algorithm-language", "algorithm-location",
                "composer-dll-directory",
                "debugging", "debugging-method"]:
        assert key in config


def test_get_complete_lean_config_sets_environment() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["environment"] == "my-environment"


def test_get_complete_lean_config_sets_close_automatically() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["close-automatically"]


def test_get_complete_lean_config_disables_debugging_when_no_method_given() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert not config["debugging"]


@pytest.mark.parametrize("method,value", [(DebuggingMethod.PyCharm, "PyCharm"),
                                          (DebuggingMethod.PTVSD, "PTVSD"),
                                          (DebuggingMethod.Mono, "LocalCmdline")])
def test_get_complete_lean_config_enables_debugging_when_method_given(method: DebuggingMethod, value: str) -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", method)

    assert config["debugging"]
    assert config["debugging-method"] == value


def test_get_complete_lean_config_sets_credentials_from_cli_config_manager() -> None:
    create_fake_lean_cli_project()

    cli_config_manager = mock.Mock()
    cli_config_manager.user_id.get_value.return_value = "123"
    cli_config_manager.api_token.get_value.return_value = "456"

    manager = LeanConfigManager(cli_config_manager, "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["job-user-id"] == "123"
    assert config["api-access-token"] == "456"


def test_get_complete_lean_config_sets_python_algorithm_details() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["algorithm-type-name"] == "main"
    assert config["algorithm-language"] == "Python"
    assert config["algorithm-location"] == "/LeanCLI/Python Project/main.py"


def test_get_complete_lean_config_sets_csharp_algorithm_details() -> None:
    create_fake_lean_cli_project()

    manager = LeanConfigManager(mock.Mock(), "lean.json")
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "CSharp Project" / "Main.cs", None)

    assert config["algorithm-type-name"] == "CSharpProject"
    assert config["algorithm-language"] == "CSharp"
    assert config["algorithm-location"] == "LeanCLI.dll"
