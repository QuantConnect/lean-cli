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

from pathlib import Path
from typing import Any, Dict, Optional, List


from lean.components.cloud.module_manager import ModuleManager
from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage, safe_save
from lean.components.util.logger import Logger
from lean.constants import DEFAULT_LEAN_CONFIG_FILE_NAME
from lean.models.errors import MoreInfoError
from lean.models.utils import DebuggingMethod


class LeanConfigManager:
    """The LeanConfigManager class contains utilities to work with files containing LEAN engine configuration."""

    def __init__(self,
                 logger: Logger,
                 cli_config_manager: CLIConfigManager,
                 project_config_manager: ProjectConfigManager,
                 module_manager: ModuleManager,
                 cache_storage: Storage) -> None:
        """Creates a new LeanConfigManager instance.

        :param logger: the logger to log messages with
        :param cli_config_manager: the CLIConfigManager instance to use when retrieving credentials
        :param project_config_manager: the ProjectConfigManager instance to use when retrieving project parameters
        :param module_manager: the ModuleManager to use
        :param cache_storage: the Storage instance to store known Lean config paths in
        """
        self._logger = logger
        self._cli_config_manager = cli_config_manager
        self._project_config_manager = project_config_manager
        self._module_manager = module_manager
        self._cache_storage = cache_storage
        self._default_path = None
        self._lean_config_path = None

    def get_lean_config_path(self) -> Path:
        """Returns the path to the closest Lean config file.

        This recurses upwards in the directory tree looking for a Lean config file.
        This search can be overridden using set_default_lean_config_path().

        Raises an error if no Lean config file can be found.

        :return: the path to the closest Lean config file
        """
        if self._default_path is not None:
            return self._default_path

        if self._lean_config_path is not None:
            return self._lean_config_path

        # Recurse upwards in the directory tree until we find a Lean config file
        current_dir = Path.cwd()
        while True:
            target_file = current_dir / DEFAULT_LEAN_CONFIG_FILE_NAME
            if target_file.exists():
                self._lean_config_path = target_file

                self.store_known_lean_config_path(self._lean_config_path)
                return self._lean_config_path

            # If the parent directory is the same as the current directory we can't go up any more
            if current_dir.parent == current_dir:
                raise MoreInfoError(f"'{DEFAULT_LEAN_CONFIG_FILE_NAME}' not found",
                                    "https://www.lean.io/docs/v2/lean-cli/initialization/configuration#03-Lean-Configuration")

            current_dir = current_dir.parent

    def set_default_lean_config_path(self, path: Path) -> None:
        """Overrides the default search for the path to the Lean config file.

        :param path: the path to the Lean config file to return in future calls to get_lean_config_path()
        """
        self.store_known_lean_config_path(path)
        self._default_path = path

    def get_known_lean_config_paths(self) -> List[Path]:
        """Returns the known Lean config file paths.

        :return: a list of paths to Lean config files that were used in the past
        """
        lean_config_paths = self._cache_storage.get("known-lean-config-paths", [])
        lean_config_paths = [Path(p) for p in lean_config_paths]
        lean_config_paths = [p for p in lean_config_paths if p.is_file()]

        self._cache_storage.set("known-lean-config-paths", [str(p) for p in lean_config_paths])

        return lean_config_paths

    def store_known_lean_config_path(self, path: Path) -> None:
        """Caches a path as being a known Lean configuration file path.

        :param path: the path to the Lean configuration file
        """
        try:
            lean_config = self.get_lean_config()
            if lean_config.get("organization-id") is None:
                return
        except Exception as e:
            # If we can't get the Lean config then it must be from the lean init.
            # Therefore, we can trust it's valid
            self._logger.debug(f"LeanConfigManager.store_known_lean_config_path(): Failed to get Lean config: {e}")
            pass
        lean_config_paths = set(self._cache_storage.get("known-lean-config-paths", []))
        lean_config_paths.add(str(path))
        self._cache_storage.set("known-lean-config-paths", list(lean_config_paths))

    def get_cli_root_directory(self) -> Path:
        """Returns the path to the directory containing the Lean config file.

        :return: the path to the directory containing the Lean config file
        """
        return self.get_lean_config_path().parent

    def get_data_directory(self) -> Path:
        """Returns the path to the data directory.

        :return: the path to the data directory as it is configured in the Lean config
        """
        config = self.get_lean_config()
        return self.get_cli_root_directory() / config["data-folder"]

    def set_properties(self, updates: Dict[str, Any]) -> None:
        """Sets a properties in the Lean config file.

        If a property does not exist yet it is added automatically.
        Comments in the Lean config file are preserved.

        :param updates: the key -> new value updates to apply to the current config
        """
        from json5 import dumps
        from re import sub

        config = self.get_lean_config()

        config_path = self.get_lean_config_path()
        config_text = config_path.read_text(encoding="utf-8")

        for key, value in reversed(list(updates.items())):
            json_value = dumps(value)

            # We can only use regex to set the property because converting the config back to JSON drops all comments
            if key in config:
                config_text = sub(fr'"{key}":\s*("?[^",]*"?)', f'"{key}": {json_value}', config_text)
            else:
                config_text = config_text.replace("{", f'{{\n  "{key}": {json_value},', 1)

        safe_save(path=config_path, data=config_text)

    def clean_lean_config(self, config: str) -> str:
        """Removes the properties from a Lean config file which can be set in get_complete_lean_config().

        This removes all the properties which the CLI can configure automatically based on the command that is ran.

        For example, given the following config:
        {
            // Environment docs
            "environment": "backtesting",

            // Key2 docs
            "key2": "value2"
        }

        Calling clean_lean_config(config) would return the following:
        {
            // Key2 docs
            "key2": "value2"
        }

        Because "environment" can be set automatically based on the command that is ran.

        :param config: the configuration to remove the auto-configurable keys from
        :return: the same config as passed in with the config argument, but without the auto-configurable keys
        """
        from re import split

        # The keys that we can set automatically based on the command that is ran
        keys_to_remove = ["environment",
                          "composer-dll-directory",
                          "debugging", "debugging-method",
                          "job-user-id", "api-access-token",
                          "algorithm-type-name", "algorithm-language", "algorithm-location",
                          "parameters", "intrinio-username", "intrinio-password", "ema-fast", "ema-slow"]

        # This function is implemented by doing string manipulation because the config contains comments
        # If we were to parse it as JSON, we would have to remove the comments, which we don't want to do
        sections = split(r"\n\s*\n", config)
        for key in keys_to_remove:
            sections = [section for section in sections if f"\"{key}\": " not in section]
        config = "\n\n".join(sections)

        # For some keys we should only remove the key itself, instead of their entire section
        lines = config.split("\n")
        for key in ["ib-host", "ib-port", "ib-tws-dir", "ib-version"]:
            lines = [line for line in lines if f"\"{key}\": " not in line]
        config = "\n".join(lines)

        # Instead of setting the IQFeed host we require the user to set the IQConnect location
        config = config.replace('"iqfeed-host": "127.0.0.1"',
                                '"iqfeed-iqconnect": "C:/Program Files (x86)/DTN/IQFeed/iqconnect.exe"')

        return config

    def get_complete_lean_config(self,
                                 environment: str,
                                 algorithm_file: Path,
                                 debugging_method: Optional[DebuggingMethod]) -> Dict[str, Any]:
        """Returns a complete Lean config object containing all properties needed for the engine to run.

        This retrieves the path of the config, parses the file and adds all properties removed in clean_lean_config().

        :param environment: the environment to set
        :param algorithm_file: the path to the algorithm that will be ran
        :param debugging_method: the debugging method to use, or None to disable debugging
        """
        config = self.get_lean_config()

        config["environment"] = environment
        config["close-automatically"] = True

        config["composer-dll-directory"] = "."

        if debugging_method is not None:
            config["debugging"] = True
            config["debugging-method"] = debugging_method.get_internal_name()
        else:
            config["debugging"] = False
            config["debugging-method"] = "LocalCmdline"

        # The following key -> value pairs are added to the config unless they are already set by the user
        config_defaults = {
            "job-user-id": self._cli_config_manager.user_id.get_value(default="0"),
            "api-access-token": self._cli_config_manager.api_token.get_value(default=""),
            "job-project-id": self._project_config_manager.get_local_id(algorithm_file.parent),

            "ib-host": "127.0.0.1",
            "ib-port": "4002",
            "ib-tws-dir": "/root/Jts",
            "ib-version": "985",

            "iqfeed-host": "host.docker.internal"
        }

        for key, value in config_defaults.items():
            if config.get(key, "") == "":
                config[key] = value

        if algorithm_file.name.endswith(".py"):
            config["algorithm-type-name"] = algorithm_file.name.split(".")[0]
            config["algorithm-language"] = "Python"
            config["algorithm-location"] = f"/LeanCLI/{algorithm_file.name}"
        else:
            from re import findall
            algorithm_text = algorithm_file.read_text(encoding="utf-8")
            config["algorithm-type-name"] = findall(r"class\s*([^\s:]+)\s*:\s*QCAlgorithm", algorithm_text)[0]
            config["algorithm-language"] = "CSharp"
            config["algorithm-location"] = f"{algorithm_file.parent.name}.dll"

        project_config = self._project_config_manager.get_project_config(algorithm_file.parent)
        config["parameters"] = project_config.get("parameters", {})

        # Add libraries paths to python project
        project_language = project_config.get("algorithm-language", None)
        if project_language == "Python":
            library_references = project_config.get("libraries", [])
            python_paths = config.get("python-additional-paths", [])
            python_paths.extend([(Path("/") / library["path"]).as_posix() for library in library_references])
            if len(python_paths) > 0:
                python_paths.append("/Library")
            config["python-additional-paths"] = python_paths

        # No real limit for the object store by default
        if "storage-limit-mb" not in config:
            config["storage-limit-mb"] = "9999999"
        if "storage-file-count" not in config:
            config["storage-file-count"] = "9999999"

        return config

    def configure_data_purchase_limit(self, lean_config: Dict[str, Any], data_purchase_limit: Optional[int]) -> None:
        """Updates the data purchase limit in the Lean config.

        Logs a warning if the historical data provider is not configured to download from QuantConnect.

        :param lean_config: the Lean config dict to update
        :param data_purchase_limit: the data purchase limit provided by the user, or None if no such limit was provided
        """
        if data_purchase_limit is None:
            return

        if lean_config.get("data-provider", None) != "QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider":
            self._logger.warn(
                "--data-purchase-limit is ignored because the historical data provider is not set to download from the QuantConnect API, use --download-data to set that up")
            return

        lean_config["data-purchase-limit"] = data_purchase_limit

    def get_lean_config(self) -> Dict[str, Any]:
        """Reads the Lean config into a dict.

        :return: a dict containing the contents of the Lean config file
        """
        path = self.get_lean_config_path()
        content = path.read_text(encoding="utf-8")
        return self.parse_json(content)

    def parse_json(self, content) -> Dict[str, Any]:
        try:
            from json import loads
            from re import sub

            # remove multi line or single line comments without double quotes
            config = sub(r'/\*.*?\*/|//[^\r\n"]*[\r\n]', '', content)

            # let's handle single line comments with double quotes in them
            new_config = ''
            for line in config.split('\n'):
                double_quotes_count = 0
                previous_element = ''
                for current_element in line:
                    if current_element == '/' and double_quotes_count % 2 == 0:
                        if previous_element == '/':
                            break
                    else:
                        # count not escaped double quotes
                        if current_element == '"' and previous_element != '\\':
                            double_quotes_count = double_quotes_count + 1
                        new_config += current_element
                    previous_element = current_element
            result = loads(new_config)
            return result

        except Exception as e:
            self._logger.error(str(e))

            # just in case slower fallback
            from json5 import loads
            return loads(content)
