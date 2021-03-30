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

from lean.components.config.storage import Storage
from lean.models.errors import MoreInfoError
from lean.models.options import ChoiceOption, Option


class CLIConfigManager:
    """The CLIConfigManager class contains all configurable CLI options."""

    def __init__(self, general_storage: Storage, credentials_storage: Storage) -> None:
        """Creates a new CLIConfigManager instance.

        :param general_storage: the Storage instance for general, non-sensitive options
        :param credentials_storage: the Storage instance for credentials
        """
        self.user_id = Option("user-id",
                              "The user id used when making authenticated requests to the QuantConnect API.",
                              True,
                              credentials_storage)

        self.api_token = Option("api-token",
                                "The API token used when making authenticated requests to the QuantConnect API.",
                                True,
                                credentials_storage)

        self.default_language = ChoiceOption("default-language",
                                             "The default language used when creating new projects.",
                                             ["python", "csharp"],
                                             False,
                                             general_storage)

        self.all_options = [
            self.user_id,
            self.api_token,
            self.default_language
        ]

    def get_option_by_key(self, key: str) -> Option:
        """Returns the option matching the given key.

        If no option with the given key exists, an error is raised.

        :param key: the key to look for
        :return: the option having a key equal to the given key
        """
        option = next((x for x in self.all_options if x.key == key), None)

        if option is None:
            raise MoreInfoError(f"There doesn't exist an option with key '{key}'",
                                "https://www.quantconnect.com/docs/v2/lean-cli/api-reference/lean-config-set#02-Description")

        return option
