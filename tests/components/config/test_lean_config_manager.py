# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from pathlib import Path
from typing import Optional
from unittest import mock

import json5
import pytest

from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage
from lean.components.util.xml_manager import XMLManager
from lean.container import container
from lean.models.utils import DebuggingMethod
from tests.test_helpers import create_fake_lean_cli_directory


def _create_lean_config_manager(cli_config_manager: Optional[CLIConfigManager] = None, storage: Storage = None) -> LeanConfigManager:
    return LeanConfigManager(mock.Mock(),
                             cli_config_manager or mock.Mock(),
                             ProjectConfigManager(XMLManager()),
                             mock.Mock(),
                             Storage(str(Path("~/.lean/cache").expanduser())) if storage is None else storage)

def test_get_lean_config_path_returns_closest_config_file() -> None:
    lean_config_path = Path.cwd() / "lean.json"
    cwd_path = Path.cwd() / "sub1" / "sub2" / "sub3"

    lean_config_path.touch()
    cwd_path.mkdir(parents=True)
    os.chdir(cwd_path)

    manager = _create_lean_config_manager()

    assert manager.get_lean_config_path() == lean_config_path


def test_get_lean_config_path_raises_error_when_no_config_file_exists() -> None:
    manager = _create_lean_config_manager()

    with pytest.raises(Exception):
        manager.get_lean_config_path()


def test_get_lean_config_path_returns_default_path_when_set() -> None:
    custom_config_path = Path.cwd() / "custom-lean.json"
    custom_config_path.touch()
    custom_config_path.write_text("{}", encoding="utf-8")

    manager = _create_lean_config_manager()
    manager.set_default_lean_config_path(custom_config_path)

    assert manager.get_lean_config_path() == custom_config_path


def test_get_known_lean_config_path_returns_previously_used_lean_config_path() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()

    assert manager.get_lean_config_path() == Path.cwd() / "lean.json"


def test_get_known_lean_config_path_returns_previously_used_custom_default() -> None:
    custom_config_path = Path.cwd() / "custom-lean.json"
    custom_config_path.touch()
    custom_config_path.write_text("{}", encoding="utf-8")

    manager = _create_lean_config_manager()
    manager.set_default_lean_config_path(custom_config_path)

    assert manager.get_known_lean_config_paths() == [Path.cwd() / "custom-lean.json"]

@pytest.mark.skipif(
    sys.platform !="win32", reason="Custom config path is only valid for Windows."
)
def test_get_known_lean_config_path_with_duplicated_paths() -> None:
    custom_config_path = Path.cwd() / "custom-Lean.json"
    custom_config_path.touch()
    custom_config_path.write_text("{}", encoding="utf-8")

    custom_config_path_second = Path.cwd() / "Custom-lean.json"
    custom_config_path_second.touch()
    custom_config_path_second.write_text("{}", encoding="utf-8")

    storage = Storage(str(Path("~/.lean/cache").expanduser()))
    storage.set("known-lean-config-paths", [custom_config_path.__str__(), custom_config_path_second.__str__()])
    manager = _create_lean_config_manager(storage = storage)

    assert manager.get_known_lean_config_paths() == [Path.cwd() / "custom-lean.json"]

@pytest.mark.skipif(
    sys.platform !="win32", reason="Custom config path is only valid for Windows."
)
def test_get_known_lean_config_path_normalizes_path_and_case() -> None:
    custom_config_path = Path.cwd() / "/folder/../custom-lean.json/"
    custom_config_path.touch()
    custom_config_path.write_text("{}", encoding="utf-8")

    manager = _create_lean_config_manager()
    manager.set_default_lean_config_path(custom_config_path)

    assert manager.get_known_lean_config_paths() == [Path(os.path.normcase(Path.cwd() / "/custom-lean.json"))]

def test_get_cli_root_directory_returns_path_to_directory_containing_config_file() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()

    assert manager.get_cli_root_directory() == Path.cwd()


def test_get_data_directory_returns_path_to_data_directory_as_configured_in_config() -> None:
    with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
        file.write('{ "data-folder": "sub1/sub2/sub3/data" }')

    manager = _create_lean_config_manager()

    assert manager.get_data_directory() == Path.cwd() / "sub1" / "sub2" / "sub3" / "data"


def test_get_data_directory_returns_path_to_data_directory_when_config_contains_comments() -> None:
    with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
        file.write("""
{
    // some comment about the data-folder
    "data-folder": "sub1/sub2/sub3/data"
}
        """)

    manager = _create_lean_config_manager()

    assert manager.get_data_directory() == Path.cwd() / "sub1" / "sub2" / "sub3" / "data"


def test_set_properties_adds_property_when_not_part_of_config_yet() -> None:
    with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
        file.write("""
{
    // some comment about the data-folder
    "data-folder": "sub1/sub2/sub3/data"
}
        """)

    manager = _create_lean_config_manager()
    manager.set_properties({"my-property": "my-value"})

    config = (Path.cwd() / "lean.json").read_text(encoding="utf-8")

    assert json5.loads(config)["my-property"] == "my-value"
    assert config.count("my-property") == 1


