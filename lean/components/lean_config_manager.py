import re
from pathlib import Path
from typing import Any, Dict, Optional

from jsoncomment import JsonComment

from lean.components.cli_config_manager import CLIConfigManager


class LeanConfigManager:
    """The LeanConfigManager class contains utilities to work with files containing LEAN engine configuration."""

    def __init__(self, cli_config_manager: CLIConfigManager, default_file_name: str) -> None:
        """Creates a new LeanConfigManager instance.

        :param cli_config_manager: the CLIConfigManager instance to use when retrieving credentials
        :param default_file_name: the default name of the file containing the Lean config
        """
        self._cli_config_manager = cli_config_manager
        self._default_file_name = default_file_name
        self._default_path = None

    def get_lean_config_path(self) -> Path:
        """Returns the path to the closest Lean config file.

        This recurses upwards in the directory tree looking for a Lean config file.
        This search can be overridden using set_default_lean_config_path().

        Raises an error if no Lean config file can be found.

        :return: the path to the closest Lean config file
        """
        if self._default_path is not None:
            return self._default_path

        # Recurse upwards in the directory tree until we find a Lean config file
        current_dir = Path.cwd()
        while True:
            target_file = current_dir / self._default_file_name
            if target_file.exists():
                return target_file

            # If the parent directory is the same as the current directory we can't go up any more
            if current_dir.parent == current_dir:
                raise RuntimeError(
                    "This command should be executed in a Lean CLI project, run `lean init` in an empty directory to create one or specify the configuration file to use with --config")

            current_dir = current_dir.parent

    def set_default_lean_config_path(self, path: Path) -> None:
        """Overrides the default search for the path to the Lean config file.

        :param path: the path to the Lean config file to return in future calls to get_lean_config_path()
        """
        self._default_path = path

    def get_data_directory(self) -> Path:
        """Returns the path to the data directory.

        :return: the path to the data directory as it is configured in the Lean config
        """
        config = self._read_lean_config()
        config_path = self.get_lean_config_path()
        return config_path.parent / config["data-folder"]

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
        # The keys that we can set automatically based on the command that is ran
        keys_to_remove = ["environment",
                          "composer-dll-directory",
                          "debugging", "debugging-method",
                          "job-user-id", "api-access-token",
                          "algorithm-type-name", "algorithm-language", "algorithm-location"]

        # This function is implemented by doing string manipulation because the config contains comments
        # If we were to parse it as JSON, we would have to remove the comments which we don't want to do
        sections = re.split(r"\n\s*\n", config)
        for key in keys_to_remove:
            sections = [section for section in sections if f"\"{key}\": " not in section]

        return "\n\n".join(sections)

    def get_complete_lean_config(self,
                                 environment: str,
                                 algorithm_file: Path,
                                 debugging_method: Optional[str]) -> Dict[str, Any]:
        """Returns a complete Lean config object containing all properties needed for the engine to run.

        This retrieves the path of the config, parses the file and adds all properties removed in clean_lean_config().

        It is assumed that the default LEAN Docker image is used and that the project containing the algorithm_file
        will be mounted in /Project.

        :param environment: the environment to set
        :param algorithm_file: the path to the algorithm that will be ran
        :param debugging_method: the debugging method to use, or None to disable debugging
        """
        config = self._read_lean_config()

        config["environment"] = environment
        config["close-automatically"] = True

        config["composer-dll-directory"] = "."

        config["debugging"] = debugging_method is not None
        config["debugging-method"] = debugging_method or "LocalCmdline"

        config["job-user-id"] = self._cli_config_manager.user_id.get_value(default="0")
        config["api-access-token"] = self._cli_config_manager.api_token.get_value(default="")

        if algorithm_file.name.endswith(".py"):
            lean_cli_project_root = self.get_lean_config_path().parent

            config["algorithm-type-name"] = algorithm_file.name.split(".")[0]
            config["algorithm-language"] = "Python"
            config["algorithm-location"] = f"/LeanCLI/{algorithm_file.relative_to(lean_cli_project_root).as_posix()}"
        else:
            algorithm_text = algorithm_file.read_text()
            config["algorithm-type-name"] = re.findall(f"class ([a-zA-Z0-9]+)", algorithm_text)[0]
            config["algorithm-language"] = "CSharp"
            config["algorithm-location"] = "QuantConnect.Algorithm.CSharp.dll"

        return config

    def _read_lean_config(self) -> Dict[str, Any]:
        """Reads the Lean config into a dict.

        :return: a dict containing the contents of the Lean config file
        """
        config_text = self.get_lean_config_path().read_text()

        # JsonComment can parse JSON with non-inline comments, so we remove the inline ones first
        config_without_inline_comments = re.sub(r",\s*//.*", ",", config_text, flags=re.MULTILINE)

        return JsonComment().loads(config_without_inline_comments)
