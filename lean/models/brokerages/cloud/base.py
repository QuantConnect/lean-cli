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

import abc
from typing import Dict, Optional

from lean.components.util.logger import Logger


class CloudBrokerage(abc.ABC):
    """The CloudBrokerage class is the base class extended for all brokerages supported in the cloud."""

    def __init__(self, id: str, name: str, notes: Optional[str] = None) -> None:
        """Creates a new BaseBrokerage instance.

        :param id: the id of the brokerage
        :param name: the display-friendly name of the brokerage
        :param notes: notes which need to be shown before prompting for settings
        """
        self.id = id
        self.name = name
        self._notes = notes

    def get_settings(self, logger: Logger) -> Dict[str, str]:
        """Returns all settings for this brokerage, prompting the user for input when necessary.

        :param logger: the logger to use for printing instructions
        """
        if self._notes is not None:
            logger.info(self._notes)

        settings = self._get_settings(logger)
        settings["id"] = self.id

        return settings

    def get_price_data_handler(self) -> str:
        """Returns the price data feed handler to use."""
        return "QuantConnectHandler"

    @abc.abstractmethod
    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        """Returns the brokerage-specific settings, prompting the user for input when necessary.

        :param logger: the logger to use when prompting for passwords
        :return: a dict containing the brokerage-specific settings (all settings except for "id")
        """
        pass
