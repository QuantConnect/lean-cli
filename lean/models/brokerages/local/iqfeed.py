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
from typing import Any, Dict

import click

from lean.click import PathParameter
from lean.components.util.logger import Logger
from lean.models.config import LeanConfigConfigurer


class IQFeedDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the IQFeed data feed."""

    def __init__(self, iqconnect: Path, username: str, password: str, product_name: str, version: str) -> None:
        self._iqconnect = iqconnect
        self._username = username
        self._password = password
        self._product_name = product_name
        self._version = version

    @classmethod
    def get_name(cls) -> str:
        return "IQFeed"

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        logger.info("The IQFeed data feed requires an IQFeed developer account and a locally installed IQFeed client.")

        default_binary = cls._get_default(lean_config, "iqfeed-iqconnect")
        if default_binary is not None:
            default_binary = Path(default_binary)
        else:
            default_binary = Path("C:/Program Files (x86)/DTN/IQFeed/iqconnect.exe")
            if not default_binary.is_file():
                default_binary = None

        iqconnect = click.prompt("IQConnect binary location",
                                 type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                                 default=default_binary)

        username = click.prompt("Username", cls._get_default(lean_config, "iqfeed-username"))
        password = logger.prompt_password("Password", cls._get_default(lean_config, "iqfeed-password"))
        product_name = click.prompt("Product id", cls._get_default(lean_config, "iqfeed-productName"))
        version = click.prompt("Product version", cls._get_default(lean_config, "iqfeed-version"))

        return IQFeedDataFeed(iqconnect, username, password, product_name, version)

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = \
            "QuantConnect.ToolBox.IQFeed.IQFeedDataQueueHandler"
        lean_config["environments"][environment_name]["history-provider"] = \
            "QuantConnect.ToolBox.IQFeed.IQFeedDataQueueHandler"

        lean_config["iqfeed-iqconnect"] = str(self._iqconnect).replace("\\", "/")
        lean_config["iqfeed-username"] = self._username
        lean_config["iqfeed-password"] = self._password
        lean_config["iqfeed-productName"] = self._product_name
        lean_config["iqfeed-version"] = self._version

        self._save_properties(lean_config, ["iqfeed-iqconnect",
                                            "iqfeed-username",
                                            "iqfeed-password",
                                            "iqfeed-productName",
                                            "iqfeed-version"])
