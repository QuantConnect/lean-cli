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
from typing import Dict

from lean.components.util.logger import Logger


class CloudBrokerage(abc.ABC):
    """The CloudBrokerage class is the base class extended for all brokerages supported in the cloud."""

    @classmethod
    @abc.abstractmethod
    def get_id(cls) -> str:
        """Returns the id of the brokerage.

        :return: the id of this brokerage as it is expected by the live/create API endpoint
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_name(cls) -> str:
        """Returns the display-friendly name of the brokerage.

        :return: the display-friendly name of this brokerage that may be shown to users
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def build(cls, logger: Logger) -> 'CloudBrokerage':
        """Builds a new instance of this class, prompting the user for input when necessary.

        :param logger: the logger to use
        :return: a CloudBrokerage instance containing all credentials needed to construct a settings dict
        """
        raise NotImplementedError()

    def get_settings(self) -> Dict[str, str]:
        """Returns all settings for this brokerage.

        :return: the settings to set in the "brokerage" property of the live/create API endpoint
        """
        settings = self._get_settings()
        settings["id"] = self.get_id()
        return settings

    @abc.abstractmethod
    def _get_settings(self) -> Dict[str, str]:
        """Returns all settings for this brokerage, except for the id.

        :return: the settings of this brokerage excluding the id
        """
        raise NotImplementedError()

    def get_price_data_handler(self) -> str:
        """Returns the price data feed handler to use.

        :return: the value to assign to the "dataHandler" property of the live/create API endpoint
        """
        return "QuantConnectHandler"