def test_set_properties_updates_property_when_part_of_config_already() -> None:
    with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
        file.write("""
{
    // some comment about the data-folder
    "data-folder": "sub1/sub2/sub3/data",
    "my-property": "my-value"
}
        """)

    manager = _create_lean_config_manager()
    manager.set_properties({"my-property": "my-value"})

    config = (Path.cwd() / "lean.json").read_text(encoding="utf-8")

    assert json5.loads(config)["my-property"] == "my-value"
    assert config.count("my-property") == 1


def test_set_properties_does_not_preserve_comments() -> None:
    with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
        file.write("""
{
    // some comment about the data-folder
    "data-folder": "sub1/sub2/sub3/data"
}
        """)

    manager = _create_lean_config_manager()
    manager.set_properties({"my-property": "my-value"})

    config = (Path.cwd() / "lean.json").read_text(encoding="utf-8")

    assert "// some comment about the data-folder" not in config


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

    // parameters to set in the algorithm (the below are just samples)
    "parameters": {
        // Intrinio account user and password
        "intrinio-username": "",
        "intrinio-password": "",

        "ema-fast": 10,
        "ema-slow": 20
    },

    // handlers
    "log-handler": "QuantConnect.Logging.CompositeLogHandler",
    "messaging-handler": "QuantConnect.Messaging.Messaging",
    "job-queue-handler": "QuantConnect.Queues.JobQueue",

    // interactive brokers configuration
    "ib-account": "",
    "ib-user-name": "",
    "ib-password": "",
    "ib-host": "127.0.0.1",
    "ib-port": "4002",
    "ib-agent-description": "Individual",
    "ib-tws-dir": "C:\\Jts",
    "ib-trading-mode": "paper",
    "ib-enable-delayed-streaming-data": false,
    "ib-version": "974",

    // iqfeed configuration
    "iqfeed-host": "127.0.0.1",
    "iqfeed-username": "",
    "iqfeed-password": "",
    "iqfeed-productName": "",
    "iqfeed-version": "1.0"
}
    """

    manager = _create_lean_config_manager()
    clean_config = manager.clean_lean_config(original_config)

    for key in ["environment",
                "algorithm-type-name", "algorithm-language", "algorithm-location",
                "composer-dll-directory",
                "debugging", "debugging-method",
                "parameters", "intrinio-username", "intrinio-password", "ema-fast", "ema-slow",
                "ib-host", "ib-port", "ib-tws-dir", "ib-version",
                "iqfeed-host"]:
        assert f'"{key}"' not in clean_config

    for key in ["data-folder", "log-handler", "messaging-handler", "job-queue-handler",
                "ib-account", "ib-user-name", "ib-password", "ib-agent-description",
                "ib-trading-mode", "ib-enable-delayed-streaming-data",
                "iqfeed-iqconnect", "iqfeed-username", "iqfeed-password", "iqfeed-productName", "iqfeed-version"]:
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

    // parameters to set in the algorithm (the below are just samples)
    "parameters": {
        // Intrinio account user and password
        "intrinio-username": "",
        "intrinio-password": "",

        "ema-fast": 10,
        "ema-slow": 20
    },

    // handlers
    "log-handler": "QuantConnect.Logging.CompositeLogHandler",
    "messaging-handler": "QuantConnect.Messaging.Messaging",
    "job-queue-handler": "QuantConnect.Queues.JobQueue",

    // interactive brokers configuration
    "ib-account": "",
    "ib-user-name": "",
    "ib-password": "",
    "ib-host": "127.0.0.1",
    "ib-port": "4002",
    "ib-agent-description": "Individual",
    "ib-tws-dir": "C:\\Jts",
    "ib-trading-mode": "paper",
    "ib-enable-delayed-streaming-data": false,
    "ib-version": "974",

    // iqfeed configuration
    "iqfeed-host": "127.0.0.1",
    "iqfeed-username": "",
    "iqfeed-password": "",
    "iqfeed-productName": "",
    "iqfeed-version": "1.0"
}
    """

    manager = _create_lean_config_manager()
    clean_config = manager.clean_lean_config(original_config)

    assert "// algorithm class selector" not in clean_config
    assert "// Algorithm language selector - options CSharp, Python" not in clean_config
    assert "//Physical DLL location" not in clean_config
    assert "//Research notebook" not in clean_config
    assert "// debugging configuration - options for debugging-method LocalCmdLine, VisualStudio, PTVSD, PyCharm" not in clean_config
    assert "// parameters to set in the algorithm (the below are just samples)" not in clean_config
    assert "// Intrinio account user and password" not in clean_config

    assert "// engine" in clean_config
    assert "// handlers" in clean_config
    assert "// interactive brokers configuration" in clean_config
    assert "// iqfeed configuration" in clean_config


def test_get_complete_lean_config_returns_dict_with_all_keys_removed_in_clean_lean_config() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("backtesting", Path.cwd() / "Python Project" / "main.py", None)

    for key in ["environment",
                "algorithm-type-name", "algorithm-language", "algorithm-location",
                "composer-dll-directory",
                "debugging", "debugging-method",
                "parameters"]:
        assert key in config


