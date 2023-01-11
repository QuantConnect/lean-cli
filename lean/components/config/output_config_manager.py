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
from typing import List, Optional

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.storage import Storage


class OutputConfigManager:
    """The OutputConfigManager class manages the configuration of a backtest, optimization or live trading session."""

    def __init__(self, lean_config_manager: LeanConfigManager) -> None:
        """Creates a new OutputConfigManager instance.

        :param lean_config_manager: the LeanConfigManager to get the CLI root directory from
        """
        self._lean_config_manager = lean_config_manager

    def get_output_config(self, output_directory: Path) -> Storage:
        """Returns a Storage instance to get/set the configuration of the contents of an output directory.

        :param output_directory: the path to the project to retrieve the configuration of
        :return: the Storage instance containing the configuration of the given backtest/optimization/live trading
        """
        return Storage(str(output_directory / "config"))

    def get_backtest_id(self, backtest_directory: Path) -> int:
        """Returns the id of a backtest.

        :param backtest_directory: the path to the backtest to retrieve the id of
        :return: the id of the given backtest
        """
        return self._get_id(backtest_directory, 1)

    def get_backtest_name(self, backtest_directory: Path) -> str:
        """Returns the name of a backtest.

        :param backtest_directory: the path to the backtest to retrieve the id of
        :return: the name of the given backtest
        """
        config = self.get_output_config(backtest_directory)

        if config.has("backtest-name"):
            return config.get("backtest-name")

        raise ValueError("Backtest name is not set")

    def get_container_name(self, backtest_directory: Path) -> str:
        """Returns the name of a the docker container lean is running in.

        :param backtest_directory: the path to the backtest to retrieve the id of
        :return: the name of the docker container lean is running in.
        """
        config = self.get_output_config(backtest_directory)

        if config.has("container"):
            return config.get("container")

        raise ValueError("Container name is not set")

    def get_backtest_by_id(self, backtest_id: int, root_directory: Optional[Path] = None) -> Path:
        """Finds the directory of a backtest by its id.

        :param backtest_id: the id of the backtest to get the directory of
        :param root_directory: the directory to search from, defaults to the `lean init` directory
        :return: the output directory of the backtest with the given id
        """
        return self._get_by_id("Backtest", backtest_id, ["backtests/*", "optimizations/*/*"], root_directory)

    def get_optimization_id(self, optimization_directory: Path) -> int:
        """Returns the id of an optimization.

        :param optimization_directory: the path to the optimization to retrieve the id of
        :return: the id of the given optimization
        """
        return self._get_id(optimization_directory, 2)

    def get_optimization_by_id(self, optimization_id: int, root_directory: Optional[Path] = None) -> Path:
        """Finds the directory of an optimization by its id.

        :param optimization_id: the id of the optimization to get the directory of
        :param root_directory: the directory to search from, defaults to the `lean init` directory
        :return: the output directory of the optimization with the given id
        """
        return self._get_by_id("Optimization", optimization_id, ["optimizations/*"], root_directory)

    def get_live_deployment_id(self, live_deployment_directory: Path) -> int:
        """Returns the id of a live deployment.

        :param live_deployment_directory: the path to the live deployment to retrieve the id of
        :return: the id of the given optimization
        """
        return self._get_id(live_deployment_directory, 3)

    def get_live_deployment_by_id(self, live_deployment_id: int, root_directory: Optional[Path] = None) -> Path:
        """Finds the directory of a live deployment by its id.

        :param live_deployment_id: the id of the live deployment to get the directory of
        :param root_directory: the directory to search from, defaults to the `lean init` directory
        :return: the output directory of the live deployment with the given id
        """
        return self._get_by_id("Live deployment", live_deployment_id, ["live/*"], root_directory)

    def get_latest_output_directory(self, environment: str) -> Optional[Path]:
        """Finds the latest output directory for the given environment (live or backtests)

        :param environment: The environment to find the latest output directory for (live or backtests)
        :return: The path to the latest output directory for the given environment
        :raises RuntimeError: If no output directory is found for the given environment
        """
        output_json_files = sorted(Path.cwd().rglob(f"{environment}/*/*.json"),
                                   key=lambda d: d.stat().st_mtime,
                                   reverse=True)

        if len(output_json_files) == 0:
            return None

        return output_json_files[0].parent

    def get_output_id(self, output_directory: Path) -> Optional[int]:
        """Returns the id of an output, regardless of whether it is a backtest or a live deployment.

        It will return None if the output directory does not contain any output with an existing id.

        :param output_directory: the path to the output to retrieve the id of
        :return: the id of the given output
        """
        output_id = self._get_id(output_directory, 9)

        if str(output_id)[0] == '9':
            # no existing id was found
            return None

        return output_id

    def _get_id(self, output_directory: Path, prefix: int) -> int:
        config = self.get_output_config(output_directory)

        if config.has("id"):
            return config.get("id")

        from random import randint
        new_id = int(str(prefix) + str(randint(100_000_000, 999_999_999)))
        config.set("id", new_id)

        return new_id

    def _get_by_id(self, label: str, object_id: int, patterns: List[str], root_directory: Optional[Path]) -> Path:
        if root_directory is None:
            root_directory = self._lean_config_manager.get_cli_root_directory()

        for pattern in patterns:
            for directory in root_directory.rglob(pattern):
                if not directory.is_dir():
                    continue

                config = self.get_output_config(directory)
                if config.get("id", None) == object_id:
                    return directory

        raise ValueError(f"{label} with id '{object_id}' does not exist")
