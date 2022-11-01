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

from typing import Dict, Any
from lean.models.json_module import JsonModule
from lean.models.configuration import InternalInputUserInput, TradingEnvConfiguration


class CloudBrokerage(JsonModule):
    """A JsonModule implementation for the cloud brokerages."""

    def __init__(self, json_cloud_brokerage_data: Dict[str, Any]) -> None:
        super().__init__(json_cloud_brokerage_data)

    def get_id(self) -> str:
        """Returns the id of the brokerage.
        :return: the id of this brokerage as it is expected by the live/create API endpoint
        """
        return self._id

    def _get_settings(self) -> Dict[str, str]:
        """Returns all settings for this brokerage, except for the id.
        :return: the settings of this brokerage excluding the id
        """
        settings = {}
        for config in self.get_required_configs():
            value = None
            if not config._cloud_id:
                continue
            # TODO: handle cases where tranding env config is not present, environment will still be required.
            if type(config) == TradingEnvConfiguration:
                value = "paper" if str(config).lower() in [
                    "practice", "demo", "beta", "paper"] else "live"
            elif type(config) is InternalInputUserInput:
                if not config._is_conditional:
                    value = config._value
                else:
                    for option in config._value_options:
                        if option._condition.check(self.get_config_value_from_name(option._condition._dependent_config_id)):
                            value = option._value
                            break
                    if not value:
                        options_to_log = set([(opt._condition._dependent_config_id,
                                               self.get_config_value_from_name(opt._condition._dependent_config_id))
                                              for opt in config._value_options])
                        raise ValueError(
                            f'No condition matched among present options for "{config._cloud_id}". '
                            f'Please review ' +
                            ', '.join([f'"{x[0]}"' for x in options_to_log]) +
                            f' given value{"s" if len(options_to_log) > 1 else ""} ' +
                            ', '.join([f'"{x[1]}"' for x in options_to_log]))
            else:
                value = config._value
            settings[config._cloud_id] = value
        return settings

    def get_settings(self) -> Dict[str, str]:
        """Returns all settings for this brokerage.
        :return: the settings to set in the "brokerage" property of the live/create API endpoint
        """
        settings = self._get_settings()
        if "environment" not in settings.keys():
            settings["environment"] = "live"
        settings["id"] = self.get_id()
        return settings

    def get_price_data_handler(self) -> str:
        """Returns the price data feed handler to use.
        :return: the value to assign to the "dataHandler" property of the live/create API endpoint
        """
        # TODO: Handle this case with json conditions
        if self.get_name() == "Interactive Brokers":
            return "InteractiveBrokersHandler" if self.get_config_value_from_name("ib-data-feed") else "QuantConnectHandler"
        return "QuantConnectHandler"