def test_get_complete_lean_config_sets_environment() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["environment"] == "my-environment"


def test_get_complete_lean_config_sets_close_automatically() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["close-automatically"]


def test_get_complete_lean_config_disables_debugging_when_no_method_given() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert not config["debugging"]


@pytest.mark.parametrize("method,value", [(DebuggingMethod.PyCharm, "PyCharm"),
                                          (DebuggingMethod.PTVSD, "PTVSD"),
                                          (DebuggingMethod.VSDBG, "LocalCmdline"),
                                          (DebuggingMethod.Rider, "LocalCmdline")])
def test_get_complete_lean_config_parses_debugging_method_correctly(method: DebuggingMethod, value: str) -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", method)

    assert config["debugging"]
    assert config["debugging-method"] == value


def test_get_complete_lean_config_sets_credentials_from_cli_config_manager() -> None:
    create_fake_lean_cli_directory()

    cli_config_manager = mock.Mock()
    cli_config_manager.user_id.get_value.return_value = "123"
    cli_config_manager.api_token.get_value.return_value = "456"

    manager = _create_lean_config_manager(cli_config_manager=cli_config_manager)
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["job-user-id"] == "123"
    assert config["api-access-token"] == "456"


def test_get_complete_lean_config_sets_interactive_brokers_config() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["ib-host"] == "127.0.0.1"
    assert config["ib-port"] == "4002"
    assert config["ib-tws-dir"] == "/root/Jts"


def test_get_complete_lean_config_sets_iqfeed_host() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["iqfeed-host"] == "host.docker.internal"


def test_get_complete_lean_config_sets_python_algorithm_details() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["algorithm-type-name"] == "main"
    assert config["algorithm-language"] == "Python"
    assert config["algorithm-location"] == "/LeanCLI/main.py"


@pytest.mark.parametrize("csharp_code,class_name", [("""
namespace QuantConnect.Algorithm.CSharp
{
    public class CSharpProject : QCAlgorithm
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class CSharpProject:QCAlgorithm
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class     CSharpProject     :     QCAlgorithm
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class CSharpProject
        : QCAlgorithm
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class
        CSharpProject
        : QCAlgorithm
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class SymbolData1
    {
    }

    public class CSharpProject : QCAlgorithm
    {
    }

    public class SymbolData2
    {
    }
}
                                                    """, "CSharpProject"),
                                                    ("""
namespace QuantConnect.Algorithm.CSharp
{
    public class _ĝᾌᾫि‿ : QCAlgorithm
    {
    }
}
                                                    """, "_ĝᾌᾫि‿")])
def test_get_complete_lean_config_sets_csharp_algorithm_details(csharp_code: str, class_name: str) -> None:
    create_fake_lean_cli_directory()

    csharp_path = Path.cwd() / "CSharp Project" / "Main.cs"
    with csharp_path.open("w+", encoding="utf-8") as file:
        file.write(csharp_code.strip() + "\n")

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", csharp_path, None)

    assert config["algorithm-type-name"] == class_name
    assert config["algorithm-language"] == "CSharp"
    assert config["algorithm-location"] == "CSharp Project.dll"


def test_get_complete_lean_config_sets_parameters() -> None:
    create_fake_lean_cli_directory()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    })

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["parameters"] == {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }


def test_get_complete_lean_config_sets_python_additional_paths() -> None:
    create_fake_lean_cli_directory()

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", Path.cwd() / "Python Project" / "main.py", None)

    assert config["python-additional-paths"] == []


def test_get_complete_lean_config_sets_python_additional_paths_when_there_are_libraries() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path.cwd() / "Python Project"
    relative_library_dir = Path("Library/Python Library")
    library_dir = Path.cwd() / relative_library_dir

    library_manager = container.library_manager
    library_manager.add_lean_library_to_project(project_dir, library_dir, False)

    manager = _create_lean_config_manager()
    config = manager.get_complete_lean_config("my-environment", project_dir / "main.py", None)

    python_additional_paths = config["python-additional-paths"]
    expected_python_paths = [(Path("/") / relative_library_dir).as_posix(), "/Library"]

    assert python_additional_paths is not None
    assert len(python_additional_paths) == len(python_additional_paths)
    assert all([path in expected_python_paths for path in python_additional_paths])


@pytest.mark.parametrize("provider,limit,result", [
    ("QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider", None, None),
    ("QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider", 100, None),
    ("QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider", None, None),
    ("QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider", 100, 100)
])
def test_configure_data_purchase_limit_works_correctly(provider: str,
                                                       limit: Optional[int],
                                                       result: Optional[int]) -> None:
    lean_config = {
        "data-provider": provider
    }

    manager = _create_lean_config_manager()
    manager.configure_data_purchase_limit(lean_config, limit)

    if result is not None:
        assert lean_config["data-purchase-limit"] == result
    else:
        assert "data-purchase-limit" not in lean_config
